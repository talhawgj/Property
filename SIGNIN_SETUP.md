# Quick Start Guide

## 1. Add JWT Secret to .env

Add this line to your `.env` file:
```
JWT_SECRET_KEY=gmVpihKJ2kQnEPJH77nXppvwO2qgvrXO9b7mt1_6FIM
```

> [!IMPORTANT]
> For production, generate your own secure key using:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

## 2. Restart Your Application

The `users` table will be created automatically when the application starts.

## 3. Create a Test User

```bash
python3 create_test_user.py --email test@example.com --password testpassword123 --name "Test User"
```

## 4. Test the Signin Endpoint

```bash
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}'
```

Or run the automated test suite:
```bash
python3 test_signin.py
```

## Signin Endpoint

**URL**: `POST /auth/signin`

**Request**:
```json
{
  "email": "test@example.com",
  "password": "testpassword123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "full_name": "Test User",
    "is_active": true,
    "created_at": "2026-01-13T12:30:00"
  }
}
```

## Security Features

✅ Bcrypt password hashing  
✅ JWT token authentication  
✅ 30-minute token expiration  
✅ Email validation  
✅ Generic error messages (prevents user enumeration)

For detailed documentation, see [walkthrough.md](file:///home/lamp/.gemini/antigravity/brain/846bd9b5-a200-482b-a8ea-c9803747f2e9/walkthrough.md)
