"""AI-powered company profile generation from URLs.

Accepts website URLs and/or LinkedIn profile URLs, fetches the
content, and uses the LLM to extract structured company profile
fields (name, description, USP, capabilities, experience, industry).

Also supports AI-assisted editing of individual profile fields.
"""

import logging
import httpx
import re
from typing import Optional, Dict, Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CompanyAIService:
    """Generate and edit company profiles using AI."""

    def __init__(self):
        self.settings = get_settings()

    async def generate_profile_from_urls(
        self,
        website_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Dict[str, str]:
        """Fetch URL content and extract company profile fields via LLM.

        Returns a dict with keys: name, description,
        unique_selling_proposition, key_capabilities, experience,
        industry_focus.
        """
        content_parts = []

        if website_url:
            text = await self._fetch_url_text(website_url)
            if text:
                content_parts.append(
                    f"=== WEBSITE CONTENT ({website_url}) ===\n{text[:12000]}"
                )

        if linkedin_url:
            text = await self._fetch_url_text(linkedin_url)
            if text:
                content_parts.append(
                    f"=== LINKEDIN CONTENT ({linkedin_url}) ===\n{text[:8000]}"
                )

        if not content_parts:
            raise ValueError(
                "Could not fetch content from provided URLs. "
                "Please check the URLs and try again."
            )

        combined = "\n\n".join(content_parts)
        return await self._extract_profile(combined)

    async def ai_edit_field(
        self,
        field_name: str,
        current_value: str,
        instruction: str,
        company_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Use AI to edit a single company profile field."""
        context_str = ""
        if company_context:
            context_str = (
                f"\nCompany: {company_context.get('name', '')}\n"
                f"Industry: {company_context.get('industry_focus', '')}\n"
            )

        prompt = f"""You are editing a company profile field.

Field: {field_name}
Current value: {current_value}
{context_str}
User instruction: {instruction}

Return ONLY the updated field value. No explanations, no quotes, no field name prefix."""

        from openai import AsyncOpenAI

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()

    # ---- Internal helpers ------------------------------------------------

    async def _fetch_url_text(self, url: str) -> Optional[str]:
        """Fetch a URL and return its text content."""
        try:
            async with httpx.AsyncClient(
                timeout=20, follow_redirects=True
            ) as client:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (compatible; BidMindAI/1.0; "
                            "+https://bidmind-ai.com)"
                        )
                    },
                )
                resp.raise_for_status()

                html = resp.text
                # Strip HTML tags for a rough text extraction
                text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text

        except Exception as e:
            logger.warning(f"Could not fetch {url}: {e}")
            return None

    async def _extract_profile(self, content: str) -> Dict[str, str]:
        """Use LLM to extract structured profile from raw content."""
        prompt = f"""Analyze the following website/LinkedIn content and extract a professional company profile.

Return a JSON object with exactly these keys:
{{
  "name": "Full legal company name",
  "description": "2-3 sentence description of what the company does, its mission, and core business",
  "unique_selling_proposition": "What makes this company unique — certifications, methodology, competitive advantages, differentiators",
  "key_capabilities": "Comma-separated list of services, products, and technical capabilities",
  "experience": "Track record, years in business, notable clients, partnerships, certifications, geographic presence",
  "industry_focus": "Target industries and market segments"
}}

Be specific and factual — only include information found in the content. If a field cannot be determined, provide a reasonable inference marked with [Inferred].

CONTENT:
{content[:15000]}

Return ONLY the JSON object, nothing else."""

        from openai import AsyncOpenAI

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Ensure all expected keys exist
            fields = [
                "name", "description", "unique_selling_proposition",
                "key_capabilities", "experience", "industry_focus",
            ]
            return {k: result.get(k, "") for k in fields}
