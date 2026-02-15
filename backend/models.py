from pydantic import BaseModel


class ConversationSummary(BaseModel):
    id: int
    title: str
    source: str
    created_at: str


class Message(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    timestamp: str


class ConversationDetail(BaseModel):
    id: int
    title: str
    source: str
    created_at: str
    updated_at: str
    messages: list[Message]


class SearchResult(BaseModel):
    conversation_id: int
    message_id: int
    snippet: str
    timestamp: str
