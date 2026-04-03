"""Response helper functions for consistent API responses."""

from typing import Any, Optional, List
from app.schemas.common import SuccessResponse, ErrorResponse


def create_success_response(
    message: str,
    data: Optional[Any] = None,
    success: bool = True
) -> SuccessResponse:
    """
    Create a standardized success response.

    Args:
        message: Success message
        data: Response data
        success: Whether operation was successful (default True)

    Returns:
        SuccessResponse object
    """
    return SuccessResponse(success=success, message=message, data=data)


def create_error_response(
    message: str,
    errors: Optional[List[str]] = None,
    success: bool = False
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        message: Error message
        errors: List of detailed error messages
        success: Whether operation was successful (default False)

    Returns:
        ErrorResponse object
    """
    return ErrorResponse(success=success, message=message, errors=errors)


# Common response messages
MESSAGES = {
    # Success messages
    "PROJECT_CREATED": "Project created successfully",
    "PROJECT_UPDATED": "Project updated successfully",
    "FILE_UPLOADED": "File uploaded successfully",
    "ANALYSIS_COMPLETED": "Document analysis completed successfully",
    "PROPOSAL_GENERATED": "Proposal generated successfully",
    "PROPOSAL_UPDATED": "Proposal updated successfully",
    "AI_EDIT_COMPLETED": "AI edit completed successfully",
    "EXPORT_SUCCESS": "DOCX exported successfully",
    "HEALTH_OK": "API is healthy",

    # Error messages
    "FILE_NOT_FOUND": "File not found",
    "PROJECT_NOT_FOUND": "Project not found",
    "INVALID_FILE_TYPE": "Invalid file type",
    "FILE_TOO_LARGE": "File size exceeds maximum allowed",
    "EMPTY_FILE": "Cannot upload empty file",
    "INVALID_REQUEST": "Invalid request data",
    "DATABASE_ERROR": "Database error occurred",
    "AI_ERROR": "Error processing with AI",
    "EXTRACTION_ERROR": "Error extracting text from file",
    "EXPORT_ERROR": "Error generating export file",
    "UNAUTHORIZED": "Unauthorized access",
    "INTERNAL_ERROR": "Internal server error",
}
