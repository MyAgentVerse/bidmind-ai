# BidMind AI Authentication Flow

## 1. User Signup Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User enters: email, full_name, password, organization_name  │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ POST /api/auth/signup                                       │
│ {                                                           │
│   "email": "user@example.com",                              │
│   "full_name": "John Doe",                                  │
│   "password": "SecurePass123!",                             │
│   "organization_name": "Acme Corp"                          │
│ }                                                           │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ Check email not already registered │
        └────────────────────┬───────────────┘
                             │
                    ┌────────┴────────┐
                    │ Already exists? │
                    └────────┬────────┘
                    Yes ──→  Return 400 error
                    No ──→   Continue
                             │
                    ▼────────▼────────┐
         ┌──────────────────────────┐ │
         │ Hash password with bcrypt│ │
         └──────────┬───────────────┘ │
                    │                  │
                    ▼                  │
         ┌──────────────────────────┐ │
         │ Create User record       │ │
         │ - id (UUID)              │ │
         │ - email                  │ │
         │ - full_name              │ │
         │ - password_hash          │ │
         │ - is_active = true       │ │
         │ - is_verified = false    │ │
         └──────────┬───────────────┘ │
                    │                  │
                    ▼                  │
         ┌──────────────────────────┐ │
         │ Create Organization      │ │
         │ (if organization_name)   │ │
         └──────────┬───────────────┘ │
                    │                  │
                    ▼                  │
         ┌──────────────────────────┐ │
         │ Link User to Org         │ │
         │ UserOrganization:        │ │
         │ - user_id               │ │
         │ - organization_id       │ │
         │ - role = "owner"        │ │
         └──────────┬───────────────┘ │
                    │                  │
                    ▼                  │
    ┌───────────────────────────────┐ │
    │ Generate JWT Tokens           │ │
    │                               │ │
    │ Access Token:                 │ │
    │ - sub = user_id               │ │
    │ - exp = now + 30 min          │ │
    │ - type = "access"             │ │
    │                               │ │
    │ Refresh Token:                │ │
    │ - sub = user_id               │ │
    │ - exp = now + 7 days          │ │
    │ - type = "refresh"            │ │
    └───────────┬───────────────────┘ │
                │                      │
                ▼                      │
    ┌───────────────────────────────┐ │
    │ Return 200 Success            │ │
    │ {                             │ │
    │   "user": {...},              │ │
    │   "organization": {...},      │ │
    │   "access_token": "...",      │ │
    │   "refresh_token": "...",     │ │
    │   "expires_in": 1800          │ │
    │ }                             │ │
    └───────────┬───────────────────┘ │
                │                      │
                ▼                      │
        ┌──────────────────┐           │
        │ Frontend stores  │           │
        │ tokens in        │           │
        │ localStorage     │           │
        └──────────┬───────┘           │
                   │                   │
                   └───────────────────┘
                           │
                           ▼
                   User logged in!
                   Redirect to dashboard
```

## 2. User Login Flow

```
┌─────────────────────────────────────────────┐
│ User enters: email, password                │
└────────────────────┬───────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ POST /api/auth/login                        │
│ {                                           │
│   "email": "user@example.com",              │
│   "password": "SecurePass123!"              │
│ }                                           │
└────────────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Find user by email     │
        └────────┬───────────────┘
                 │
        ┌────────┴────────┐
        │ User exists?    │
        └────────┬────────┘
        No ──→   Return 401
        Yes ──→  Continue
                 │
                 ▼
        ┌────────────────────────────┐
        │ Verify password with bcrypt│
        │ compare(plain, hash)       │
        └────────┬────────────────────┘
                 │
        ┌────────┴──────────┐
        │ Password matches? │
        └────────┬──────────┘
        No ──→   Return 401
        Yes ──→  Continue
                 │
                 ▼
        ┌────────────────────┐
        │ Check user active? │
        │ is_active = true   │
        └────────┬───────────┘
                 │
        ┌────────┴────────┐
        │ User active?    │
        └────────┬────────┘
        No ──→   Return 403
        Yes ──→  Continue
                 │
                 ▼
        ┌────────────────────────┐
        │ Update last_login      │
        │ timestamp              │
        └────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Generate JWT Tokens        │
    │ (same as signup)           │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │ Return 200 Success         │
    │ {                          │
    │   "user": {...},           │
    │   "access_token": "...",   │
    │   "refresh_token": "...",  │
    │   "expires_in": 1800       │
    │ }                          │
    └────────┬───────────────────┘
             │
             ▼
    Frontend stores tokens & redirects
