"""Proposal service for generating grounded, coherent proposal sections.

Phase 2 of the BidMind AI deep-analysis upgrade.

Key changes from Phase 1:

  - **Sequential generation** instead of parallel ``asyncio.gather()``.
    Sections are generated in dependency order so each section can see
    what prior sections wrote, producing a coherent narrative instead of
    8 disconnected blobs.

  - **Chunk retrieval** via ``ChunkRetriever``. Each section prompt
    receives the most relevant RFP chunks (with page citations) and
    compliance matrix entries, instead of tiny pre-extracted slices.

  - **Single shared AsyncOpenAI client** per request. Created via
    ``async with`` at the top of ``generate_proposal`` and passed to
    each sequential call. No singleton, no cross-loop binding issues.

  - **Self-critique** via ``ProposalReviewer``. After generation,
    a deterministic compliance coverage check runs and the result
    is logged (and optionally stored).

The public API is unchanged:
  - ``generate_proposal(project_id, db, company_id)`` -> ``ProposalDraft``
  - ``get_proposal_draft(project_id, db)`` -> ``Optional[ProposalDraft]``
  - ``update_proposal_section(project_id, section_name, text, db)``
  - ``generate_proposal_background(project_id, company_id)``
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ProposalDraft, AnalysisResult, Project, UploadedFile
from app.models import Company, CompanyWritingPreferences
from app.services.file_parser_service import FileParserService
from app.services.chunk_retriever import ChunkRetriever
from app.prompts.proposal_prompts import (
    get_understanding_prompt,
    get_solution_prompt,
    get_why_us_prompt,
    get_risk_mitigation_prompt,
    get_pricing_prompt,
    get_executive_summary_prompt,
    get_cover_letter_prompt,
    get_closing_prompt,
)
from app.prompts.writing_preferences_helpers import enhance_section_prompt

logger = logging.getLogger(__name__)


# Section generation order. Later sections see all prior sections.
GENERATION_ORDER = [
    "understanding_of_requirements",
    "proposed_solution",
    "why_us",
    "risk_mitigation",
    "pricing_positioning",
    "executive_summary",
    "cover_letter",
    "closing_statement",
]

# Maps section names to their prompt-building functions
PROMPT_FUNCTIONS = {
    "understanding_of_requirements": get_understanding_prompt,
    "proposed_solution": get_solution_prompt,
    "why_us": get_why_us_prompt,
    "risk_mitigation": get_risk_mitigation_prompt,
    "pricing_positioning": get_pricing_prompt,
    "executive_summary": get_executive_summary_prompt,
    "cover_letter": get_cover_letter_prompt,
    "closing_statement": get_closing_prompt,
}


class ProposalService:
    """Service for generating grounded, coherent proposal sections."""

    def __init__(self):
        self.settings = get_settings()
        self._initialize_openai_client()

    def _initialize_openai_client(self):
        """Verify the OpenAI library is installed."""
        try:
            from openai import AsyncOpenAI  # noqa: F401
        except ImportError:
            raise ImportError(
                "OpenAI library is required. Install with: pip install openai"
            )

    # ---- Company / preferences helpers -----------------------------------

    def _get_company_dict(
        self, company_id: Optional[str], db: Session
    ) -> Optional[Dict[str, Any]]:
        """Fetch company profile as a dict."""
        if not company_id:
            return None
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return None
            return {
                "name": company.name,
                "description": company.description,
                "usp": company.unique_selling_proposition,
                "capabilities": company.key_capabilities,
                "experience": company.experience,
                "industry_focus": company.industry_focus,
            }
        except Exception as e:
            logger.warning(f"Could not fetch company data: {e}")
            return None

    def _get_writing_preferences(
        self, company_id: Optional[str], db: Session
    ) -> Optional[Dict[str, Any]]:
        """Fetch company writing preferences as a dict."""
        if not company_id:
            return None
        try:
            prefs = (
                db.query(CompanyWritingPreferences)
                .filter(CompanyWritingPreferences.company_id == company_id)
                .first()
            )
            if not prefs:
                return None
            logger.info(f"Using writing preferences for company {company_id}")
            return prefs.to_dict()
        except Exception as e:
            logger.warning(f"Could not fetch writing preferences: {e}")
            return None

    # ---- Chunk retrieval -------------------------------------------------

    def _build_retriever(
        self, project_id: str, analysis: AnalysisResult, db: Session
    ) -> ChunkRetriever:
        """Re-parse uploaded files to get chunks, then build a retriever.

        The upload route stores ``extracted_text`` but not the structured
        ``DocumentChunk`` list. We re-parse from ``file_path`` on disk.
        This is fast (~50ms for a 50-page PDF) and avoids a migration.
        """
        all_chunks: list = []

        uploaded_files = (
            db.query(UploadedFile)
            .filter(UploadedFile.project_id == project_id)
            .order_by(UploadedFile.created_at.asc())
            .all()
        )

        for uf in uploaded_files:
            try:
                parsed = FileParserService.parse_file_structured(uf.file_path)
                all_chunks.extend(parsed.chunks)
            except Exception as e:
                logger.warning(
                    f"Could not re-parse {uf.file_path} for chunks: {e}"
                )

        compliance_matrix = analysis.compliance_matrix or []
        logger.info(
            f"Built retriever: {len(all_chunks)} chunks, "
            f"{len(compliance_matrix)} compliance entries"
        )
        return ChunkRetriever(all_chunks, compliance_matrix)

    # ---- Analysis dict builder -------------------------------------------

    @staticmethod
    def _build_analysis_dict(analysis: AnalysisResult) -> Dict[str, Any]:
        """Convert AnalysisResult ORM to a dict with all 30 fields."""
        return {
            "opportunity_summary": analysis.opportunity_summary,
            "scope_of_work": analysis.scope_of_work,
            "mandatory_requirements": analysis.mandatory_requirements,
            "deadlines": analysis.deadlines,
            "evaluation_criteria": analysis.evaluation_criteria,
            "budget_clues": analysis.budget_clues,
            "risks": analysis.risks,
            "fit_score": analysis.fit_score,
            "usp_suggestions": analysis.usp_suggestions,
            "pricing_strategy_summary": analysis.pricing_strategy_summary,
            "document_type": analysis.document_type,
            "eligibility_requirements": analysis.eligibility_requirements,
            "compliance_matrix": analysis.compliance_matrix,
            "submission_instructions": analysis.submission_instructions,
            "pricing_format": analysis.pricing_format,
            "key_personnel_requirements": analysis.key_personnel_requirements,
            "naics_codes": analysis.naics_codes,
            "set_aside_status": analysis.set_aside_status,
            "contract_type": analysis.contract_type,
            "period_of_performance": analysis.period_of_performance,
            "place_of_performance": analysis.place_of_performance,
            "estimated_value": analysis.estimated_value,
            "contracting_officer": analysis.contracting_officer,
        }

    # ---- Core generation -------------------------------------------------

    async def generate_proposal(
        self,
        project_id: str,
        db: Session,
        company_id: Optional[str] = None,
    ) -> ProposalDraft:
        """Generate a complete, grounded proposal from analysis results.

        Phase 2: sections are generated sequentially in dependency order.
        Each section sees retrieved RFP chunks, compliance entries, the
        full analysis, and all previously generated sections.
        """
        logger.info(f"Starting Phase 2 proposal generation for project {project_id}")

        # 1. Load analysis
        analysis = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.project_id == project_id)
            .first()
        )
        if not analysis:
            raise ValueError(f"No analysis results found for project {project_id}")

        analysis_dict = self._build_analysis_dict(analysis)

        # 2. Load company + preferences
        company_data = self._get_company_dict(company_id, db)
        writing_preferences = self._get_writing_preferences(company_id, db)

        # 3. Build chunk retriever
        retriever = self._build_retriever(project_id, analysis, db)

        # 4. Sequential generation
        sections: Dict[str, str] = {}

        try:
            from openai import AsyncOpenAI

            async with AsyncOpenAI(
                api_key=self.settings.openai_api_key
            ) as client:
                for idx, section_name in enumerate(GENERATION_ORDER, 1):
                    logger.info(
                        f"Generating {idx}/{len(GENERATION_ORDER)}: {section_name}"
                    )

                    # Retrieve relevant chunks
                    context = retriever.retrieve_for_section(section_name)

                    # Build grounded prompt
                    prompt_fn = PROMPT_FUNCTIONS[section_name]
                    base_prompt = prompt_fn(
                        analysis_data=analysis_dict,
                        retrieved_context=context,
                        prior_sections=sections,
                        company=company_data,
                    )

                    # Apply writing preferences
                    final_prompt = enhance_section_prompt(
                        base_prompt, section_name, writing_preferences
                    )

                    # Generate
                    sections[section_name] = await self._generate_section(
                        client, final_prompt
                    )

            # 5. Compliance coverage check
            try:
                from app.services.proposal_reviewer import ProposalReviewer

                reviewer = ProposalReviewer()
                review = reviewer.review_coverage(
                    sections, analysis.compliance_matrix or []
                )
                logger.info(
                    f"Coverage: {review.coverage_percentage:.0f}% total, "
                    f"{review.must_coverage_percentage:.0f}% mandatory. "
                    f"Gaps: {len(review.gaps)}"
                )
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Coverage check failed (non-fatal): {e}")

            # 6. Save to database
            existing = (
                db.query(ProposalDraft)
                .filter(ProposalDraft.project_id == project_id)
                .first()
            )
            if existing:
                for k, v in sections.items():
                    setattr(existing, k, v)
                proposal = existing
            else:
                proposal = ProposalDraft(project_id=project_id, **sections)
                db.add(proposal)

            # Update project status
            project = (
                db.query(Project).filter(Project.id == project_id).first()
            )
            if project:
                project.status = "proposal_generated"
                if company_id and not project.company_id:
                    project.company_id = company_id

            db.commit()
            logger.info(f"Proposal generation completed for {project_id}")
            return proposal

        except Exception as e:
            logger.error(f"Error generating proposal: {e}")
            db.rollback()
            raise ValueError(f"Failed to generate proposal: {e}")

    async def _generate_section(self, client, prompt: str) -> str:
        """Generate a single section using the shared AsyncOpenAI client."""
        try:
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating section: {e}")
            raise ValueError(f"Failed to generate proposal section: {e}")

    # ---- Read / update helpers (unchanged) --------------------------------

    def get_proposal_draft(
        self, project_id: str, db: Session
    ) -> Optional[ProposalDraft]:
        """Retrieve proposal draft for a project."""
        return (
            db.query(ProposalDraft)
            .filter(ProposalDraft.project_id == project_id)
            .first()
        )

    def update_proposal_section(
        self,
        project_id: str,
        section_name: str,
        section_text: str,
        db: Session,
    ) -> ProposalDraft:
        """Update a single proposal section."""
        if section_name not in ProposalDraft.SECTION_ORDER:
            raise ValueError(f"Invalid section name: {section_name}")

        proposal = self.get_proposal_draft(project_id, db)
        if not proposal:
            raise ValueError(f"Proposal not found for project {project_id}")

        setattr(proposal, section_name, section_text)
        db.commit()
        return proposal

    def get_proposal_dict(self, proposal: ProposalDraft) -> dict:
        """Convert proposal to dictionary with ordered sections."""
        return proposal.to_dict()

    def generate_proposal_background(
        self, project_id: str, company_id: Optional[str] = None
    ) -> None:
        """Generate proposal in background (for BackgroundTasks)."""
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                self.generate_proposal(project_id, db, company_id)
            )
            logger.info(f"Background proposal generation completed for {project_id}")
        except Exception as e:
            logger.error(f"Background proposal generation failed for {project_id}: {e}")
        finally:
            db.close()
