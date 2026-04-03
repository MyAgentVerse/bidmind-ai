# BidMind AI - API Specification

Complete REST API specification for the BidMind AI backend.

## Base URL

- Development: `http://localhost:8000/api`
- Production: `https://api.bidmind.ai/api`

## Authentication

Currently no authentication required. Add JWT-based auth to `app/core/security.py` when implementing user accounts.

## Response Format

All successful responses follow this format:

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

Error responses:

```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Detailed error 1", "Detailed error 2"]
}
```

## Endpoints

### Health Check

#### GET /health
Check if API is running.

**Response:** 200 OK
```json
{
  "success": true,
  "message": "API is healthy",
  "data": {"status": "healthy"}
}
```

---

### Projects

#### POST /projects
Create a new project.

**Request Body:**
```json
{
  "title": "RFP: Cloud Services",
  "description": "Enterprise cloud infrastructure RFP"
}
```

**Response:** 201 Created
```json
{
  "success": true,
  "message": "Project created successfully",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "RFP: Cloud Services",
    "description": "Enterprise cloud infrastructure RFP",
    "status": "created",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

**Errors:**
- 400: Invalid request data
- 500: Server error

---

#### GET /projects
List all projects.

**Query Parameters:**
- `skip` (int, default: 0) - Number of projects to skip
- `limit` (int, default: 100) - Maximum number of projects to return

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Projects retrieved successfully",
  "data": {
    "projects": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "RFP: Cloud Services",
        "status": "created",
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
      }
    ],
    "total": 1
  }
}
```

---

#### GET /projects/{project_id}
Get a specific project.

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Project retrieved successfully",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "RFP: Cloud Services",
    "description": "Enterprise cloud infrastructure RFP",
    "status": "analyzed",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T11:45:00"
  }
}
```

**Errors:**
- 404: Project not found
- 500: Server error

---

#### PATCH /projects/{project_id}
Update a project.

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "status": "analyzed"
}
```

All fields are optional. Omit fields you don't want to update.

**Response:** 200 OK (same as GET)

**Errors:**
- 404: Project not found
- 500: Server error

---

#### DELETE /projects/{project_id}
Delete a project.

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Project deleted successfully"
}
```

**Errors:**
- 404: Project not found
- 500: Server error

---

### File Upload

#### POST /projects/{project_id}/upload
Upload a procurement document.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (binary)
- Accepted types: PDF, DOCX
- Max size: 25MB (configurable)

**Response:** 201 Created
```json
{
  "success": true,
  "message": "File uploaded successfully",
  "data": {
    "id": "223e4567-e89b-12d3-a456-426614174001",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "original_filename": "rfp-2024.pdf",
    "file_size": 1524288,
    "mime_type": "application/pdf",
    "created_at": "2024-01-15T10:35:00"
  }
}
```

**Errors:**
- 400: Invalid file type, file too large, empty file, corrupted file
- 404: Project not found
- 500: Server error

---

#### GET /projects/{project_id}/files
List all files for a project.

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Files retrieved successfully",
  "data": {
    "files": [
      {
        "id": "223e4567-e89b-12d3-a456-426614174001",
        "project_id": "123e4567-e89b-12d3-a456-426614174000",
        "original_filename": "rfp-2024.pdf",
        "file_size": 1524288,
        "mime_type": "application/pdf",
        "created_at": "2024-01-15T10:35:00"
      }
    ],
    "total": 1
  }
}
```

---

### Document Analysis

#### POST /projects/{project_id}/analyze
Analyze uploaded document to extract intelligence.

**Prerequisites:**
- File must be uploaded (POST /upload)
- Takes 10-30 seconds depending on document size

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Document analysis completed successfully",
  "data": {
    "id": "323e4567-e89b-12d3-a456-426614174002",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "document_type": "RFP",
    "opportunity_summary": "Enterprise-wide cloud infrastructure modernization project...",
    "scope_of_work": [
      "Cloud infrastructure setup",
      "Migration of legacy systems",
      "Training and support"
    ],
    "mandatory_requirements": [
      "ISO 27001 certification",
      "24/7 support availability",
      "SLA guarantee of 99.9% uptime"
    ],
    "deadlines": {
      "proposal_submission": "2024-02-15",
      "decision_date": "2024-03-01"
    },
    "evaluation_criteria": [
      "Technical capability (40%)",
      "Cost (30%)",
      "Experience (20%)",
      "Support (10%)"
    ],
    "budget_clues": {
      "estimated_budget": "$500K - $1M annually",
      "pricing_model": "Value-based with performance incentives"
    },
    "risks": [
      "Tight implementation timeline",
      "Complex legacy system integration"
    ],
    "fit_score": 85.5,
    "usp_suggestions": [
      "Proven cloud migration experience",
      "Cost optimization expertise"
    ],
    "pricing_strategy_summary": "Value-based pricing with performance guarantees...",
    "created_at": "2024-01-15T10:40:00",
    "updated_at": "2024-01-15T10:40:00"
  }
}
```

**Errors:**
- 400: No file uploaded, analysis failed
- 404: Project not found
- 500: Server error or OpenAI API error

---

#### GET /projects/{project_id}/analysis
Retrieve analysis results.

**Response:** 200 OK (same as POST response)

**Errors:**
- 404: Project or analysis not found
- 500: Server error

---

### Proposal Generation

#### POST /projects/{project_id}/generate-proposal
Generate complete proposal draft from analysis.

**Prerequisites:**
- Document must be analyzed (POST /analyze)
- Takes 30-60 seconds depending on section complexity

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Proposal generated successfully",
  "data": {
    "id": "423e4567-e89b-12d3-a456-426614174003",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "cover_letter": "Dear Procurement Manager...",
    "executive_summary": "We propose a comprehensive solution...",
    "understanding_of_requirements": "We understand the following requirements...",
    "proposed_solution": "Our approach includes...",
    "why_us": "Our company brings unique capabilities...",
    "pricing_positioning": "Our pricing strategy is based on...",
    "risk_mitigation": "We mitigate risks by...",
    "closing_statement": "We appreciate the opportunity...",
    "created_at": "2024-01-15T10:50:00",
    "updated_at": "2024-01-15T10:50:00"
  }
}
```

