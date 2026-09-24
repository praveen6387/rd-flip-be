# Change password

Update the authenticated user's password. JWT required.

```http
POST /api/auth/change-password/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Back to [Auth index](./README.md) · [Response format](./response-format.md)

---

## Auth

Requires a valid JWT access token:

```text
Authorization: Bearer eyJ...
```

The token identifies the user. The current password is then checked against that user.

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `current_password` | Yes | Existing account password |
| `new_password` | Yes | Min 8 characters. Must differ from `current_password` |

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/change-password/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "secret123",
    "new_password": "newsecret123"
  }'
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Password updated",
  "details": "",
  "data": null
}
```

---

## Fail response (`400`)

Current password does not match:

```json
{
  "status": "fail",
  "message": "Current password is incorrect.",
  "details": "Current password is incorrect.",
  "data": null
}
```

New password same as current:

```json
{
  "status": "fail",
  "message": "New password must be different from the current password.",
  "details": "New password must be different from the current password.",
  "data": null
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
