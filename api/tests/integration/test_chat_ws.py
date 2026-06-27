"""Integration tests for WebSocket chat endpoint and REST skill endpoints."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from src.index import app
from src.services.chat_service import ChatService
from src.services.skill_registry import SkillRegistry

client = TestClient(app)


# ---------------------------------------------------------------------------
# REST skill endpoints
# ---------------------------------------------------------------------------
class TestSkillEndpoints:
    """Tests for GET/POST /api/v1/skills endpoints."""

    def test_list_skills(self) -> None:
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        assert data["total"] >= 25

    def test_list_skills_by_category(self) -> None:
        resp = client.get("/api/v1/skills?category=GL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 4
        for s in data["skills"]:
            assert s["category"] == "GL"

    def test_list_skills_invalid_category(self) -> None:
        resp = client.get("/api/v1/skills?category=nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_get_skill_found(self) -> None:
        resp = client.get("/api/v1/skills/gl.record_expense")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "gl.record_expense"
        assert data["category"] == "GL"

    def test_get_skill_not_found(self) -> None:
        resp = client.get("/api/v1/skills/nonexistent.skill")
        assert resp.status_code == 404

    def test_reload_skills(self) -> None:
        resp = client.post("/api/v1/skills/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 25
        assert "Reloaded" in data["message"]


# ---------------------------------------------------------------------------
# WebSocket tests (using TestClient WebSocket support)
# ---------------------------------------------------------------------------
class TestWebSocketChat:
    """Tests for the WebSocket /ws/chat/{session_id} endpoint."""

    def test_websocket_connect_and_message(self) -> None:
        """Basic WebSocket connection and message exchange."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-1") as ws:
            # Send a user message
            ws.send_json({
                "type": "user_message",
                "content": "Paid £50 for office supplies",
                "session_id": "test-session-1",
            })

            # Expect tool_call response
            data1 = ws.receive_json()
            assert data1["type"] == "tool_call"
            assert data1["skill_id"] == "gl.record_expense"

            # Expect tool_result response
            data2 = ws.receive_json()
            assert data2["type"] == "tool_result"
            assert data2["success"] is True
            assert "response" in data2["result"]

    def test_websocket_invalid_json(self) -> None:
        """Invalid JSON should return an error."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-2") as ws:
            ws.send_text("not json at all")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "INVALID_JSON"

    def test_websocket_missing_content(self) -> None:
        """Message without content should return error."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-3") as ws:
            ws.send_json({"type": "user_message", "session_id": "s3"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "BAD_REQUEST"

    def test_websocket_wrong_type(self) -> None:
        """Non-user_message type should return error."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-4") as ws:
            ws.send_json({"type": "wrong_type", "content": "hello"})
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_websocket_multi_turn(self) -> None:
        """Multi-turn conversation should preserve context."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-5") as ws:
            # Turn 1: record expense
            ws.send_json({
                "type": "user_message",
                "content": "Paid £100 for software",
                "session_id": "test-session-5",
            })
            _ = ws.receive_json()  # tool_call
            res1 = ws.receive_json()
            assert res1["type"] == "tool_result"
            assert res1["success"] is True

            # Turn 2: ask for VAT return
            ws.send_json({
                "type": "user_message",
                "content": "Show my VAT return",
                "session_id": "test-session-5",
            })
            tc = ws.receive_json()
            assert tc["skill_id"] == "vat.preview_return"

    def test_websocket_invoice_keyword(self) -> None:
        """'invoice' keyword should route to invoice.create."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-6") as ws:
            ws.send_json({
                "type": "user_message",
                "content": "Create an invoice for Acme Ltd",
                "session_id": "test-session-6",
            })
            data = ws.receive_json()
            assert data["skill_id"] == "invoice.create"

    def test_websocket_report_keyword(self) -> None:
        """'P&L' keyword should route to report.run."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-7") as ws:
            ws.send_json({
                "type": "user_message",
                "content": "Run a P&L report",
                "session_id": "test-session-7",
            })
            data = ws.receive_json()
            assert data["skill_id"] == "report.run"
            assert data["params"].get("report_type") == "profit_and_loss"

    def test_websocket_multiple_turns(self) -> None:
        """Multiple turns across different intents."""
        with client.websocket_connect("/api/v1/ws/chat/test-session-8") as ws:
            # Turn 1
            ws.send_json({
                "type": "user_message",
                "content": "Show all customers",
                "session_id": "test-session-8",
            })
            tc1 = ws.receive_json()
            assert tc1["skill_id"] == "contact.list"
            ws.receive_json()  # consume tool_result

            # Turn 2
            ws.send_json({
                "type": "user_message",
                "content": "Start reconciliation",
                "session_id": "test-session-8",
            })
            tc2 = ws.receive_json()
            assert tc2["skill_id"] == "recon.start"


# ---------------------------------------------------------------------------
# Integration: skill registry loaded
# ---------------------------------------------------------------------------
class TestSkillRegistryIntegration:
    """Verify the skill registry is correctly loaded."""

    def test_all_categories_present(self) -> None:
        reg = SkillRegistry()
        skills = reg.load_registry()
        categories = {s.get("category") for s in skills}
        expected = {"COA", "GL", "Contact", "Bank", "Reconciliation", "Invoice", "VAT", "Report"}
        assert categories == expected

    def test_all_skill_ids_loadable(self) -> None:
        reg = SkillRegistry()
        expected_ids = [
            "coa.list", "coa.add_account", "coa.edit_account", "coa.set_vat_rate",
            "gl.record_expense", "gl.record_income", "gl.record_transfer", "gl.journal_entry",
            "gl.list_transactions", "gl.transaction_detail", "gl.undo_transaction",
            "contact.create", "contact.edit", "contact.list", "contact.detail", "contact.archive",
            "bank.import_csv", "bank.import_ofx", "bank.list_accounts", "bank.add_account",
            "bank.transactions", "bank.categorize",
            "recon.start", "recon.match", "recon.create_and_match", "recon.status", "recon.report",
            "invoice.create", "invoice.send", "invoice.list", "invoice.mark_paid",
            "invoice.credit_note", "invoice.overdue",
            "vat.preview_return", "vat.transaction_detail", "vat.adjustment", "vat.audit_trail",
            "report.run", "report.list", "report.schedule",
        ]
        for sid in expected_ids:
            skill = reg.get_skill(sid)
            assert skill is not None, f"Skill '{sid}' not found in registry"
            assert skill["id"] == sid

    def test_reload_preserves_skills(self) -> None:
        reg = SkillRegistry()
        before = len(reg.load_registry())
        after = len(reg.reload())
        assert before == after
