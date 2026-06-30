"""Chat UI server for Agentic Accounting — serves the HTML frontend and bridges
WebSocket connections to the accounting API backend.

Pattern: Follows the Git-Maid pattern — single HTML file, FastAPI + WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from pathlib import Path

import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

API_BASE_URL = os.getenv("API_BASE_URL", "http://accounting-api:8000")

app = FastAPI(title="Agentic Accounting Chat UI", version="0.2.0")

UI_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Mock company data — matches the new UI design's 3 companies.
# Used as fallback when the accounting API backend is unreachable.
# ---------------------------------------------------------------------------
MOCK_COMPANIES = [
    {
        "id": "brightwork",
        "name": "Brightwork Studio Ltd",
        "initials": "BS",
        "swatch": "#5eead4",
        "type": "Ltd Company",
        "region": "UK",
        "currency": "£",
        "standard": "FRS 105",
        "vat_status": "VAT registered",
        "vat_number": "GB 412 7785 09",
        "period": "VAT Q1 · Apr–Jun 2026",
        "balanced": True,
        "last_activity": "£500 office supplies",
        "address": "Unit 4, Gasworks, Bristol BS1 6XN",
        "year_end": "31 March",
        "coa_template": "UK Limited Company",
        "bank_balance": 2458042,
        "income": 4230000,
        "expenses": 821000,
        "credit_card": 194055,
        "ar": 675000,
        "ar_count": 3,
        "ap": 231000,
        "ap_count": 2,
    },
    {
        "id": "marcus",
        "name": "Marcus Reed",
        "initials": "MR",
        "swatch": "#7fb4ff",
        "type": "Sole Trader",
        "region": "UK",
        "currency": "£",
        "standard": "Cash basis",
        "vat_status": "Not VAT registered",
        "vat_number": "—",
        "period": "Tax year 2025/26",
        "balanced": True,
        "last_activity": "£90 fuel",
        "address": "12 Elm Row, Leeds LS6 2TX",
        "year_end": "5 April",
        "coa_template": "UK Sole Trader",
        "bank_balance": 812010,
        "income": 1540000,
        "expenses": 345000,
        "credit_card": 62000,
        "ar": 120000,
        "ar_count": 1,
        "ap": 43000,
        "ap_count": 1,
    },
    {
        "id": "northgate",
        "name": "Northgate Properties",
        "initials": "NP",
        "swatch": "#f0b86e",
        "type": "LLC",
        "region": "US",
        "currency": "$",
        "standard": "US GAAP",
        "vat_status": "Sales tax",
        "vat_number": "EIN 84-3920117",
        "period": "FY2026 · Q2",
        "balanced": False,
        "last_activity": "$2,400 repairs",
        "address": "88 Harbor Dr, Austin TX 78701",
        "year_end": "31 December",
        "coa_template": "US Real Estate",
        "bank_balance": 9642000,
        "income": 12890000,
        "expenses": 3120000,
        "credit_card": 540000,
        "ar": 1830000,
        "ar_count": 5,
        "ap": 912000,
        "ap_count": 4,
    },
]


def _get_mock_company(company_id: str | None = None) -> dict:
    """Return a specific company from the persistent store, falling back to built-in defaults."""
    cid = company_id or "brightwork"
    # Search persistent store first
    for c in _company_store:
        if c["id"] == cid:
            return c
    # Then built-in defaults
    for c in MOCK_COMPANIES:
        if c["id"] == cid:
            return c
    # Last resort: first available company
    if _company_store:
        return _company_store[0]
    return MOCK_COMPANIES[0]


def _fmt_pence(pence: int, currency: str) -> str:
    """Format pence amount to display string."""
    units = pence / 100
    return f"{currency}{units:,.2f}"


def _build_report_from_company(key: str, c: dict) -> dict | None:
    """Build a report response from mock company data (same logic as JS buildReport)."""
    f = lambda p: _fmt_pence(p, c["currency"])
    income = c["income"]
    expenses = c["expenses"]
    bank = c["bank_balance"]
    ar = c["ar"]
    ap = c["ap"]
    cc = c["credit_card"]
    fixed = int(income * 0.22)
    total_assets = bank + ar + fixed
    total_liab = cc + ap
    equity = total_assets - total_liab
    net = income - expenses

    reports = {
        "bs": {
            "icon": "⚖️", "title": "Balance Sheet",
            "sub": f'{c["name"]} · as at period end',
            "note": f'Assets = Liabilities + Equity. Both sides equal {f(total_assets)}, so the sheet balances.',
            "columns": [{"label": "", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": [
                {"type": "section_head", "label": "Assets"},
                {"type": "line", "label": "Bank Account", "values": [f(bank)]},
                {"type": "line", "label": "Accounts Receivable", "values": [f(ar)]},
                {"type": "line", "label": "Fixed Assets", "values": [f(fixed)]},
                {"type": "total", "label": "Total Assets", "values": [f(total_assets)]},
                {"type": "section_head", "label": "Liabilities"},
                {"type": "line", "label": "Credit Card", "values": [f(cc)]},
                {"type": "line", "label": "Accounts Payable", "values": [f(ap)]},
                {"type": "total", "label": "Total Liabilities", "values": [f(total_liab)]},
                {"type": "section_head", "label": "Equity"},
                {"type": "line", "label": "Retained Earnings", "values": [f(equity)]},
                {"type": "total", "label": "Total Equity", "values": [f(equity)]},
            ],
        },
        "pl": {
            "icon": "📈", "title": "Profit & Loss",
            "sub": f'{c["name"]} · {c["period"]}',
            "note": f'Net profit is income minus expenses for the period.',
            "columns": [{"label": "", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": [
                {"type": "section_head", "label": "Income"},
                {"type": "line", "label": "Sales", "values": [f(int(income * 0.94))]},
                {"type": "line", "label": "Other income", "values": [f(int(income * 0.06))]},
                {"type": "total", "label": "Total income", "values": [f(income)]},
                {"type": "section_head", "label": "Expenses"},
                {"type": "line", "label": "Staff & subcontract", "values": [f(int(expenses * 0.45))]},
                {"type": "line", "label": "Office & supplies", "values": [f(int(expenses * 0.25))]},
                {"type": "line", "label": "Software & tools", "values": [f(int(expenses * 0.18))]},
                {"type": "line", "label": "Other", "values": [f(int(expenses * 0.12))]},
                {"type": "total", "label": "Total expenses", "values": [f(expenses)]},
                {"type": "total", "label": "Net profit", "values": [f(net)]},
            ],
        },
        "tb": {
            "icon": "📊", "title": "Trial Balance",
            "sub": f'{c["name"]} · all accounts',
            "note": "Total debits equal total credits — the fundamental check that your ledger is internally consistent.",
            "columns": [{"label": "Account", "align": "left"}, {"label": "Debit", "align": "right"}, {"label": "Credit", "align": "right"}],
            "sections": [
                {"type": "line", "label": "Bank Account", "values": [f(bank), ""]},
                {"type": "line", "label": "Accounts Receivable", "values": [f(ar), ""]},
                {"type": "line", "label": "Fixed Assets", "values": [f(fixed), ""]},
                {"type": "line", "label": "Expenses", "values": [f(expenses), ""]},
                {"type": "line", "label": "Credit Card", "values": ["", f(cc)]},
                {"type": "line", "label": "Accounts Payable", "values": ["", f(ap)]},
                {"type": "line", "label": "Sales / Income", "values": ["", f(income)]},
                {"type": "line", "label": "Retained Earnings", "values": ["", f(int(equity * 0.4))]},
                {"type": "total", "label": "Totals", "values": [f(bank + ar + fixed + expenses), f(bank + ar + fixed + expenses)]},
            ],
        },
        "vat": {
            "icon": "🧾", "title": "VAT Return (9-box)" if c["currency"] == "£" else "Sales Tax Summary",
            "sub": f'{c["name"]} · {c["period"]}',
            "note": "Box 5 is what you pay HMRC." if c["currency"] == "£" else "US company — sales tax shown instead of UK VAT.",
            "columns": [{"label": "Box" if c["currency"] == "£" else "", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": (
                [
                    {"type": "line", "label": "1 · VAT due on sales", "values": [f(int(income * 0.2))]},
                    {"type": "line", "label": "2 · VAT due on EC acquisitions", "values": [f(0)]},
                    {"type": "line", "label": "3 · Total VAT due", "values": [f(int(income * 0.2))]},
                    {"type": "line", "label": "4 · VAT reclaimed on purchases", "values": [f(int(expenses * 0.2))]},
                    {"type": "total", "label": "5 · Net VAT to pay", "values": [f(int(income * 0.2) - int(expenses * 0.2))]},
                    {"type": "line", "label": "6 · Total sales ex VAT", "values": [f(income)]},
                    {"type": "line", "label": "7 · Total purchases ex VAT", "values": [f(expenses)]},
                    {"type": "line", "label": "8 · EC supplies", "values": [f(0)]},
                    {"type": "line", "label": "9 · EC acquisitions", "values": [f(0)]},
                ] if c["currency"] == "£" else [
                    {"type": "line", "label": "Taxable sales", "values": [f(income)]},
                    {"type": "line", "label": "Sales tax collected (8.25%)", "values": [f(int(income * 0.0825))]},
                    {"type": "line", "label": "Tax paid on purchases", "values": [f(int(expenses * 0.0825))]},
                    {"type": "total", "label": "Net tax due", "values": [f(int(income * 0.0825) - int(expenses * 0.0825))]},
                ]
            ),
        },
        "cf": {
            "icon": "💧", "title": "Cash Flow",
            "sub": f'{c["name"]} · {c["period"]}',
            "note": "Cash flow shows actual money moving — distinct from profit.",
            "columns": [{"label": "", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": [
                {"type": "section_head", "label": "Operating"},
                {"type": "line", "label": "Net profit", "values": [f(net)]},
                {"type": "line", "label": "Change in receivables", "values": [f"({f(int(ar * 0.3))})"]},
                {"type": "line", "label": "Change in payables", "values": [f(int(ap * 0.2))]},
                {"type": "total", "label": "Cash from operations", "values": [f(net - int(ar * 0.3) + int(ap * 0.2))]},
                {"type": "section_head", "label": "Investing"},
                {"type": "line", "label": "Equipment purchased", "values": [f"({f(int(income * 0.05))})"]},
                {"type": "section_head", "label": "Financing"},
                {"type": "line", "label": "Card repayments", "values": [f"({f(int(cc * 0.4))})"]},
                {"type": "total", "label": "Net cash movement", "values": [f(net - int(ar * 0.3) + int(ap * 0.2) - int(income * 0.05) - int(cc * 0.4))]},
            ],
        },
        "ar": {
            "icon": "⏳", "title": "Aged Receivables",
            "sub": f'{c["name"]} · {c["ar_count"]} open invoices',
            "note": "Money customers owe you. Chase the 60+ bucket first.",
            "columns": [{"label": "Age", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": [
                {"type": "line", "label": "Current (not due)", "values": [f(int(ar * 0.5))]},
                {"type": "line", "label": "1–30 days", "values": [f(int(ar * 0.3))]},
                {"type": "line", "label": "31–60 days", "values": [f(int(ar * 0.15))]},
                {"type": "line", "label": "60+ days overdue", "values": [f(int(ar * 0.05))]},
                {"type": "total", "label": "Total owed to you", "values": [f(ar)]},
            ],
        },
        "ap": {
            "icon": "📥", "title": "Aged Payables",
            "sub": f'{c["name"]} · {c["ap_count"]} open bills',
            "note": "Bills you owe suppliers. Pay the oldest first.",
            "columns": [{"label": "Age", "align": "left"}, {"label": "Amount", "align": "right"}],
            "sections": [
                {"type": "line", "label": "Current (not due)", "values": [f(int(ap * 0.6))]},
                {"type": "line", "label": "1–30 days", "values": [f(int(ap * 0.25))]},
                {"type": "line", "label": "31–60 days", "values": [f(int(ap * 0.1))]},
                {"type": "line", "label": "60+ days overdue", "values": [f(int(ap * 0.05))]},
                {"type": "total", "label": "Total you owe", "values": [f(ap)]},
            ],
        },
    }
    return reports.get(key)


@app.get("/")
async def root():
    """Serve the chat UI from disk or embedded fallback."""
    index_path = UI_DIR / "index.html"
    content = index_path.read_text() if index_path.exists() else _get_ui_html()
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return HTMLResponse(content=content, headers=headers)


@app.get("/api/health")
async def health():
    """Check if the accounting API backend is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            return {
                "status": "ok",
                "backend": "connected" if resp.status_code == 200 else "unhealthy",
            }
    except Exception:
        return {"status": "ok", "backend": "unreachable"}


