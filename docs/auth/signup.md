# Signup

Create a new user account.

```http
POST /api/auth/signup/
Content-Type: application/json
```

Back to [Auth index](./README.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `first_name` | Yes | User first name |
| `last_name` | Yes | User last name |
| `phone` | Yes | Indian mobile. Saved as `+91…`. If already has `+91`, it is not doubled. |
| `password` | Yes | Min 8 characters |
| `email` | No | If empty/missing → `{10digitphone}@gmail.com` |
| `studio_name` | No | Studio name |

**Not accepted on signup** (update API later):

- `whatsapp_number`
- `instagram_url`
- `facebook_url`

**Always set by backend:**

- `plan` = `studio`

### Phone rules

Accepted:

- `9876543210`
- `+919876543210`
- `919876543210`
- `09876543210`

All stored as:

```text
+919876543210
```

Invalid numbers (wrong length / not starting with 6–9) are rejected.

---

## cURL

### Without email

```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Praveen",
    "last_name": "Maurya",
    "phone": "9876543210",
    "password": "secret123",
    "studio_name": "My Studio"
  }'
```

Email saved as: `9876543210@gmail.com`

### With email

```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Praveen",
    "last_name": "Maurya",
    "email": "praveen@example.com",
    "phone": "9876543210",
    "password": "secret123",
    "studio_name": "My Studio"
  }'
```

---

## Success response (`201 Created`)

```json
{
  "message": "Signup successful",
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

---

## Common errors (`400`)

```json
{ "phone": ["A user with this phone already exists."] }
```

```json
{ "phone": ["Enter a valid 10-digit Indian mobile number."] }
```

```json
{ "email": ["A user with this email already exists."] }
```
