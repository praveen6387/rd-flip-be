# Create flipbook

Create a flipbook with ordered page images. JWT required.

```http
POST /api/flipbooks/create/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Back to [Flipbook index](./README.md) · [Response format](../auth/response-format.md)

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `title` | Yes | Flipbook title |
| `date` | Yes | Event / shoot date (`YYYY-MM-DD`) |
| `images` | Yes | Non-empty array. Each item: `page_number`, `image_url`, `cover_type` |
| `description` | No | Text. Defaults to `""` |
| `studio_name` | Lab only | Ignored for **studio** plan |
| `whatsapp_number` | Lab only | Ignored for **studio** plan. Same `+91` rules as signup |
| `instagram_url` | Lab only | Ignored for **studio** plan |
| `facebook_url` | Lab only | Ignored for **studio** plan |

### Images

```json
"images": [
  { "page_number": 1, "image_url": "https://cdn.example.com/p1.jpg", "cover_type": "front" },
  { "page_number": 2, "image_url": "https://cdn.example.com/p2.jpg", "cover_type": "middle" },
  { "page_number": 3, "image_url": "https://cdn.example.com/p3.jpg", "cover_type": "back" }
]
```

- `page_number` must be unique and ≥ 1
- Pages are stored in `page_number` order
- `cover_type` is required per image: `front` | `middle` | `back`

### Studio vs lab branding

| Plan | `studio_name`, `whatsapp_number`, `instagram_url`, `facebook_url` |
|------|-------------------------------------------------------------------|
| **studio** | Always copied from the logged-in **user** profile. Payload values are ignored. |
| **lab** | Use payload if provided (non-empty). If missing or blank, fall back to the user profile. |

`studio_name` and `whatsapp_number` must end up non-empty (from payload and/or profile). Instagram and Facebook may be empty.

The backend generates a unique `flip_id` (10 characters, letters + numbers) and stores it with a unique index. It is not sent in the request.

---

## cURL (studio)

```bash
curl -X POST http://127.0.0.1:8000/api/flipbooks/create/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Riya weds Arjun",
    "description": "Wedding highlight",
    "date": "2026-08-30",
    "images": [
      { "page_number": 1, "image_url": "https://cdn.example.com/front.jpg", "cover_type": "front" },
      { "page_number": 2, "image_url": "https://cdn.example.com/p2.jpg", "cover_type": "middle" },
      { "page_number": 3, "image_url": "https://cdn.example.com/back.jpg", "cover_type": "back" }
    ]
  }'
```

## cURL (lab — optional branding in payload)

```bash
curl -X POST http://127.0.0.1:8000/api/flipbooks/create/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Client album",
    "date": "2026-08-30",
    "studio_name": "Guest Studio",
    "whatsapp_number": "9876543210",
    "instagram_url": "https://instagram.com/gueststudio",
    "facebook_url": "https://facebook.com/gueststudio",
    "images": [
      { "page_number": 1, "image_url": "https://cdn.example.com/front.jpg", "cover_type": "front" },
      { "page_number": 2, "image_url": "https://cdn.example.com/back.jpg", "cover_type": "back" }
    ]
  }'
```

---

## Success response (`201 Created`)

```json
{
  "status": "success",
  "message": "Flipbook created",
  "details": "",
  "data": {
    "flipbook": {
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
      "pages": [
        {
          "id": 1,
          "page_number": 1,
          "image_url": "https://cdn.example.com/front.jpg",
          "cover_type": "front",
          "created_at": "2026-08-30T12:00:00.000000Z"
        },
        {
          "id": 2,
          "page_number": 2,
          "image_url": "https://cdn.example.com/p2.jpg",
          "cover_type": "middle",
          "created_at": "2026-08-30T12:00:00.000000Z"
        },
        {
          "id": 3,
          "page_number": 3,
          "image_url": "https://cdn.example.com/back.jpg",
          "cover_type": "back",
          "created_at": "2026-08-30T12:00:00.000000Z"
        }
      ],
      "created_at": "2026-08-30T12:00:00.000000Z",
      "updated_at": "2026-08-30T12:00:00.000000Z"
    }
  }
}
```

---

## Fail response (`400`)

```json
{
  "status": "fail",
  "message": "Provide at least one image.",
  "details": "Provide at least one image.",
  "data": null
}
```
