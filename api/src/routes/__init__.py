"""Routes package."""

from src.routes.auth import router as auth_router
from src.routes.chat import router as chat_router
from src.routes.coa import router as coa_router

__all__ = ["auth_router", "chat_router", "coa_router"]
