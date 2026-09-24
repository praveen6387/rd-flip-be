# Forgot password

Send a password reset link to the user's email. No JWT required.

```http
POST /api/auth/forgot-password/
Content-Type: application/json
```

Back to [Auth index](./README.md) · [Response format](./response-format.md) · [Reset password](./reset-password.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `email` | Yes | Must match an existing user |

If the email exists, the backend stores a hashed token and emails:

```text
https://rd-studio.in/reset-password?token=<password_reset_token>
```

The raw token is never stored. It expires in **5 minutes** and can be used once. A new request invalidates any unused token for that user.

Override the site URL with `FRONTEND_BASE_URL` in `.env` (default `https://rd-studio.in`).

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/forgot-password/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "praveen@example.com"
  }'
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Password reset link sent",
  "details": "",
  "data": null
}
```

In local `DEBUG`, the email is printed to the Django console unless SMTP is configured.

---

## Fail response (`400`)

Unknown email:

```json
{
  "status": "fail",
  "message": "No account found with this email.",
  "details": "No account found with this email.",
  "data": null
}
```