@app.get("/api/account")
async def account():
    """Return backend connection info."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            return {
                "backend_configured": resp.status_code == 200,
                "api_base_url": API_BASE_URL,
            }
    except Exception:
        return {"backend_configured": False, "api_base_url": API_BASE_URL}



# ---------------------------------------------------------------------------
# LLM Configuration — stored in memory, initialized from env
# ---------------------------------------------------------------------------
LLM_CONFIG = {
    "api_url": os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions"),
    "model": os.getenv("LLM_MODEL", "deepseek-v4-pro"),
    "api_key": os.getenv("LLM_API_KEY", ""),
}


@app.get("/api/llm-config")
async def get_llm_config():
    """Return current LLM configuration (key masked)."""
    return {
        "api_url": LLM_CONFIG["api_url"],
        "model": LLM_CONFIG["model"],
        "api_key": LLM_CONFIG["api_key"][:8] + "***" if LLM_CONFIG["api_key"] else "",
        "has_key": bool(LLM_CONFIG["api_key"]),
    }


@app.post("/api/llm-config")
async def update_llm_config(data: dict):
    """Update LLM configuration. Persists to env for the API bridge."""
    global LLM_CONFIG
    for field in ("api_url", "model", "api_key"):
        if field in data and data[field]:
            LLM_CONFIG[field] = data[field]
    # Push to accounting API so the LLM chat can use the new key
    if LLM_CONFIG["api_key"]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{API_BASE_URL}/api/v1/chat/llm-config",
                    json={
                        "api_url": LLM_CONFIG["api_url"],
                        "model": LLM_CONFIG["model"],
                        "api_key": LLM_CONFIG["api_key"],
                    },
                )
        except Exception:
            pass
    return {"status": "ok", "config": {k: v for k, v in LLM_CONFIG.items() if k != "api_key"}}

@app.post("/api/settings")
async def update_settings(data: dict):
    """Update API backend URL (runtime override)."""
    global API_BASE_URL
    new_url = (data.get("api_base_url") or "").strip()
    if new_url:
        API_BASE_URL = new_url
        return {"status": "ok", "updated": ["api_base_url"], "message": "Settings saved. Reconnect to use new URL."}
    return {"status": "ok", "updated": [], "message": "No settings changed."}


# ---------------------------------------------------------------------------
# Company persistence — stored in memory, backed by JSON file on disk
# ---------------------------------------------------------------------------
_COMPANIES_FILE = UI_DIR / "data" / "companies.json"
_company_store: list[dict] = []


def _load_companies() -> list[dict]:
    """Load companies from disk, falling back to built-in defaults."""
    global _company_store
    if _COMPANIES_FILE.exists():
        try:
            _company_store = json.loads(_COMPANIES_FILE.read_text())
            if _company_store:
                return _company_store
        except (json.JSONDecodeError, OSError):
            pass
    _company_store = [dict(c) for c in MOCK_COMPANIES]
    _save_companies()
    return _company_store


def _save_companies() -> None:
    """Persist current company store to disk."""
    try:
        _COMPANIES_FILE.write_text(json.dumps(_company_store, indent=2))
    except OSError:
        pass


# Load on startup
UI_DIR.joinpath("data").mkdir(exist_ok=True)
_company_store = _load_companies()


@app.get("/api/companies")
async def list_companies():
    """Return all companies in the persistent store."""
    return {
        "companies": [
            {
                "id": c["id"],
                "name": c["name"],
                "initials": c["initials"],
                "swatch": c["swatch"],
                "type": c["type"],
                "region": c["region"],
                "currency": c["currency"],
                "vat_status": c.get("vat_status", c.get("vat", "")),
            }
            for c in _company_store
        ],
        "source": "local",
    }


@app.post("/api/companies")
async def create_company(data: dict):
    """Create a new company. Persists to disk."""
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "Company name is required."}
    ctype = data.get("type", "Ltd Company")
    region = data.get("region", "UK")
    currency = "£" if region == "UK" else "$"
    swatches = ["#5eead4", "#7fb4ff", "#f0b86e", "#f49b9b", "#6ee7a8", "#a78bfa"]
    new_id = f"co-{uuid.uuid4().hex[:8]}"
    initials = "".join(w[0] for w in name.split())[:3].upper()
    company = {
        "id": new_id,
        "name": name,
        "initials": initials,
        "swatch": swatches[len(_company_store) % len(swatches)],
        "type": ctype,
        "region": region,
        "currency": currency,
        "standard": "FRS 105" if region == "UK" else "US GAAP",
        "vat_status": "VAT registered" if region == "UK" else "Sales tax",
        "vat_number": "—",
        "period": "Current period",
        "balanced": True,
        "last_activity": "—",
        "address": data.get("address", "—"),
        "year_end": data.get("year_end", "—"),
        "coa_template": f"{'UK' if region == 'UK' else 'US'} {ctype}",
        "bank_balance": 0,
        "income": 0,
        "expenses": 0,
        "credit_card": 0,
        "ar": 0,
        "ar_count": 0,
        "ap": 0,
        "ap_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _company_store.append(company)
    _save_companies()
    return {"status": "ok", "company": company}


@app.patch("/api/companies/{company_id}")
async def update_company(company_id: str, data: dict):
    """Update an existing company's editable fields. Accepts both camelCase and snake_case."""
    # Normalize camelCase → snake_case
    FIELD_MAP = {
        "name": "name", "type": "type", "region": "region",
        "address": "address", "addr": "address",
        "year_end": "year_end", "yearEnd": "year_end",
        "vat_status": "vat_status", "vatStatus": "vat_status",
        "vat_number": "vat_number", "vatNo": "vat_number", "vat_number": "vat_number",
    }
    for c in _company_store:
        if c["id"] == company_id:
            for key, value in data.items():
                mapped = FIELD_MAP.get(key)
                if mapped and value:
                    c[mapped] = value
            if "name" in data and data["name"]:
                c["initials"] = "".join(w[0] for w in data["name"].split())[:3].upper()
            _save_companies()
            return {"status": "ok", "company": c}
    return {"error": "Company not found."}


