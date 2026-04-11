"""Analysis service for extracting opportunity intelligence from documents.

Phase 1 of the BidMind AI deep-analysis upgrade adds multi-document support:
a single project may have many uploaded files (the main RFP, addenda, the
SOW, pricing template, technical spec attachments, etc.) and they all need
to be analyzed together as one bid package.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AnalysisResult, Project, Company
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

    @staticmethod
    def combine_files_for_analysis(
        files: List[Tuple[str, str]]
    ) -> Tuple[str, List[str]]:
        """Combine multiple uploaded files into one analysis-ready document.

        Each file is wrapped with clear delimiters so the LLM can attribute
        every extracted requirement back to its source file. This is the
        "analyze the whole bid package" path: a real procurement opportunity
        is almost always main RFP + Q&A addenda + SOW + pricing template +
        technical specs, and they need to be reasoned about together.

        Args:
            files: List of ``(filename, extracted_text)`` tuples in the order
                they should appear in the combined document. The first file
                is treated as the primary document; subsequent files are
                addenda / attachments.

        Returns:
            ``(combined_text, list_of_filenames_used)``. Files with empty
            extracted text are skipped silently.
        """
        if not files:
            return "", []

        sections: List[str] = []
        used_filenames: List[str] = []

        # Pre-filter to files that actually have extractable text
        files_with_text = [(fn, txt) for fn, txt in files if txt and txt.strip()]
        total = len(files_with_text)

        for idx, (filename, text) in enumerate(files_with_text, start=1):
            used_filenames.append(filename)
            sections.append(
                f"===== DOCUMENT {idx} of {total}: {filename} =====\n\n"
                f"{text}\n\n"
                f"===== END OF {filename} ====="
            )

        combined = "\n\n".join(sections)
        return combined, used_filenames

    def _get_company_context(self, company_id: Optional[str], db: Session) -> Optional[str]:
        """
        Fetch company profile and format as context string.

        Args:
            company_id: The company ID
            db: Database session

        Returns:
            Formatted company context string or None
        """
        if not company_id:
            return None

        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return None

            context = f"""Company Name: {company.name}
Industry Focus: {company.industry_focus or 'Not specified'}
Unique Selling Proposition: {company.unique_selling_proposition or 'Not specified'}
Key Capabilities: {company.key_capabilities or 'Not specified'}
Experience: {company.experience or 'Not specified'}"""

            return context
        except Exception as e:
            logger.warning(f"Could not fetch company context: {str(e)}")
            return None

    async def analyze_document(
        self,
        project_id: str,
        extracted_text: str,
        db: Session,
        company_id: Optional[str] = None,
        source_files: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """
        Analyze extracted document text and save results.

        Args:
            project_id: The project ID
            extracted_text: The extracted text. May be a single document or
                a multi-file bid package combined via
                :meth:`combine_files_for_analysis`.
            db: Database session
            company_id: Optional company ID for personalized analysis
            source_files: Optional list of filenames that make up this bid
                package. When supplied, the prompt is told the package is
                multi-document and asked to attribute extracted items back
                to the right file. The list is also persisted in
                ``raw_ai_json`` so the API can show it to the user.

        Returns:
            AnalysisResult object

        Raises:
            ValueError: If analysis fails
        """
        if source_files and len(source_files) > 1:
            logger.info(
                f"Starting multi-document analysis for project {project_id} "
                f"({len(source_files)} files: {source_files})"
            )
        else:
            logger.info(f"Starting analysis for project {project_id}")

        # Get company context if available
        company_context = self._get_company_context(company_id, db)
        if company_context:
            logger.info(f"Using company context for project {project_id}")

        # Generate analysis prompt with company context and file list
        prompt = get_analysis_prompt(extracted_text, company_context, source_files)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            response_text = response.choices[0].message.content

            # Parse JSON response
            analysis_data = self._parse_analysis_response(response_text)

            # Stash the source files alongside the raw AI output so we can
            # surface "this analysis covered files X, Y, Z" in the API
            # response and audit which files contributed to a given analysis.
            if source_files:
                analysis_data["_source_files"] = source_files

            # Check if analysis already exists for this project (upsert pattern)
            existing_analysis = db.query(AnalysisResult).filter(
                AnalysisResult.project_id == project_id
            ).first()

            if existing_analysis:
                # Update existing analysis
                existing_analysis.document_type = analysis_data.get("document_type")
                existing_analysis.opportunity_summary = analysis_data.get("opportunity_summary")
                existing_analysis.scope_of_work = analysis_data.get("scope_of_work")
                existing_analysis.mandatory_requirements = analysis_data.get("mandatory_requirements")
                existing_analysis.deadlines = analysis_data.get("deadlines")
                existing_analysis.evaluation_criteria = analysis_data.get("evaluation_criteria")
                existing_analysis.budget_clues = analysis_data.get("budget_clues")
                existing_analysis.risks = analysis_data.get("risks")
                existing_analysis.fit_score = analysis_data.get("fit_score")
                existing_analysis.usp_suggestions = analysis_data.get("usp_suggestions")
                existing_analysis.pricing_strategy_summary = analysis_data.get("pricing_strategy_summary")
                existing_analysis.raw_ai_json = analysis_data
                existing_analysis.updated_at = datetime.utcnow()
                analysis_result = existing_analysis
            else:
                # Create new analysis
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
                db.add(analysis_result)

            # Update project status and company_id if provided
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "analyzed"
                if company_id and not project.company_id:
                    project.company_id = company_id

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
