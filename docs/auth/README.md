# Auth

Auth feature docs live here — one topic per file (no duplicates).

Base URL (local):

```text
http://127.0.0.1:8000/api/auth/
```

## Pages

| Page | What it covers |
|------|----------------|
| [Response format](./response-format.md) | Common success/fail JSON shape |
| [Signup](./signup.md) | Signup + tokens (go to dashboard) |
| [Login](./login.md) | Login + tokens |
| [Refresh](./refresh.md) | Refresh access token + frontend flow |

## Code folder (`apps/auth/`)

```text
apps/auth/
├── apps.py            ← App config (label: user_auth)
├── helpers.py         ← Shared helpers (normalize_indian_phone)
├── urls.py            ← Routes: health/, signup/, login/, refresh/
├── views.py           ← API views
├── serializers.py     ← Request validation
└── migrations/
```

Models stay in `rd_flip_be/models.py`.

### Request flow

```text
Client → /api/auth/...
  → rd_flip_be/urls.py
    → apps/auth/urls.py
      → views.py
        → serializers.py
          → User model
```

## APIs overview

| Method | Path | Doc |
|--------|------|-----|
| `GET` | `/api/auth/health/` | below |
| `POST` | `/api/auth/signup/` | [signup.md](./signup.md) |
| `POST` | `/api/auth/login/` | [login.md](./login.md) |
| `POST` | `/api/auth/refresh/` | [refresh.md](./refresh.md) |

### Health (quick)

```bash
curl http://127.0.0.1:8000/api/auth/health/
```

```json
{
  "status": "success",
  "message": "OK",
  "details": "",
  "data": { "status": "ok" }
}
```

## Coming next

- Profile update (WhatsApp / Instagram / Facebook)
