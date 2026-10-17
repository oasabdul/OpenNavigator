from __future__ import annotations

from apps.trips.domain.entities import RiskTotals, RouteAnalysis, RouteOption
from apps.trips.domain.recommendation import recommend_routes
from apps.trips.domain.risk import RiskLevel


def route(route_id: str, duration_minutes: float, distance_miles: float = 100) -> RouteOption:
    return RouteOption(
        id=route_id,
        label=f"Route {route_id.upper()}",
        segments=(),
        distance_miles=distance_miles,
        duration_minutes=duration_minutes,
    )


def analysis(
    route_id: str,
    *,
    duration_minutes: float,
    severe: float = 0,
    high: float = 0,
    moderate: float = 0,
    low: float = 0,
    no_travel: float = 0,
    average_risk: float = 0,
) -> RouteAnalysis:
    total = severe + high + moderate + low + no_travel
    totals = RiskTotals(
        low_miles=low,
        moderate_miles=moderate,
        high_miles=high,
        severe_miles=severe,
        no_travel_miles=no_travel,
        total_miles=total,
        average_risk=average_risk,
        max_risk=RiskLevel.NO_TRAVEL if no_travel else RiskLevel.SEVERE if severe else RiskLevel.LOW,
    )
    return RouteAnalysis(
        route=route(route_id, duration_minutes, total or 100),
        checkpoints=(),
        totals=totals,
    )


def test_fewest_severe_miles_wins_first() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=20, high=0, average_risk=1.0),
            analysis("b", duration_minutes=200, severe=10, high=40, average_risk=2.0),
        ]
    )

    assert recommended.route_id == "b"


def test_fewest_high_miles_breaks_a_severe_tie() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=10, high=20, average_risk=1.0),
            analysis("b", duration_minutes=200, severe=10, high=5, average_risk=2.0),
        ]
    )

    assert recommended.route_id == "b"


def test_lowest_average_risk_breaks_a_high_tie() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=0, high=10, average_risk=1.8),
            analysis("b", duration_minutes=200, severe=0, high=10, average_risk=1.2),
        ]
    )

    assert recommended.route_id == "b"


def test_shortest_travel_time_breaks_all_other_ties() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=300, severe=0, high=10, average_risk=1.2),
            analysis("b", duration_minutes=280, severe=0, high=10, average_risk=1.2),
        ]
    )

    assert recommended.route_id == "b"
    assert recommended.ranked_route_ids == ("b", "a")


def test_no_travel_route_is_excluded_when_a_safe_option_exists() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=2, high=0, average_risk=1.0, no_travel=20),
            analysis("b", duration_minutes=500, severe=80, high=20, average_risk=2.8),
        ]
    )

    assert recommended.route_id == "b"
    assert "no-travel" in recommended.rationale.lower()


def test_all_no_travel_routes_rank_by_exposure_then_normal_rules() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=0, high=0, average_risk=4.0, no_travel=30),
            analysis("b", duration_minutes=500, severe=0, high=0, average_risk=4.0, no_travel=10),
        ]
    )

    assert recommended.route_id == "b"


def test_rationale_mentions_the_winning_metrics() -> None:
    recommended = recommend_routes(
        [
            analysis("a", duration_minutes=100, severe=20, high=10, average_risk=2.0),
            analysis("b", duration_minutes=200, severe=0, high=0, average_risk=0.4),
        ]
    )

    assert recommended.route_id == "b"
    assert "severe miles" in recommended.rationale.lower()
    assert "high miles" in recommended.rationale.lower()
