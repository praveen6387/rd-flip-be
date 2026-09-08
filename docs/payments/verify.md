# Verify payment

Verify Razorpay Checkout response, mark the order as `paid`, create `PaymentTransaction`, create `UserPlan`, and allocate purchased credits. JWT required.

```http
POST /api/payments/verify/
Authorization: Bearer <access_token>
Content-Type: application/json
```

Back to [Payments index](./README.md) · [Response format](../auth/response-format.md)

---

## Flow

```text
Receive Razorpay response
        ↓
Find Order using razorpay_order_id (= gateway_order_id)
        ↓
Verify Razorpay signature
        ↓
If valid → payment verified
        ↓
Update Order (payment_status = paid, link user_plan)
        ↓
Create PaymentTransaction (success)
        ↓
Expire any existing active UserPlan
        ↓
Create UserPlan (active, start → +validity_days)
        ↓
Allocate credits (User totals + CreditTransaction)
```

Credit allocation (`apps/payments/services/credit_allocation.py`):

- Not expired: `left += plan.credit`, `total += plan.credit`, set `credit_expire_date` from new plan
- Expired with leftover: move old `left` → `expired`, then add new credits; write `expiry` + `purchase` transactions
- `left = 0`: just add new credits
- Sets `user.plan` = `plan.plan_type` (`studio` / `lab`)
- Idempotent: skips if a `purchase` `CreditTransaction` already exists for this order

---

## Request body

| Field | Required | Notes |
|-------|----------|--------|
| `razorpay_payment_id` | Yes | From Razorpay Checkout success handler |
| `razorpay_order_id` | Yes | Must match `order.gateway_order_id` |
| `razorpay_signature` | Yes | From Razorpay Checkout success handler |

---

## cURL

```bash
curl -X POST http://127.0.0.1:8000/api/payments/verify/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_payment_id": "pay_xxxxx",
    "razorpay_order_id": "order_xxxxx",
    "razorpay_signature": "xxxxx"
  }'
```

---

## Success response (`200`)

```json
{
  "status": "success",
  "message": "Payment verified",
  "details": "",
  "data": {
    "order": {
      "id": 1,
      "order_name": "ORDA1B2C3D4E5",
      "plan_id": 1,
      "plan_name": "Studio Starter",
      "plan_type": "studio",
      "amount": "499.00",
      "payment_status": "paid",
      "gateway_order_id": "order_xxxxx",
      "created_at": "2026-09-08T12:00:00.000000Z"
    },
    "razorpay_payment_id": "pay_xxxxx"
  }
}
```

If the order was already `paid`, message is `"Payment already verified"` (idempotent).

---

## Fail responses (`400`)

Order not found (wrong id or not owned by user):

```json
{
  "status": "fail",
  "message": "Order not found.",
  "details": "Order not found.",
  "data": null
}
```

Invalid signature:

```json
{
  "status": "fail",
  "message": "Payment signature verification failed.",
  "details": "Payment signature verification failed.",
  "data": null
}
```

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
