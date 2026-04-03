"""File parsing service for extracting text from PDF and DOCX files."""

import logging
from pathlib import Path
from typing import Tuple
from app.utils.text_cleaning import normalize_text

logger = logging.getLogger(__name__)


class FileParserService:
    """
    Service for extracting text from uploaded documents.

    Supports:
    - PDF files (using PyMuPDF)
    - DOCX files (using python-docx)
    """

    @staticmethod
    def parse_file(file_path: str) -> Tuple[str, str]:
        """
        Parse file and extract text.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (extracted_text, file_type)

        Raises:
            ValueError: If file type not supported
            IOError: If file cannot be read
        """
        path = Path(file_path)

        if not path.exists():
            raise IOError(f"File not found: {file_path}")

        extension = path.suffix.lower()

        try:
            if extension == '.pdf':
                text = FileParserService._parse_pdf(file_path)
                return text, 'pdf'
            elif extension == '.docx':
                text = FileParserService._parse_docx(file_path)
                return text, 'docx'
            else:
                raise ValueError(f"Unsupported file type: {extension}")
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            raise

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """
        Extract text from PDF file using PyMuPDF.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF is required for PDF parsing. Install with: pip install pymupdf")

        logger.info(f"Parsing PDF: {file_path}")
        text_parts = []

        try:
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text:
                    text_parts.append(text)

            doc.close()

            # Combine text from all pages
            full_text = "\n\n".join(text_parts)

            # Normalize text
            full_text = normalize_text(full_text)

            logger.info(f"Successfully parsed PDF: {len(full_text)} characters extracted")
            return full_text

        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """
        Extract text from DOCX file using python-docx.

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required for DOCX parsing. Install with: pip install python-docx")

        logger.info(f"Parsing DOCX: {file_path}")

        try:
            doc = Document(file_path)
            text_parts = []

            # Extract text from paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text for cell in row.cells])
                    if row_text.strip():
                        text_parts.append(row_text)

            # Combine text
            full_text = "\n\n".join(text_parts)

            # Normalize text
            full_text = normalize_text(full_text)

            logger.info(f"Successfully parsed DOCX: {len(full_text)} characters extracted")
            return full_text

        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {str(e)}")
            raise

    @staticmethod
    def validate_file_content(file_content: bytes, file_extension: str) -> bool:
        """
        Validate that file content appears valid for the extension.

        Args:
            file_content: File content as bytes
            file_extension: File extension (e.g., 'pdf', 'docx')

        Returns:
            True if file appears valid
        """
        if not file_content or len(file_content) == 0:
            return False

        extension = file_extension.lower().lstrip('.')

        # Check magic bytes (file signatures)
        if extension == 'pdf':
            # PDF files start with %PDF
            return file_content.startswith(b'%PDF')
        elif extension == 'docx':
            # DOCX files are ZIP archives, start with PK
            return file_content.startswith(b'PK')

        return True
