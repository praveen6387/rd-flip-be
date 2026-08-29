# Login

Login with phone or email and get JWT tokens.

```http
POST /api/auth/login/
Content-Type: application/json
```

Back to [Auth index](./README.md)

---

## Request body

Provide **either** `phone` **or** `email`, plus `password`.

| Field | Required | Notes |
|-------|----------|--------|
| `password` | Yes | Account password |
| `phone` | One of phone/email | Same `+91` rules as signup |
| `email` | One of phone/email | Exact email used at signup |

---

## cURL

### With phone

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "9876543210",
    "password": "secret123"
  }'
```

### With email

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "praveen@example.com",
    "password": "secret123"
  }'
```

---

## Success response (`200 OK`)

```json
{
  "message": "Login successful",
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  },
  "user": {
    "user_id": "uuid-here",
    "first_name": "Praveen",
    "last_name": "Maurya",
    "email": "9876543210@gmail.com",
    "phone": "+919876543210",
    "studio_name": "My Studio",
    "plan": "studio",
    "created_at": "2026-08-29T08:00:00.000000Z"
  }
}
```

Use the access token on protected APIs later:

```text
Authorization: Bearer <access>
```

When access expires, use [Refresh](./refresh.md) — do not ask the user to log in again until refresh also fails.

---

## Common errors (`400`)

```json
{ "non_field_errors": ["Invalid credentials."] }
```

```json
{ "non_field_errors": ["Provide email or phone to login."] }
```
