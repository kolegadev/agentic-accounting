"""Phase 2 instrumentation — structured contract-check logging.

Adds correlation_id-aware JSON logging at all instrumentation targets.
Imports as: from src.services.instrument import log_event
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("accounting-api.instrument")


class InstrumentLog:
    """Structured JSON logger for Phase 2 contract checks."""

    def __init__(self) -> None:
        self._current_correlation_id: str | None = None

    def set_correlation_id(self, cid: str) -> None:
        self._current_correlation_id = cid

    def new_correlation_id(self) -> str:
        cid = str(uuid.uuid4())
        self._current_correlation_id = cid
        return cid

    @property
    def correlation_id(self) -> str:
        return self._current_correlation_id or "no-correlation-id"

    def event(
        self,
        module: str,
        function: str,
        event: str,
        state_snapshot: dict[str, Any] | None = None,
        error: str | None = None,
        contract: str | None = None,
        contract_held: bool | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "correlation_id": self.correlation_id,
            "module": module,
            "function": function,
            "event": event,
        }
        if state_snapshot is not None:
            entry["state_snapshot"] = state_snapshot
        if error is not None:
            entry["error"] = error
        if contract is not None:
            entry["contract"] = contract
            entry["contract_held"] = contract_held
        logger.warning("INSTRUMENT %s", json.dumps(entry, default=str))


_instrument = InstrumentLog()


def log_event(
    module: str,
    function: str,
    event: str,
    state_snapshot: dict[str, Any] | None = None,
    error: str | None = None,
    contract: str | None = None,
    contract_held: bool | None = None,
) -> None:
    _instrument.event(module, function, event, state_snapshot, error, contract, contract_held)


def set_correlation_id(cid: str) -> None:
    _instrument.set_correlation_id(cid)


def new_correlation_id() -> str:
    return _instrument.new_correlation_id()


def get_correlation_id() -> str:
    return _instrument.correlation_id
