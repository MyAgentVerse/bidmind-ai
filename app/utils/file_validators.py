"""File validation utilities."""

from typing import Tuple
from app.core.config import get_settings


def validate_file_type(filename: str, mime_type: str) -> Tuple[bool, str]:
    """
    Validate that file type is allowed.

    Args:
        filename: The uploaded filename
        mime_type: The MIME type of the file

    Returns:
        Tuple of (is_valid, error_message)
    """
    settings = get_settings()
    allowed_extensions = settings.get_allowed_extensions
    allowed_mimes = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    # Check extension
    extension = filename.split('.')[-1].lower() if '.' in filename else ""

    if extension not in allowed_extensions:
        return False, f"File type '.{extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"

    # Check MIME type
    expected_mime = allowed_mimes.get(extension)
    if expected_mime and mime_type != expected_mime:
        return False, f"Invalid MIME type for .{extension} file. Expected {expected_mime}, got {mime_type}"

    return True, ""


def validate_file_size(file_size: int) -> Tuple[bool, str]:
    """
    Validate that file size is within limits.

    Args:
        file_size: File size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    settings = get_settings()
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        max_mb = settings.max_file_size_mb
        actual_mb = file_size / (1024 * 1024)
        return False, f"File size ({actual_mb:.1f}MB) exceeds maximum allowed size ({max_mb}MB)"

    if file_size == 0:
        return False, "File is empty"

    return True, ""


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    if '.' not in filename:
        return ""
    return filename.split('.')[-1].lower()


def validate_filename_safety(filename: str) -> Tuple[bool, str]:
    """
    Validate that filename is safe to process.

    Args:
        filename: The filename to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Check for path traversal attempts
    dangerous_patterns = ["../", "..\\", "\x00"]
    for pattern in dangerous_patterns:
        if pattern in filename.lower():
            return False, "Filename contains unsafe characters"

    # Check filename length
    if len(filename) > 255:
        return False, "Filename is too long (max 255 characters)"

    if len(filename) == 0:
        return False, "Filename is empty"

    return True, ""