```

## 3. Protected Route Access Flow

```
┌───────────────────────────────────────────────┐
│ GET /api/auth/me                              │
│ Header: Authorization: Bearer {access_token}  │
└────────────────────┬──────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │ HTTPBearer extracts token from     │
    │ Authorization header               │
    └────────┬─────────────────────────┘
             │
    ┌────────┴────────┐
    │ Token provided? │
    └────────┬────────┘
    No ──→   Return 401
    Yes ──→  Continue
             │
             ▼
    ┌─────────────────────────────────┐
    │ JWT decode(token, secret_key)   │
    │ Verify signature with HS256     │
    └────────┬───────────────────────┘
             │
    ┌────────┴──────────┐
    │ Signature valid?  │
    └────────┬──────────┘
    No ──→   Return 401
    Yes ──→  Continue
             │
             ▼
    ┌──────────────────────┐
    │ Check expiry        │
    │ if (now > exp)      │
    └────────┬──────────┘
             │
    ┌────────┴───────────┐
    │ Token expired?     │
    └────────┬───────────┘
    Yes ──→  Return 401
    No ──→   Continue
             │
             ▼
    ┌──────────────────────┐
    │ Check token type    │
    │ must be "access"    │
    └────────┬──────────┘
             │
    ┌────────┴────────────┐
    │ Type correct?      │
    └────────┬────────────┘
    No ──→   Return 401
    Yes ──→  Continue
             │
             ▼
    ┌────────────────────────┐
    │ Extract user_id from  │
    │ token payload["sub"]   │
    └────────┬───────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ Query database for User      │
    │ WHERE id = user_id           │
    └────────┬──────────────────────┘
             │
    ┌────────┴──────────┐
    │ User found?      │
    └────────┬──────────┘
    No ──→   Return 401
    Yes ──→  Continue
             │
             ▼
    ┌──────────────────────────┐
    │ Check user is_active    │
    └────────┬────────────────┘
             │
    ┌────────┴──────────────┐
    │ User still active?   │
    └────────┬──────────────┘
    No ──→   Return 403
    Yes ──→  Continue (Success!)
             │
             ▼
    ┌────────────────────────┐
    │ Return current_user    │
    │ User object passed to  │
    │ the route handler      │
    └────────────────────────┘
```

## 4. Token Refresh Flow

```
┌─────────────────────────────────────┐
│ POST /api/auth/refresh              │
│ {                                   │
│   "refresh_token": "eyJhbGc..."     │
│ }                                   │
└────────────────────┬────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Decode refresh_token       │
        │ with secret_key            │
        └────────┬───────────────────┘
                 │
        ┌────────┴───────────┐
        │ Token valid?       │
        └────────┬───────────┘
        No ──→   Return 401
        Yes ──→  Continue
                 │
                 ▼
        ┌───────────────────────┐
        │ Check type = refresh  │
        └────────┬──────────────┘
                 │
        ┌────────┴────────────┐
        │ Type correct?      │
        └────────┬────────────┘
        No ──→   Return 401
        Yes ──→  Continue
                 │
                 ▼
        ┌──────────────────────┐
        │ Extract user_id      │
        │ from token["sub"]    │
        └────────┬─────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │ Verify user exists     │
        │ and is_active = true   │
        └────────┬───────────────┘
                 │
        ┌────────┴────────┐
        │ User valid?     │
        └────────┬────────┘
        No ──→   Return 401
        Yes ──→  Continue
                 │
                 ▼
    ┌────────────────────────────┐
    │ Create new access_token    │
    │ (same 30-min expiry)       │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │ Return 200 Success         │
    │ {                          │
    │   "access_token": "...",   │
    │   "token_type": "bearer",  │
    │   "expires_in": 1800       │
    │ }                          │
    └────────┬───────────────────┘
             │
             ▼
    Frontend updates localStorage
    with new access_token
```

## 5. HTTP Status Codes

| Status | Meaning | Scenario |
|--------|---------|----------|
| 200 | Success | Login/signup successful, token valid |
| 400 | Bad Request | Email already exists, invalid input |
| 401 | Unauthorized | Invalid credentials, expired token, invalid token |
| 403 | Forbidden | User inactive, token type wrong |
| 500 | Server Error | Database error, hashing error |

## 6. Token Storage Strategy

```
Frontend (Lovable)
├── localStorage
│   ├── access_token (30-min expiry) ← Use for all API calls
│   └── refresh_token (7-day expiry) ← Use to get new access_token
├── In-Memory
│   ├── current_user object
│   └── token_expiry timestamp
└── HTTP Headers
    └── Authorization: Bearer {access_token}
```

## 7. Security Guarantees

```
Password: "SecurePass123!"
    ↓
bcrypt.hash(password)
    ↓
$2b$12$R9h.cIPz0gi.URNNX3kh2Opst9/PgBkqquzi.Ss7KIUgO2t0jKMUm
    ↓
Stored in database (never plain text)
    ↓
On login: bcrypt.verify(input_password, stored_hash)
    ↓
Returns True/False (comparison is constant-time)
```

## 8. Token Structure (JWT)

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

Header (decoded):
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload (decoded):
{
  "sub": "user_id_uuid",
  "exp": 1712151000,
  "type": "access"
}

Signature:
HMACSHA256(
  base64url(header) + "." + base64url(payload),
  secret_key
)
```

## Implementation Status

✅ All flows implemented
✅ All security checks in place
✅ All HTTP status codes handled
✅ Database integration complete
✅ Ready for Lovable frontend integration
