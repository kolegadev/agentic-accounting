"""Routes package."""

from src.routes.approvals import router as approvals_router
from src.routes.auth import router as auth_router
from src.routes.bank_rules import router as bank_rules_router
from src.routes.chat import router as chat_router
from src.routes.coa import router as coa_router

__all__ = ["approvals_router", "auth_router", "bank_rules_router", "chat_router", "coa_router"]
