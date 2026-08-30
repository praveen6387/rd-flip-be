# Public flipbook (by flip_id)

Return one flipbook and **all** of its pages. No JWT.

Image URLs in the response are **signed** (browser can load private S3 objects).

```http
GET /api/flipbooks/<flip_id>/
```

Back to [Flipbook index](./README.md) · [Response format](../auth/response-format.md)

---

## Auth

None. Only `flip_id` is required (path).

---

## cURL

```bash
curl http://127.0.0.1:8000/api/flipbooks/aB3kP9xQ2m/
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Flipbook fetched",
  "details": "",
  "data": {
    "flipbook": {
      "flip_id": "aB3kP9xQ2m",
      "title": "Riya weds Arjun",
      "description": "Wedding highlight",
      "date": "2026-08-30",
      "studio_name": "My Studio",
      "whatsapp_number": "+919876543210",
      "instagram_url": "https://instagram.com/mystudio",
      "facebook_url": "https://facebook.com/mystudio",
      "total_pages": 3,
      "pages": [
        {
          "page_number": 1,
          "image_url": "https://rd-flip-photos.s3.ap-south-1.amazonaws.com/flipbooks/.../front-001.jpg?X-Amz-Algorithm=...&X-Amz-Signature=...",
          "cover_type": "front"
        },
        {
          "page_number": 2,
          "image_url": "https://rd-flip-photos.s3.ap-south-1.amazonaws.com/flipbooks/.../p2.jpg?X-Amz-Algorithm=...&X-Amz-Signature=...",
          "cover_type": "middle"
        },
        {
          "page_number": 3,
          "image_url": "https://rd-flip-photos.s3.ap-south-1.amazonaws.com/flipbooks/.../back.jpg?X-Amz-Algorithm=...&X-Amz-Signature=...",
          "cover_type": "back"
        }
      ]
    }
  }
}
```

Use each `image_url` as-is in `<img src>` (keep the query string). Signed URLs expire after `AWS_S3_PRESIGN_EXPIRES` seconds (default 1 hour).

---

## Fail response (`404`)

```json
{
  "status": "fail",
  "message": "Flipbook not found.",
  "details": "Flipbook not found.",
  "data": null
}
```
