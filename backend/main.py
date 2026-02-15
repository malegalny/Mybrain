from datetime import datetime
from io import BytesIO
import mimetypes
from pathlib import Path, PurePosixPath
import zipfile

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import MEDIA_DIR, get_db, init_db
from models import Attachment, ConversationDetail, ConversationSummary, Message, SearchResult
from parsers import parse_chat_export, parse_chatgpt_conversations
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

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


@app.on_event("startup")
def startup() -> None:
    init_db()


def _safe_media_name(file_name: str) -> str:
    return PurePosixPath(file_name).name or "attachment.bin"


def _is_binary_file(path: str, file_bytes: bytes) -> bool:
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        if mime_type.startswith("text/") or mime_type in {
            "application/json",
            "application/xml",
            "application/javascript",
        }:
            return False
        return True

    chunk = file_bytes[:1024]
    return b"\0" in chunk


def _extract_binary_files(raw_zip: bytes, source_name: str) -> dict[str, dict[str, str | None]]:
    extracted: dict[str, dict[str, str | None]] = {}

    with zipfile.ZipFile(BytesIO(raw_zip)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue

            name = info.filename
            if PurePosixPath(name).name == "conversations.json":
                continue

            data = archive.read(info)
            if not _is_binary_file(name, data):
                continue

            safe_name = _safe_media_name(name)
            output_name = f"{Path(source_name).stem}_{safe_name}"
            output_path = MEDIA_DIR / output_name

            counter = 1
            while output_path.exists():
                output_name = f"{Path(source_name).stem}_{counter}_{safe_name}"
                output_path = MEDIA_DIR / output_name
                counter += 1

            output_path.write_bytes(data)
            mime_type, _ = mimetypes.guess_type(output_path.name)

            normalized_path = str(PurePosixPath("media") / output_path.name)
            record = {
                "file_name": safe_name,
                "local_path": normalized_path,
                "mime_type": mime_type,
            }

            extracted[safe_name.lower()] = record
            extracted[output_path.name.lower()] = record

    return extracted


def _insert_simple_json(conn, upload_name: str, raw: bytes, created_ids: list[int]) -> None:
    parsed = parse_chat_export(raw, fallback_title=Path(upload_name).stem)

    cursor = conn.execute(
        """
        INSERT INTO conversations (title, source, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (parsed.title, upload_name, parsed.created_at, parsed.updated_at),
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


def _insert_zip_export(conn, upload_name: str, raw: bytes, created_ids: list[int]) -> None:
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        conversations_member = next(
            (name for name in archive.namelist() if PurePosixPath(name).name == "conversations.json"),
            None,
        )
        if not conversations_member:
            raise ValueError("ZIP export is missing conversations.json")

        conversations_raw = archive.read(conversations_member)

    media_index = _extract_binary_files(raw, upload_name)
    parsed_conversations = parse_chatgpt_conversations(conversations_raw)

    for parsed in parsed_conversations:
        convo_cursor = conn.execute(
            """
            INSERT INTO conversations (title, source, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (parsed.title, upload_name, parsed.created_at, parsed.updated_at),
        )
        conversation_id = convo_cursor.lastrowid
        created_ids.append(conversation_id)

        external_to_message_id: dict[str, int] = {}
        for message in parsed.messages:
            message_cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, message.role, message.content, message.timestamp),
            )
            if message.external_id:
                external_to_message_id[message.external_id] = message_cursor.lastrowid

        now = datetime.utcnow().isoformat()
        for ref in parsed.attachment_refs:
            if not ref.file_name:
                continue

            media = media_index.get(ref.file_name.lower())
            if not media and ref.file_id:
                media = media_index.get(ref.file_id.lower())
            if not media:
                continue

            conn.execute(
                """
                INSERT INTO attachments (
                    conversation_id, message_id, file_id, file_name, mime_type, local_path, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    external_to_message_id.get(ref.message_id or ""),
                    ref.file_id,
                    str(media["file_name"]),
                    ref.mime_type or media["mime_type"],
                    str(media["local_path"]),
                    now,
                ),
            )


@app.post("/api/upload")
async def upload_chat_exports(files: list[UploadFile] = File(...)):
    created_ids: list[int] = []

    with get_db() as conn:
        for upload in files:
            if not upload.filename:
                raise HTTPException(status_code=400, detail="Uploaded file is missing a filename")

            file_name = upload.filename
            raw = await upload.read()

            try:
                if file_name.lower().endswith(".json"):
                    _insert_simple_json(conn, file_name, raw, created_ids)
                elif file_name.lower().endswith(".zip"):
                    _insert_zip_export(conn, file_name, raw, created_ids)
                else:
                    raise HTTPException(status_code=400, detail="Only JSON and ZIP files are supported")
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Failed to parse {file_name}: {exc}") from exc

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


@app.get("/api/conversations/{conversation_id}/attachments", response_model=list[Attachment])
def get_attachments(conversation_id: int):
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Conversation not found")

        rows = conn.execute(
            """
            SELECT id, conversation_id, message_id, file_id, file_name, mime_type, local_path, created_at
            FROM attachments
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()

    return [Attachment(**dict(row)) for row in rows]


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
