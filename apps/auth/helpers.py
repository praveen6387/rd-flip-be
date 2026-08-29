import re

from rest_framework import serializers


def normalize_indian_phone(value: str) -> str:
    """
    Validate an Indian mobile number and return it as +91XXXXXXXXXX.
    If +91 is already present, it is kept (not duplicated).
    """
    raw = (value or "").strip()
    if not raw:
        raise serializers.ValidationError("Phone number is required.")

    digits = re.sub(r"\D", "", raw)

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) != 10 or digits[0] not in "6789":
        raise serializers.ValidationError(
            "Enter a valid 10-digit Indian mobile number."
        )

    return f"+91{digits}"
