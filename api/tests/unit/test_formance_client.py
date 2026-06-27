"""Unit tests for Formance Ledger v2 HTTP client adapter."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.formance_client import FormanceClient, FORNANCE_URL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return FormanceClient(base_url="http://formance:3068")


@pytest.fixture
def sample_postings():
    return [
        {"source": "world", "destination": "cash", "amount": 10.00, "asset": "GBP/2"},
        {"source": "revenue", "destination": "world", "amount": 10.00, "asset": "GBP/2"},
    ]


# ---------------------------------------------------------------------------
# create_transaction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_transaction_success(client, sample_postings):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"txid": 42, "postings": sample_postings}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.create_transaction(
            ledger="main",
            postings=sample_postings,
            reference="JE-2026-0001",
            timestamp="2026-06-27T12:00:00Z",
            metadata={"desc": "Test"},
        )

    assert result["txid"] == 42
    mock_client.__aenter__.return_value.post.assert_called_once()
    call_args = mock_client.__aenter__.return_value.post.call_args
    assert call_args[0][0] == "http://formance:3068/main/transactions"
    body = call_args[1]["json"]
    assert body["postings"] == sample_postings
    assert body["reference"] == "JE-2026-0001"
    assert body["timestamp"] == "2026-06-27T12:00:00Z"
    assert body["metadata"] == {"desc": "Test"}


@pytest.mark.asyncio
async def test_create_transaction_minimal(client, sample_postings):
    """Create transaction with only required fields (no ref, timestamp, metadata)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"txid": 1}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.create_transaction(
            ledger="main",
            postings=sample_postings,
        )

    assert result["txid"] == 1
    body = mock_client.__aenter__.return_value.post.call_args[1]["json"]
    assert "reference" not in body
    assert "timestamp" not in body
    assert "metadata" not in body


@pytest.mark.asyncio
async def test_create_transaction_http_error(client, sample_postings):
    import httpx

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    mock_client.__aenter__.return_value.post.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_transaction(
                ledger="main",
                postings=sample_postings,
            )


# ---------------------------------------------------------------------------
# get_transaction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_transaction_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"txid": 42, "postings": []}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.get_transaction("main", 42)

    assert result["txid"] == 42
    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/main/transactions/42"
    )


@pytest.mark.asyncio
async def test_get_transaction_not_found(client):
    import httpx

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_transaction("main", 99999)


# ---------------------------------------------------------------------------
# list_transactions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_transactions_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cursor": {"hasMore": False},
        "data": [{"txid": 1}, {"txid": 2}],
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.list_transactions("main", page_size=10)

    assert len(result["data"]) == 2
    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/main/transactions",
        params={"pageSize": 10},
    )


@pytest.mark.asyncio
async def test_list_transactions_with_cursor(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"cursor": {"hasMore": True}, "data": []}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        await client.list_transactions("main", page_size=50, after="cursor123")

    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/main/transactions",
        params={"pageSize": 50, "after": "cursor123"},
    )


# ---------------------------------------------------------------------------
# get_balances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_balances_all(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"balances": ...}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.get_balances("main")

    assert "data" in result
    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/main/balances",
        params={},
    )


@pytest.mark.asyncio
async def test_get_balances_filtered(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"balances": ...}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        await client.get_balances("main", address="users:001")

    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/main/balances",
        params={"address": "users:001"},
    )


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.health_check()

    assert result is True
    mock_client.__aenter__.return_value.get.assert_called_once_with(
        "http://formance:3068/_info"
    )


@pytest.mark.asyncio
async def test_health_check_unhealthy(client):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.side_effect = Exception("Connection refused")

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_health_check_500_error(client):
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("src.services.formance_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.health_check()

    assert result is False


# ---------------------------------------------------------------------------
# default base_url
# ---------------------------------------------------------------------------


def test_default_base_url():
    """Client without explicit base_url should use FORNANCE_URL env var."""
    client = FormanceClient()
    assert client.base_url == "http://localhost:3068"


def test_custom_base_url():
    client = FormanceClient(base_url="http://custom:9999")
    assert client.base_url == "http://custom:9999"


def test_base_url_trailing_slash():
    client = FormanceClient(base_url="http://formance:3068/")
    assert client.base_url == "http://formance:3068"
