import { Check, Clock3, Sparkles } from "lucide-react";

import type { RouteOption } from "../types";
import { arrivalIso, formatDuration, formatMiles, formatTime } from "../lib/format";
import { RISK_META, riskScore, riskSegments, riskSummary } from "../lib/risk";

interface RouteCardProps {
  route: RouteOption;
  departure: string;
  selected: boolean;
  recommended: boolean;
  fastest: boolean;
  onSelect: () => void;
}

export function RouteCard({
  route,
  departure,
  selected,
  recommended,
  fastest,
  onSelect,
}: RouteCardProps) {
  const segments = riskSegments(route.totals);
  const arrival = formatTime(arrivalIso(departure, route.durationMinutes));
  const noTravel = route.totals.noTravelMiles > 0;

  return (
    <button
      type="button"
      className={`route-card${selected ? " route-card--selected" : ""}`}
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={`Select ${route.label}, ${formatDuration(route.durationMinutes)}, ${formatMiles(
        route.distanceMiles,
      )}`}
    >
      <div className="route-card__top">
        <div className="route-card__title">
          <span className="route-card__name">{route.label}</span>
          <span className="route-card__badges">
            {recommended && (
              <span className="badge badge--recommended">
                <Sparkles size={12} /> Recommended
              </span>
            )}
            {fastest && (
              <span className="badge badge--fastest">
                <Clock3 size={12} /> Fastest
              </span>
            )}
          </span>
        </div>
        <span className="route-card__select" aria-hidden="true">
          {selected ? <Check size={15} /> : null}
        </span>
      </div>

      <div className="route-card__numbers">
        <span>
          <b>{formatDuration(route.durationMinutes)}</b>
          <small>drive time</small>
        </span>
        <span>
          <b>{formatMiles(route.distanceMiles)}</b>
          <small>distance</small>
        </span>
        <span>
          <b>{arrival}</b>
          <small>arrival</small>
        </span>
      </div>

      <div
        className="risk-bar"
        role="img"
        aria-label={`Risk distribution: ${segments
          .map((segment) => `${RISK_META[segment.level].label} ${segment.miles.toFixed(1)} miles`)
          .join(", ")}`}
      >
        {segments.map((segment) => (
          <span
            key={segment.level}
            className="risk-bar__segment"
            style={{
              width: `${Math.max(segment.percent, 1.5)}%`,
              background: RISK_META[segment.level].color,
            }}
            title={`${RISK_META[segment.level].label}: ${segment.miles.toFixed(1)} mi`}
          />
        ))}
      </div>

      <div className="route-card__stats">
        <span>
          <small>Severe</small>
          <b className={route.totals.severeMiles > 0 ? "text-severe" : ""}>
            {route.totals.severeMiles.toFixed(1)} mi
          </b>
        </span>
        <span>
          <small>High</small>
          <b className={route.totals.highMiles > 0 ? "text-high" : ""}>
            {route.totals.highMiles.toFixed(1)} mi
          </b>
        </span>
        <span>
          <small>Avg risk</small>
          <b>{riskScore(route.totals.averageRisk)}/100</b>
        </span>
      </div>

      <div className="route-card__footer">
        <span className={noTravel ? "route-card__summary route-card__summary--alert" : "route-card__summary"}>
          {riskSummary(route.totals)}
        </span>
        {noTravel && <span className="badge badge--no-travel">No Travel exposure</span>}
      </div>
    </button>
  );
}
