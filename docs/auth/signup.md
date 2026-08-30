# Signup

Create a new user account and receive JWT tokens (same as login) so the app can open the dashboard immediately.

```http
POST /api/auth/signup/
Content-Type: application/json
```

Back to [Auth index](./README.md) · [Response format](./response-format.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `first_name` | Yes | User first name |
| `last_name` | Yes | User last name |
| `email` | Yes | Required at API level |
| `phone` | Yes | Indian mobile. Saved as `+91…`. If already has `+91`, it is not doubled. |
| `password` | Yes | Min 8 characters |
| `dob` | No | Date of birth (`YYYY-MM-DD`) |
| `studio_name` | No | Studio name |

**Not accepted on signup** (use [Me PUT](./me.md)):

- `whatsapp_number`
- `instagram_url`
- `facebook_url`

**Always set by backend:**

- `plan` = `studio`
- `total_credit` = `1` (1 free welcome credit)
- `used_credit` = `0`
- `left_credit` = `1`
- `expired_credit` = `0`
- `credit_expire_date` = signup date + 7 days

### Phone rules

Accepted: `9876543210`, `+919876543210`, `919876543210`, `09876543210`  
Stored as: `+919876543210`

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Praveen",
    "last_name": "Maurya",
    "email": "praveen@example.com",
    "phone": "9876543210",
    "password": "secret123",
    "dob": "1995-08-15",
    "studio_name": "My Studio"
  }'
```

---

## Success response (`201 Created`)

```json
{
  "status": "success",
  "message": "Signup successful",
  "details": "",
  "data": {
    "tokens": {
      "access": "eyJ...",
      "refresh": "eyJ..."
    },
    "user": {
      "user_id": "uuid-here",
      "first_name": "Praveen",
      "last_name": "Maurya",
      "dob": "1995-08-15",
      "email": "praveen@example.com",
      "phone": "+919876543210",
      "studio_name": "My Studio",
      "plan": "studio",
      "total_credit": 1,
      "used_credit": 0,
      "left_credit": 1,
      "expired_credit": 0,
      "credit_expire_date": "2026-09-06",
      "created_at": "2026-08-29T08:00:00.000000Z"
    }
  }
}
```

Frontend: save `data.tokens` and go to dashboard (no separate login needed).

---

## Fail response (`400`)

```json
{
  "status": "fail",
  "message": "A user with this phone already exists.",
  "details": "A user with this phone already exists.",
  "data": null
}
```
