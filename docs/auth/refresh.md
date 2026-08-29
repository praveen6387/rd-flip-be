# Refresh token

Get a new **access** token using a valid **refresh** token (when access has expired).

```http
POST /api/auth/refresh/
Content-Type: application/json
```

Back to [Auth index](./README.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `refresh` | Yes | Refresh token from login (or previous refresh) |

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<refresh_token_from_login>"
  }'
```

---

## Success response (`200 OK`)

Because `ROTATE_REFRESH_TOKENS=True` in settings, you usually get **both** a new access and a new refresh:

```json
{
  "message": "Token refreshed",
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

Store the new refresh token too (replace the old one).

---

## Common errors (`401`)

Invalid / expired refresh:

```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

If refresh fails, the frontend should send the user back to **login**.

---

## Frontend flow (when access expires)

### Tokens after login

Save both tokens (memory, secure storage, or httpOnly cookie — your choice):

- `access` — send on every protected API call
- `refresh` — only send to `/api/auth/refresh/`

### Normal API call

```text
Request → Authorization: Bearer <access>
```

- If `200` → use the response
- If `401` (access expired / invalid) → try refresh (below)

### Refresh flow

```text
1. Protected API returns 401 (access expired)
2. Frontend calls POST /api/auth/refresh/ with { "refresh": "..." }
3. If refresh OK:
     - save new access
     - save new refresh (because rotation is on)
     - retry the original API with the new access
4. If refresh fails (401):
     - clear tokens
     - redirect user to Login screen
```

### Simple diagram

```text
[ Login ]
    │
    ▼
store access + refresh
    │
    ▼
[ Call API with access ] ──200──► success
    │
   401
    │
    ▼
[ POST /api/auth/refresh/ ]
    │
    ├── success → update tokens → retry API
    └── fail    → clear tokens → go to Login
```

### Pseudocode (frontend)

```js
async function apiFetch(url, options = {}) {
  let access = getAccessToken();
  let res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${access}`,
    },
  });

  if (res.status !== 401) return res;

  // access likely expired → refresh
  const refresh = getRefreshToken();
  const refreshRes = await fetch("http://127.0.0.1:8000/api/auth/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!refreshRes.ok) {
    clearTokens();
    goToLogin();
    return refreshRes;
  }

  const data = await refreshRes.json();
  setAccessToken(data.tokens.access);
  if (data.tokens.refresh) setRefreshToken(data.tokens.refresh);

  // retry original request once
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${data.tokens.access}`,
    },
  });
}
```

### Rules of thumb

1. Never send `refresh` on normal APIs — only to `/api/auth/refresh/`
2. Always send `access` as `Authorization: Bearer ...`
3. On refresh success, replace stored tokens
4. On refresh failure, force login again
5. Don’t loop refresh forever — retry the original request **once**
