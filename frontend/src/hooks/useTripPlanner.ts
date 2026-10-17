import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, planTrip as planTripRequest } from "../api/client";
import type { PlanRequest, TripPlan } from "../types";

const STAGES = [
  "Locating origin and destination",
  "Building three route options",
  "Sampling weather along the corridor",
  "Scoring risk and comparing routes",
] as const;

export interface TripPlannerState {
  plan: TripPlan | null;
  isLoading: boolean;
  loadingStage: string;
  error: string | null;
  planTrip: (request: PlanRequest) => Promise<void>;
  clearError: () => void;
}

export function useTripPlanner(): TripPlannerState {
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const planTrip = useCallback(async (request: PlanRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setStageIndex(0);
    setError(null);
    const stageTimer = window.setInterval(() => {
      setStageIndex((current) => Math.min(current + 1, STAGES.length - 1));
    }, 1_900);

    try {
      const result = await planTripRequest(request, controller.signal);
      if (!controller.signal.aborted) {
        setPlan(result);
      }
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") {
        return;
      }
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Trip planning failed unexpectedly. Please try again.",
      );
    } finally {
      window.clearInterval(stageTimer);
      if (!controller.signal.aborted) {
        setIsLoading(false);
        setStageIndex(0);
      }
    }
  }, []);

  return {
    plan,
    isLoading,
    loadingStage: STAGES[stageIndex] ?? STAGES[0],
    error,
    planTrip,
    clearError: () => setError(null),
  };
}
