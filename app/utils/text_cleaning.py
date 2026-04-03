"""Text cleaning and normalization utilities."""

import re
from typing import List


def clean_whitespace(text: str) -> str:
    """
    Clean excessive whitespace from text.

    - Removes leading/trailing whitespace
    - Converts multiple spaces to single space
    - Converts multiple newlines to max 2 newlines
    """
    if not text:
        return ""

    # Remove leading/trailing whitespace
    text = text.strip()

    # Replace multiple spaces with single space (within lines)
    text = re.sub(r' +', ' ', text)

    # Replace multiple newlines with max 2 newlines
    text = re.sub(r'\n\n+', '\n\n', text)

    return text


def normalize_text(text: str) -> str:
    """
    Normalize text for processing.

    - Clean whitespace
    - Remove special characters that don't add value
    - Normalize unicode
    - Normalize line endings
    """
    if not text:
        return ""

    # Normalize unicode (NFKC normalization)
    import unicodedata
    text = unicodedata.normalize('NFKC', text)

    # Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove null characters
    text = text.replace('\x00', '')

    # Remove excessive control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Clean whitespace
    text = clean_whitespace(text)

    return text


def extract_paragraphs(text: str, min_length: int = 10) -> List[str]:
    """
    Extract paragraphs from text.

    - Splits by double newlines
    - Filters out very short paragraphs
    - Preserves paragraph structure
    """
    if not text:
        return []

    # Split by double newlines
    paragraphs = text.split('\n\n')

    # Filter and clean
    paragraphs = [
        p.strip()
        for p in paragraphs
        if len(p.strip()) >= min_length
    ]

    return paragraphs


def truncate_text(text: str, max_length: int = 3000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length, preserving word boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Leave room for suffix
    truncate_at = max_length - len(suffix)

    # Find last space before truncation point
    truncated = text[:truncate_at]
    last_space = truncated.rfind(' ')

    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + suffix


def remove_special_characters(text: str, keep_newlines: bool = True) -> str:
    """Remove special characters from text."""
    if not text:
        return ""

    # Keep alphanumeric, spaces, and newlines if requested
    if keep_newlines:
        text = re.sub(r'[^a-zA-Z0-9\s\n\-.,!?;:\'"()]', '', text)
    else:
        text = re.sub(r'[^a-zA-Z0-9\s\-.,!?;:\'"()]', '', text)

    return clean_whitespace(text)
