from __future__ import annotations

from collections.abc import Sequence

from apps.trips.domain.entities import Recommendation, RouteAnalysis


def _rank_key(analysis: RouteAnalysis) -> tuple[float, float, float, float, float, str]:
    totals = analysis.totals
    return (
        totals.severe_miles,
        totals.high_miles,
        totals.average_risk,
        analysis.route.duration_minutes,
        analysis.route.distance_miles,
        analysis.route.id,
    )


def recommend_routes(analyses: Sequence[RouteAnalysis]) -> Recommendation:
    if not analyses:
        raise ValueError("At least one analysed route is required")

    safe = [analysis for analysis in analyses if analysis.totals.no_travel_miles == 0]
    unsafe = [analysis for analysis in analyses if analysis.totals.no_travel_miles > 0]
    ranked = sorted(safe, key=_rank_key) + sorted(
        unsafe,
        key=lambda analysis: (
            analysis.totals.no_travel_miles,
            *_rank_key(analysis),
        ),
    )
    best = ranked[0]
    totals = best.totals

    if safe:
        rationale = (
            f"Fewest severe miles ({totals.severe_miles:.1f}), fewest high miles "
            f"({totals.high_miles:.1f}), lowest average risk ({totals.average_risk:.2f}), "
            f"with travel time as the final tie-breaker ({best.route.duration_minutes:.0f} min) "
            "among the options without No-travel conditions."
        )
        if unsafe:
            rationale += " No-travel routes were avoided."
    else:
        rationale = (
            "Every route includes No-travel conditions. This option has the least "
            f"exposure ({totals.no_travel_miles:.1f} no-travel miles), fewest severe miles "
            f"({totals.severe_miles:.1f}), fewest high miles ({totals.high_miles:.1f}), and "
            f"the lowest average risk ({totals.average_risk:.2f})."
        )

    return Recommendation(
        route_id=best.route.id,
        rationale=rationale,
        ranked_route_ids=tuple(analysis.route.id for analysis in ranked),
    )
