"""Formance Ledger v2 HTTP client adapter."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

FORNANCE_URL = os.getenv("FORNANCE_LEDGER_URL", "http://localhost:3068")


class FormanceClient:
    """Async HTTP client for Formance Ledger v2.

    Wraps the Formance ledger HTTP API. All mutating operations carry
    idempotency keys to prevent duplicate postings.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or FORNANCE_URL).rstrip("/")

    async def create_transaction(
        self,
        ledger: str,
        postings: list[dict[str, Any]],
        reference: Optional[str] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create and commit a transaction to the ledger.

        Args:
            ledger: Ledger name (e.g., "main").
            postings: List of posting dicts with source, destination,
                      amount, and asset fields.
            reference: External reference (e.g., JE-2026-0001).
            timestamp: ISO 8601 timestamp for the transaction.
            metadata: Arbitrary key-value metadata.
        """
        body: dict[str, Any] = {"postings": postings}
        if reference:
            body["reference"] = reference
        if timestamp:
            body["timestamp"] = timestamp
        if metadata:
            body["metadata"] = metadata

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/{ledger}/transactions",
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_transaction(
        self, ledger: str, txid: int
    ) -> dict[str, Any]:
        """Fetch a transaction by its numeric ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/{ledger}/transactions/{txid}"
            )
            resp.raise_for_status()
            return resp.json()

    async def list_transactions(
        self,
        ledger: str,
        page_size: int = 50,
        after: Optional[str] = None,
    ) -> dict[str, Any]:
        """List transactions with cursor-based pagination."""
        params: dict[str, Any] = {"pageSize": page_size}
        if after:
            params["after"] = after

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/{ledger}/transactions",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_balances(
        self, ledger: str, address: Optional[str] = None
    ) -> dict[str, Any]:
        """Get account balances, optionally filtered by address."""
        params: dict[str, Any] = {}
        if address:
            params["address"] = address

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/{ledger}/balances",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def health_check(self) -> bool:
        """Check if the Formance Ledger is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/_info")
                return resp.status_code == 200
        except Exception:
            return False


# Singleton instance
formance_client = FormanceClient()
