"""
Assumption: uploaded JSON is either:
1) {"title": "Optional Title", "messages": [{"role": "user", "content": "...", "timestamp": "..."}]}
or 2) [{"role": "user", "content": "...", "timestamp": "..."}] as a top-level list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ParsedMessage:
    role: str
    content: str
    timestamp: str


@dataclass
class ParsedConversation:
    title: str
    messages: list[ParsedMessage]


def parse_chat_export(raw_bytes: bytes, fallback_title: str) -> ParsedConversation:
    payload = json.loads(raw_bytes.decode("utf-8"))

    if isinstance(payload, dict):
        title = str(payload.get("title") or fallback_title)
        messages = payload.get("messages", [])
    elif isinstance(payload, list):
        title = fallback_title
        messages = payload
    else:
        raise ValueError("Unsupported JSON format")

    normalized: list[ParsedMessage] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "unknown"))
        content = str(item.get("content", "")).strip()
        timestamp = str(item.get("timestamp") or datetime.utcnow().isoformat())
        if content:
            normalized.append(ParsedMessage(role=role, content=content, timestamp=timestamp))

    if not normalized:
        raise ValueError("No valid messages found")

    return ParsedConversation(title=title, messages=normalized)
