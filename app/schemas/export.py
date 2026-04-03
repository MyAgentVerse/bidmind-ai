"""Export-related schemas."""

from pydantic import BaseModel


class ExportDocxResponse(BaseModel):
    """Schema for DOCX export response."""
    message: str = "DOCX file generated successfully"
    filename: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "DOCX file generated successfully",
                "filename": "proposal_project_2024-01-15.docx"
            }
        }
