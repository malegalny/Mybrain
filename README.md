# ai-chat-archive

Minimal full-stack app for uploading, browsing, and searching AI chat exports.

## Project structure

```text
ai-chat-archive/
├── backend/
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   ├── parsers.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── styles.css
│       └── components/
│           ├── ConversationDetail.tsx
│           ├── ConversationList.tsx
│           ├── SearchPanel.tsx
│           └── types.ts
├── chat_archive.db (created at runtime)
└── media/ (created at runtime for ZIP attachments)
└── chat_archive.db (created at runtime)
```

## Backend setup (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend setup (React + Vite)

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Upload API

- Endpoint: `POST /api/upload`
- Content-Type: `multipart/form-data`
- Field name: `files`
- Accepts one or more `.json` files and `.zip` files.
- ZIP uploads should be full OpenAI ChatGPT data exports that include `conversations.json`.
- Accepts one or more `.json` files.

## Example JSON upload format

```json
{
  "title": "Example Conversation",
  "messages": [
    {
      "role": "user",
      "content": "Hello, assistant.",
      "timestamp": "2025-01-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2025-01-01T10:00:03Z"
    }
  ]
}
```

Also supported:

```json
[
  {
    "role": "user",
    "content": "Top-level list format",
    "timestamp": "2025-01-01T10:00:00Z"
  }
]
```

## Available endpoints

- `POST /api/upload`
- `GET /api/conversations`
- `GET /api/conversations/{id}`
- `GET /api/conversations/{id}/attachments`
- `GET /api/search?query=keyword`
- Static media: `GET /media/{file}`
- `GET /api/search?query=keyword`
