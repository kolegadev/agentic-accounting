"""FastAPI router for LLM Chat Interface — WebSocket + REST skill endpoints."""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.services.chat_service import ChatService
from src.services.skill_registry import SkillRegistry
from src.validators.chat import (
    ErrorMessage,
    ToolCall,
    ToolResult,
    UserMessage,
)

router = APIRouter(prefix="/api/v1", tags=["Chat"])

_chat_service = ChatService()
_registry = SkillRegistry()


# ---------------------------------------------------------------------------
# WebSocket /ws/chat/{session_id}
# ---------------------------------------------------------------------------
@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for multi-turn LLM chat."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                err = ErrorMessage(
                    session_id=session_id,
                    code="INVALID_JSON",
                    message="Could not parse message as JSON.",
                )
                await websocket.send_text(err.model_dump_json())
                continue

            msg_type = data.get("type", "")
            content = data.get("content", "")

            if not content or msg_type != "user_message":
                err = ErrorMessage(
                    session_id=session_id,
                    code="BAD_REQUEST",
                    message="Expected a 'user_message' with non-empty 'content'.",
                )
                await websocket.send_text(err.model_dump_json())
                continue

            # Process the message through the chat pipeline
            result = await _chat_service.process_message(session_id, content)

            # Send tool call
            tool_call = ToolCall(
                session_id=session_id,
                skill_id=result["tool_call"]["skill_id"],
                params=result["tool_call"]["params"],
                confidence=result["tool_call"]["confidence"],
            )
            await websocket.send_text(tool_call.model_dump_json())

            # Send tool result (simulated)
            tool_result = ToolResult(
                session_id=session_id,
                tool_call_id=tool_call.tool_call_id,
                success=True,
                result={
                    "response": result["message"]["text"],
                    "persona": result["message"]["persona"],
                    "skill": result["tool_call"]["skill"]["name"] if result["tool_call"].get("skill") else result["tool_call"]["skill_id"],
                },
            )
            await websocket.send_text(tool_result.model_dump_json())

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# GET /skills — list all skills
# ---------------------------------------------------------------------------
class SkillListResponse(BaseModel):
    skills: list[dict[str, Any]]
    total: int


@router.get(
    "/skills",
    response_model=SkillListResponse,
    summary="List all registered skills",
)
async def list_skills(category: Optional[str] = None) -> SkillListResponse:
    """Return all skills, optionally filtered by category."""
    skills = _registry.list_skills(category)
    return SkillListResponse(skills=skills, total=len(skills))


# ---------------------------------------------------------------------------
# GET /skills/{skill_id} — skill detail
# ---------------------------------------------------------------------------
@router.get(
    "/skills/{skill_id}",
    summary="Get skill detail",
)
async def get_skill(skill_id: str) -> dict[str, Any]:
    """Return a single skill definition by ID."""
    skill = _registry.get_skill(skill_id)
    if skill is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return skill


# ---------------------------------------------------------------------------
# POST /chat/message — REST endpoint for chat messages
# ---------------------------------------------------------------------------
class ChatMessageRequest(BaseModel):
    session_id: str
    message: str
    persona: str = "professional"


class ChatMessageResponse(BaseModel):
    session_id: str
    message: dict[str, Any]
    tool_call: dict[str, Any]


@router.post(
    "/chat/message",
    response_model=ChatMessageResponse,
    summary="Process a chat message via REST (fallback for WS-unavailable clients)",
)
async def chat_message(body: ChatMessageRequest) -> ChatMessageResponse:
    """Process a chat message through the same pipeline as the WebSocket endpoint.

    This is the fallback REST endpoint used by the Chat UI when WebSocket
    bridging is unavailable.  It returns the full pipeline result including the
    formatted response and tool-call metadata.
    """
    result = await _chat_service.process_message(body.session_id, body.message)
    return ChatMessageResponse(
        session_id=result["session_id"],
        message=result["message"],
        tool_call=result["tool_call"],
    )


# ---------------------------------------------------------------------------
# POST /skills/reload — reload registry from YAML
# ---------------------------------------------------------------------------
class ReloadResponse(BaseModel):
    skills: list[dict[str, Any]]
    total: int
    message: str


@router.post(
    "/skills/reload",
    response_model=ReloadResponse,
    summary="Reload skill registry from YAML",
)
async def reload_skills() -> ReloadResponse:
    """Force a reload of the skill registry from the YAML file on disk."""
    skills = _registry.reload()
    return ReloadResponse(
        skills=skills,
        total=len(skills),
        message=f"Reloaded {len(skills)} skills from registry.yaml",
    )
