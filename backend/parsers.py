"""
Assumptions:
- Simple JSON uploads are either {"title": ..., "messages": [...]} or a top-level list of messages.
- ChatGPT ZIP uploads include a conversations.json file following the mapping/current_node graph format.
Assumption: uploaded JSON is either:
1) {"title": "Optional Title", "messages": [{"role": "user", "content": "...", "timestamp": "..."}]}
or 2) [{"role": "user", "content": "...", "timestamp": "..."}] as a top-level list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any


VALID_ROLES = {"user", "assistant", "system"}


@dataclass
class ParsedAttachmentRef:
    message_id: str | None
    file_id: str | None
    file_name: str | None
    mime_type: str | None
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ParsedMessage:
    role: str
    content: str
    timestamp: str
    external_id: str | None = None


@dataclass
class ParsedConversation:
    title: str
    created_at: str
    updated_at: str
    messages: list[ParsedMessage]
    attachment_refs: list[ParsedAttachmentRef] = field(default_factory=list)



def _iso_or_now(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value).isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return datetime.utcnow().isoformat()
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

    now = datetime.utcnow().isoformat()
    return ParsedConversation(title=title, created_at=now, updated_at=now, messages=normalized)


def _extract_text_content(content: dict[str, Any]) -> str:
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, str):
            stripped = part.strip()
            if stripped:
                text_parts.append(stripped)
        elif isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    return "\n".join(text_parts).strip()


def _extract_attachment_refs(message: dict[str, Any], node_id: str) -> list[ParsedAttachmentRef]:
    refs: list[ParsedAttachmentRef] = []
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        return refs

    attachments = metadata.get("attachments")
    if not isinstance(attachments, list):
        return refs

    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        refs.append(
            ParsedAttachmentRef(
                message_id=node_id,
                file_id=str(attachment.get("file_id") or attachment.get("id") or "") or None,
                file_name=str(attachment.get("name") or attachment.get("file_name") or "") or None,
                mime_type=str(attachment.get("mime_type") or attachment.get("content_type") or "") or None,
            )
        )

    return refs


def parse_chatgpt_conversations(raw_bytes: bytes) -> list[ParsedConversation]:
    payload = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("conversations.json must contain a list")

    parsed_conversations: list[ParsedConversation] = []

    for conversation in payload:
        if not isinstance(conversation, dict):
            continue

        mapping = conversation.get("mapping")
        current_node = conversation.get("current_node")
        if not isinstance(mapping, dict) or not isinstance(current_node, str):
            continue

        ordered_node_ids: list[str] = []
        cursor: str | None = current_node
        seen: set[str] = set()
        while cursor and cursor not in seen:
            seen.add(cursor)
            ordered_node_ids.append(cursor)
            node = mapping.get(cursor)
            if not isinstance(node, dict):
                break
            parent = node.get("parent")
            cursor = parent if isinstance(parent, str) else None

        ordered_node_ids.reverse()

        messages: list[ParsedMessage] = []
        refs: list[ParsedAttachmentRef] = []

        for node_id in ordered_node_ids:
            node = mapping.get(node_id)
            if not isinstance(node, dict):
                continue

            message = node.get("message")
            if not isinstance(message, dict):
                continue

            author = message.get("author")
            role = author.get("role") if isinstance(author, dict) else None
            if role not in VALID_ROLES:
                continue

            content = message.get("content")
            if not isinstance(content, dict):
                continue

            text_content = _extract_text_content(content)
            if not text_content:
                continue

            messages.append(
                ParsedMessage(
                    role=role,
                    content=text_content,
                    timestamp=_iso_or_now(message.get("create_time") or conversation.get("create_time")),
                    external_id=node_id,
                )
            )

            refs.extend(_extract_attachment_refs(message, node_id))

        if not messages:
            continue

        parsed_conversations.append(
            ParsedConversation(
                title=str(conversation.get("title") or "Untitled conversation"),
                created_at=_iso_or_now(conversation.get("create_time")),
                updated_at=_iso_or_now(conversation.get("update_time") or conversation.get("create_time")),
                messages=messages,
                attachment_refs=refs,
            )
        )

    return parsed_conversations
    return ParsedConversation(title=title, messages=normalized)