@app.get("/api/dashboard")
async def dashboard(company_id: str = "brightwork"):
    """Return aggregated dashboard data.

    Built-in companies (brightwork/marcus/northgate): live data from API.
    Locally-created companies: local store data only (zero until multi-tenancy).
    """
    c = None
    for entry in _company_store:
        if entry["id"] == company_id:
            c = entry
            break
    if c is None:
        c = _company_store[0] if _company_store else MOCK_COMPANIES[0]

    currency = c.get("currency", "£")
    balanced = c.get("balanced", True)
    last_activity = c.get("last_activity", "—")
    cards = []
    source = "local"
    BUILT_IN_IDS = {"brightwork", "marcus", "northgate"}

    if company_id in BUILT_IN_IDS:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                coa_resp = await client.get(f"{API_BASE_URL}/api/v1/coa")
                bank_resp = await client.get(f"{API_BASE_URL}/api/v1/bank/accounts")
                bank_accounts = []
                total_bank = 0
                if bank_resp.status_code == 200:
                    bank_data = bank_resp.json()
                    bank_accounts = bank_data if isinstance(bank_data, list) else bank_data.get("accounts", [])
                    total_bank = sum(a.get("current_balance", 0) for a in bank_accounts)

                txn_resp = await client.get(f"{API_BASE_URL}/api/v1/transactions/?limit=5")
                if txn_resp.status_code == 200:
                    txn_data = txn_resp.json()
                    transactions = txn_data if isinstance(txn_data, list) else txn_data.get("transactions", [])
                    if transactions:
                        last_txn = transactions[0]
                        desc = last_txn.get("description", "")
                        amt = last_txn.get("total_amount", 0)
                        last_activity = f"{_fmt_pence(amt, currency)} {desc}" if amt else desc

                bs_resp = await client.post(
                    f"{API_BASE_URL}/api/v1/reports/run",
                    json={"template_name": "balance_sheet", "start_date": "2026-01-01", "end_date": "2026-12-31"},
                )
                bs_data = bs_resp.json() if bs_resp.status_code == 200 else None

                pl_resp = await client.post(
                    f"{API_BASE_URL}/api/v1/reports/run",
                    json={"template_name": "profit_and_loss", "start_date": "2026-01-01", "end_date": "2026-12-31"},
                )
                pl_data = pl_resp.json() if pl_resp.status_code == 200 else None

                source = "backend"
                income_total = pl_data.get("revenue", {}).get("total", 0) if pl_data else 0
                expenses_total = pl_data.get("expenses", {}).get("total", 0) if pl_data else 0
                ar_total = bs_data.get("accounts_receivable", 0) if bs_data else 0
                ap_total = bs_data.get("accounts_payable", 0) if bs_data else 0
                if bs_data:
                    total_assets = bs_data.get("total_assets", 0)
                    total_liab = bs_data.get("total_liabilities", 0)
                    total_equity = bs_data.get("total_equity", 0)
                    balanced = abs(total_assets - (total_liab + total_equity)) < 100

                bs_bank = total_bank
                if bs_data:
                    bs_report = bs_data.get("report", bs_data)
                    current_assets = bs_report.get("current_assets", {})
                    for acct in current_assets.get("accounts", []):
                        if "bank" in acct.get("account_name", "").lower():
                            bs_bank = acct.get("amount", bs_bank)
                            break
                    if bs_bank == 0 and current_assets.get("subtotal", 0) > 0:
                        bs_bank = current_assets["subtotal"]

                cards = [
                    {"title": "Bank Account", "type": "Asset", "tone": "asset",
                     "balance": _fmt_pence(bs_bank, currency), "sub": f"{len(bank_accounts)} account(s)" if bank_accounts else "Current account",
                     "dr_label": "Money in", "dr_desc": "Deposits & receipts raise your cash",
                     "cr_label": "Money out", "cr_desc": "Payments & withdrawals reduce it"},
                    {"title": "Sales / Income", "type": "Income", "tone": "income",
                     "balance": _fmt_pence(income_total, currency), "sub": "Revenue this period",
                     "dr_label": "Refunds reduce income", "dr_desc": "Reversals lower the total",
                     "cr_label": "Every sale adds income", "cr_desc": "New revenue is a credit"},
                    {"title": "Expenses", "type": "Expense", "tone": "expense",
                     "balance": _fmt_pence(expenses_total, currency), "sub": "Costs this period",
                     "dr_label": "Each cost adds up", "dr_desc": "Bills & purchases are debits",
                     "cr_label": "Refunds reduce costs", "cr_desc": "Money back is a credit"},
                    {"title": "Credit Card", "type": "Liability", "tone": "liability",
                     "balance": _fmt_pence(0, currency), "sub": "No card accounts",
                     "dr_label": "Repayments lower it", "dr_desc": "Paying down reduces what you owe",
                     "cr_label": "New spend raises it", "cr_desc": "Card purchases add to the debt"},
                    {"title": "Invoices · AR", "type": "Asset", "tone": "asset",
                     "balance": _fmt_pence(ar_total, currency), "sub": "Money owed to you",
                     "dr_label": "Invoice sent", "dr_desc": "Raising one adds money owed to you",
                     "cr_label": "Customer paid", "cr_desc": "Payment clears the balance"},
                    {"title": "Bills · AP", "type": "Liability", "tone": "liability",
                     "balance": _fmt_pence(ap_total, currency), "sub": "Money you owe",
                     "dr_label": "Bill paid", "dr_desc": "Settling lowers what you owe",
                     "cr_label": "Bill received", "cr_desc": "A new bill raises what you owe"},
                ]
        except Exception:
            pass

    if not cards:
        cards = [
            {"title": "Bank Account", "type": "Asset", "tone": "asset",
             "balance": _fmt_pence(c.get("bank_balance", 0), currency), "sub": "Current account",
             "dr_label": "Money in", "dr_desc": "Deposits & receipts raise your cash",
             "cr_label": "Money out", "cr_desc": "Payments & withdrawals reduce it"},
            {"title": "Sales / Income", "type": "Income", "tone": "income",
             "balance": _fmt_pence(c.get("income", 0), currency), "sub": "Revenue earned this period",
             "dr_label": "Refunds reduce income", "dr_desc": "Reversals lower the total",
             "cr_label": "Every sale adds income", "cr_desc": "New revenue is a credit"},
            {"title": "Expenses", "type": "Expense", "tone": "expense",
             "balance": _fmt_pence(c.get("expenses", 0), currency), "sub": "Costs this period",
             "dr_label": "Each cost adds up", "dr_desc": "Bills & purchases are debits",
             "cr_label": "Refunds reduce costs", "cr_desc": "Money back is a credit"},
            {"title": "Credit Card", "type": "Liability", "tone": "liability",
             "balance": _fmt_pence(c.get("credit_card", 0), currency), "sub": "Owed to card provider",
             "dr_label": "Repayments lower it", "dr_desc": "Paying down reduces what you owe",
             "cr_label": "New spend raises it", "cr_desc": "Card purchases add to the debt"},
            {"title": "Invoices · AR", "type": "Asset", "tone": "asset",
             "balance": _fmt_pence(c.get("ar", 0), currency), "sub": f'{c.get("ar_count", 0)} open',
             "dr_label": "Invoice sent", "dr_desc": "Raising one adds money owed to you",
             "cr_label": "Customer paid", "cr_desc": "Payment clears the balance"},
            {"title": "Bills · AP", "type": "Liability", "tone": "liability",
             "balance": _fmt_pence(c.get("ap", 0), currency), "sub": f'{c.get("ap_count", 0)} open',
             "dr_label": "Bill paid", "dr_desc": "Settling lowers what you owe",
             "cr_label": "Bill received", "cr_desc": "A new bill raises what you owe"},
        ]
        source = "local"

    bal_color = "#6ee7a8" if balanced else "#f0b86e"
    bal_bg = "#0d1b14" if balanced else "#241a0d"
    bal_border = "#1a3a2a" if balanced else "#3a2c15"

    return {
        "company": {
            "id": c["id"], "name": c["name"], "initials": c.get("initials", ""),
            "swatch": c.get("swatch", "#5eead4"), "type": c.get("type", ""),
            "region": c.get("region", "UK"), "currency": currency,
            "standard": c.get("standard", ""), "vat_status": c.get("vat_status", ""),
            "vat_number": c.get("vat_number", "—"), "period": c.get("period", ""),
            "last_activity": last_activity, "address": c.get("address", ""),
            "year_end": c.get("year_end", ""), "coa_template": c.get("coa_template", ""),
        },
        "status": {
            "balanced": balanced, "text": "Balanced" if balanced else "Needs review",
            "color": bal_color, "background": bal_bg, "border_color": bal_border,
            "dot": "●" if balanced else "▲",
        },
        "cards": cards,
        "source": source,
    }



