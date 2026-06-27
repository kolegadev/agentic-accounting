"""Unit tests for ChatService — state management, response formatting, personas."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.services.chat_service import ChatService


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Return a mocked aioredis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def chat_service(mock_redis: AsyncMock) -> ChatService:
    """Return a ChatService with mocked Redis."""
    svc = ChatService()
    svc._redis = mock_redis
    return svc


# ---------------------------------------------------------------------------
# Conversation state
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_conversation_state_new_session(chat_service: ChatService, mock_redis: AsyncMock) -> None:
    """New session should return default state."""
    mock_redis.get.return_value = None
    state = await chat_service.get_conversation_state("session-1")
    assert state["session_id"] == "session-1"
    assert state["persona"] == "professional"
    assert state["history"] == []
    assert state["context"] == {}


@pytest.mark.asyncio
async def test_get_conversation_state_existing(chat_service: ChatService, mock_redis: AsyncMock) -> None:
    """Existing session should restore saved state."""
    saved = {
        "session_id": "session-2",
        "persona": "friendly",
        "history": [{"role": "user", "content": "hello"}],
        "context": {"contact_id": "abc"},
    }
    mock_redis.get.return_value = json.dumps(saved)
    state = await chat_service.get_conversation_state("session-2")
    assert state["persona"] == "friendly"
    assert len(state["history"]) == 1


@pytest.mark.asyncio
async def test_save_conversation_state(chat_service: ChatService, mock_redis: AsyncMock) -> None:
    """Should persist state to Redis with TTL."""
    state = {"session_id": "s", "persona": "minimal", "history": [], "context": {}}
    await chat_service.save_conversation_state("s", state)
    mock_redis.set.assert_called_once()


# ---------------------------------------------------------------------------
# process_message pipeline
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_process_message_routes_and_formats(chat_service: ChatService, mock_redis: AsyncMock) -> None:
    """Full pipeline: route → format → save."""
    mock_redis.get.return_value = json.dumps({
        "session_id": "s1",
        "persona": "professional",
        "history": [],
        "context": {},
    })

    result = await chat_service.process_message("s1", "Paid £50 for office supplies at Tesco")
    assert result["session_id"] == "s1"
    assert result["tool_call"]["skill_id"] == "gl.record_expense"
    assert result["tool_call"]["params"].get("amount") == 5000
    assert "text" in result["message"]
    # History should have 2 entries (user + assistant)
    assert len(result["history"]) == 2
    mock_redis.set.assert_called()


@pytest.mark.asyncio
async def test_process_message_with_context(chat_service: ChatService, mock_redis: AsyncMock) -> None:
    """Context from previous turns should be injected."""
    mock_redis.get.return_value = json.dumps({
        "session_id": "s2",
        "persona": "friendly",
        "history": [],
        "context": {"contact_id": "abc-123"},
    })

    result = await chat_service.process_message("s2", "Create invoice for this client")
    assert result["tool_call"]["skill_id"] == "invoice.create"
    # contact_id should be injected
    assert result["tool_call"]["params"].get("contact_id") == "abc-123"


# ---------------------------------------------------------------------------
# Persona formatting
# ---------------------------------------------------------------------------
class TestFormatResponse:
    """Tests for persona-specific response formatting."""

    def setup_method(self) -> None:
        self.svc = ChatService()

    def test_professional_persona(self) -> None:
        result = {"skill_id": "gl.record_expense", "params": {"description": "Office supplies", "amount": 5000},
                   "skill": {"name": "Record Expense"}}
        formatted = self.svc.format_response(result, "professional")
        assert "Action:" in formatted["text"]
        assert "£50.00" in formatted["text"]
        assert formatted["persona"] == "professional"
        assert "further details" in formatted["text"]

    def test_friendly_persona(self) -> None:
        result = {"skill_id": "gl.record_income", "params": {"description": "Consulting fee", "amount": 120000},
                   "skill": {"name": "Record Income"}}
        formatted = self.svc.format_response(result, "friendly")
        assert "help you" in formatted["text"]
        assert "£1,200.00" in formatted["text"]
        assert formatted["persona"] == "friendly"

    def test_minimal_persona(self) -> None:
        result = {"skill_id": "coa.list", "params": {},
                   "skill": {"name": "List Chart of Accounts"}}
        formatted = self.svc.format_response(result, "minimal")
        assert formatted["text"].startswith("•")
        assert "List Chart of Accounts" in formatted["text"]
        assert formatted["persona"] == "minimal"
        # Minimal persona should NOT have prefix/suffix fluff
        assert "further details" not in formatted["text"]
