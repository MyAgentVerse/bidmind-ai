"""Admin dashboard — open endpoints (no auth required).

Read-only aggregated views across all users, projects, and usage.
Does NOT expose proposal content (privacy). Does NOT modify any data.
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.admin_dashboard_service import AdminDashboardService
from app.services.openai_tracker import get_usage_summary
from app.middleware.request_logger import get_recent_errors, get_request_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def admin_dashboard(db: Session = Depends(get_db)):
    """Single comprehensive dashboard — everything in one call."""
    try:
        svc = AdminDashboardService(db)

        return {
            "overview": svc.get_overview(),
            "openai_usage": get_usage_summary(),
            "request_stats": get_request_stats(),
            "recent_errors": get_recent_errors(limit=20),
        }
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/users")
async def admin_users(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """All users with org/company info."""
    try:
        svc = AdminDashboardService(db)
        return {"users": svc.get_users(limit=limit, offset=offset)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/projects")
async def admin_projects(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """All projects with status, file count, analysis/proposal flags."""
    try:
        svc = AdminDashboardService(db)
        return {"projects": svc.get_projects_summary(limit=limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/activity")
async def admin_activity(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Unified activity timeline across all tables."""
    try:
        svc = AdminDashboardService(db)
        return {"events": svc.get_activity_timeline(limit=limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/openai-usage")
async def admin_openai_usage():
    """OpenAI token usage and cost breakdown."""
    return get_usage_summary()


@router.get("/errors")
async def admin_errors(limit: int = Query(50, le=200)):
    """Recent API errors."""
    return {
        "errors": get_recent_errors(limit=limit),
        "stats": get_request_stats(),
    }
