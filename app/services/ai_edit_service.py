"""AI edit service for refining proposal sections."""

import logging
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import AIEditHistory, ProposalDraft
from app.prompts.edit_prompts import get_edit_prompt

logger = logging.getLogger(__name__)


class AIEditService:
    """
    Service for AI-assisted editing of proposal sections.

    Allows users to improve sections with specific instructions.
    Tracks edit history for auditing and potential rollback.
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

    async def edit_section(
        self,
        project_id: str,
        section_name: str,
        current_text: str,
        instruction: str,
        db: Session,
        save_to_proposal: bool = True
    ) -> tuple[str, AIEditHistory]:
        """
        Edit a proposal section using AI.

        Args:
            project_id: The project ID
            section_name: The section to edit (e.g., 'executive_summary')
            current_text: The current section text
            instruction: The editing instruction (e.g., 'make more concise')
            db: Database session
            save_to_proposal: Whether to save edited text back to proposal

        Returns:
            Tuple of (edited_text, AIEditHistory)

        Raises:
            ValueError: If edit fails
        """
        logger.info(f"Starting AI edit for {section_name} in project {project_id}")

        try:
            # Generate edit prompt
            prompt = get_edit_prompt(section_name, current_text, instruction)

            # Call OpenAI
            response = self.client.messages.create(
                model=self.settings.openai_model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            edited_text = response.content[0].text

            # Create edit history record
            edit_history = AIEditHistory(
                project_id=project_id,
                section_name=section_name,
                instruction=instruction,
                original_text=current_text,
                edited_text=edited_text
            )

            # Save to database
            db.add(edit_history)

            # Optionally update proposal with edited text
            if save_to_proposal:
                proposal = db.query(ProposalDraft).filter(
                    ProposalDraft.project_id == project_id
                ).first()

                if proposal:
                    setattr(proposal, section_name, edited_text)
                    logger.info(f"Updated {section_name} with edited text")

            db.commit()
            logger.info(f"AI edit completed for {section_name}")

            return edited_text, edit_history

        except Exception as e:
            logger.error(f"Error editing section: {str(e)}")
            db.rollback()
            raise ValueError(f"Failed to edit section: {str(e)}")

    def get_edit_history(self, project_id: str, db: Session) -> list[AIEditHistory]:
        """
        Get edit history for a project.

        Args:
            project_id: The project ID
            db: Database session

        Returns:
            List of AIEditHistory objects
        """
        return db.query(AIEditHistory).filter(
            AIEditHistory.project_id == project_id
        ).order_by(AIEditHistory.created_at.desc()).all()

    def get_section_edit_history(
        self,
        project_id: str,
        section_name: str,
        db: Session
    ) -> list[AIEditHistory]:
        """
        Get edit history for a specific section.

        Args:
            project_id: The project ID
            section_name: The section name
            db: Database session

        Returns:
            List of AIEditHistory objects for that section
        """
        return db.query(AIEditHistory).filter(
            AIEditHistory.project_id == project_id,
            AIEditHistory.section_name == section_name
        ).order_by(AIEditHistory.created_at.desc()).all()
