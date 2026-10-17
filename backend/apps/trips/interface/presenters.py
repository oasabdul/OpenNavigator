from __future__ import annotations

import math
from collections.abc import Iterable

from apps.trips.application.models import HeatmapFrame, TripPlanResult
from apps.trips.domain.entities import GeoPoint, RiskLevel, Weather

RISK_KEYS = {
    RiskLevel.LOW: "low",
    RiskLevel.MODERATE: "moderate",
    RiskLevel.HIGH: "high",
    RiskLevel.SEVERE: "severe",
    RiskLevel.NO_TRAVEL: "no_travel",
}


def risk_payload(level: RiskLevel) -> dict:
    return {"level": RISK_KEYS[level], "label": level.label}


def weather_payload(weather: Weather) -> dict:
    return {
        "windMph": round(weather.wind_mph, 1),
        "rainInPerHour": round(weather.rain_in_per_hour, 3),
        "snowInPerHour": round(weather.snow_in_per_hour, 2),
        "temperatureF": (
            round(weather.temperature_f, 1) if weather.temperature_f is not None else None
        ),
    }


def point_payload(point: GeoPoint) -> dict:
    return {"lat": round(point.lat, 5), "lon": round(point.lon, 5)}


def thin_geometry(points: Iterable[GeoPoint], limit: int = 800) -> tuple[GeoPoint, ...]:
    geometry = tuple(points)
    if len(geometry) <= limit:
        return geometry
    step = math.ceil(len(geometry) / limit)
    sampled = list(geometry[::step])
    if sampled[-1] != geometry[-1]:
        sampled.append(geometry[-1])
    return tuple(sampled)


def serialize_plan(result: TripPlanResult) -> dict:
    totals_by_id = {analysis.route.id: analysis.totals for analysis in result.analyses}
    return {
        "planId": str(result.plan_id),
        "origin": {
            "label": result.origin.label,
            **point_payload(result.origin.point),
        },
        "destination": {
            "label": result.destination.label,
            **point_payload(result.destination.point),
        },
        "departure": result.departure.isoformat(),
        "loadWeightLb": result.load_lb,
        "samplingIntervalMiles": result.interval_miles,
        "generatedAt": result.generated_at.isoformat(),
        "warnings": list(result.warnings),
        "routes": [
            {
                "id": analysis.route.id,
                "label": analysis.route.label,
                "distanceMiles": round(analysis.route.distance_miles, 1),
                "durationMinutes": round(analysis.route.duration_minutes, 1),
                "geometry": [
                    [round(point.lat, 5), round(point.lon, 5)]
                    for point in thin_geometry(analysis.route.geometry)
                ],
                "checkpoints": [
                    {
                        "mile": round(checkpoint.mile, 2),
                        "coveredMiles": round(checkpoint.covered_miles, 2),
                        **point_payload(checkpoint.point),
                        "eta": checkpoint.eta.isoformat(),
                        "weather": weather_payload(checkpoint.weather),
                        "risk": {
                            **risk_payload(checkpoint.risk.level),
                            "reasons": list(checkpoint.risk.reasons),
                        },
                    }
                    for checkpoint in analysis.checkpoints
                ],
                "totals": {
                    "lowMiles": round(analysis.totals.low_miles, 1),
                    "moderateMiles": round(analysis.totals.moderate_miles, 1),
                    "highMiles": round(analysis.totals.high_miles, 1),
                    "severeMiles": round(analysis.totals.severe_miles, 1),
                    "noTravelMiles": round(analysis.totals.no_travel_miles, 1),
                    "totalMiles": round(analysis.totals.total_miles, 1),
                    "averageRisk": round(analysis.totals.average_risk, 2),
                    "maxRisk": RISK_KEYS[analysis.totals.max_risk],
                    "maxRiskLabel": analysis.totals.max_risk.label,
                },
            }
            for analysis in result.analyses
        ],
        "recommendation": {
            "routeId": result.recommendation.route_id,
            "rationale": result.recommendation.rationale,
            "rankedRouteIds": list(result.recommendation.ranked_route_ids),
            "recommendedTotals": {
                "severeMiles": round(totals_by_id[result.recommendation.route_id].severe_miles, 1),
                "highMiles": round(totals_by_id[result.recommendation.route_id].high_miles, 1),
            },
        },
    }


def serialize_heatmap_frame(frame: HeatmapFrame, plan_id: str, route_id: str) -> dict:
    return {
        "planId": plan_id,
        "routeId": route_id,
        "hour": frame.hour,
        "forecastTime": frame.forecast_time.isoformat(),
        "points": [
            {
                **point_payload(item.point),
                "weather": weather_payload(item.weather),
                "risk": {
                    **risk_payload(item.risk.level),
                    "reasons": list(item.risk.reasons),
                },
            }
            for item in frame.points
        ],
    }
