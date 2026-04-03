"""Health check endpoints."""

from fastapi import APIRouter
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> SuccessResponse:
    """Health check endpoint for monitoring."""
    return create_success_response(
        message=MESSAGES["HEALTH_OK"],
        data={"status": "healthy"}
    )
