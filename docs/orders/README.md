# Orders

Base URL (local):

```text
http://127.0.0.1:8000/api/orders/
```

## Pages

| Page | What it covers |
|------|----------------|
| [Create](./create.md) | Create order for a plan (JWT required) |

## APIs overview

| Method | Path | Doc |
|--------|------|-----|
| `POST` | `/api/orders/create/` | [create.md](./create.md) |

## Code folder (`apps/orders/`)

```text
apps/orders/
├── apps.py
├── helpers.py       ← generate unique order_name
├── urls.py
├── views.py
├── serializers.py
└── migrations/
```

Models stay in `rd_flip_be/models.py` (`Order`, `Plan`).
