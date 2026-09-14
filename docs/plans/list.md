# List plans

Return all **active** plans from the `plans` table. No JWT required.

Ordered by `price` ascending.

```http
GET /api/plans/
```

Back to [Plans index](./README.md) · [Response format](../auth/response-format.md)

---

## Auth

None. Public endpoint.

---

## cURL

```bash
curl http://127.0.0.1:8000/api/plans/
```

---

## Success — plans exist (`200`)

```json
{
  "status": "success",
  "message": "Plans fetched",
  "details": "",
  "data": {
    "plans": [
      {
        "id": 1,
        "name": "Studio Starter",
        "plan_type": "studio",
        "price": "499.00",
        "credit": 5,
        "validity_days": 30,
        "features": [],
        "is_active": true,
        "created_at": "2026-09-08T10:00:00.000000Z",
        "updated_at": "2026-09-08T10:00:00.000000Z"
      },
      {
        "id": 2,
        "name": "Lab Pro",
        "plan_type": "lab",
        "price": "999.00",
        "credit": 20,
        "validity_days": 30,
        "features": [],
        "is_active": true,
        "created_at": "2026-09-08T10:00:00.000000Z",
        "updated_at": "2026-09-08T10:00:00.000000Z"
      }
    ]
  }
}
```

---

## Success — no plans (`200`)

When the table has no active plans, `plans` is an empty array:

```json
{
  "status": "success",
  "message": "Plans fetched",
  "details": "",
  "data": {
    "plans": []
  }
}
```

Inactive plans (`is_active=false`) are not returned.