@app.get("/api/reports/{report_type}")
async def get_report(report_type: str, company_id: str = "brightwork"):
    """Return a specific report for the active company.

    Tries the accounting API report endpoint first; falls back to
    computed mock data.
    """
    valid_types = {"bs", "pl", "tb", "vat", "cf", "ar", "ap"}
    if report_type not in valid_types:
        return {"error": f"Unknown report type: {report_type}. Valid: {', '.join(sorted(valid_types))}"}

    c = _get_mock_company(company_id)
    # Always query the API for reports. Single-tenant — shared data.
    if True:
    # Query the API — single-tenant, data is shared across company profiles
        try:
            type_map = {
                "bs": "balance_sheet", "pl": "profit_and_loss",
                "tb": "trial_balance", "ar": "aged_receivables", "ap": "aged_payables",
            }
            if report_type in type_map:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{API_BASE_URL}/api/v1/reports/run",
                        json={
                            "template_name": type_map[report_type],
                            "start_date": "2026-01-01",
                            "end_date": "2026-12-31",
                        },
                    )
                    if resp.status_code == 200:
                        transformed = _transform_api_report(resp.json(), report_type, c)
                        if transformed:
                            return {**transformed, "source": "backend"}
            if report_type == "vat":
                async with httpx.AsyncClient(timeout=10.0) as client:
                    periods_resp = await client.get(f"{API_BASE_URL}/api/v1/vat/periods")
                    if periods_resp.status_code == 200:
                        periods = periods_resp.json()
                        if periods:
                            pid = periods[0].get("id") if isinstance(periods, list) else list(periods.get("periods", []))[0].get("id") if isinstance(periods, dict) else None
                            if pid:
                                calc_resp = await client.post(f"{API_BASE_URL}/api/v1/vat/periods/{pid}/calculate")
                                if calc_resp.status_code == 200:
                                    return {**calc_resp.json(), "source": "backend"}
        except Exception:
            pass

    # Compute report from company store data
    report = _build_report_from_company(report_type, c)
    if report is None:
        return {"error": f"Report type '{report_type}' not available"}
    return {**report, "source": "local"}


