# BidMind AI Backend

A production-ready Python FastAPI backend for intelligent procurement document analysis and AI-assisted proposal generation.

## Overview

BidMind AI helps organizations respond to RFPs, RFQs, RFIs, and other procurement documents by:

1. **Analyzing** procurement documents to extract key intelligence
2. **Understanding** requirements, deadlines, evaluation criteria, and risks
3. **Generating** structured proposal drafts with 8 comprehensive sections
4. **Refining** proposal content with AI-assisted editing
5. **Exporting** complete proposals as professional Word documents

## Features

- **Multi-format Document Support**: PDF and DOCX file uploads
- **Intelligent Document Analysis**: AI-powered extraction of opportunities, requirements, risks, and positioning
- **Proposal Generation**: Automated generation of 8 proposal sections
- **AI-Assisted Editing**: Improve any section with natural language instructions
- **Edit History Tracking**: Audit trail of all AI modifications
- **DOCX Export**: Download complete proposals as formatted Word documents
- **RESTful API**: Clean, well-documented API endpoints
- **Database Persistence**: PostgreSQL backend with SQLAlchemy ORM
- **Modular Architecture**: Clean separation of concerns with service layer pattern
- **Production Ready**: Logging, error handling, validation, security checks

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI (modern async web framework)
- Uvicorn (ASGI server)
- SQLAlchemy (ORM)
- Alembic (database migrations)
- PostgreSQL (primary database)
- OpenAI API (document analysis and proposal generation)
- PyMuPDF (PDF parsing)
- python-docx (Word document creation)

**Architecture:**
- REST API design
- Service layer pattern
- Pydantic validation
- Dependency injection
- CORS support

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/                      # Core configuration and setup
│   │   ├── config.py             # Settings management
│   │   ├── database.py           # Database configuration
│   │   ├── logging.py            # Logging setup
│   │   └── security.py           # Security utilities
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── project.py            # Project model
│   │   ├── uploaded_file.py      # File upload model
│   │   ├── analysis_result.py    # Analysis results model
│   │   ├── proposal_draft.py     # Proposal draft model
│   │   └── ai_edit_history.py    # Edit history model
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── common.py             # Common response schemas
│   │   ├── project.py            # Project schemas
│   │   ├── upload.py             # Upload schemas
│   │   ├── analysis.py           # Analysis schemas
│   │   ├── proposal.py           # Proposal schemas
│   │   ├── ai_edit.py            # AI edit schemas
│   │   └── export.py             # Export schemas
│   ├── api/                       # API routes and endpoints
│   │   ├── deps.py               # Dependency injection
│   │   └── routes/               # Route handlers
│   │       ├── health.py         # Health check
│   │       ├── projects.py       # Project management
│   │       ├── uploads.py        # File uploads
│   │       ├── analysis.py       # Document analysis
│   │       ├── proposal.py       # Proposal generation
│   │       ├── ai_edit.py        # AI-assisted editing
│   │       └── export.py         # DOCX export
│   ├── services/                  # Business logic layer
│   │   ├── storage_service.py    # File storage (local/S3/Azure)
│   │   ├── file_parser_service.py # PDF/DOCX parsing
│   │   ├── analysis_service.py   # Document analysis with OpenAI
│   │   ├── proposal_service.py   # Proposal generation
│   │   ├── ai_edit_service.py    # AI editing
│   │   └── export_service.py     # DOCX generation
│   ├── prompts/                   # AI prompt templates
│   │   ├── analysis_prompts.py   # Document analysis prompts
│   │   ├── proposal_prompts.py   # Section generation prompts
│   │   └── edit_prompts.py       # Editing prompts
│   ├── utils/                     # Utility functions
│   │   ├── text_cleaning.py      # Text normalization
│   │   ├── file_validators.py    # File validation
│   │   └── response_helpers.py   # Response formatting
│   └── db/                        # Database utilities
│       └── base.py               # SQLAlchemy base models
├── alembic/                       # Database migrations
│   ├── env.py                    # Migration environment
│   ├── script.py.mako            # Migration template
│   └── versions/                 # Migration scripts
├── tests/                         # Test suite
│   ├── test_health.py            # Health check tests
│   └── ...                       # Other test files
├── .env.example                   # Environment variables template
├── requirements.txt               # Python dependencies
├── alembic.ini                    # Alembic configuration
└── README.md                      # This file
```

## Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 12 or higher
- OpenAI API key

### Setup Instructions

1. **Clone and setup environment:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration:
# - DATABASE_URL: PostgreSQL connection string
# - OPENAI_API_KEY: Your OpenAI API key
# - Other settings as needed
```

4. **Set up database:**

```bash
# Run migrations
alembic upgrade head

# Or create tables directly (development only)
python -c "from app.core.database import init_db; init_db()"
```

5. **Start the server:**

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## API Endpoints

### Health Check
- `GET /api/health` - Health check endpoint

