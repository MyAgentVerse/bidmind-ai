"""File storage service for managing uploaded files."""

import os
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import get_settings
from app.core.security import SecurityUtils

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for managing file storage operations.

    Currently uses local filesystem storage.
    Can be extended to support S3, Azure Blob Storage, etc.
    """

    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = Path(self.settings.upload_dir)
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory ready: {self.upload_dir.absolute()}")

    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename for storage.

        Args:
            original_filename: The original uploaded filename

        Returns:
            A unique filename safe for storage
        """
        # Extract extension
        _, ext = os.path.splitext(original_filename)

        # Generate unique ID
        unique_id = uuid.uuid4().hex[:12]

        # Create filename: timestamp_uuid_ext
        stored_filename = f"{unique_id}{ext.lower()}"

        logger.debug(f"Generated unique filename: {original_filename} -> {stored_filename}")
        return stored_filename

    def save_file(self, file_content: bytes, original_filename: str) -> Tuple[str, str]:
        """
        Save uploaded file to storage.

        Args:
            file_content: File content as bytes
            original_filename: Original filename

        Returns:
            Tuple of (stored_filename, file_path)

        Raises:
            IOError: If file save fails
        """
        # Generate unique filename
        stored_filename = self.generate_unique_filename(original_filename)

        # Build full path
        file_path = self.upload_dir / stored_filename

        try:
            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info(f"File saved: {original_filename} -> {file_path}")
            return stored_filename, str(file_path)

        except IOError as e:
            logger.error(f"Failed to save file {original_filename}: {str(e)}")
            raise

    def read_file(self, stored_filename: str) -> bytes:
        """
        Read file from storage.

        Args:
            stored_filename: The stored filename (not original)

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.upload_dir / stored_filename

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {stored_filename}")

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content
        except IOError as e:
            logger.error(f"Failed to read file {stored_filename}: {str(e)}")
            raise

    def delete_file(self, stored_filename: str) -> bool:
        """
        Delete file from storage.

        Args:
            stored_filename: The stored filename

        Returns:
            True if deleted successfully, False otherwise
        """
        file_path = self.upload_dir / stored_filename

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except OSError as e:
            logger.error(f"Failed to delete file {stored_filename}: {str(e)}")
            return False

    def file_exists(self, stored_filename: str) -> bool:
        """Check if file exists in storage."""
        file_path = self.upload_dir / stored_filename
        return file_path.exists()

    def get_file_size(self, stored_filename: str) -> int:
        """Get file size in bytes."""
        file_path = self.upload_dir / stored_filename
        if file_path.exists():
            return file_path.stat().st_size
        return 0

    # TODO: Implement S3 storage backend
    """
    def save_file_s3(self, file_content: bytes, original_filename: str, bucket_name: str):
        '''Save file to S3 bucket.'''
        pass

    def read_file_s3(self, stored_filename: str, bucket_name: str) -> bytes:
        '''Read file from S3 bucket.'''
        pass
    """

    # TODO: Implement Azure Blob Storage backend
    """
    def save_file_azure(self, file_content: bytes, original_filename: str, container_name: str):
        '''Save file to Azure Blob Storage.'''
        pass
    """
