"""Dependency injection for API routes."""

from app.core.database import get_db
from app.services import (
    StorageService,
    FileParserService,
    AnalysisService,
    ProposalService,
    AIEditService,
    ExportService,
)

# Initialize services (these are singletons)
storage_service = StorageService()
file_parser_service = FileParserService()
analysis_service = AnalysisService()
proposal_service = ProposalService()
ai_edit_service = AIEditService()
export_service = ExportService()


# Export all
__all__ = [
    "get_db",
    "storage_service",
    "file_parser_service",
    "analysis_service",
    "proposal_service",
    "ai_edit_service",
    "export_service",
]
