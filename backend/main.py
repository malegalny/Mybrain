from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from db import get_db, init_db
from models import ConversationDetail, ConversationSummary, Message, SearchResult
from parsers import parse_chat_export

app = FastAPI(title="AI Chat Archive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/api/upload")
async def upload_chat_exports(files: list[UploadFile] = File(...)):
    created_ids: list[int] = []

    with get_db() as conn:
        for upload in files:
            if not upload.filename or not upload.filename.lower().endswith(".json"):
                raise HTTPException(status_code=400, detail="Only JSON files are supported")

            raw = await upload.read()
            try:
                parsed = parse_chat_export(raw, fallback_title=Path(upload.filename).stem)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Failed to parse {upload.filename}: {exc}") from exc

            now = datetime.utcnow().isoformat()
            cursor = conn.execute(
                """
                INSERT INTO conversations (title, source, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (parsed.title, upload.filename, now, now),
            )
            conversation_id = cursor.lastrowid
            created_ids.append(conversation_id)

            conn.executemany(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (conversation_id, message.role, message.content, message.timestamp)
                    for message in parsed.messages
                ],
            )

    return {"created_conversation_ids": created_ids, "count": len(created_ids)}


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, source, created_at
            FROM conversations
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [ConversationSummary(**dict(row)) for row in rows]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int):
    with get_db() as conn:
        convo = conn.execute(
            """
            SELECT id, title, source, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = conn.execute(
            """
            SELECT id, conversation_id, role, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC, id ASC
            """,
            (conversation_id,),
        ).fetchall()

    return ConversationDetail(
        **dict(convo),
        messages=[Message(**dict(message)) for message in messages],
    )


@app.get("/api/search", response_model=list[SearchResult])
def search_messages(query: str = Query(..., min_length=1)):
    like_query = f"%{query}%"

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT conversation_id, id AS message_id, content AS snippet, timestamp
            FROM messages
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT 200
            """,
            (like_query,),
        ).fetchall()

    return [SearchResult(**dict(row)) for row in rows]
