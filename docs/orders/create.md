# Create order

Create a pending order for an active plan, create a matching Razorpay order, save `gateway_order_id`, and return both to the FE. JWT required.

```http
POST /api/orders/create/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Back to [Orders index](./README.md) · [Response format](../auth/response-format.md)

---

## Flow

```text
Create Order (DB)
    ↓
Create Razorpay Order
    ↓
Save gateway_order_id
    ↓
Return Order + Razorpay payload
```

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `plan_id` | Yes | ID of an **active** plan from `GET /api/plans/` |

Backend sets:

- `order_name` — unique (`ORD` + 10 chars)
- `user` — logged-in user
- `amount` — from `plan.price`
- `payment_status` — `pending`
- `gateway_order_id` — Razorpay order id (`order_…`)
- `created_by` / `updated_by` — current user's `user_id`

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/orders/create/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1
  }'
```

---

## Success response (`201 Created`)

```json
{
  "status": "success",
  "message": "Order created",
  "details": "",
  "data": {
    "order": {
      "id": 1,
      "order_name": "ORDA1B2C3D4E5",
      "plan_id": 1,
      "plan_name": "Studio Starter",
      "plan_type": "studio",
      "amount": "499.00",
      "payment_status": "pending",
      "gateway_order_id": "order_Nxyz123",
      "created_at": "2026-09-08T12:00:00.000000Z"
    },
    "razorpay": {
      "key_id": "rzp_test_xxxxxxxxx",
      "order_id": "order_Nxyz123",
      "amount": 49900,
      "currency": "INR"
    }
  }
}
```

`razorpay.amount` is in **paise** (₹499 → `49900`). Use `data.razorpay` to open Razorpay Checkout on the FE.

---

## Fail — missing / invalid `plan_id` (`400`)

Missing field:

```json
{
  "status": "fail",
  "message": "This field is required.",
  "details": "This field is required.",
  "data": null
}
```

Not an integer / invalid value:

```json
{
  "status": "fail",
  "message": "A valid integer is required.",
  "details": "A valid integer is required.",
  "data": null
}
```

Plan does not exist or is inactive:

```json
{
  "status": "fail",
  "message": "Invalid plan.",
  "details": "Invalid plan.",
  "data": null
}
```

Razorpay order creation failed:

```json
{
  "status": "fail",
  "message": "Unable to create payment order. Please try again.",
  "details": "Unable to create payment order. Please try again.",
  "data": null
}
```

(If Razorpay fails, the local order is rolled back — no orphan row.)

---

## Fail — not authenticated (`401`)

```json
{
  "status": "fail",
  "message": "Authentication credentials were not provided.",
  "details": "Authentication credentials were not provided.",
  "data": null
}
```
