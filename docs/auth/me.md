# Me (profile)

Return the authenticated user's full profile for the profile page.

```http
GET /api/auth/me/
Authorization: Bearer <access_token>
```

Back to [Auth index](./README.md) · [Response format](./response-format.md)

---

## Auth

Requires a valid JWT access token in the `Authorization` header:

```text
Authorization: Bearer eyJ...
```

---

## cURL

```bash
curl http://127.0.0.1:8000/api/auth/me/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Profile fetched",
  "details": "",
  "data": {
    "user": {
      "user_id": "uuid-here",
      "first_name": "Praveen",
      "last_name": "Maurya",
      "dob": "1995-08-15",
      "email": "praveen@example.com",
      "phone": "+919876543210",
      "studio_name": "My Studio",
      "plan": "studio",
      "whatsapp_number": "",
      "instagram_url": "",
      "facebook_url": "",
      "total_credit": 0,
      "used_credit": 0,
      "left_credit": 0,
      "credit_expire_date": null,
      "created_at": "2026-08-29T08:00:00.000000Z",
      "updated_at": "2026-08-29T08:00:00.000000Z",
      "updated_by": null
    }
  }
}
```

---

## Fail response (`401`)

Missing or invalid token:

```json
{
  "status": "fail",
  "message": "Authentication credentials were not provided.",
  "details": "Authentication credentials were not provided.",
  "data": null
}
```
