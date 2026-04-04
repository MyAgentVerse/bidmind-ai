# BidMind AI Authentication System - Deployment Guide

## What Was Fixed

The Railway deployment was crashing because the critical `app/api/routes/auth.py` file was never fully created. This guide covers what's been completed and how to deploy it.

### Completed Components

✅ **Authentication Routes** (`app/api/routes/auth.py`)
- `POST /api/auth/signup` - Create new user with organization
- `POST /api/auth/login` - Authenticate and get tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current authenticated user

✅ **Pydantic Schemas** (`app/schemas/auth.py`)
- SignupRequest, LoginRequest, TokenResponse, RefreshTokenRequest
- UserResponse, OrganizationResponse

✅ **Security System**
- PasswordManager with bcrypt hashing
- TokenManager with JWT access/refresh tokens
- get_current_user dependency for protected routes

✅ **Database Models & Migrations**
- User, Organization, UserOrganization tables
- Alembic migration 006_add_authentication.py

✅ **Dependencies**
- Updated requirements.txt with python-jose, passlib, bcrypt

## Deployment Steps

### 1. Push Code to GitHub (Fix Network Issue First)
```bash
cd /path/to/BidMind\ AI
git push origin feature/saas-auth-multi-tenant
```

### 2. Deploy to Railway

Go to your Railway project dashboard and:
- Connect the feature/saas-auth-multi-tenant branch
- Railway will automatically:
  - Install dependencies from requirements.txt
  - Run Alembic migrations (if configured)
  - Start the FastAPI application

### 3. Run Database Migrations (If Not Automatic)

In Railway bash terminal:
```bash
alembic upgrade head
```

### 4. Create Super Admin User

Option A: Via Railway Bash Terminal
```bash
python create_super_admin.py
```

Option B: Create Manually (if script fails)
Use the `/api/auth/signup` endpoint with:
```json
{
  "email": "dawoodshabbir734@gmail.com",
  "full_name": "Super Admin",
  "password": "@Dfimbk734*@",
  "organization_name": "Super Admin Organization"
}
```

## Testing Authentication Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database (SQLite for Development)
```bash
# Create .env file with:
# DATABASE_URL=sqlite:///./test.db
# SECRET_KEY=your-secret-key-at-least-32-chars

alembic upgrade head
```

### 3. Create Super Admin
```bash
python create_super_admin.py
```

### 4. Start Server
```bash
python -m app.main
```

### 5. Test Endpoints
```bash
# Signup
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "TestPass123!",
    "organization_name": "Test Org"
  }'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Get Current User (use token from login response)
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Refresh Token
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## Lovable UI Integration

Use this prompt in your Lovable project to generate the authentication UI:

---

### Lovable Prompt: BidMind AI Authentication UI

Create a complete authentication system UI for BidMind AI with:

**Pages:**

1. **Login Page** (/login)
   - Email input field
   - Password input field
   - "Login" button that calls POST /api/auth/login
   - Link to signup page
   - Display error messages from API
   - Show loading state while authenticating
   - On success: Store access_token and refresh_token in localStorage
   - Redirect to /dashboard

2. **Signup Page** (/signup)
   - Email input field with validation
   - Full Name input field
   - Password input field with strength indicator
   - Organization Name input field (optional)
   - "Create Account" button that calls POST /api/auth/signup
   - Link to login page
   - Display validation errors from API
   - Show loading state
   - On success: Auto-login user and redirect to /dashboard

3. **Protected Routes**
   - Create a PrivateRoute component that checks for access_token in localStorage
   - If no token, redirect to /login
   - Add a logout button in header that clears tokens and redirects to /login

4. **Dashboard** (/dashboard)
   - Display "Welcome {user.full_name}"
   - Show user's organization and role
   - Display user email
   - Add logout button
   - This is the protected landing page after login

5. **Token Management**
   - Store access_token and refresh_token in localStorage
   - Add Authorization header to all API requests: "Bearer {access_token}"
   - When token expires (401 response), automatically call POST /api/auth/refresh
   - Update access_token with new token
   - Retry the original request
   - If refresh fails, logout user and redirect to /login

6. **UI Features**
   - Professional styling with your brand colors
   - Form validation before submission
   - Clear error messages (e.g., "Invalid email or password")
   - Loading spinners during API calls
   - Responsive design for mobile
   - Password field with show/hide toggle
   - Organization field should be optional (can leave blank)

7. **Security**
   - Clear passwords from inputs after submission
   - Don't show tokens in URLs
   - Use HTTPS in production
   - Validate email format on frontend

**API Endpoints:**
- POST /api/auth/signup
- POST /api/auth/login
- POST /api/auth/refresh
- GET /api/auth/me (for getting current user info)

**Expected Request/Response Formats:**

Signup Request:
```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "SecurePass123!",
  "organization_name": "Acme Corp"
}
```

Signup Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": false
  },
  "organization": {
    "id": "uuid",
    "name": "Acme Corp"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Login Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Login Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": false
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Refresh Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Me Response:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_verified": false,
  "last_login": "2026-04-03T15:30:00",
  "organizations": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "role": "owner"
    }
  ]
}
```

---

## Security Notes

1. **Passwords** - Hashed with bcrypt, never stored in plain text
2. **Tokens** - JWT with HS256 algorithm, signed with SECRET_KEY
3. **Access Token** - Expires in 30 minutes
4. **Refresh Token** - Expires in 7 days
5. **Database** - User organizations linked via role-based access control (owner/admin/member/viewer)

## Next Steps

1. Push this code to GitHub
2. Deploy to Railway
3. Run create_super_admin.py to create admin user
4. Create Lovable project with authentication UI using the prompt above
5. Connect Lovable frontend to this backend API
6. Test end-to-end: signup → login → dashboard → logout
7. Merge feature branch to main once tested

## Troubleshooting

**Issue: "Already exists" error when creating super admin**
- The super admin user was already created
- Either use different email or delete the existing user from database

**Issue: "Invalid token" errors**
- Check that SECRET_KEY is the same across all instances
- Ensure token_manager.secret_key matches settings.secret_key
- Verify JWT_SECRET_KEY environment variable is set on Railway

**Issue: Database migration fails**
- Run: `alembic upgrade head` manually
- Check database connection in DATABASE_URL
- Verify alembic/versions/ directory exists

**Issue: CORS errors in frontend**
- Backend already allows all origins in main.py
- Check that frontend URL is making requests correctly
- Verify Content-Type headers are set to application/json
