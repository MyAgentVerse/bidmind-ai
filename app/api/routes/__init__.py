"""API route modules."""

from .health import router as health_router
from .company import router as company_router
from .writing_preferences import router as writing_preferences_router
from .projects import router as projects_router
from .uploads import router as uploads_router
from .analysis import router as analysis_router
from .proposal import router as proposal_router
from .ai_edit import router as ai_edit_router
from .export import router as export_router

__all__ = [
    "health_router",
    "company_router",
    "writing_preferences_router",
    "projects_router",
    "uploads_router",
    "analysis_router",
    "proposal_router",
    "ai_edit_router",
    "export_router",
]
