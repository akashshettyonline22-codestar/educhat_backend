from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    USER = "user"
    BOT = "bot"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ENDED = "ended"


# REQUEST MODELS (for API input)

class ChatSessionCreate(BaseModel):
    textbook_id: str
    session_name: Optional[str] = None


class ChatMessageSend(BaseModel):
    textbook_id: str
    question: str
    session_id: Optional[str] = None


# RESPONSE MODELS (for API output)

class ChatSessionResponse(BaseModel):
    session_id: str
    textbook_id: str
    session_name: Optional[str] = None
    created_at: datetime
    last_active: datetime
    message_count: int
    status: SessionStatus
    preview_message: Optional[str] = None


class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    message_type: MessageType
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatConversationResponse(BaseModel):
    success: bool
    session_id: str
    messages: List[ChatMessageResponse]
    total_messages: int
    session_info: Optional[Dict[str, Any]] = None


class ChatBotResponse(BaseModel):
    success: bool
    session_id: str
    user_message_id: str
    bot_message_id: str
    question: str
    answer: str
    answer_type: str
    context_used: bool
    out_of_context: bool
    educational_image: Optional[str] = None
    reference_pages: List[int] = []
    page_image_used: bool = False
    conversation_length: int = 0
    error: Optional[str] = None


class ChatSessionListResponse(BaseModel):
    success: bool
    sessions: List[ChatSessionResponse]
    total: int
