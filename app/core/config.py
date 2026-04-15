"""
Application configuration management using Pydantic settings.
Loads configuration from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or environment variables.
    """

    # Application
    app_name: str = "BidMind AI API"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+psycopg2://postgres:password@localhost:5432/bidmind_ai"

    # Security (set SECRET_KEY env var in production — never use the default)
    secret_key: str = "local-dev-only-change-in-production-min-32-chars"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini" # Fast, affordable, and widely available

    # File Upload
    upload_dir: str = "uploads"
    max_file_size_mb: int = 25
    allowed_extensions: str = "pdf,docx"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://*.lovable.dev,https://*.vercel.app,https://localhost:3000"

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_starter_price_id: str = ""  # one-time $59 price from Stripe dashboard
    stripe_pro_price_id: str = ""  # recurring $29/month price from Stripe dashboard

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def get_allowed_extensions(self) -> List[str]:
        """Parse allowed extensions from comma-separated string."""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        # Allow all origins — the API is protected by Bearer token auth,
        # not cookies, so CORS restrictions add no security value.
        # This also avoids the issue where CORSMiddleware doesn't support
        # wildcard sub-domain patterns like https://*.lovable.dev.
        return ["*"]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure only one Settings instance is created.
    """
    return Settings()