# ---------------------------------------------------------------------------

def _clean_llm_response(text: str) -> str:
    """Remove internal pence formatting from LLM responses."""
    import re
    # Remove "(X,XXX,XXX pence)" patterns
    text = re.sub(r'\([\d,]+ pence\)', '', text)
    # Remove standalone "X,XXX,XXX pence" references
    text = re.sub(r'\b[\d,]+\s+pence\b', '', text)
    return text.strip()

# WebSocket chat bridge
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """Bridge browser WebSocket to the accounting API WebSocket.

    Translates message formats between the Git-Maid UI protocol and the
    accounting API's chat protocol.
    """
    await ws.accept()

    # Accept client-supplied session_id if provided (enables session persistence across refreshes)
    client_sid = ws.query_params.get("session_id")
    session_id = client_sid if client_sid else str(uuid.uuid4())
    backend_ws_url = f"{API_BASE_URL.replace('http', 'ws')}/api/v1/ws/chat/{session_id}"

    await ws.send_text(json.dumps({
        "type": "connected",
        "session_id": session_id,
    }))

    try:
        import websockets as ws_client

        async with ws_client.connect(backend_ws_url) as backend:

            async def forward_to_backend():
                """Read browser messages, translate, and send to backend."""
                try:
                    while True:
                        data = await ws.receive_text()
                        msg = json.loads(data)
                        msg_type = msg.get("type", "message")

                        if msg_type == "message":
                            content = msg.get("content", "")
                            persona = msg.get("persona", "professional")
                            await backend.send(json.dumps({
                                "type": "user_message",
                                "session_id": session_id,
                                "content": content,
                                "persona": persona,
                            }))
                        elif msg_type in ("confirm", "reject"):
                            # Map confirm/reject to confirmation_response
                            await backend.send(json.dumps({
                                "type": "confirmation_response",
                                "session_id": session_id,
                                "confirmed": msg_type == "confirm",
                            }))
                        elif msg_type == "stop":
                            await ws.send_text(json.dumps({
                                "type": "cancelled",
                                "content": "Processing stopped.",
                            }))
                        elif msg_type == "ping":
                            await ws.send_text(json.dumps({"type": "pong"}))

                except WebSocketDisconnect:
                    pass

            async def forward_to_browser():
                """Read backend messages, translate, and send to browser."""
                try:
                    async for raw in backend:
                        msg = json.loads(raw)
                        msg_type = msg.get("type", "")

                        if msg_type == "error":
                            await ws.send_text(json.dumps({
                                "type": "error",
                                "content": msg.get("message", msg.get("content", "Backend error")),
                            }))

                        elif msg_type == "tool_call":
                            skill_id = msg.get("skill_id", "unknown")
                            params = msg.get("params", {})
                            await ws.send_text(json.dumps({
                                "type": "tool_calls",
                                "content": f"Invoking {skill_id}...",
                                "tools": [{
                                    "id": msg.get("tool_call_id", ""),
                                    "name": skill_id,
                                    "args": params,
                                }],
                            }))
                            await ws.send_text(json.dumps({
                                "type": "thinking",
                                "content": f"Processing {skill_id}...",
                            }))

                        elif msg_type == "tool_result":
                            result_data = msg.get("result", {})
                            response = result_data.get("response", "")
                            skill_name = result_data.get("skill", "unknown")
                            persona = result_data.get("persona", "professional")

                            await ws.send_text(json.dumps({
                                "type": "text",
                                "content": _clean_llm_response(response) or f"Completed {skill_name}.",
                                "persona": persona,
                                "session_id": session_id,
                            }))

                        elif msg_type == "confirmation_request":
                            await ws.send_text(json.dumps({
                                "type": "confirm_request",
                                "content": msg.get("message", "Confirm this action?"),
                                "tools": [msg.get("action", "unknown")],
                            }))

                        elif msg_type == "stream_start":
                            pass  # Skip — tokens follow

                        elif msg_type in ("stream_token", "stream_end"):
                            token = msg.get("token", msg.get("content", ""))
                            if token:
                                # Accumulated streaming handled by client
                                await ws.send_text(json.dumps({
                                    "type": "text",
                                    "content": _clean_llm_response(token),
                                }))

                        else:
                            # Unknown message type — pass through as text if content exists
                            content = msg.get("content", "")
                            if content:
                                await ws.send_text(json.dumps({
                                    "type": "text",
                                    "content": str(content),
                                }))

                except Exception:
                    pass

            await asyncio.gather(
                forward_to_backend(),
                forward_to_browser(),
            )

    except ImportError:
        # websockets lib not available — fall back to HTTP REST bridge
        await _fallback_http_bridge(ws, session_id)
    except Exception as e:
        await ws.send_text(json.dumps({
            "type": "error",
            "content": f"Cannot connect to accounting backend: {e}",
        }))


async def _fallback_http_bridge(ws: WebSocket, session_id: str):
    """Fallback: use HTTP REST endpoint when WebSocket bridge is not available."""
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "message")

            if msg_type == "message":
                content = msg.get("content", "")
                persona = msg.get("persona", "professional")

                await ws.send_text(json.dumps({
                    "type": "thinking",
                    "content": "Processing...",
                }))

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{API_BASE_URL}/api/v1/chat/message",
                        json={
                            "session_id": session_id,
                            "message": content,
                            "persona": persona,
                        },
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        response_text = result.get("message", {}).get("text", "I processed your request.")
                        tool_call = result.get("tool_call")

                        # Send tool call info if present
                        if tool_call:
                            await ws.send_text(json.dumps({
                                "type": "tool_calls",
                                "content": f"Invoking {tool_call.get('skill_id', 'unknown')}...",
                                "tools": [{
                                    "id": tool_call.get("tool_call_id", ""),
                                    "name": tool_call.get("skill_id", "unknown"),
                                    "args": tool_call.get("params", {}),
                                }],
                            }))

                        await ws.send_text(json.dumps({
                            "type": "text",
                            "content": response_text,
                            "session_id": session_id,
                        }))
                    else:
                        await ws.send_text(json.dumps({
                            "type": "error",
                            "content": f"Backend error: {resp.status_code}",
                        }))

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Server launcher
# ---------------------------------------------------------------------------

