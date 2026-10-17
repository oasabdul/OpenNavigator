from __future__ import annotations

import logging
from datetime import UTC, datetime

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trips.application.errors import (
    InvalidTripRequest,
    LocationNotFound,
    NoRoutesFound,
    PlanNotFound,
    UpstreamUnavailable,
)
from apps.trips.application.heatmap import HeatmapUseCase
from apps.trips.application.models import HeatmapCommand, PlanTripCommand
from apps.trips.application.plan_trip import PlanTripUseCase
from apps.trips.interface.container import build_heatmap_use_case, build_plan_trip_use_case
from apps.trips.interface.presenters import serialize_heatmap_frame, serialize_plan
from apps.trips.interface.serializers import (
    HeatmapRequestSerializer,
    PlanTripRequestSerializer,
)

logger = logging.getLogger(__name__)
API_VERSION = "1.0.0"


def error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


class HealthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "OpenNavigator API",
                "version": API_VERSION,
                "time": datetime.now(UTC).isoformat(),
            }
        )


class ConfigView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        return Response(
            {
                "samplingIntervalsMiles": [10, 25, 50],
                "forecastHours": 48,
                "units": {"distance": "miles", "wind": "mph", "precipitation": "in/hr"},
                "riskLevels": [
                    {"key": "low", "label": "Low"},
                    {"key": "moderate", "label": "Moderate"},
                    {"key": "high", "label": "High"},
                    {"key": "severe", "label": "Severe"},
                    {"key": "no_travel", "label": "No Travel"},
                ],
            }
        )


class PlanTripView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PlanTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        use_case: PlanTripUseCase = build_plan_trip_use_case()

        try:
            result = use_case.execute(
                PlanTripCommand(
                    origin_query=payload["origin"],
                    destination_query=payload["destination"],
                    departure=payload["departure"],
                    load_lb=payload["load_weight_lb"],
                    interval_miles=payload["sampling_interval_miles"],
                )
            )
        except InvalidTripRequest as exc:
            return error_response("invalid_trip", str(exc), status.HTTP_400_BAD_REQUEST)
        except LocationNotFound as exc:
            return error_response("location_not_found", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY)
        except NoRoutesFound as exc:
            return error_response("route_not_found", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY)
        except UpstreamUnavailable as exc:
            logger.warning("Upstream service unavailable: %s", exc)
            return error_response("upstream_unavailable", str(exc), status.HTTP_502_BAD_GATEWAY)
        except Exception:
            logger.exception("Trip planning failed")
            return error_response(
                "internal_error",
                "An unexpected error occurred while planning this trip.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(serialize_plan(result))


class HeatmapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, plan_id):
        serializer = HeatmapRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        use_case: HeatmapUseCase = build_heatmap_use_case()

        try:
            frame = use_case.execute(
                HeatmapCommand(
                    plan_id=plan_id,
                    route_id=serializer.validated_data["route_id"],
                    hour=serializer.validated_data["hour"],
                )
            )
        except InvalidTripRequest as exc:
            return error_response("invalid_forecast_hour", str(exc), status.HTTP_400_BAD_REQUEST)
        except PlanNotFound as exc:
            return error_response("plan_not_found", str(exc), status.HTTP_410_GONE)
        except UpstreamUnavailable as exc:
            logger.warning("Heatmap forecast unavailable: %s", exc)
            return error_response("upstream_unavailable", str(exc), status.HTTP_502_BAD_GATEWAY)
        except Exception:
            logger.exception("Heatmap generation failed")
            return error_response(
                "internal_error",
                "An unexpected error occurred while building the forecast.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = Response(
            serialize_heatmap_frame(
                frame,
                plan_id=str(plan_id),
                route_id=serializer.validated_data["route_id"],
            )
        )
        response["Cache-Control"] = "public, max-age=300"
        return response

