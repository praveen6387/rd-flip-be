# Delete flipbook

Soft-delete a flipbook owned by the logged-in user. Sets `is_active=false` (row is kept). JWT required.

Uses the numeric database `id` (not `flip_id`).

```http
DELETE /api/flipbooks/<id>/
Authorization: Bearer <access_token>
```

Back to [Flipbook index](./README.md) · [Response format](../auth/response-format.md)

---

## Auth

Requires a valid JWT access token. Only the owner can delete their flipbook.

```text
Authorization: Bearer eyJ...
```

---

## Path params

| Param | Type | Notes |
|-------|------|--------|
| `id` | int | Flipbook primary key (`Flipbook.id`) |

---

## Behaviour

- Looks up flipbook by `id` **and** `user=request.user` **and** `is_active=true`
- On success: `is_active=false`, updates `updated_by`
- Soft-deleted flipbooks are hidden from [list](./list.md) and [public](./public.md) APIs

---

## cURL

```bash
curl -X DELETE http://127.0.0.1:8000/api/flipbooks/1/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Flipbook deleted",
  "details": "",
  "data": null
}
```

---

## Fail response (`404`)

Not found, already deleted, or not owned by the user:

```json
{
  "status": "fail",
  "message": "Flipbook not found.",
  "details": "Flipbook not found.",
  "data": null
}
```

Unauthorized (missing/invalid JWT) returns the usual auth fail from DRF/JWT.
