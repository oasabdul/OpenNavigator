import { useState } from "react";
import {
  ArrowLeftRight,
  ArrowRight,
  CalendarClock,
  MapPin,
  Truck,
  Weight,
} from "lucide-react";

import type { PlanRequest } from "../types";
import { defaultDepartureValue, toDatetimeLocalValue, toIsoDeparture } from "../lib/format";

interface PlannerFormProps {
  isLoading: boolean;
  onSubmit: (request: PlanRequest) => void;
}

const EXAMPLES = [
  { label: "NYC → Boston", origin: "New York, NY", destination: "Boston, MA" },
  { label: "Chicago → Denver", origin: "Chicago, IL", destination: "Denver, CO" },
  { label: "Dallas → Atlanta", origin: "Dallas, TX", destination: "Atlanta, GA" },
];

const LOAD_PRESETS = [10_000, 30_000, 42_000, 60_000, 80_000];

export function PlannerForm({ isLoading, onSubmit }: PlannerFormProps) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departure, setDeparture] = useState(defaultDepartureValue);
  const [loadWeight, setLoadWeight] = useState("42000");
  const [interval, setInterval] = useState<10 | 25 | 50>(25);
  const [error, setError] = useState<string | null>(null);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (origin.trim().length < 2) {
      setError("Enter an origin city or address.");
      return;
    }
    if (destination.trim().length < 2) {
      setError("Enter a destination city or address.");
      return;
    }
    const load = Number(loadWeight);
    if (!Number.isFinite(load) || load < 0 || load > 200_000) {
      setError("Load weight must be between 0 and 200,000 lb.");
      return;
    }

    let departureIso: string;
    try {
      departureIso = toIsoDeparture(departure);
    } catch {
      setError("Enter a valid departure date and time.");
      return;
    }
    if (new Date(departureIso).getTime() < Date.now() - 5 * 60_000) {
      setError("Departure cannot be in the past.");
      return;
    }

    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      departure: departureIso,
      loadWeightLb: load,
      samplingIntervalMiles: interval,
    });
  };

  const swap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const minDeparture = toDatetimeLocalValue(new Date());
  const maxDeparture = toDatetimeLocalValue(new Date(Date.now() + 14 * 86_400_000));

  return (
    <form className="planner" onSubmit={submit}>
      <div className="planner__heading">
        <div>
          <span className="eyebrow">Trip planner</span>
          <h1>Find the safest route.</h1>
        </div>
        <span className="planner__badge">
          <Truck size={14} /> Load-aware
        </span>
      </div>
      <p className="planner__intro">
        Three road routes, weather sampled at your arrival time, and a recommendation that
        weighs risk before speed.
      </p>

      <div className="route-fields">
        <label className="field field--with-icon">
          <span className="field__label">Origin</span>
          <span className="field__control">
            <MapPin size={17} className="field__icon" />
            <input
              value={origin}
              onChange={(event) => setOrigin(event.target.value)}
              placeholder="City, address, or lat, lon"
              autoComplete="off"
              spellCheck={false}
              aria-invalid={Boolean(error) && origin.trim().length < 2}
            />
          </span>
        </label>

        <button
          type="button"
          className="swap-button"
          onClick={swap}
          aria-label="Swap origin and destination"
          title="Swap origin and destination"
        >
          <ArrowLeftRight size={16} />
        </button>

        <label className="field field--with-icon">
          <span className="field__label">Destination</span>
          <span className="field__control">
            <MapPin size={17} className="field__icon field__icon--destination" />
            <input
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
              placeholder="City, address, or lat, lon"
              autoComplete="off"
              spellCheck={false}
              aria-invalid={Boolean(error) && destination.trim().length < 2}
            />
          </span>
        </label>
      </div>

      <div className="field-grid">
        <label className="field">
          <span className="field__label">
            <CalendarClock size={14} /> Departure
          </span>
          <span className="field__control field__control--plain">
            <input
              type="datetime-local"
              value={departure}
              min={minDeparture}
              max={maxDeparture}
              onChange={(event) => setDeparture(event.target.value)}
            />
          </span>
        </label>

        <label className="field">
          <span className="field__label">
            <Weight size={14} /> Load weight
          </span>
          <span className="field__control field__control--suffix">
            <input
              type="number"
              inputMode="decimal"
              min={0}
              max={200_000}
              step={500}
              value={loadWeight}
              onChange={(event) => setLoadWeight(event.target.value)}
            />
            <span className="field__suffix">lb</span>
          </span>
        </label>
      </div>

      <div className="load-presets" aria-label="Load weight presets">
        {LOAD_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            className={Number(loadWeight) === preset ? "chip chip--active" : "chip"}
            onClick={() => setLoadWeight(String(preset))}
          >
            {preset / 1000}k
          </button>
        ))}
      </div>

      <fieldset className="segmented-field">
        <legend>
          Weather sampling <span>every</span>
        </legend>
        <div className="segmented">
          {([10, 25, 50] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={interval === value ? "segmented__item segmented__item--active" : "segmented__item"}
              onClick={() => setInterval(value)}
              aria-pressed={interval === value}
            >
              {value} mi
            </button>
          ))}
        </div>
      </fieldset>

      <div className="examples">
        <span>Try</span>
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            type="button"
            className="example-chip"
            onClick={() => {
              setOrigin(example.origin);
              setDestination(example.destination);
            }}
          >
            {example.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      <button type="submit" className="button button--primary planner__submit" disabled={isLoading}>
        {isLoading ? (
          <>
            <span className="spinner spinner--small" />
            Planning route…
          </>
        ) : (
          <>
            Plan safest route
            <ArrowRight size={18} />
          </>
        )}
      </button>
    </form>
  );
}
