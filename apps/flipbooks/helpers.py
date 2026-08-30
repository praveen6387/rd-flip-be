import secrets
import string

FLIP_ID_ALPHABET = string.ascii_letters + string.digits
FLIP_ID_LENGTH = 10


def first_non_empty(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def generate_flip_id() -> str:
    return "".join(secrets.choice(FLIP_ID_ALPHABET) for _ in range(FLIP_ID_LENGTH))


def unique_flip_id() -> str:
    from rd_flip_be.models import Flipbook

    for _ in range(20):
        code = generate_flip_id()
        if not Flipbook.objects.filter(flip_id=code).exists():
            return code
    raise RuntimeError("Could not generate a unique flip_id")
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
