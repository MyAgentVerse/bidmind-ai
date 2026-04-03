"""Common response schemas used across the API."""

from pydantic import BaseModel
from typing import Any, Optional, List


class SuccessResponse(BaseModel):
    """Standard successful API response."""
    success: bool = True
    message: str
    data: Optional[Any] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {}
            }
        }


class ErrorResponse(BaseModel):
    """Standard error API response."""
    success: bool = False
    message: str
    errors: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "An error occurred",
                "errors": ["Error detail 1", "Error detail 2"]
            }
        }
