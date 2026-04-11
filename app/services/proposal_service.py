"""Proposal service for generating proposal sections."""

import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ProposalDraft, AnalysisResult, Project, Company, CompanyWritingPreferences
from app.prompts.proposal_prompts import (
    get_cover_letter_prompt,
    get_executive_summary_prompt,
    get_understanding_prompt,
    get_solution_prompt,
    get_why_us_prompt,
    get_pricing_prompt,
    get_risk_mitigation_prompt,
    get_closing_prompt,
)
from app.prompts.writing_preferences_helpers import enhance_section_prompt

logger = logging.getLogger(__name__)


class ProposalService:
    """
    Service for generating proposal sections using OpenAI.

    Generates all 8 proposal sections based on analysis results and company profile.
    """

    def __init__(self):
        self.settings = get_settings()
        self._initialize_openai_client()

    def _initialize_openai_client(self):
        """Verify the OpenAI library is installed.

        See :meth:`AnalysisService._initialize_openai_client` for why we
        don't store a singleton client. For proposal generation we still
        create only **one** client per request — at the top of
        :meth:`generate_proposal` — and pass it down to all 8 parallel
        section calls, so the fan-out shares a single connection pool.
        """
        try:
            from openai import AsyncOpenAI  # noqa: F401  (import check only)
        except ImportError:
            raise ImportError("OpenAI library is required. Install with: pip install openai")

    def _get_company_dict(self, company_id: Optional[str], db: Session) -> Optional[Dict[str, Any]]:
        """
        Fetch company profile and return as dictionary.

        Args:
            company_id: The company ID
            db: Database session

        Returns:
            Company data dictionary or None
        """
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
            logger.warning(f"Could not fetch company data: {str(e)}")
            return None

    def _get_writing_preferences(self, company_id: Optional[str], db: Session) -> Optional[Dict[str, Any]]:
        """
        Fetch company writing preferences and return as dictionary.

        Args:
            company_id: The company ID
            db: Database session

        Returns:
            Writing preferences dictionary or None
        """
        if not company_id:
            return None

        try:
            preferences = db.query(CompanyWritingPreferences).filter(
                CompanyWritingPreferences.company_id == company_id
            ).first()

            if not preferences:
                logger.debug(f"No writing preferences found for company {company_id}")
                return None

            logger.info(f"Using writing preferences for company {company_id}")
            return preferences.to_dict()

        except Exception as e:
            logger.warning(f"Could not fetch writing preferences: {str(e)}")
            return None

    async def generate_proposal(
        self,
        project_id: str,
        db: Session,
        company_id: Optional[str] = None
    ) -> ProposalDraft:
        """
        Generate complete proposal draft from analysis results.

        Args:
            project_id: The project ID
            db: Database session
            company_id: Optional company ID for personalized proposal

        Returns:
            ProposalDraft object

        Raises:
            ValueError: If generation fails
        """
        logger.info(f"Starting proposal generation for project {project_id}")

        # Get analysis results
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.project_id == project_id
        ).first()

        if not analysis:
            raise ValueError(f"No analysis results found for project {project_id}")

        # Get company data if available
        company_data = self._get_company_dict(company_id, db)
        if company_data:
            logger.info(f"Using company context for proposal: {company_data['name']}")

        # Get writing preferences if available
        writing_preferences = self._get_writing_preferences(company_id, db)
        if writing_preferences:
            logger.info(f"Using writing preferences for company {company_id}")

        # Convert analysis to dict for easier access
        analysis_dict = {
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
        }

        try:
            # Generate all sections in parallel using asyncio.gather()
            # This reduces total time from ~8x API call duration to ~1x
            cover_letter_prompt = enhance_section_prompt(
                get_cover_letter_prompt(analysis_dict, company_data),
                "cover_letter",
                writing_preferences
            )
            executive_summary_prompt = enhance_section_prompt(
                get_executive_summary_prompt(analysis_dict, company_data),
                "executive_summary",
                writing_preferences
            )
            understanding_prompt = enhance_section_prompt(
                get_understanding_prompt(analysis_dict, company_data),
                "understanding_of_requirements",
                writing_preferences
            )
            solution_prompt = enhance_section_prompt(
                get_solution_prompt(analysis_dict, company_data),
                "proposed_solution",
                writing_preferences
            )
            why_us_prompt = enhance_section_prompt(
                get_why_us_prompt(analysis_dict, company_data),
                "why_us",
                writing_preferences
            )
            pricing_prompt = enhance_section_prompt(
                get_pricing_prompt(analysis_dict, company_data),
                "pricing_positioning",
                writing_preferences
            )
            risk_prompt = enhance_section_prompt(
                get_risk_mitigation_prompt(analysis_dict, company_data),
                "risk_mitigation",
                writing_preferences
            )
            closing_prompt = enhance_section_prompt(
                get_closing_prompt(summary=analysis_dict.get("opportunity_summary", ""), company=company_data),
                "closing_statement",
                writing_preferences
            )

            # Create one AsyncOpenAI client per request and share it across
            # all 8 parallel section generations. The async-with block
            # ensures the underlying httpx connection pool is closed before
            # we leave the function, even on exception.
            from openai import AsyncOpenAI

            async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
                (
                    cover_letter,
                    executive_summary,
                    understanding_of_requirements,
                    proposed_solution,
                    why_us,
                    pricing_positioning,
                    risk_mitigation,
                    closing_statement
                ) = await asyncio.gather(
                    self._generate_section(client, cover_letter_prompt),
                    self._generate_section(client, executive_summary_prompt),
                    self._generate_section(client, understanding_prompt),
                    self._generate_section(client, solution_prompt),
                    self._generate_section(client, why_us_prompt),
                    self._generate_section(client, pricing_prompt),
                    self._generate_section(client, risk_prompt),
                    self._generate_section(client, closing_prompt),
                )

            sections = {
                "cover_letter": cover_letter,
                "executive_summary": executive_summary,
                "understanding_of_requirements": understanding_of_requirements,
                "proposed_solution": proposed_solution,
                "why_us": why_us,
                "pricing_positioning": pricing_positioning,
                "risk_mitigation": risk_mitigation,
                "closing_statement": closing_statement,
            }

            # Create proposal draft
            proposal = ProposalDraft(
                project_id=project_id,
                cover_letter=sections.get("cover_letter"),
                executive_summary=sections.get("executive_summary"),
                understanding_of_requirements=sections.get("understanding_of_requirements"),
                proposed_solution=sections.get("proposed_solution"),
                why_us=sections.get("why_us"),
                pricing_positioning=sections.get("pricing_positioning"),
                risk_mitigation=sections.get("risk_mitigation"),
                closing_statement=sections.get("closing_statement"),
            )

            # Save to database
            db.add(proposal)

            # Update project status and company_id if provided
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "proposal_generated"
                if company_id and not project.company_id:
                    project.company_id = company_id

            db.commit()
            logger.info(f"Proposal generation completed for project {project_id}")

            return proposal

        except Exception as e:
            logger.error(f"Error generating proposal: {str(e)}")
            db.rollback()
            raise ValueError(f"Failed to generate proposal: {str(e)}")

    async def _generate_section(self, client, prompt: str) -> str:
        """
        Generate a single proposal section using a shared AsyncOpenAI client.

        Args:
            client: An ``AsyncOpenAI`` instance owned by the caller. The
                caller is responsible for opening and closing it (typically
                via ``async with`` in :meth:`generate_proposal`). Sharing one
                client across all 8 parallel section calls means a single
                connection pool instead of 8.
            prompt: The prompt for generating the section.

        Returns:
            Generated section text

        Raises:
            ValueError: If generation fails
        """
        try:
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating section: {str(e)}")
            raise ValueError(f"Failed to generate proposal section: {str(e)}")

    def get_proposal_draft(self, project_id: str, db: Session) -> Optional[ProposalDraft]:
        """
        Retrieve proposal draft for a project.

        Args:
            project_id: The project ID
            db: Database session

        Returns:
            ProposalDraft or None if not found
        """
        return db.query(ProposalDraft).filter(
            ProposalDraft.project_id == project_id
        ).first()

    def update_proposal_section(
        self,
        project_id: str,
        section_name: str,
        section_text: str,
        db: Session
    ) -> ProposalDraft:
        """
        Update a single proposal section.

        Args:
            project_id: The project ID
            section_name: The section name (e.g., 'executive_summary')
            section_text: The new section text
            db: Database session

        Returns:
            Updated ProposalDraft

        Raises:
            ValueError: If section or proposal not found
        """
        # Validate section name
        if section_name not in ProposalDraft.SECTION_ORDER:
            raise ValueError(f"Invalid section name: {section_name}")

        # Get proposal draft
        proposal = self.get_proposal_draft(project_id, db)
        if not proposal:
            raise ValueError(f"Proposal not found for project {project_id}")

        # Update section
        setattr(proposal, section_name, section_text)

        db.commit()
        logger.info(f"Updated section {section_name} for project {project_id}")

        return proposal

    def get_proposal_dict(self, proposal: ProposalDraft) -> dict:
        """
        Convert proposal to dictionary with ordered sections.

        Args:
            proposal: The ProposalDraft object

        Returns:
            Dictionary with all sections
        """
        return proposal.to_dict()

    def generate_proposal_background(self, project_id: str, company_id: Optional[str] = None) -> None:
        """
        Generate proposal in background (for BackgroundTasks).

        This is a synchronous wrapper that creates its own database session
        and runs proposal generation without blocking the HTTP response.

        Args:
            project_id: The project ID
            company_id: Optional company ID for personalized proposal
        """
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            # Create a new event loop for this background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(self.generate_proposal(project_id, db, company_id))
            logger.info(f"Background proposal generation completed for {project_id}")
        except Exception as e:
            logger.error(f"Background proposal generation failed for {project_id}: {str(e)}")
        finally:
            db.close()
