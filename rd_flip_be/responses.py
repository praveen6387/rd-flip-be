from rest_framework import status
from rest_framework.response import Response


def api_success(message: str, data=None, http_status=status.HTTP_200_OK) -> Response:
    return Response(
        {
            "status": "success",
            "message": message,
            "details": "",
            "data": data,
        },
        status=http_status,
    )


def api_fail(message: str, details: str = "", data=None, http_status=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response(
        {
            "status": "fail",
            "message": message,
            "details": details or message,
            "data": data,
        },
        status=http_status,
    )
