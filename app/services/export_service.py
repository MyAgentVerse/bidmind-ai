"""Export service for generating DOCX files from proposals."""

import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ProposalDraft

logger = logging.getLogger(__name__)


class ExportService:
    """
    Service for exporting proposals as DOCX files.

    Generates professional Word documents with proper formatting.
    """

    def __init__(self):
        self.settings = get_settings()
        self.export_dir = Path(self.settings.upload_dir) / "exports"
        self._ensure_export_dir()

    def _ensure_export_dir(self):
        """Create export directory if it doesn't exist."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Export directory ready: {self.export_dir.absolute()}")

    def generate_docx(
        self,
        proposal: ProposalDraft,
        project_title: str = "Proposal",
        db: Session = None
    ) -> str:
        """
        Generate DOCX file from proposal draft.

        Args:
            proposal: The ProposalDraft object
            project_title: Title for the proposal
            db: Database session (optional)

        Returns:
            Path to generated DOCX file

        Raises:
            ImportError: If python-docx is not installed
            IOError: If file write fails
        """
        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            raise ImportError("python-docx is required. Install with: pip install python-docx")

        logger.info(f"Generating DOCX for project {proposal.project_id}")

        try:
            # Create Document
            doc = Document()

            # Set default font
            style = doc.styles['Normal']
            style.font.name = 'Calibri'
            style.font.size = Pt(11)

            # Add title
            title = doc.add_heading(project_title, level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_format = title.runs[0]
            title_format.font.size = Pt(18)
            title_format.font.bold = True

            # Add date
            date_para = doc.add_paragraph(f"Submitted: {datetime.now().strftime('%B %d, %Y')}")
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Add page break
            doc.add_page_break()

            # Add table of contents placeholder
            toc_heading = doc.add_heading("Contents", level=1)

            # Create table of contents
            toc_items = [
                "1. Cover Letter",
                "2. Executive Summary",
                "3. Understanding of Requirements",
                "4. Proposed Solution / Approach",
                "5. Why Us",
                "6. Pricing Positioning",
                "7. Risk Mitigation",
                "8. Closing Statement"
            ]

            for item in toc_items:
                doc.add_paragraph(item, style='List Bullet')

            # Add sections
            sections_data = [
                ("Cover Letter", proposal.cover_letter),
                ("Executive Summary", proposal.executive_summary),
                ("Understanding of Requirements", proposal.understanding_of_requirements),
                ("Proposed Solution / Approach", proposal.proposed_solution),
                ("Why Us", proposal.why_us),
                ("Pricing Positioning", proposal.pricing_positioning),
                ("Risk Mitigation", proposal.risk_mitigation),
                ("Closing Statement", proposal.closing_statement),
            ]

            for section_title, section_text in sections_data:
                # Add page break between sections
                doc.add_page_break()

                # Add section heading
                heading = doc.add_heading(section_title, level=1)
                heading_format = heading.runs[0]
                heading_format.font.size = Pt(14)
                heading_format.font.bold = True

                # Add section content
                if section_text:
                    # Split text into paragraphs and add
                    paragraphs = section_text.split("\n\n")
                    for para_text in paragraphs:
                        if para_text.strip():
                            para = doc.add_paragraph(para_text.strip())
                            para_format = para.paragraph_format
                            para_format.line_spacing = 1.5
                            para_format.space_after = Pt(12)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"proposal_{project_title.replace(' ', '_')}_{timestamp}.docx"
            filepath = self.export_dir / filename

            # Save document
            doc.save(str(filepath))
            logger.info(f"DOCX exported successfully: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error generating DOCX: {str(e)}")
            raise IOError(f"Failed to generate DOCX file: {str(e)}")

    def get_export_filename(self, project_title: str) -> str:
        """Generate filename for export."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"proposal_{project_title.replace(' ', '_')}_{timestamp}.docx"

    def read_export_file(self, filepath: str) -> bytes:
        """
        Read exported file for download.

        Args:
            filepath: Path to the exported file

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(filepath)

        if not path.exists():
            logger.warning(f"Export file not found: {filepath}")
            raise FileNotFoundError(f"Export file not found: {filepath}")

        try:
            with open(path, 'rb') as f:
                return f.read()
        except IOError as e:
            logger.error(f"Error reading export file: {str(e)}")
            raise

    def cleanup_old_exports(self, days_old: int = 7) -> int:
        """
        Delete old export files.

        Args:
            days_old: Delete files older than this many days

        Returns:
            Number of files deleted
        """
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(days=days_old)
        deleted_count = 0

        try:
            for filepath in self.export_dir.glob("*.docx"):
                file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_time < cutoff_time:
                    filepath.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old export: {filepath}")

            logger.info(f"Cleanup complete: {deleted_count} old exports deleted")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return 0
