# Plans

Base URL (local):

```text
http://127.0.0.1:8000/api/plans/
```

## Pages

| Page | What it covers |
|------|----------------|
| [List](./list.md) | List active plans (public) |

## APIs overview

| Method | Path | Doc |
|--------|------|-----|
| `GET` | `/api/plans/` | [list.md](./list.md) |

## Code folder (`apps/plans/`)

```text
apps/plans/
├── apps.py
├── urls.py
├── views.py
├── serializers.py
└── migrations/
```

Models stay in `rd_flip_be/models.py` (`Plan`).
