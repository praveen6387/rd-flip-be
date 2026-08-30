# List flipbooks

Return the logged-in user's flipbooks. JWT required.

Does **not** return all page images. Only the first page (`page_number` order) is sent as `thumbnail`.

S3 objects are private. `thumbnail` in the response is a **signed URL** (expires after `AWS_S3_PRESIGN_EXPIRES` seconds, default 1 hour) so the browser can show the image without a 403.

```http
GET /api/flipbooks/
Authorization: Bearer <access_token>
```

Back to [Flipbook index](./README.md) · [Response format](../auth/response-format.md)

---

## Auth

Requires a valid JWT access token. Only flipbooks owned by that user are returned.

```text
Authorization: Bearer eyJ...
```

---

## cURL

```bash
curl http://127.0.0.1:8000/api/flipbooks/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Flipbooks fetched",
  "details": "",
  "data": {
    "flipbooks": [
      {
        "id": 1,
        "flip_id": "aB3kP9xQ2m",
        "title": "Riya weds Arjun",
        "description": "Wedding highlight",
        "date": "2026-08-30",
        "studio_name": "My Studio",
        "whatsapp_number": "+919876543210",
        "instagram_url": "https://instagram.com/mystudio",
        "facebook_url": "https://facebook.com/mystudio",
        "total_pages": 3,
        "thumbnail": "https://cdn.example.com/front.jpg",
        "created_at": "2026-08-30T12:00:00.000000Z",
        "updated_at": "2026-08-30T12:00:00.000000Z"
      }
    ]
  }
}
```

`thumbnail` is `null` if the flipbook has no pages. For S3 photos it looks like:

```text
https://rd-flip-photos.s3.ap-south-1.amazonaws.com/flipbooks/.../front-001.jpg?X-Amz-Algorithm=...&X-Amz-Signature=...
```

Use that full URL in `<img src>`. Do not strip the query string.

---

## Fail response (`401`)

```json
{
  "status": "fail",
  "message": "Authentication credentials were not provided.",
  "details": "Authentication credentials were not provided.",
  "data": null
}
```
