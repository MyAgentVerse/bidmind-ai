"""Proposal service for generating proposal sections."""

import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ProposalDraft, AnalysisResult, Project
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

logger = logging.getLogger(__name__)


class ProposalService:
    """
    Service for generating proposal sections using OpenAI.

    Generates all 8 proposal sections based on analysis results.
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

    async def generate_proposal(
        self,
        project_id: str,
        db: Session
    ) -> ProposalDraft:
        """
        Generate complete proposal draft from analysis results.

        Args:
            project_id: The project ID
            db: Database session

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
                self._generate_section(get_cover_letter_prompt(analysis_dict)),
                self._generate_section(get_executive_summary_prompt(analysis_dict)),
                self._generate_section(get_understanding_prompt(analysis_dict)),
                self._generate_section(get_solution_prompt(analysis_dict)),
                self._generate_section(get_why_us_prompt(analysis_dict)),
                self._generate_section(get_pricing_prompt(analysis_dict)),
                self._generate_section(get_risk_mitigation_prompt(analysis_dict)),
                self._generate_section(get_closing_prompt(summary=analysis_dict.get("opportunity_summary", ""))),
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

            # Update project status
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "proposal_generated"

            db.commit()
            logger.info(f"Proposal generation completed for project {project_id}")

            return proposal

        except Exception as e:
            logger.error(f"Error generating proposal: {str(e)}")
            db.rollback()
            raise ValueError(f"Failed to generate proposal: {str(e)}")

    async def _generate_section(self, prompt: str) -> str:
        """
        Generate a single proposal section using OpenAI.

        Args:
            prompt: The prompt for generating the section

        Returns:
            Generated section text

        Raises:
            ValueError: If generation fails
        """
        try:
            response = self.client.chat.completions.create(
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
