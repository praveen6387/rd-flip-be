import secrets
import string

ORDER_NAME_ALPHABET = string.ascii_uppercase + string.digits
ORDER_NAME_SUFFIX_LENGTH = 10


def generate_order_name() -> str:
    suffix = "".join(secrets.choice(ORDER_NAME_ALPHABET) for _ in range(ORDER_NAME_SUFFIX_LENGTH))
    return f"RD-{suffix}"


def unique_order_name() -> str:
    from rd_flip_be.models import Order

    for _ in range(20):
        name = generate_order_name()
        if not Order.objects.filter(order_name=name).exists():
            return name
    raise RuntimeError("Could not generate a unique order_name")
