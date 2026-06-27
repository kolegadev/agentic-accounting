"""Pydantic schemas for WebSocket chat messages."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class UserMessage(BaseModel):
    """Incoming message from the user via WebSocket."""

    type: Literal["user_message"] = "user_message"
    session_id: str
    content: str = Field(..., min_length=1, max_length=4000)
    timestamp: Optional[str] = None


class StreamToken(BaseModel):
    """Streaming token for progressive response delivery."""

    type: Literal["stream_start", "stream_token", "stream_end"]
    session_id: str
    content: str = ""
    token: Optional[str] = None


class ConfirmationRequest(BaseModel):
    """Server asks user to confirm a potentially destructive action."""

    type: Literal["confirmation_request"] = "confirmation_request"
    session_id: str
    confirmation_id: str
    message: str
    action: str  # e.g. "undo", "delete", "archive"
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorMessage(BaseModel):
    """Error payload sent to the client."""

    type: Literal["error"] = "error"
    session_id: str
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ToolCall(BaseModel):
    """Server-initiated tool call that the LLM wants to execute."""

    type: Literal["tool_call"] = "tool_call"
    session_id: str
    tool_call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ToolResult(BaseModel):
    """Result of a tool call, sent back to the client."""

    type: Literal["tool_result"] = "tool_result"
    session_id: str
    tool_call_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
