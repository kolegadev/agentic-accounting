"""Intent Router — rule-based NL → (skill_id, params, confidence) for MVP."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from src.services.skill_registry import SkillRegistry


# ---------------------------------------------------------------------------
# lightweight date helpers — avoids heavy pendulum/dateutil deps at MVP
# ---------------------------------------------------------------------------
_TODAY: date = date.today()
_CURRENT_YEAR: int = _TODAY.year

# Map of UK financial year start: 6 April → year(N)
_FY_START_MONTH = 4
_FY_START_DAY = 6


def _fy_start_for(year: int) -> date:
    return date(year, _FY_START_MONTH, _FY_START_DAY)


def _fy_for_date(d: date) -> tuple[date, date]:
    """Return (start, end) of the UK financial year containing *d*."""
    fy_start = _fy_start_for(d.year if (d.month, d.day) >= (_FY_START_MONTH, _FY_START_DAY) else d.year - 1)
    fy_end = _fy_start_for(fy_start.year + 1) - timedelta(days=1)
    return fy_start, fy_end


def parse_natural_date(text: str) -> Optional[date]:
    """Try to parse a natural-language date expression.

    Supported:
    - "today", "yesterday", "tomorrow"
    - "last month" → 1st of previous month
    - "this month" → 1st of current month
    - "Q1 2025", "Q2", "Q3 2025", "Q4 2025"
    - "this financial year", "last financial year"
    - ISO dates "2025-06-27", "2025/06/27"
    """
    t = text.strip().lower()

    # absolute keywords
    if t in ("today",):
        return _TODAY
    if t in ("yesterday",):
        return _TODAY - timedelta(days=1)
    if t in ("tomorrow",):
        return _TODAY + timedelta(days=1)
    if t == "last month":
        if _TODAY.month == 1:
            return date(_TODAY.year - 1, 12, 1)
        return date(_TODAY.year, _TODAY.month - 1, 1)
    if t == "this month":
        return date(_TODAY.year, _TODAY.month, 1)

    # quarters
    qm = re.match(r"q([1-4])\s*(\d{4})?", t)
    if qm:
        quarter = int(qm.group(1))
        year = int(qm.group(2)) if qm.group(2) else _CURRENT_YEAR
        month = (quarter - 1) * 3 + 1
        return date(year, month, 1)

    # financial years
    if t in ("this financial year", "this fy"):
        return _fy_for_date(_TODAY)[0]
    if t in ("last financial year", "last fy"):
        prev = _fy_for_date(_TODAY)[0] - timedelta(days=1)
        return _fy_for_date(prev)[0]

    # ISO / slash dates
    for fmt in (r"\d{4}-\d{2}-\d{2}", r"\d{4}/\d{2}/\d{2}", r"\d{2}/\d{2}/\d{4}"):
        m = re.search(fmt, text)
        if m:
            ds = m.group(0).replace("/", "-")
            parts = ds.split("-")
            if len(parts[0]) == 4:
                y, mo, d = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                d, mo, y = int(parts[0]), int(parts[1]), int(parts[2])
            try:
                return date(y, mo, d)
            except ValueError:
                return None

    return None


# ---------------------------------------------------------------------------
# Amount extraction
# ---------------------------------------------------------------------------
_AMOUNT_PATTERN = re.compile(r"£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)", re.IGNORECASE)


def extract_amount(text: str) -> Optional[int]:
    """Extract the first currency amount in pounds and return pence."""
    m = _AMOUNT_PATTERN.search(text)
    if m:
        raw = m.group(1).replace(",", "")
        try:
            return int(round(float(raw) * 100))
        except (ValueError, OverflowError):
            pass
    # also try bare number with £ sign elsewhere
    m2 = re.search(r"(\d+(?:\.\d{1,2})?)\s*(?:pounds|quid|£)", text, re.IGNORECASE)
    if m2:
        try:
            return int(round(float(m2.group(1)) * 100))
        except (ValueError, OverflowError):
            pass
    return None


# ---------------------------------------------------------------------------
# Keyword → skill mapping
# ---------------------------------------------------------------------------
_KEYWORD_ROUTES: list[tuple[re.Pattern, str]] = [
    # Order matters: more specific patterns first
    (re.compile(r"\bchart\s*of\s*accounts\b", re.IGNORECASE), "coa.list"),
    (re.compile(r"\badd\b.*\baccount\b", re.IGNORECASE), "coa.add_account"),
    (re.compile(r"\badd\s+(?:new\s+)?(?:contact|supplier|customer)\b", re.IGNORECASE), "contact.create"),
    (re.compile(r"\bcreate\s+invoice\b", re.IGNORECASE), "invoice.create"),
    (re.compile(r"\bsend\s+invoice\b", re.IGNORECASE), "invoice.send"),
    (re.compile(r"\bmark\s+.*\bpaid\b", re.IGNORECASE), "invoice.mark_paid"),
    (re.compile(r"\bcredit\s*note\b", re.IGNORECASE), "invoice.credit_note"),
    (re.compile(r"\boverdue\b", re.IGNORECASE), "invoice.overdue"),
    (re.compile(r"\bvat\s*return\b", re.IGNORECASE), "vat.preview_return"),
    (re.compile(r"\bprofit\s*(?:and|&)\s*loss|p&l|p\s*&\s*l\b", re.IGNORECASE), "report.run"),
    (re.compile(r"\bbalance\s*sheet\b", re.IGNORECASE), "report.run"),
    (re.compile(r"\btrial\s*balance\b", re.IGNORECASE), "report.run"),
    (re.compile(r"\baged\s*(?:receivables|payables|debtors|creditors)\b", re.IGNORECASE), "report.run"),
    (re.compile(r"\bjournal\s*entry\b", re.IGNORECASE), "gl.journal_entry"),
    (re.compile(r"\bclient\s*paid|customer\s*paid\b", re.IGNORECASE), "gl.record_income"),
    (re.compile(r"\b(?:received|got paid|income)\b", re.IGNORECASE), "gl.record_income"),
    (re.compile(r"\b(?:paid|bought|spent|purchased|paid for)\b", re.IGNORECASE), "gl.record_expense"),
    (re.compile(r"\btransfer\b", re.IGNORECASE), "gl.record_transfer"),
    (re.compile(r"\bbank\s*statement\b", re.IGNORECASE), "bank.import_csv"),
    (re.compile(r"\bimport\s*(?:csv|ofx|statement)\b", re.IGNORECASE), "bank.import_csv"),
    (re.compile(r"\bcategor(?:ize|y|ise)\b", re.IGNORECASE), "bank.categorize"),
    (re.compile(r"\breconcil(?:e|iation)\b", re.IGNORECASE), "recon.start"),
    (re.compile(r"\breport\b", re.IGNORECASE), "report.run"),
    (re.compile(r"\bvat\b", re.IGNORECASE), "vat.preview_return"),
    (re.compile(r"\binvoice|bill\b", re.IGNORECASE), "invoice.create"),
    (re.compile(r"\badd\s+(?:a\s+)?(?:new\s+)?contact|supplier|customer\b", re.IGNORECASE), "contact.create"),
    (re.compile(r"\bundo|reverse|delete\b", re.IGNORECASE), "gl.undo_transaction"),
    (re.compile(r"\baccounts?\s*(?:list|show|display)\b", re.IGNORECASE), "coa.list"),
    (re.compile(r"\b(?:contacts?|suppliers?|customers?)\b", re.IGNORECASE), "contact.list"),
    (re.compile(r"\btransactions?\b", re.IGNORECASE), "gl.list_transactions"),
]


_REPORT_TYPE_MAP: dict[str, str] = {
    "profit": "profit_and_loss",
    "p&l": "profit_and_loss",
    "p & l": "profit_and_loss",
    "profit and loss": "profit_and_loss",
    "balance sheet": "balance_sheet",
    "balance": "balance_sheet",
    "trial balance": "trial_balance",
    "aged receivables": "aged_receivables",
    "aged payables": "aged_payables",
    "debtors": "aged_receivables",
    "creditors": "aged_payables",
}


class IntentRouter:
    """Rule-based intent router for MVP.

    Maps a user message + optional context to an (skill_id, params_dict, confidence)
    tuple.  Confidence is 0.0–1.0.
    """

    def __init__(self) -> None:
        self._registry = SkillRegistry()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def route(self, user_message: str, context: Optional[dict[str, Any]] = None) -> tuple[str, dict[str, Any], float]:
        """Route a user message to a skill.

        Returns (skill_id, params_dict, confidence).
        """
        # 1. keyword match
        skill_id, conf = self._match_keywords(user_message)
        if skill_id is None:
            return ("coa.list", {}, 0.1)  # fallback

        # 2. extract entities
        params: dict[str, Any] = {}

        amount = extract_amount(user_message)
        if amount is not None:
            params["amount"] = amount

        # try to find a date phrase in the message
        date_patterns = [
            r"((?:last|this)\s+month)",
            r"(q[1-4]\s*\d{4}?)",
            r"((?:this|last)\s+financial\s+year)",
            r"(yesterday|today|tomorrow)",
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{2}/\d{2}/\d{4})",
        ]
        for pat in date_patterns:
            dm = re.search(pat, user_message, re.IGNORECASE)
            if dm:
                parsed = parse_natural_date(dm.group(1))
                if parsed:
                    params["date"] = parsed.isoformat()
                break

        # description: grab first sentence or meaningful text
        desc = re.sub(r"(paid|bought|received|show|list|run|create|invoice)", "", user_message, flags=re.IGNORECASE).strip()
        if desc:
            params["description"] = desc[:200]

        # report type detection
        msg_lower = user_message.lower()
        for keyword, rtype in _REPORT_TYPE_MAP.items():
            if keyword in msg_lower and skill_id == "report.run":
                params["report_type"] = rtype
                break

        # vat → set date range defaults if missing
        if skill_id == "vat.preview_return" and "start_date" not in params:
            fy_start, fy_end = _fy_for_date(_TODAY)
            params["start_date"] = fy_start.isoformat()
            params["end_date"] = fy_end.isoformat()

        # Inject context values if provided
        if context:
            for key in ("contact_id", "bank_account_id", "reconciliation_id", "account_id"):
                if key in context and key not in params:
                    params[key] = context[key]

        return (skill_id, params, conf)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    def _match_keywords(self, text: str) -> tuple[Optional[str], float]:
        """Return (skill_id, confidence) from keyword matching."""
        for pattern, skill_id in _KEYWORD_ROUTES:
            if pattern.search(text):
                # higher confidence for longer patterns
                conf = min(1.0, 0.5 + 0.05 * len(pattern.pattern))
                return (skill_id, conf)
        return (None, 0.0)
