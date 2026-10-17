import { useEffect, useRef, useState } from "react";
import { CircleAlert, X } from "lucide-react";

import { CheckpointList } from "./components/CheckpointList";
import { EmptyMapState } from "./components/EmptyMapState";
import { Header } from "./components/Header";
import { HeatmapControls } from "./components/HeatmapControls";
import { IntroPanel } from "./components/IntroPanel";
import { LoadingOverlay } from "./components/LoadingOverlay";
import { PlannerForm } from "./components/PlannerForm";
import { RiskLegend } from "./components/RiskLegend";
import { RouteList } from "./components/RouteList";
import { RulesDialog } from "./components/RulesDialog";
import { TripMap } from "./features/map/TripMap";
import { useHeatmap } from "./hooks/useHeatmap";
import { useTripPlanner } from "./hooks/useTripPlanner";

export default function App() {
  const planner = useTripPlanner();
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [heatmapEnabled, setHeatmapEnabled] = useState(true);
  const [rulesOpen, setRulesOpen] = useState(false);
  const mapStageRef = useRef<HTMLElement>(null);

  const plan = planner.plan;
  const selectedRoute =
    plan?.routes.find((route) => route.id === selectedRouteId) ??
    plan?.routes.find((route) => route.id === plan.recommendation.routeId) ??
    plan?.routes[0] ??
    null;
  const heatmap = useHeatmap(
    plan?.planId ?? null,
    selectedRoute?.id ?? null,
    heatmapEnabled,
  );
  const activeFrame =
    heatmap.frame && heatmap.frame.routeId === selectedRoute?.id ? heatmap.frame : null;

  useEffect(() => {
    if (plan) {
      setSelectedRouteId(plan.recommendation.routeId);
    }
  }, [plan]);

  useEffect(() => {
    if (!plan) return;
    const isMobile = window.matchMedia("(max-width: 860px)").matches;
    if (!isMobile) return;
    const timer = window.setTimeout(() => {
      mapStageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 160);
    return () => window.clearTimeout(timer);
  }, [plan]);

  return (
    <div className="app">
      <Header onOpenRules={() => setRulesOpen(true)} />

      <main className="workspace">
        <aside className="sidebar">
          <div className="sidebar__scroll">
            <div className="sidebar__planner">
              <PlannerForm isLoading={planner.isLoading} onSubmit={planner.planTrip} />

              {planner.error && (
                <div className="error-banner" role="alert">
                  <CircleAlert size={17} />
                  <span>{planner.error}</span>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={planner.clearError}
                    aria-label="Dismiss error"
                  >
                    <X size={15} />
                  </button>
                </div>
              )}

              {!plan && <IntroPanel />}
            </div>

            {plan && (
              <div className="sidebar__results">
                <RouteList
                  plan={plan}
                  selectedRouteId={selectedRoute?.id ?? null}
                  onSelectRoute={setSelectedRouteId}
                />
                {selectedRoute && (
                  <CheckpointList
                    route={selectedRoute}
                    samplingIntervalMiles={plan.samplingIntervalMiles}
                  />
                )}
              </div>
            )}
          </div>
        </aside>

        <section className="map-stage" ref={mapStageRef}>
          <TripMap
            plan={plan}
            selectedRouteId={selectedRoute?.id ?? null}
            onSelectRoute={setSelectedRouteId}
            heatmapFrame={activeFrame}
            heatmapVisible={heatmapEnabled}
          />

          {plan && <RiskLegend />}

          {plan && (
            <HeatmapControls
              enabled={heatmapEnabled}
              hour={heatmap.hour}
              frame={activeFrame}
              isLoading={heatmap.isLoading}
              error={heatmap.error}
              onToggle={() => setHeatmapEnabled((value) => !value)}
              onHourChange={heatmap.setHour}
              onRetry={heatmap.retry}
            />
          )}

          {planner.isLoading && <LoadingOverlay stage={planner.loadingStage} />}
          {!plan && !planner.isLoading && <EmptyMapState />}
        </section>
      </main>

      <RulesDialog open={rulesOpen} onClose={() => setRulesOpen(false)} />
    </div>
  );
}
