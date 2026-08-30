# Flipbook

Base URL (local):

```text
http://127.0.0.1:8000/api/flipbooks/
```

## Pages

| Page | What it covers |
|------|----------------|
| [Create](./create.md) | Create flipbook + pages (JWT required) |

## APIs overview

| Method | Path | Doc |
|--------|------|-----|
| `POST` | `/api/flipbooks/` | [create.md](./create.md) |

## Code folder (`apps/flipbooks/`)

```text
apps/flipbooks/
├── apps.py
├── helpers.py
├── urls.py
├── views.py
├── serializers.py
└── migrations/
```

Models stay in `rd_flip_be/models.py` (`Flipbook`, `FlipbookPage`).
