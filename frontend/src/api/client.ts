import type { ApiErrorPayload, HeatmapFrame, PlanRequest, TripPlan } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fields?: Record<string, string[]>;

  constructor(
    message: string,
    options: { code: string; status: number; fields?: Record<string, string[]> },
  ) {
    super(message);
    this.name = "ApiError";
    this.code = options.code;
    this.status = options.status;
    this.fields = options.fields;
  }
}

async function readError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | null = null;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = null;
  }
  return new ApiError(payload?.error?.message ?? "Something went wrong. Please try again.", {
    code: payload?.error?.code ?? "request_failed",
    status: response.status,
    fields: payload?.error?.fields,
  });
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError("Cannot reach the OpenNavigator API. Check your connection.", {
      code: "network_error",
      status: 0,
    });
  }

  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as T;
}

export function planTrip(input: PlanRequest, signal?: AbortSignal): Promise<TripPlan> {
  return request<TripPlan>("/trips/plan/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      origin: input.origin,
      destination: input.destination,
      departure: input.departure,
      load_weight_lb: input.loadWeightLb,
      sampling_interval_miles: input.samplingIntervalMiles,
    }),
    signal,
  });
}

export function fetchHeatmap(
  planId: string,
  routeId: string,
  hour: number,
  signal?: AbortSignal,
): Promise<HeatmapFrame> {
  const params = new URLSearchParams({ route_id: routeId, hour: String(hour) });
  return request<HeatmapFrame>(`/trips/${planId}/heatmap/?${params.toString()}`, {
    method: "GET",
    signal,
  });
}
