from functools import lru_cache

import razorpay
from django.conf import settings


@lru_cache(maxsize=1)
def get_razorpay_client():
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )


def create_razorpay_order(order) -> dict:
    """
    Create a Razorpay order for a local Order row.
    Amount is in paise (INR * 100).
    Does not save gateway_order_id — the order create API saves it.
    """
    client = get_razorpay_client()
    return client.order.create(
        {
            "amount": int(order.amount * 100),
            "currency": "INR",
            "receipt": order.order_name,
        }
    )


def verify_razorpay_signature(
    *,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify Checkout payment signature.
    Returns True if valid; False if signature does not match.
    """
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
