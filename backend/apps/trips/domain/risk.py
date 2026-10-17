from __future__ import annotations

from apps.trips.domain.entities import RiskAssessment, RiskLevel, Weather


def classify_wind(wind_mph: float) -> RiskLevel:
    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 45:
        return RiskLevel.SEVERE
    if wind_mph >= 35:
        return RiskLevel.HIGH
    if wind_mph >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(rain_in_per_hour: float) -> RiskLevel:
    if rain_in_per_hour > 1.00:
        return RiskLevel.NO_TRAVEL
    if rain_in_per_hour >= 0.50:
        return RiskLevel.SEVERE
    if rain_in_per_hour >= 0.25:
        return RiskLevel.HIGH
    if rain_in_per_hour >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(snow_in_per_hour: float) -> RiskLevel:
    if snow_in_per_hour > 3.0:
        return RiskLevel.NO_TRAVEL
    if snow_in_per_hour >= 2.0:
        return RiskLevel.SEVERE
    if snow_in_per_hour >= 1.0:
        return RiskLevel.HIGH
    if snow_in_per_hour >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def assess_weather(weather: Weather, load_lb: float) -> RiskAssessment:
    wind_level = classify_wind(weather.wind_mph)
    rain_level = classify_rain(weather.rain_in_per_hour)
    snow_level = classify_snow(weather.snow_in_per_hour)
    base_level = max(wind_level, rain_level, snow_level)

    reasons: list[str] = []
    if base_level is RiskLevel.LOW:
        reasons.append("Wind, rain, and snow are within low-risk thresholds")
    else:
        if wind_level is base_level:
            reasons.append(f"Wind {weather.wind_mph:.1f} mph is {wind_level.label.lower()} risk")
        if rain_level is base_level:
            reasons.append(
                f"Rain {weather.rain_in_per_hour:.2f} in/hr is {rain_level.label.lower()} risk"
            )
        if snow_level is base_level:
            reasons.append(
                f"Snow {weather.snow_in_per_hour:.2f} in/hr is {snow_level.label.lower()} risk"
            )

    level = base_level
    if weather.wind_mph >= 55:
        level = RiskLevel.NO_TRAVEL
        reasons.append("Wind at or above 55 mph is No Travel for any load")
    elif weather.wind_mph >= 45 and load_lb > 30_000:
        level = RiskLevel.NO_TRAVEL
        reasons.append("45-54 mph wind with more than 30,000 lb is No Travel")
    elif weather.wind_mph >= 35 and load_lb > 40_000:
        level = max(level, RiskLevel.SEVERE)
        reasons.append("35-44 mph wind with more than 40,000 lb is Severe")

    return RiskAssessment(level=level, reasons=tuple(dict.fromkeys(reasons)))
