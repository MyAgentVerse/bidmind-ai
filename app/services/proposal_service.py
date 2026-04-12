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
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ProposalDraft, AnalysisResult, Project, UploadedFile
from app.models import Company, CompanyWritingPreferences
from app.services.file_parser_service import FileParserService
from app.services.chunk_retriever import ChunkRetriever, SECTION_RELEVANCE
from app.services.embedding_service import EmbeddingService
from app.services.learning_service import LearningService
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

    async def _build_retriever_and_embeddings(
        self, project_id: str, analysis: AnalysisResult, db: Session
    ) -> Tuple[ChunkRetriever, Optional[EmbeddingService]]:
        """Re-parse files, build retriever, and lazily create embeddings.

        Phase 3: if pgvector is available and embeddings don't exist yet
        for this project, embed all chunks and store them. This adds ~2-5s
        on first run but enables semantic search for all subsequent
        proposal generations.

        Returns:
            (retriever, embedding_service_or_None)
        """
        all_chunks: list = []
        file_chunks: list = []  # (file_id, chunks) pairs for embedding

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
                file_chunks.append((str(uf.id), parsed.chunks))
            except Exception as e:
                logger.warning(
                    f"Could not re-parse {uf.file_path} for chunks: {e}"
                )

        compliance_matrix = analysis.compliance_matrix or []
        retriever = ChunkRetriever(all_chunks, compliance_matrix)

        # Phase 3: lazy embedding
        embedding_service = None
        try:
            embedding_service = EmbeddingService()

            if not embedding_service.has_embeddings(project_id, db):
                logger.info(
                    f"Creating embeddings for project {project_id} "
                    f"({len(all_chunks)} chunks)"
                )
                total_embedded = 0
                for file_id, chunks in file_chunks:
                    count = await embedding_service.embed_and_store_chunks(
                        project_id, file_id, chunks, db
                    )
                    total_embedded += count
                db.commit()
                logger.info(f"Embedded {total_embedded} chunks for project {project_id}")
            else:
                logger.info(f"Reusing existing embeddings for project {project_id}")

        except Exception as e:
            logger.warning(
                f"Embedding setup failed (non-fatal, falling back to "
                f"keyword-only retrieval): {e}"
            )
            embedding_service = None

        logger.info(
            f"Built retriever: {len(all_chunks)} chunks, "
            f"{len(compliance_matrix)} compliance entries, "
            f"embeddings={'yes' if embedding_service else 'no'}"
        )
        return retriever, embedding_service

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

        # 3. Phase 5: Retrieve learned preferences from past feedback
        org_learnings = None
        try:
            org_id = None
            project = db.query(Project).filter(Project.id == project_id).first()
            if project and hasattr(project, "organization_id"):
                org_id = str(project.organization_id) if project.organization_id else None

            if org_id:
                learning_svc = LearningService()
                org_learnings = learning_svc.get_learnings_for_prompt(org_id, db)
                if org_learnings:
                    logger.info(
                        f"Using learned preferences for org {org_id}: "
                        f"{org_learnings.get('total_feedback', 0)} feedback entries, "
                        f"{org_learnings.get('satisfaction_rate', 0)}% satisfaction"
                    )
        except Exception as e:
            db.rollback()  # Clear failed transaction so subsequent queries work
            logger.debug(f"Could not load org learnings (non-fatal): {e}")

        # 4. Build chunk retriever + create embeddings if needed
        retriever, embedding_service = await self._build_retriever_and_embeddings(
            project_id, analysis, db
        )

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

                    # Retrieve relevant chunks (hybrid if embeddings available)
                    if embedding_service:
                        context = await self._retrieve_hybrid(
                            retriever, embedding_service,
                            section_name, project_id, db
                        )
                    else:
                        context = retriever.retrieve_for_section(section_name)

                    # Build grounded prompt (with learnings from Phase 5)
                    prompt_fn = PROMPT_FUNCTIONS[section_name]
                    base_prompt = prompt_fn(
                        analysis_data=analysis_dict,
                        retrieved_context=context,
                        prior_sections=sections,
                        company=company_data,
                        learnings=org_learnings,
                    )

                    # Apply writing preferences
                    final_prompt = enhance_section_prompt(
                        base_prompt, section_name, writing_preferences
                    )

                    # Generate
                    sections[section_name] = await self._generate_section(
                        client, final_prompt
                    )

            # 5. Phase 4: LLM-enhanced compliance review + targeted revision
            try:
                from app.services.proposal_reviewer import ProposalReviewer

                reviewer = ProposalReviewer()

                # Stage 1: deterministic keyword check
                review = reviewer.review_coverage(
                    sections, analysis.compliance_matrix or []
                )
                logger.info(
                    f"Deterministic coverage: {review.coverage_percentage:.0f}% "
                    f"({review.must_coverage_percentage:.0f}% must). "
                    f"Gaps: {len(review.gaps)}"
                )

                # Stage 2: if there are gaps, ask the LLM to confirm them
                if review.gaps:
                    logger.info(
                        f"Running LLM gap confirmation on {len(review.gaps)} "
                        f"potential gap(s)..."
                    )
                    review = await reviewer.review_coverage_with_llm(
                        sections, analysis.compliance_matrix or []
                    )
                    logger.info(
                        f"After LLM review: {review.coverage_percentage:.0f}% "
                        f"coverage, {len(review.gaps)} confirmed gap(s)"
                    )

                # Stage 3: if confirmed gaps remain, revise affected sections
                if review.gaps:
                    logger.info(
                        f"Revising {len(review.sections_needing_revision)} "
                        f"section(s) to address {len(review.gaps)} gap(s)..."
                    )
                    sections, review = await reviewer.revise_sections_for_gaps(
                        sections, review, retriever, analysis_dict, company_data
                    )
                    logger.info(
                        f"After revision: {review.coverage_percentage:.0f}% "
                        f"coverage, {review.revision_passes_completed} pass(es)"
                    )

            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Review/revision failed (non-fatal): {e}")

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

            # Phase 5: Record this generation for future feedback
            try:
                if org_id:
                    learning_svc = LearningService()
                    title = analysis_dict.get("opportunity_summary", "Untitled Proposal")[:200]
                    learning_svc.record_generation(
                        organization_id=org_id,
                        proposal_title=title,
                        sections=sections,
                        analysis_data=analysis_dict,
                        writing_preferences=None,
                        db=db,
                    )
            except Exception as e:
                logger.debug(f"Failed to record generation (non-fatal): {e}")

            db.commit()
            logger.info(f"Proposal generation completed for {project_id}")
            return proposal

        except Exception as e:
            logger.error(f"Error generating proposal: {e}")
            db.rollback()
            raise ValueError(f"Failed to generate proposal: {e}")

    async def _retrieve_hybrid(
        self,
        retriever: ChunkRetriever,
        embedding_service: EmbeddingService,
        section_name: str,
        project_id: str,
        db: Session,
    ) -> Any:
        """Hybrid retrieval: keyword + semantic for a single section.

        Builds a query string from the section's keywords + top compliance
        entries, embeds it, does a pgvector similarity search, then
        merges with keyword results.
        """
        keywords, cm_categories = SECTION_RELEVANCE.get(section_name, ([], []))

        # Build a natural-language query from the section's keywords
        query = f"RFP sections about: {', '.join(keywords[:10])}"
        cm_entries = retriever._filter_compliance(cm_categories)
        if cm_entries:
            top_reqs = " ".join(
                e.get("requirement_text", "")[:100] for e in cm_entries[:3]
            )
            query += f". Key requirements: {top_reqs}"

        # Semantic search
        try:
            semantic_results = await embedding_service.search_similar(
                project_id, query, db, top_k=15
            )
        except Exception as e:
            logger.warning(f"Semantic search failed for {section_name}: {e}")
            semantic_results = []

        # Hybrid merge
        if semantic_results:
            return retriever.retrieve_for_section_hybrid(
                section_name, semantic_results
            )
        else:
            return retriever.retrieve_for_section(section_name)

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