### Projects
- `POST /api/projects` - Create new project
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project details
- `PATCH /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project

### File Upload
- `POST /api/projects/{project_id}/upload` - Upload procurement document (PDF/DOCX)
- `GET /api/projects/{project_id}/files` - List project files

### Analysis
- `POST /api/projects/{project_id}/analyze` - Analyze uploaded document
- `GET /api/projects/{project_id}/analysis` - Get analysis results

### Proposal
- `POST /api/projects/{project_id}/generate-proposal` - Generate proposal draft
- `GET /api/projects/{project_id}/proposal` - Get proposal
- `PATCH /api/projects/{project_id}/proposal` - Update proposal section
- `PUT /api/projects/{project_id}/proposal` - Update multiple sections

### AI Editing
- `POST /api/projects/{project_id}/proposal/ai-edit` - AI-assisted section edit
- `GET /api/projects/{project_id}/proposal/edit-history` - Get edit history

### Export
- `GET /api/projects/{project_id}/export/docx` - Download proposal as DOCX

## Workflow

### Typical User Flow

1. **Create Project**
   ```bash
   POST /api/projects
   {
     "title": "RFP: Cloud Services",
     "description": "Response to enterprise cloud RFP"
   }
   ```

2. **Upload Document**
   ```bash
   POST /api/projects/{project_id}/upload
   # Upload PDF or DOCX file
   ```

3. **Analyze Document**
   ```bash
   POST /api/projects/{project_id}/analyze
   # Extracts requirements, risks, deadlines, etc.
   ```

4. **Generate Proposal**
   ```bash
   POST /api/projects/{project_id}/generate-proposal
   # Creates 8 proposal sections
   ```

5. **Edit Sections** (optional)
   ```bash
   PATCH /api/projects/{project_id}/proposal
   {
     "section_name": "executive_summary",
     "text": "Updated content..."
   }
   ```

6. **AI Improve Section** (optional)
   ```bash
   POST /api/projects/{project_id}/proposal/ai-edit
   {
     "section_name": "executive_summary",
     "current_text": "...",
     "instruction": "Make this more persuasive"
   }
   ```

7. **Export as DOCX**
   ```bash
   GET /api/projects/{project_id}/export/docx
   # Returns formatted Word document
   ```

## Database Schema

### Projects
- `id` (UUID): Primary key
- `title` (String): Project title
- `status` (Enum): created, file_uploaded, analyzed, proposal_generated
- `created_at`, `updated_at`: Timestamps

### UploadedFiles
- `id` (UUID): Primary key
- `project_id` (FK): Reference to project
- `original_filename`, `stored_filename`: File names
- `extracted_text`: Raw text from document
- `mime_type`, `file_size`: File metadata

### AnalysisResults
- `id` (UUID): Primary key
- `project_id` (FK): Reference to project
- `document_type`: RFP, RFQ, RFI, etc.
- `opportunity_summary`: High-level summary
- `scope_of_work` (JSON): List of work items
- `mandatory_requirements` (JSON): Must-have requirements
- `deadlines` (JSON): Important dates
- `evaluation_criteria` (JSON): Scoring criteria
- `budget_clues` (JSON): Budget information
- `risks` (JSON): Identified risks
- `fit_score` (Float): 0-100 fit assessment
- `usp_suggestions` (JSON): Positioning ideas
- `pricing_strategy_summary`: Pricing guidance

### ProposalDrafts
- `id` (UUID): Primary key
- `project_id` (FK): Reference to project
- 8 text fields: One for each proposal section
  - `cover_letter`
  - `executive_summary`
  - `understanding_of_requirements`
  - `proposed_solution`
  - `why_us`
  - `pricing_positioning`
  - `risk_mitigation`
  - `closing_statement`

### AIEditHistory
- `id` (UUID): Primary key
- `project_id` (FK): Reference to project
- `section_name`: Section being edited
- `instruction`: Edit instruction
- `original_text`: Text before edit
- `edited_text`: Text after edit

## Configuration

### Environment Variables

Key configuration variables in `.env`:

```
# Application
APP_NAME=BidMind AI API
ENVIRONMENT=development|production
DEBUG=true|false

# Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost/dbname

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# File Upload
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=25
ALLOWED_EXTENSIONS=pdf,docx

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## Development

### Running Tests

```bash
pytest tests/
pytest tests/test_health.py -v
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Revert to previous
alembic downgrade -1
```

### Linting and Formatting

```bash
# Format code
black app tests

# Type checking
mypy app

# Linting
flake8 app tests
```

## Future Improvements

- [ ] User authentication (JWT + OAuth2)
- [ ] Multi-tenant support with organization accounts
- [ ] Vector search for similarity matching
- [ ] Multi-document project support
- [ ] S3/Azure Blob Storage integration
- [ ] PDF export option
- [ ] Proposal templates and customization
- [ ] Advanced caching layer
- [ ] WebSocket support for real-time updates
- [ ] Advanced analytics and insights
- [ ] Integration with CRM systems (Salesforce, Pipedrive, etc.)
- [ ] Email integration for sharing proposals
- [ ] Version control for proposals
- [ ] Collaborative editing support
- [ ] Advanced audit logging
- [ ] Rate limiting and quota management

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: bidmind_ai
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/bidmind_ai
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - db
    command: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0
```

## Security Considerations

- Input validation on all endpoints
- File upload validation (type, size, content)
- CORS protection
- SQL injection prevention (via SQLAlchemy ORM)
- Path traversal prevention
- Rate limiting (TODO: implement)
- Authentication/authorization (TODO: implement)
- API key management (TODO: implement)

## Performance Optimization

- Database indexing on frequently queried fields
- Async/await for I/O operations
- Connection pooling
- Query optimization
- Caching layer (TODO: implement with Redis)
- File streaming for large exports
- Pagination for list endpoints

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "message": "Error message",
  "errors": ["Detailed error 1", "Detailed error 2"]
}
```

## Logging

Application logs are configured with:
- Timestamp
- Logger name
- Log level
- Message

Logs are written to stdout by default (suitable for Docker/Kubernetes).

## Contributing

1. Follow the existing code structure and patterns
2. Write tests for new functionality
3. Update documentation as needed
4. Use consistent naming conventions
5. Add type hints to functions

## Support

For issues, questions, or contributions:
1. Check existing documentation
2. Review API documentation at `/api/docs`
3. Check error messages and logs
4. File an issue with detailed information

## License

Proprietary - BidMind AI

---

**Built with ❤️ for procurement professionals**
