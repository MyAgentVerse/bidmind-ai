# BidMind AI Backend - Quick Start Guide

Get the BidMind AI backend up and running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 12+ (running locally or remote)
- OpenAI API key (get from https://platform.openai.com/api-keys)

## Quick Setup

### 1. Run Setup Script (Recommended)

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
setup.bat
```

### 2. Configure Environment

Edit `.env` file with your settings:

```env
# REQUIRED: Your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here

# REQUIRED: PostgreSQL connection string
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/bidmind_ai

# Optional: Adjust these if needed
ENVIRONMENT=development
DEBUG=true
MAX_FILE_SIZE_MB=25
```

### 3. Initialize Database

Activate virtual environment first:

```bash
# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

Then run migrations:

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit: **http://localhost:8000/api/docs**

## Test the API

### 1. Create a Project

```bash
curl -X POST "http://localhost:8000/api/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test RFP",
    "description": "Testing BidMind AI"
  }'
```

Save the `id` from the response.

### 2. Upload a Document

```bash
curl -X POST "http://localhost:8000/api/projects/{project_id}/upload" \
  -F "file=@sample_rfp.pdf"
```

### 3. Analyze the Document

```bash
curl -X POST "http://localhost:8000/api/projects/{project_id}/analyze"
```

### 4. Generate Proposal

```bash
curl -X POST "http://localhost:8000/api/projects/{project_id}/generate-proposal"
```

### 5. Get Proposal

```bash
curl "http://localhost:8000/api/projects/{project_id}/proposal"
```

### 6. Export as DOCX

```bash
curl -X GET "http://localhost:8000/api/projects/{project_id}/export/docx" \
  -o proposal.docx
```

## Project Structure at a Glance

```
app/
├── main.py              → FastAPI application
├── core/                → Configuration & setup
├── models/              → Database models
├── schemas/             → Request/response validation
├── api/                 → API endpoints
├── services/            → Business logic
├── prompts/             → AI prompt templates
└── utils/               → Helper functions
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry point |
| `app/core/config.py` | Settings management |
| `app/api/routes/*.py` | API endpoints |
| `app/services/*.py` | Business logic |
| `alembic/` | Database migrations |
| `.env` | Environment configuration |

## Troubleshooting

### Database Connection Error

Make sure PostgreSQL is running:
```bash
# Test connection
psql -U postgres -h localhost -d bidmind_ai
```

Update `DATABASE_URL` in `.env` with correct credentials.

### OpenAI API Error

Check your API key:
- Ensure `OPENAI_API_KEY` is set correctly in `.env`
- Verify key has valid credits
- Check key permissions on OpenAI dashboard

### File Upload Error

Ensure upload directory exists:
```bash
mkdir -p uploads
```

Check `MAX_FILE_SIZE_MB` setting for large files.

### Port Already in Use

Change port in startup command:
```bash
uvicorn app.main:app --reload --port 8001
```

## Frontend Integration

The backend provides clean REST APIs for frontend consumption:

- **Base URL:** `http://localhost:8000/api`
- **Docs:** `http://localhost:8000/api/docs`
- **All responses:** JSON with consistent `{success, message, data}` structure
- **CORS:** Configured for localhost (update in `.env` for production)

## Next Steps

1. **Review the API Documentation:**
   - Visit http://localhost:8000/api/docs
   - Interactive Swagger UI with test capabilities

2. **Check the Full README:**
   - Detailed architecture explanation
   - Complete API endpoint documentation
   - Database schema details
   - Deployment guidelines

3. **Configure for Your Needs:**
   - Adjust prompts in `app/prompts/`
   - Customize response formats in `app/schemas/`
   - Add authentication in `app/core/security.py`

4. **Connect Your Frontend:**
   - Point frontend to http://localhost:8000/api
   - Use endpoints documented in `/api/docs`
   - Follow request/response schemas

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=false` in `.env`
- [ ] Update `CORS_ORIGINS` with actual frontend URLs
- [ ] Use strong PostgreSQL password
- [ ] Implement authentication (see TODOs in code)
- [ ] Configure S3 or cloud storage (instead of local)
- [ ] Set up proper logging and monitoring
- [ ] Use environment-specific database
- [ ] Enable HTTPS/SSL
- [ ] Set up rate limiting
- [ ] Review security settings
- [ ] Configure backup strategy

## Support

- **API Documentation:** http://localhost:8000/api/docs
- **README:** See `README.md` for detailed docs
- **Code Comments:** Extensive inline documentation
- **Type Hints:** Full type hints for IDE support

---

**Ready to go! Happy bidding! 🚀**