def start_server(host: str = "0.0.0.0", port: int = 3000):
    """Start the uvicorn server."""
    ui_path = UI_DIR / "index.html"
    if not ui_path.exists():
        _generate_ui(ui_path)

    print(f"🚀 Agentic Accounting Chat UI starting at http://{host}:{port}")
    print("Press Ctrl+C to stop.")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        log_level="warning",
    )


def _generate_ui(path: Path):
    """Write the embedded UI HTML to disk."""
    html = _get_ui_html()
    path.write_text(html)


def _get_ui_html() -> str:
    """Return the complete UI HTML as a string (accounting themed)."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentic Accounting — AI Bookkeeper</title>
<style>
  :root {
    --bg: #0d0d0d;
    --surface: #161616;
    --surface2: #1e1e1e;
    --border: #2a2a2a;
    --text: #d4d4d4;
    --text-dim: #6b6b6b;
    --accent: #4ec9b0;
    --accent-glow: rgba(78,201,176,0.15);
    --accent-text: #1a1a1a;
    --green: #4ec9b0;
    --red: #f44747;
    --blue: #569cd6;
    --radius: 8px;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "SF Mono", "JetBrains Mono", "Fira Code", monospace;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Header */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  header .logo {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.3px;
  }
  header .logo span { color: var(--text-dim); font-weight: 400; }
  header .status {
    margin-left: auto;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-dim);
  }
  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px rgba(78,201,176,0.4);
  }
  .status-dot.off { background: var(--red); box-shadow: 0 0 6px rgba(244,71,71,0.4); }

  /* Chat area */
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .chat-container::-webkit-scrollbar { width: 6px; }
  .chat-container::-webkit-scrollbar-track { background: transparent; }
  .chat-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  /* Messages */
  .msg {
    display: flex;
    flex-direction: column;
    max-width: 85%;
    animation: fadeIn 0.25s ease;
  }
  @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
  .msg.user { align-self: flex-end; }
  .msg.assistant { align-self: flex-start; }
  .msg.system { align-self: center; max-width: 100%; }

  .msg-bubble {
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.55;
    font-size: 14px;
    word-wrap: break-word;
  }
  .msg.user .msg-bubble {
    background: var(--accent);
    color: var(--accent-text);
    border-bottom-right-radius: 2px;
  }
  .msg.assistant .msg-bubble {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-bottom-left-radius: 2px;
  }
  .msg.system .msg-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    font-size: 13px;
    color: var(--text-dim);
    text-align: center;
    padding: 8px 16px;
  }
  .msg.system.error .msg-bubble {
    border-color: rgba(244,71,71,0.3);
    color: var(--red);
  }
  .msg-bubble p { margin-bottom: 8px; }
  .msg-bubble p:last-child { margin-bottom: 0; }
  .msg-bubble code {
    font-family: var(--mono);
    font-size: 13px;
    background: rgba(255,255,255,0.06);
    padding: 2px 6px;
    border-radius: 3px;
  }
  .msg-bubble pre {
    background: rgba(0,0,0,0.3);
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.5;
  }

  /* Tool call display */
  .tool-call {
    margin-top: 6px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    font-size: 13px;
  }
  .tool-call-header {
    background: var(--surface);
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }
  .tool-call-header:hover { background: var(--surface2); }
  .tool-call-icon { font-size: 14px; }
  .tool-call-name { font-family: var(--mono); color: var(--blue); font-size: 12px; }
  .tool-call-chevron { margin-left: auto; color: var(--text-dim); transition: transform 0.2s; }
  .tool-call.open .tool-call-chevron { transform: rotate(180deg); }
  .tool-call-body {
    display: none;
    padding: 10px 12px;
    background: rgba(0,0,0,0.2);
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
    color: var(--text-dim);
    max-height: 200px;
    overflow-y: auto;
  }
  .tool-call.open .tool-call-body { display: block; }

  /* Confirmation bar */
  .confirm-bar {
    align-self: center;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    animation: fadeIn 0.25s ease;
  }
  .confirm-bar .text { font-size: 14px; color: var(--accent); flex: 1; }
  .confirm-bar button {
    padding: 8px 18px;
    border-radius: 5px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-confirm {
    background: var(--accent);
    color: var(--accent-text);
  }
  .btn-confirm:hover { filter: brightness(1.1); }
  .btn-reject {
    background: transparent;
    color: var(--text-dim);
    border: 1px solid var(--border) !important;
  }
  .btn-reject:hover { color: var(--text); border-color: var(--text-dim) !important; }

  /* Input area */
  .input-container {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 14px 20px;
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }
  .input-container input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    font-family: var(--font);
    outline: none;
    transition: border-color 0.15s;
  }
  .input-container input:focus { border-color: var(--accent); }
  .input-container input::placeholder { color: var(--text-dim); }
  .input-container button {
    background: var(--accent);
    color: var(--accent-text);
    border: none;
    border-radius: var(--radius);
    padding: 0 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .input-container button:hover { filter: brightness(1.1); }
  .input-container button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .input-container button.btn-stop {
    background: var(--red);
    color: #fff;
    animation: pulseStop 1.5s infinite;
  }
  @keyframes pulseStop {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  /* Settings modal */
  .settings-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-dim);
    font-size: 16px;
    padding: 4px 8px;
    cursor: pointer;
    transition: all 0.15s;
    margin-right: 8px;
  }
  .settings-btn:hover { color: var(--text); border-color: var(--text-dim); }
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    align-items: center;
    justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    width: 90%;
    max-width: 440px;
    animation: fadeIn 0.2s ease;
  }
  .modal h2 { font-size: 18px; color: var(--accent); margin-bottom: 20px; }
  .modal label { font-size: 12px; color: var(--text-dim); display: block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .modal input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    color: var(--text);
    font-size: 13px;
    font-family: var(--mono);
    margin-bottom: 14px;
    outline: none;
    transition: border-color 0.15s;
  }
  .modal input:focus { border-color: var(--accent); }
  .modal .account-info {
    background: var(--surface2);
    border-radius: var(--radius);
    padding: 10px 14px;
    margin-bottom: 16px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .modal .account-info .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
  }
  .modal .account-info .dot.off { background: var(--red); }
  .modal .account-info .label { color: var(--text-dim); }
  .modal .account-info .value { color: var(--accent); font-weight: 600; }
  .modal .account-info .source { color: var(--text-dim); font-size: 11px; }
  .modal .btn-row { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
  .modal .btn-row button {
    padding: 8px 18px;
    border-radius: 5px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .modal .btn-save { background: var(--accent); color: var(--accent-text); }
  .modal .btn-save:hover { filter: brightness(1.1); }
  .modal .btn-cancel { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
  .modal .btn-cancel:hover { color: var(--text); }
  .modal .saved-msg {
    text-align: center;
    color: var(--green);
    font-size: 13px;
    margin-top: 10px;
    display: none;
  }

  /* Loading dots */
  .typing-dots {
    display: flex;
    gap: 4px;
    padding: 4px 0;
  }
  .typing-dots span {
    width: 6px; height: 6px;
    background: var(--text-dim);
    border-radius: 50%;
    animation: bounce 1.2s infinite;
  }
  .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
  .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,60%,100% { transform:translateY(0); } 30% { transform:translateY(-6px); } }
</style>
</head>
<body>

<header>
  <div class="logo">ledger.chat <span>/ your AI bookkeeper</span></div>
  <div style="background:var(--accent);color:var(--accent-text);font-size:10px;padding:2px 8px;border-radius:3px;font-weight:700;" id="version-tag">MVP</div>
  <div class="status">
    <button class="settings-btn" id="settings-btn" title="Settings">⚙</button>
    <span id="backend-status" style="color:var(--accent);font-weight:600;font-size:12px;margin-right:12px;"></span>
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">connecting...</span>
  </div>
</header>

<div class="chat-container" id="chat"></div>

<div class="input-container">
  <input id="msg-input" type="text" placeholder="Record a transaction, create an invoice, check your VAT..." disabled />
  <button id="send-btn" disabled>Send</button>
</div>

<!-- Settings Modal -->
<div class="modal-overlay" id="modal-overlay">
  <div class="modal">
    <h2>Settings</h2>
    <div class="account-info" id="settings-account">
      <div class="dot" id="settings-dot"></div>
      <div>
        <div>Backend: <span class="value" id="settings-url">...</span></div>
        <div class="source" id="settings-source">loading...</div>
      </div>
    </div>
    <label>Accounting API Base URL</label>
    <input type="text" id="settings-api-url" placeholder="http://accounting-api:8000" />
    <div class="btn-row">
      <button class="btn-cancel" onclick="closeSettings()">Cancel</button>
      <button class="btn-save" onclick="saveSettings()">Save &amp; Reconnect</button>
    </div>
    <div class="saved-msg" id="saved-msg">Saved! Reconnecting...</div>
  </div>
</div>

<script>
// --- Debug banner ---
var DEBUG = document.createElement('div');
DEBUG.style.cssText = 'position:fixed;top:8px;right:8px;background:#111;color:#4ec9b0;font:10px monospace;padding:3px 8px;z-index:999;max-width:360px;max-height:24px;overflow:hidden;border-radius:4px;border:1px solid #2a2a2a;opacity:0.75;transition:max-height 0.3s;cursor:pointer;';
DEBUG.id = 'debug-log';
DEBUG.title = 'Click to expand';
DEBUG.onclick = function() {
  if (DEBUG.style.maxHeight === '200px') {
    DEBUG.style.maxHeight = '24px';
    DEBUG.title = 'Click to expand';
  } else {
    DEBUG.style.maxHeight = '200px';
    DEBUG.style.overflowY = 'auto';
    DEBUG.title = 'Click to collapse';
  }
};
var DBG_CLOSE = document.createElement('span');
DBG_CLOSE.textContent = '\u00d7';
DBG_CLOSE.style.cssText = 'position:absolute;top:1px;right:4px;cursor:pointer;color:#6b6b6b;font-size:12px;display:none;';
DBG_CLOSE.onclick = function(e) { e.stopPropagation(); DEBUG.style.display = 'none'; };
DEBUG.appendChild(DBG_CLOSE);
var DBG_TEXT = document.createElement('div');
DBG_TEXT.style.cssText = 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
DEBUG.appendChild(DBG_TEXT);
document.body.appendChild(DEBUG);

var _dbgTimeout = null;
function debug(msg) {
  DEBUG.style.display = 'block';
  DBG_TEXT.textContent = msg;
  if (msg.indexOf('FATAL') >= 0 || msg.indexOf('ERROR') >= 0) {
    DEBUG.style.color = '#f44747';
    DEBUG.style.borderColor = 'rgba(244,71,71,0.4)';
    DEBUG.style.maxHeight = '200px';
    DEBUG.style.overflowY = 'auto';
    DBG_CLOSE.style.display = 'inline';
    DBG_TEXT.style.whiteSpace = 'pre-wrap';
    DBG_TEXT.style.wordBreak = 'break-all';
    if (_dbgTimeout) clearTimeout(_dbgTimeout);
  } else if (msg.indexOf('WS onopen fired') >= 0) {
    if (_dbgTimeout) clearTimeout(_dbgTimeout);
    _dbgTimeout = setTimeout(function() { DEBUG.style.display = 'none'; }, 4000);
  } else {
    DBG_TEXT.style.whiteSpace = 'nowrap';
    DBG_TEXT.textContent = msg;
    DEBUG.style.maxHeight = '24px';
    DEBUG.style.overflowY = 'hidden';
  }
}

(function() {
  debug('Script starting...');

  var chat = document.getElementById('chat');
  var input = document.getElementById('msg-input');
  var sendBtn = document.getElementById('send-btn');
  var statusDot = document.getElementById('status-dot');
  var statusText = document.getElementById('status-text');

  debug('Elements found: chat=' + !!chat + ' input=' + !!input + ' sendBtn=' + !!sendBtn);

  var ws = null;
  var pendingConfirm = false;
  var isProcessing = false;

  function connect() {
    debug('connect() called');
    var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    var host = location.hostname === 'localhost' || location.hostname === '::1'
      ? '127.0.0.1:' + location.port
      : location.host;
    var url = protocol + '//' + host + '/ws/chat';
    debug('WebSocket URL: ' + url);

    statusText.textContent = 'connecting to ' + url + '...';

    try {
      ws = new WebSocket(url);
      debug('WebSocket created, readyState=' + ws.readyState);
    } catch(e) {
      debug('WebSocket constructor ERROR: ' + e.message);
      return;
    }

    ws.onopen = function() {
      debug('WS onopen fired');
      setStatus(true, 'connected');
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    };

    ws.onclose = function(e) {
      debug('WS onclose fired, code=' + e.code + ' reason=' + (e.reason || 'none') + ' wasClean=' + e.wasClean);
      setStatus(false, 'disconnected (code ' + e.code + ')');
      input.disabled = true;
      sendBtn.disabled = true;
      setTimeout(connect, 3000);
    };

    ws.onmessage = function(e) {
      try {
        var msg = JSON.parse(e.data);
        var info = msg.type === 'thinking' ? (' (' + (msg.content||'') + ')') :
                   msg.type === 'tool_calls' ? (' [' + (msg.tools||[]).map(function(t){return t.name;}).join(', ') + ']') :
                   msg.type === 'error' ? (': ' + (msg.content||'')) :
                   msg.type === 'confirm_request' ? (' [' + (msg.tools||[]).join(', ') + ']') :
                   '';
        debug('WS msg: type=' + msg.type + info);
        handleMessage(msg);
      } catch (err) {
        debug('WS parse error: ' + err.message);
        setStatus(false, 'parse error: ' + err.message);
      }
    };

    ws.onerror = function(e) {
      debug('WS onerror fired, readyState=' + ws.readyState);
      setStatus(false, 'ws error');
    };
  }

  function setStatus(ok, text) {
    statusDot.className = 'status-dot' + (ok ? '' : ' off');
    statusText.textContent = text;
  }

  function setIsProcessing(processing) {
    isProcessing = processing;
    if (processing) {
      sendBtn.textContent = 'Stop';
      sendBtn.className = 'btn-stop';
      sendBtn.disabled = false;
    } else {
      sendBtn.textContent = 'Send';
      sendBtn.className = '';
      sendBtn.disabled = false;
    }
  }

  function handleMessage(msg) {
    removeTyping();

    switch (msg.type) {
      case 'connected':
        setStatus(true, 'connected');
        setIsProcessing(false);
        addMessage('assistant', msg.content);
        break;
      case 'text':
        setIsProcessing(false);
        addMessage('assistant', msg.content);
        break;
      case 'tool_calls':
        addToolCalls(msg.content, msg.tools);
        addTyping();
        break;
      case 'confirm_request':
        setIsProcessing(false);
        addConfirmBar(msg.content, msg.tools);
        pendingConfirm = true;
        break;
      case 'thinking':
        addTyping();
        break;
      case 'status':
        addMessage('system', msg.content);
        break;
      case 'cancelled':
        setIsProcessing(false);
        if (msg.content) addMessage('system', msg.content);
        break;
      case 'error':
        setIsProcessing(false);
        addMessage('system', msg.content, true);
        break;
      case 'pong':
        break;
    }
    scrollDown();
  }

  function addMessage(role, content, isError) {
    isError = isError || false;
    var div = document.createElement('div');
    div.className = 'msg ' + role + (isError ? ' error' : '');

    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = renderMarkdown(content);
    div.appendChild(bubble);

    chat.appendChild(div);
  }

  function addToolCalls(text, tools) {
    var div = document.createElement('div');
    div.className = 'msg assistant';

    if (text) {
      var bubble = document.createElement('div');
      bubble.className = 'msg-bubble';
      bubble.innerHTML = renderMarkdown(text);
      div.appendChild(bubble);
    }

    tools.forEach(function(t) {
      var tc = document.createElement('div');
      tc.className = 'tool-call';
      tc.innerHTML = '<div class="tool-call-header" onclick="this.parentElement.classList.toggle(\'open\')">' +
        '<span class="tool-call-icon">\ud83d\udd27</span>' +
        '<span class="tool-call-name">' + esc(t.name) + '</span>' +
        '<span class="tool-call-chevron">\u25be</span>' +
        '</div>' +
        '<div class="tool-call-body">' + esc(JSON.stringify(t.args, null, 2)) + '</div>';
      div.appendChild(tc);
    });

    chat.appendChild(div);
  }

  function addConfirmBar(text, tools) {
    var div = document.createElement('div');
    div.className = 'confirm-bar';
    div.id = 'confirm-bar';
    div.innerHTML = '<span class="text">\u26a0\ufe0f ' + esc(text) + '</span>' +
      '<button class="btn-confirm" onclick="confirmAction()">\u2713 Confirm</button>' +
      '<button class="btn-reject" onclick="rejectAction()">\u2717 Cancel</button>';
    chat.appendChild(div);
  }

  function addTyping() {
    removeTyping();
    var div = document.createElement('div');
    div.className = 'msg assistant';
    div.id = 'typing-indicator';
    div.innerHTML = '<div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    chat.appendChild(div);
    scrollDown();
  }

  function removeTyping() {
    var el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  function renderMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/```([\\s\\S]*?)```/g, '<pre>$1</pre>')
      .replace(/^### (.+)/gm, '<strong>$1</strong>')
      .replace(/^## (.+)/gm, '<strong>$1</strong>')
      .replace(/^# (.+)/gm, '<strong>$1</strong>')
      .replace(/^- (.+)/gm, '\u2022 $1')
      .replace(/\\n/g, '<br>');
  }

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function scrollDown() {
    chat.scrollTop = chat.scrollHeight;
  }

  function sendMessage() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (isProcessing) {
      ws.send(JSON.stringify({ type: 'stop' }));
      return;
    }

    var text = input.value.trim();
    if (!text || pendingConfirm) return;

    addMessage('user', text);
    input.value = '';
    setIsProcessing(true);
    addTyping();

    ws.send(JSON.stringify({ type: 'message', content: text }));
  }

  window.confirmAction = function() {
    if (!ws || !pendingConfirm) return;
    removeConfirmBar();
    pendingConfirm = false;
    setIsProcessing(true);
    addTyping();
    ws.send(JSON.stringify({ type: 'confirm' }));
  };

  window.rejectAction = function() {
    if (!ws || !pendingConfirm) return;
    removeConfirmBar();
    pendingConfirm = false;
    setIsProcessing(true);
    addTyping();
    ws.send(JSON.stringify({ type: 'reject' }));
  };

  function removeConfirmBar() {
    var el = document.getElementById('confirm-bar');
    if (el) el.remove();
  }

  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); sendMessage(); }
  });
  sendBtn.addEventListener('click', sendMessage);

  connect();

  // --- Settings Modal ---

  window.openSettings = async function() {
    debug('openSettings() called');
    var overlay = document.getElementById('modal-overlay');
    overlay.classList.add('open');

    try {
      var resp = await fetch('/api/account');
      var data = await resp.json();

      document.getElementById('settings-url').textContent = data.api_base_url || 'not configured';
      document.getElementById('settings-source').textContent = data.backend_configured ? 'connected' : 'unreachable';
      var dot = document.getElementById('settings-dot');
      dot.className = dot.className.replace(' off', '');
      if (!data.backend_configured) dot.className += ' off';

      document.getElementById('settings-api-url').value = '';
      document.getElementById('saved-msg').style.display = 'none';
    } catch (e) {
      document.getElementById('settings-url').textContent = 'error';
      document.getElementById('settings-source').textContent = e.message;
    }
  };

  window.closeSettings = function() {
    document.getElementById('modal-overlay').classList.remove('open');
  };

  window.saveSettings = async function() {
    debug('saveSettings() called');
    var apiUrl = document.getElementById('settings-api-url').value.trim();
    debug('apiUrl=' + apiUrl);

    if (!apiUrl) {
      document.getElementById('saved-msg').textContent = 'Enter a backend URL.';
      document.getElementById('saved-msg').style.color = 'var(--red)';
      document.getElementById('saved-msg').style.display = 'block';
      return;
    }

    var saveBtn = document.querySelector('.btn-save');
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;

    try {
      debug('POST /api/settings...');
      var resp = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_base_url: apiUrl }),
      });
      var data = await resp.json();
      debug('Settings response: ' + JSON.stringify(data));

      if (data.status === 'ok') {
        document.getElementById('saved-msg').style.color = 'var(--green)';
        document.getElementById('saved-msg').textContent = 'Saved! Reconnecting...';
        document.getElementById('saved-msg').style.display = 'block';
        setTimeout(function() {
          if (ws) ws.close();
          connect();
        }, 800);
      } else {
        throw new Error(data.message || 'Unknown error');
      }
    } catch (e) {
      debug('saveSettings ERROR: ' + e.message);
      document.getElementById('saved-msg').textContent = 'Error: ' + e.message;
      document.getElementById('saved-msg').style.color = 'var(--red)';
      document.getElementById('saved-msg').style.display = 'block';
      saveBtn.textContent = 'Save & Reconnect';
      saveBtn.disabled = false;
    }
  };

  document.getElementById('settings-btn').addEventListener('click', window.openSettings);
  document.getElementById('modal-overlay').addEventListener('click', function(e) {
    if (e.target === e.currentTarget) window.closeSettings();
  });

})();
</script>

</body>
</html>'''


if __name__ == "__main__":
    start_server()
