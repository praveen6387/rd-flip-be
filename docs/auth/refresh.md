# Refresh token

Get a new **access** token using a valid **refresh** token (when access has expired).

```http
POST /api/auth/refresh/
Content-Type: application/json
```

Back to [Auth index](./README.md) · [Response format](./response-format.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `refresh` | Yes | Refresh token from login/signup (or previous refresh) |

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<refresh_token>"
  }'
```

---

## Success response (`200 OK`)

```json
{
  "status": "success",
  "message": "Token refreshed",
  "details": "",
  "data": {
    "tokens": {
      "access": "eyJ...",
      "refresh": "eyJ..."
    }
  }
}
```

Store the new refresh token too (rotation is on).

---

## Fail response (`401`)

```json
{
  "status": "fail",
  "message": "Token is invalid or expired",
  "details": "Token is invalid or expired",
  "data": null
}
```

If refresh fails, clear tokens and go to **Login**.

---

## Frontend flow (when access expires)

### After signup or login

Save `data.tokens.access` and `data.tokens.refresh`.

### Normal API call

```text
Authorization: Bearer <access>
```

- success → done  
- `401` → try refresh

### Refresh flow

```text
1. Protected API returns 401
2. POST /api/auth/refresh/  { "refresh": "..." }
3. If status === "success":
     - save data.tokens.access
     - save data.tokens.refresh (if present)
     - retry original API once
4. If status === "fail":
     - clear tokens
     - go to Login
```

### Diagram

```text
[ Signup / Login ]
    │
    ▼
store data.tokens.access + data.tokens.refresh
    │
    ▼
[ Call API with access ] ──success──► done
    │
   401
    │
    ▼
[ POST /api/auth/refresh/ ]
    │
    ├── success → update tokens → retry API once
    └── fail    → clear tokens → Login
```

### Pseudocode

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

  const refreshRes = await fetch("http://127.0.0.1:8000/api/auth/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: getRefreshToken() }),
  });
  const body = await refreshRes.json();

  if (body.status !== "success") {
    clearTokens();
    goToLogin();
    return refreshRes;
  }

  setAccessToken(body.data.tokens.access);
  if (body.data.tokens.refresh) setRefreshToken(body.data.tokens.refresh);

  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${body.data.tokens.access}`,
    },
  });
}
```

### Rules

1. Send `refresh` only to `/api/auth/refresh/`
2. Send `access` as `Authorization: Bearer ...`
3. On refresh success, replace stored tokens
4. On refresh failure, force login
5. Retry the original request **once** only
