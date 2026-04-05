"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.api.routes import (
    health_router,
    auth_router,
    users_router,
    organizations_router,
    company_router,
    writing_preferences_router,
    projects_router,
    projects_v2_router,
    uploads_router,
    analysis_router,
    proposal_router,
    ai_edit_router,
    export_router,
)

# Setup logging
logger = setup_logging()

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Document intelligence and proposal generation platform",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    # Run pending migrations
    try:
        from alembic.config import Config
        from alembic import command
        import os

        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.warning(f"Migration check completed with note: {str(e)}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down application")


# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(organizations_router)
app.include_router(company_router)
app.include_router(writing_preferences_router)
app.include_router(projects_router)
app.include_router(projects_v2_router)
app.include_router(uploads_router)
app.include_router(analysis_router)
app.include_router(proposal_router)
app.include_router(ai_edit_router)
app.include_router(export_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
