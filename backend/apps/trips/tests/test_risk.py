from __future__ import annotations

import pytest

from apps.trips.domain.entities import Weather
from apps.trips.domain.risk import RiskLevel, assess_weather


def weather(
    wind_mph: float = 0.0,
    rain: float = 0.0,
    snow: float = 0.0,
    temp_f: float = 70.0,
) -> Weather:
    return Weather(
        wind_mph=wind_mph,
        rain_in_per_hour=rain,
        snow_in_per_hour=snow,
        temperature_f=temp_f,
    )


@pytest.mark.parametrize(
    ("wind_mph", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (24.999, RiskLevel.LOW),
        (25.0, RiskLevel.MODERATE),
        (34.999, RiskLevel.MODERATE),
        (35.0, RiskLevel.HIGH),
        (44.999, RiskLevel.HIGH),
        (45.0, RiskLevel.SEVERE),
        (54.999, RiskLevel.SEVERE),
        (55.0, RiskLevel.NO_TRAVEL),
    ],
)
def test_wind_thresholds(wind_mph: float, expected: RiskLevel) -> None:
    assert assess_weather(weather(wind_mph=wind_mph), load_lb=0).level is expected


@pytest.mark.parametrize(
    ("rain", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.099, RiskLevel.LOW),
        (0.10, RiskLevel.MODERATE),
        (0.249, RiskLevel.MODERATE),
        (0.25, RiskLevel.HIGH),
        (0.499, RiskLevel.HIGH),
        (0.50, RiskLevel.SEVERE),
        (1.00, RiskLevel.SEVERE),
        (1.001, RiskLevel.NO_TRAVEL),
    ],
)
def test_rain_thresholds(rain: float, expected: RiskLevel) -> None:
    assert assess_weather(weather(rain=rain), load_lb=0).level is expected


@pytest.mark.parametrize(
    ("snow", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.499, RiskLevel.LOW),
        (0.50, RiskLevel.MODERATE),
        (0.999, RiskLevel.MODERATE),
        (1.0, RiskLevel.HIGH),
        (1.999, RiskLevel.HIGH),
        (2.0, RiskLevel.SEVERE),
        (3.0, RiskLevel.SEVERE),
        (3.001, RiskLevel.NO_TRAVEL),
    ],
)
def test_snow_thresholds(snow: float, expected: RiskLevel) -> None:
    assert assess_weather(weather(snow=snow), load_lb=0).level is expected


def test_worst_condition_controls_the_checkpoint() -> None:
    result = assess_weather(weather(wind_mph=10, rain=0.3, snow=0), load_lb=0)
    assert result.level is RiskLevel.HIGH
    assert any("rain" in reason.lower() for reason in result.reasons)


def test_heavy_load_turns_high_crosswind_into_severe() -> None:
    result = assess_weather(weather(wind_mph=40), load_lb=40_001)
    assert result.level is RiskLevel.SEVERE
    assert any("40,000" in reason for reason in result.reasons)


def test_forty_thousand_pounds_is_not_over_the_limit() -> None:
    assert assess_weather(weather(wind_mph=40), load_lb=40_000).level is RiskLevel.HIGH


def test_heavy_load_with_severe_crosswind_is_no_travel() -> None:
    result = assess_weather(weather(wind_mph=45), load_lb=30_001)
    assert result.level is RiskLevel.NO_TRAVEL
    assert any("30,000" in reason for reason in result.reasons)


def test_thirty_thousand_pounds_is_not_over_the_limit() -> None:
    assert assess_weather(weather(wind_mph=45), load_lb=30_000).level is RiskLevel.SEVERE


def test_any_load_is_no_travel_at_or_above_55_mph() -> None:
    result = assess_weather(weather(wind_mph=55), load_lb=0)
    assert result.level is RiskLevel.NO_TRAVEL
    assert any("55" in reason for reason in result.reasons)


def test_no_travel_rain_dominates_even_with_a_light_load() -> None:
    assert assess_weather(weather(rain=1.2), load_lb=1_000).level is RiskLevel.NO_TRAVEL
