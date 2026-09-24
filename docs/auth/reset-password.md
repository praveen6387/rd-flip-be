# Reset password

Set a new password using the token from the forgot-password email. No JWT required.

```http
POST /api/auth/reset-password/
Content-Type: application/json
```

Back to [Auth index](./README.md) · [Response format](./response-format.md) · [Forgot password](./forgot-password.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `password_reset_token` | Yes | `token` query value from the email link |
| `new_password` | Yes | Min 8 characters |

The frontend should read `token` from `/reset-password?token=...` and send it as `password_reset_token`. The user does not type the token.

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/reset-password/ \
  -H "Content-Type: application/json" \
  -d '{
    "password_reset_token": "<token-from-email-link>",
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

Invalid or expired token:

```json
{
  "status": "fail",
  "message": "Invalid or expired reset token.",
  "details": "Invalid or expired reset token.",
  "data": null
}
```
