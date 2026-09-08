# Payments

Base URL (local):

```text
http://127.0.0.1:8000/api/payments/
```

## Pages

| Page | What it covers |
|------|----------------|
| [Verify](./verify.md) | Verify Razorpay payment signature (JWT required) |

## APIs overview

| Method | Path | Doc |
|--------|------|-----|
| `POST` | `/api/payments/verify/` | [verify.md](./verify.md) |

## Code folder (`apps/payments/`)

```text
apps/payments/
├── apps.py
├── urls.py
├── views.py
├── serializers.py
├── services/
│   └── razorpay_service.py
└── migrations/
```
