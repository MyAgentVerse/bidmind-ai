"""Analysis service for extracting opportunity intelligence from documents.

Phase 1 of the BidMind AI deep-analysis upgrade adds:

  - Multi-document support (Step 2): a single project may have many uploaded
    files (the main RFP, addenda, the SOW, pricing template, technical spec
    attachments, etc.) and they all need to be analyzed together as one bid
    package.
  - Per-call ``AsyncOpenAI`` clients (Step A): no more singleton client
    bound to a single event loop, no more blocking the FastAPI loop.
  - Structured outputs + Pydantic validation + retry (Step B): the LLM call
    runs in JSON mode, the response is parsed and validated against
    ``AnalysisExtraction`` (the Pydantic source-of-truth schema), and on
    validation failure we retry up to 3 times with the validation error fed
    back to the model. Retry attempts intentionally do **not** re-send the
    full document — they ask the model to fix its previous response, which
    is far cheaper and almost always sufficient.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AnalysisResult, Project, Company
from app.prompts.analysis_prompts import get_analysis_prompt
from app.schemas.analysis_extraction import AnalysisExtraction


# Maximum number of times we'll ask the LLM to fix a malformed analysis
# response before giving up. The first attempt is the real call; attempts
# 2 and 3 only re-send the previous (broken) response and the validation
# error, NOT the full document — so retries are cheap.
MAX_ANALYSIS_ATTEMPTS = 3

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
        """Verify the OpenAI library is installed.

        We do **not** store a singleton client. The service is instantiated
        once at import time (see ``app/api/deps.py``) but the OpenAI calls
        run inside async request handlers and inside background tasks that
        spawn their own event loops. ``AsyncOpenAI``'s underlying httpx
        connection pool binds to the loop in which it's first awaited, so
        sharing a single instance across loops crashes with cross-loop
        errors.

        Solution: create a fresh ``AsyncOpenAI`` (via ``async with``) inside
        each method. Per-call cost is negligible (a few hundred microseconds
        for the connection pool setup) and the code is bulletproof.
        """
        try:
            from openai import AsyncOpenAI  # noqa: F401  (import check only)
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
            # Run the analysis call with JSON-mode + Pydantic validation +
            # retry-on-validation-failure. Returns a dict that has already
            # been validated against AnalysisExtraction.
            analysis_data = await self._call_with_validation_retry(prompt)

            # Stash the source files alongside the raw AI output so we can
            # surface "this analysis covered files X, Y, Z" in the API
            # response and audit which files contributed to a given analysis.
            if source_files:
                analysis_data["_source_files"] = source_files

            # Check if analysis already exists for this project (upsert pattern)
            existing_analysis = db.query(AnalysisResult).filter(
                AnalysisResult.project_id == project_id
            ).first()

            # Map validated analysis_data to ORM column kwargs.
            # The new Step C columns are JSONB and accept the raw dicts/lists
            # straight from the validated Pydantic dump.
            column_kwargs = {
                # Core (Step B)
                "document_type": analysis_data.get("document_type"),
                "opportunity_summary": analysis_data.get("opportunity_summary"),
                "scope_of_work": analysis_data.get("scope_of_work"),
                "mandatory_requirements": analysis_data.get("mandatory_requirements"),
                "deadlines": analysis_data.get("deadlines"),
                "evaluation_criteria": analysis_data.get("evaluation_criteria"),
                "budget_clues": analysis_data.get("budget_clues"),
                "risks": analysis_data.get("risks"),
                "fit_score": analysis_data.get("fit_score"),
                "usp_suggestions": analysis_data.get("usp_suggestions"),
                "pricing_strategy_summary": analysis_data.get("pricing_strategy_summary"),
                # New in Step C (queryable / dedicated columns)
                "eligibility_requirements": analysis_data.get("eligibility_requirements"),
                "compliance_matrix": analysis_data.get("compliance_matrix"),
                "submission_instructions": analysis_data.get("submission_instructions"),
                "pricing_format": analysis_data.get("pricing_format"),
                "key_personnel_requirements": analysis_data.get("key_personnel_requirements"),
                "naics_codes": analysis_data.get("naics_codes"),
                "set_aside_status": analysis_data.get("set_aside_status"),
                "contract_type": analysis_data.get("contract_type"),
                "period_of_performance": analysis_data.get("period_of_performance"),
                "place_of_performance": analysis_data.get("place_of_performance"),
                "estimated_value": analysis_data.get("estimated_value"),
                "contracting_officer": analysis_data.get("contracting_officer"),
                # raw_ai_json holds the full validated dict + the
                # less-queryable Step C fields (required_forms,
                # past_performance_requirements, insurance_requirements,
                # clauses_by_reference, wage_determinations,
                # protest_procedures, funding_source) plus _source_files.
                "raw_ai_json": analysis_data,
            }

            if existing_analysis:
                for k, v in column_kwargs.items():
                    setattr(existing_analysis, k, v)
                existing_analysis.updated_at = datetime.utcnow()
                analysis_result = existing_analysis
            else:
                analysis_result = AnalysisResult(
                    project_id=project_id,
                    **column_kwargs,
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

    async def _call_with_validation_retry(
        self,
        prompt: str,
        max_attempts: int = MAX_ANALYSIS_ATTEMPTS,
    ) -> Dict[str, Any]:
        """Call the LLM in JSON mode and validate the response.

        Strategy:
            1. Call OpenAI with ``response_format={"type": "json_object"}``
               so the model is forced to return syntactically valid JSON.
            2. Parse the JSON.
            3. Validate the parsed dict against ``AnalysisExtraction`` (the
               Pydantic source-of-truth schema).
            4. If validation fails, send the model only its previous response
               and the validation error, asking it to fix the issues. We do
               **not** re-send the full document — the model already saw it
               on attempt 1, and the document text often dominates the input
               token count.
            5. After ``max_attempts`` failures, raise ``ValueError``.

        Returns:
            A dict that has been validated against ``AnalysisExtraction``
            and is safe to write to the database. Note: this is the
            ``model_dump()`` output, so callers can still attach extra keys
            (like ``_source_files``) afterwards.
        """
        from openai import AsyncOpenAI

        last_error: Optional[str] = None
        last_response_text: Optional[str] = None

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            for attempt in range(1, max_attempts + 1):
                # On attempt 1 we send the real prompt. On retries we send
                # only the previous response + the validation error so the
                # model can fix the structure without re-reading the doc.
                if attempt == 1:
                    messages = [{"role": "user", "content": prompt}]
                else:
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are correcting a JSON validation error "
                                "from your previous response. Return ONLY the "
                                "corrected JSON object that fixes the listed "
                                "errors while keeping the substance of your "
                                "previous analysis. Do not add commentary."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Your previous response was:\n\n"
                                f"{last_response_text}\n\n"
                                f"It failed validation with these errors:\n"
                                f"{last_error}\n\n"
                                f"Return the corrected JSON now."
                            ),
                        },
                    ]

                try:
                    response = await client.chat.completions.create(
                        model=self.settings.openai_model,
                        max_tokens=4096,
                        # JSON mode: forces syntactically valid JSON.
                        # Available in openai>=1.3 on gpt-4-1106-preview,
                        # gpt-4-turbo-preview, gpt-3.5-turbo-1106, and later.
                        response_format={"type": "json_object"},
                        messages=messages,
                    )
                except Exception as e:
                    # Network / API errors — log and retry. We do NOT
                    # consume our validation-retry budget on these because
                    # the budget is meant for *fixable* output errors.
                    logger.error(
                        f"Analysis API call failed on attempt {attempt}: {e}"
                    )
                    last_error = f"API error: {e}"
                    if attempt == max_attempts:
                        raise ValueError(
                            f"OpenAI API failed after {max_attempts} attempts: {e}"
                        )
                    continue

                response_text = response.choices[0].message.content or ""
                last_response_text = response_text

                # Parse JSON. JSON mode should guarantee syntactic validity,
                # but we still try to be tolerant of edge cases (markdown
                # code fences, leading prose, etc.).
                try:
                    raw_dict = self._parse_json_text(response_text)
                except ValueError as e:
                    logger.warning(
                        f"Attempt {attempt}: response was not valid JSON "
                        f"despite JSON mode: {e}"
                    )
                    last_error = f"Response was not valid JSON: {e}"
                    continue

                # Validate against the Pydantic schema. The model has built-in
                # coercers for common LLM sloppiness (string fit_score, single
                # string instead of list, etc.) so this often passes even when
                # the raw output isn't a perfect match.
                try:
                    validated = AnalysisExtraction.model_validate(raw_dict)
                except ValidationError as e:
                    logger.warning(
                        f"Attempt {attempt}: Pydantic validation failed: {e}"
                    )
                    last_error = self._format_validation_error(e)
                    continue

                logger.info(
                    f"Analysis validated successfully on attempt {attempt}"
                )
                return validated.model_dump()

        # All retries exhausted with a validation error (not an API error)
        raise ValueError(
            f"Failed to obtain a valid analysis after {max_attempts} "
            f"attempts. Last validation error: {last_error}"
        )

    @staticmethod
    def _parse_json_text(response_text: str) -> Dict[str, Any]:
        """Parse a JSON object from an LLM response, tolerating common noise.

        JSON mode should guarantee a clean object, but on rare occasions the
        model still wraps it in a markdown code fence or adds a leading
        sentence. This helper strips both before parsing.
        """
        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            # Drop the first line (``` or ```json)
            text = text.split("\n", 1)[1] if "\n" in text else text
            # Drop the trailing fence
            if text.endswith("```"):
                text = text[: -3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Last-ditch: find the first { and last } and try to parse
            # that substring.
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last != -1 and last > first:
                try:
                    return json.loads(text[first : last + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(str(e))

    @staticmethod
    def _format_validation_error(err: ValidationError) -> str:
        """Format a Pydantic ValidationError into a short, model-friendly hint."""
        lines = []
        for e in err.errors():
            loc = ".".join(str(part) for part in e.get("loc", ())) or "(root)"
            msg = e.get("msg", "invalid")
            lines.append(f"  - {loc}: {msg}")
        return "\n".join(lines) if lines else str(err)

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
