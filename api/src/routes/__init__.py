"""Routes package."""

from src.routes.chat import router as chat_router
from src.routes.coa import router as coa_router

__all__ = ["chat_router", "coa_router"]