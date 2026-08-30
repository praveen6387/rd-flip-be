# Me (profile)

Return the authenticated user's full profile, or update social links.

```http
GET  /api/auth/me/
PUT  /api/auth/me/
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
      "expired_credit": 0,
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

---

## Update social links (`PUT`)

Update WhatsApp, Instagram, and/or Facebook. JWT required. Send only the fields you want to change; omit a field to leave it unchanged. Send `""` to clear a field.

Sets `updated_by` to the current user's `user_id`.

```http
PUT /api/auth/me/
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request body

| Field | Required | Notes |
|-------|----------|--------|
| `whatsapp_number` | No | Same Indian mobile rules as signup phone. Saved as `+91…`. |
| `instagram_url` | No | Full URL (e.g. `https://instagram.com/studio`) |
| `facebook_url` | No | Full URL (e.g. `https://facebook.com/studio`) |

### cURL

```bash
curl -X PUT http://127.0.0.1:8000/api/auth/me/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "whatsapp_number": "9876543210",
    "instagram_url": "https://instagram.com/mystudio",
    "facebook_url": "https://facebook.com/mystudio"
  }'
```

### Success response (`200`)

Same `data.user` shape as GET above, with updated social fields and `updated_by` set to the current `user_id`.

```json
{
  "status": "success",
  "message": "Profile updated",
  "details": "",
  "data": {
    "user": {
      "user_id": "uuid-here",
      "whatsapp_number": "+919876543210",
      "instagram_url": "https://instagram.com/mystudio",
      "facebook_url": "https://facebook.com/mystudio"
    }
  }
}
```

### Fail response (`400`)

```json
{
  "status": "fail",
  "message": "Enter a valid 10-digit Indian mobile number.",
  "details": "Enter a valid 10-digit Indian mobile number.",
  "data": null
}
```
