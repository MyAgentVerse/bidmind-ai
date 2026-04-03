"""Analysis service for extracting opportunity intelligence from documents."""

import logging
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AnalysisResult, Project
from app.prompts.analysis_prompts import get_analysis_prompt

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service for analyzing procurement documents using OpenAI.

    Extracts structured intelligence from document text and saves results.
    """

    def __init__(self):
        self.settings = get_settings()
        self._initialize_openai_client()

    def _initialize_openai_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.settings.openai_api_key)
        except ImportError:
            raise ImportError("OpenAI library is required. Install with: pip install openai")

    async def analyze_document(
        self,
        project_id: str,
        extracted_text: str,
        db: Session
    ) -> AnalysisResult:
        """
        Analyze extracted document text and save results.

        Args:
            project_id: The project ID
            extracted_text: The extracted text from the document
            db: Database session

        Returns:
            AnalysisResult object

        Raises:
            ValueError: If analysis fails
        """
        logger.info(f"Starting analysis for project {project_id}")

        # Generate analysis prompt
        prompt = get_analysis_prompt(extracted_text)

        try:
            # Call OpenAI API with structured output
            response = self.client.beta.messages.create(
                model=self.settings.openai_model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                betas=["interleaved-thinking-2025-05-14"],  # Optional: for extended thinking
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse JSON response
            analysis_data = self._parse_analysis_response(response_text)

            # Create analysis result in database
            analysis_result = AnalysisResult(
                project_id=project_id,
                document_type=analysis_data.get("document_type"),
                opportunity_summary=analysis_data.get("opportunity_summary"),
                scope_of_work=analysis_data.get("scope_of_work"),
                mandatory_requirements=analysis_data.get("mandatory_requirements"),
                deadlines=analysis_data.get("deadlines"),
                evaluation_criteria=analysis_data.get("evaluation_criteria"),
                budget_clues=analysis_data.get("budget_clues"),
                risks=analysis_data.get("risks"),
                fit_score=analysis_data.get("fit_score"),
                usp_suggestions=analysis_data.get("usp_suggestions"),
                pricing_strategy_summary=analysis_data.get("pricing_strategy_summary"),
                raw_ai_json=analysis_data
            )

            # Save to database
            db.add(analysis_result)

            # Update project status
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "analyzed"

            db.commit()
            logger.info(f"Analysis completed for project {project_id}")

            return analysis_result

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            db.rollback()
            raise ValueError(f"Failed to analyze document: {str(e)}")

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate AI analysis response.

        Args:
            response_text: Raw response from OpenAI

        Returns:
            Parsed analysis data as dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        try:
            # Extract JSON from response
            analysis_data = json.loads(response_text)
            logger.debug(f"Successfully parsed analysis response")
            return analysis_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response as JSON: {str(e)}")
            # Try to extract JSON from markdown code block
            if "```json" in response_text:
                try:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    json_str = response_text[start:end].strip()
                    return json.loads(json_str)
                except (json.JSONDecodeError, ValueError):
                    pass

            raise ValueError("AI response is not valid JSON")

    def get_analysis_result(self, project_id: str, db: Session) -> Optional[AnalysisResult]:
        """
        Retrieve analysis result for a project.

        Args:
            project_id: The project ID
            db: Database session

        Returns:
            AnalysisResult or None if not found
        """
        return db.query(AnalysisResult).filter(
            AnalysisResult.project_id == project_id
        ).first()
