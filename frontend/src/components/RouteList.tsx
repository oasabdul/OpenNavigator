import { useMemo } from "react";
import { CircleAlert, Sparkles } from "lucide-react";

import type { TripPlan } from "../types";
import { fastestRouteId } from "../lib/route";
import { RouteCard } from "./RouteCard";

interface RouteListProps {
  plan: TripPlan;
  selectedRouteId: string | null;
  onSelectRoute: (routeId: string) => void;
}

export function RouteList({ plan, selectedRouteId, onSelectRoute }: RouteListProps) {
  const fastestId = useMemo(() => fastestRouteId(plan.routes), [plan.routes]);
  const recommended = plan.routes.find((route) => route.id === plan.recommendation.routeId);

  return (
    <section className="results" aria-label="Route options">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Analysis complete</span>
          <h2>Route options</h2>
        </div>
        <span className="count-pill">{plan.routes.length} routes</span>
      </div>

      <div className="recommendation">
        <span className="recommendation__icon">
          <Sparkles size={17} />
        </span>
        <div>
          <strong>
            {recommended?.label ?? "Recommended route"}{" "}
            {recommended && recommended.totals.noTravelMiles > 0
              ? "is the lowest-exposure option"
              : "is the safest choice"}
          </strong>
          <p>{plan.recommendation.rationale}</p>
        </div>
      </div>

      {plan.warnings.map((warning) => (
        <div className="inline-warning" key={warning}>
          <CircleAlert size={16} />
          <span>{warning}</span>
        </div>
      ))}

      <div className="route-list">
        {plan.routes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            departure={plan.departure}
            selected={route.id === (selectedRouteId ?? plan.recommendation.routeId)}
            recommended={route.id === plan.recommendation.routeId}
            fastest={route.id === fastestId}
            onSelect={() => onSelectRoute(route.id)}
          />
        ))}
      </div>
      <p className="results__hint">Select a route to inspect its checkpoints and corridor heatmap.</p>
    </section>
  );
}
