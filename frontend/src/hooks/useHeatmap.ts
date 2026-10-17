import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, fetchHeatmap } from "../api/client";
import type { HeatmapFrame } from "../types";

const MAX_HOUR = 48;

export interface HeatmapState {
  hour: number;
  frame: HeatmapFrame | null;
  isLoading: boolean;
  error: string | null;
  setHour: (hour: number) => void;
  retry: () => void;
}

export function useHeatmap(
  planId: string | null,
  routeId: string | null,
  enabled: boolean,
): HeatmapState {
  const [hour, setHourState] = useState(0);
  const [frame, setFrame] = useState<HeatmapFrame | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const cacheRef = useRef(new Map<string, HeatmapFrame>());

  useEffect(() => {
    cacheRef.current.clear();
    setHourState(0);
    setFrame(null);
    setError(null);
  }, [planId]);

  useEffect(() => {
    setFrame(null);
    setError(null);
  }, [routeId]);

  const setHour = useCallback((value: number) => {
    setHourState(Math.max(0, Math.min(MAX_HOUR, Math.round(value))));
  }, []);

  useEffect(() => {
    if (!enabled || !planId || !routeId) {
      setIsLoading(false);
      return;
    }

    const key = `${planId}:${routeId}:${hour}`;
    const cached = cacheRef.current.get(key);
    if (cached) {
      setFrame(cached);
      setError(null);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    const timer = window.setTimeout(async () => {
      try {
        const result = await fetchHeatmap(planId, routeId, hour, controller.signal);
        if (controller.signal.aborted) return;
        cacheRef.current.set(key, result);
        setFrame(result);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        if (controller.signal.aborted) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "The corridor forecast could not be loaded.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }, 90);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [enabled, hour, nonce, planId, routeId]);

  const retry = useCallback(() => {
    if (planId && routeId) {
      cacheRef.current.delete(`${planId}:${routeId}:${hour}`);
    }
    setNonce((value) => value + 1);
  }, [hour, planId, routeId]);

  return {
    hour,
    frame,
    isLoading,
    error,
    setHour,
    retry,
  };
}
