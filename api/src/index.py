"""FastAPI application entry point — Agentic Accounting MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import close_db_connection
from src.routes.approvals import router as approvals_router
from src.routes.auth import router as auth_router
from src.routes.bank import router as bank_router
from src.routes.bank_rules import router as bank_rules_router
from src.routes.chat import router as chat_router
from src.routes.coa import router as coa_router
from src.routes.contacts import router as contacts_router
from src.routes.invoices import router as invoices_router
from src.routes.mtd import router as mtd_router
from src.routes.reconciliation import router as reconciliation_router
from src.routes.reports import router as reports_router
from src.routes.transactions import router as transactions_router
from src.routes.vat import router as vat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    yield
    await close_db_connection()


app = FastAPI(
    title="Agentic Accounting MVP",
    description="Headless LLM-Native Small Business Accounting System",
    version="0.1.0",
    lifespan=lifespan,
)

# ---- CORS ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ---------------------------------------------------------------
app.include_router(approvals_router)
app.include_router(auth_router)
app.include_router(bank_router)
app.include_router(bank_rules_router)
app.include_router(chat_router)
app.include_router(coa_router)
app.include_router(contacts_router)
app.include_router(invoices_router)
app.include_router(mtd_router)
app.include_router(reconciliation_router)
app.include_router(reports_router)
app.include_router(transactions_router)
app.include_router(vat_router)


# ---- Health Check ----------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return health status of the API."""
    return {"status": "ok"}