**Errors:**
- 400: Analysis not found
- 404: Project not found
- 500: Server error or OpenAI API error

---

#### GET /projects/{project_id}/proposal
Retrieve proposal draft.

**Response:** 200 OK (same as POST response)

**Errors:**
- 404: Project or proposal not found
- 500: Server error

---

#### PATCH /projects/{project_id}/proposal
Update a single proposal section.

**Request Body:**
```json
{
  "section_name": "executive_summary",
  "text": "Updated executive summary content..."
}
```

**Valid Section Names:**
- `cover_letter`
- `executive_summary`
- `understanding_of_requirements`
- `proposed_solution`
- `why_us`
- `pricing_positioning`
- `risk_mitigation`
- `closing_statement`

**Response:** 200 OK (full proposal)

**Errors:**
- 400: Invalid section name
- 404: Project or proposal not found
- 500: Server error

---

#### PUT /projects/{project_id}/proposal
Update multiple proposal sections at once.

**Request Body:**
```json
{
  "executive_summary": "Updated summary...",
  "why_us": "Updated why us...",
  "pricing_positioning": "Updated pricing..."
}
```

All fields are optional.

**Response:** 200 OK (full proposal)

**Errors:**
- 404: Project or proposal not found
- 500: Server error

---

### AI-Assisted Editing

#### POST /projects/{project_id}/proposal/ai-edit
Use AI to improve a proposal section.

**Request Body:**
```json
{
  "section_name": "executive_summary",
  "current_text": "Current section text...",
  "instruction": "Make this more persuasive and add specific benefits"
}
```

**Valid Instructions Examples:**
- "Make this more concise"
- "Strengthen this section"
- "Make this more professional"
- "Add more specific examples"
- "Simplify the language"
- "Make it more persuasive"
- "Add compliance focus"

**Response:** 200 OK
```json
{
  "success": true,
  "message": "AI edit completed successfully",
  "data": {
    "section_name": "executive_summary",
    "instruction": "Make this more persuasive and add specific benefits",
    "original_text": "Current text...",
    "edited_text": "Improved text with benefits...",
    "created_at": "2024-01-15T11:00:00"
  }
}
```

Note: The edited text automatically updates the proposal.

**Errors:**
- 400: AI edit failed
- 404: Project not found
- 500: Server error or OpenAI API error

---

#### GET /projects/{project_id}/proposal/edit-history
Get edit history for a project.

**Query Parameters:**
- `section_name` (optional) - Filter by section name

**Response:** 200 OK
```json
{
  "success": true,
  "message": "Edit history retrieved successfully",
  "data": {
    "edits": [
      {
        "id": "523e4567-e89b-12d3-a456-426614174004",
        "section_name": "executive_summary",
        "instruction": "Make this more persuasive",
        "created_at": "2024-01-15T11:00:00"
      }
    ],
    "total": 1
  }
}
```

**Errors:**
- 404: Project not found
- 500: Server error

---

### Export

#### GET /projects/{project_id}/export/docx
Download proposal as DOCX file.

**Response:** 200 OK
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Binary file content
- Filename: `proposal_ProjectTitle_YYYYMMDD_HHMMSS.docx`

**Includes:**
- Project title and submission date
- Table of contents
- All 8 proposal sections as separate chapters
- Professional formatting with headings and spacing

**Errors:**
- 404: Project or proposal not found
- 500: File generation failed

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Resource not found |
| 500 | Internal Server Error - Server error |

## Rate Limiting

Not currently implemented. Will be added in future versions.

## Error Handling

All errors include:
- HTTP status code
- `success: false`
- `message`: Human-readable error description
- `errors`: Array of detailed error messages (if applicable)

Example error response:

```json
{
  "success": false,
  "message": "File upload failed",
  "errors": [
    "File type 'text/plain' not allowed",
    "Allowed types: pdf, docx"
  ]
}
```

## Workflow Examples

### Complete Workflow

1. Create project: `POST /projects`
2. Upload file: `POST /projects/{id}/upload`
3. Analyze: `POST /projects/{id}/analyze`
4. Generate proposal: `POST /projects/{id}/generate-proposal`
5. Edit sections: `PATCH /projects/{id}/proposal` (optional)
6. AI improve: `POST /projects/{id}/proposal/ai-edit` (optional)
7. Export: `GET /projects/{id}/export/docx`

### Quick Check

1. Check health: `GET /health`
2. List projects: `GET /projects`
3. Get project: `GET /projects/{id}`

## Testing

Use the interactive API documentation:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`

Or use curl/Postman with examples provided above.

## Future API Features (Planned)

- [ ] User authentication & authorization
- [ ] Proposal versioning
- [ ] Bulk operations
- [ ] Webhooks for async operations
- [ ] Advanced filtering and search
- [ ] Export to PDF, HTML
- [ ] Template management
- [ ] Collaboration features
- [ ] Analytics endpoints
- [ ] CRM integration endpoints

---

**Last Updated:** January 2024
**Version:** 0.1.0
