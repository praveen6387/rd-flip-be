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
      "active_until": "2026-11-28T12:00:00.000000Z",
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

`active_until` is the free-period expiry datetime, or `null` when the flipbook has no fixed expiry (e.g. after a paid plan / recharge).

Use each `image_url` as-is in `<img src>` (keep the query string). Signed URLs expire after `AWS_S3_PRESIGN_EXPIRES` seconds (default 1 hour).

---

## Expired flipbook (`200`, body `status: "fail"`)

When `active_until` is set and in the past, HTTP stays **200** but the body uses `status: "fail"`. Same flipbook fields as success, but **without** `pages`.

```json
{
  "status": "fail",
  "message": "This flipbook has expired.",
  "details": "This flipbook is no longer available.",
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
      "active_until": "2026-11-28T12:00:00.000000Z"
    }
  }
}
```

Frontend: treat `body.status === "fail"` as expired even when HTTP is 200.

---

## Fail response (`404`)

Unknown `flip_id`, or flipbook was soft-deleted (`is_active=false`):

```json
{
  "status": "fail",
  "message": "Flipbook not found.",
  "details": "Flipbook not found.",
  "data": null
}
```
