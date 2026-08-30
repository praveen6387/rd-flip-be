from rest_framework.views import exception_handler

from rd_flip_be.responses import api_fail


def _first_error_message(detail) -> str:
    """Pick the first human-readable error string from DRF error payloads."""
    if detail is None:
        return "Something went wrong."
    if isinstance(detail, list):
        if not detail:
            return "Something went wrong."
        return _first_error_message(detail[0])
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_error_message(value)
        return "Something went wrong."
    return str(detail)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return api_fail(
            message="Something went wrong.",
            details=str(exc),
            http_status=500,
        )

    message = _first_error_message(response.data)
    fail = api_fail(message=message, details=message, http_status=response.status_code)
    return fail
