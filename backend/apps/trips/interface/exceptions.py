from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred. Please try again.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        response.data = {
            "error": {
                "code": "validation_error",
                "message": "Some of the trip details are invalid.",
                "fields": response.data,
            }
        }
    elif isinstance(response.data, dict) and "detail" in response.data:
        response.data = {
            "error": {
                "code": "request_error",
                "message": str(response.data["detail"]),
            }
        }
    return response
