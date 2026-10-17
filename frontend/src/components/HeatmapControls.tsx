import { useEffect, useState, type CSSProperties } from "react";
import { CircleAlert, Layers, Pause, Play, RefreshCw } from "lucide-react";

import type { HeatmapFrame } from "../types";
import { formatDateTime, formatHourOffset } from "../lib/format";

interface HeatmapControlsProps {
  enabled: boolean;
  hour: number;
  frame: HeatmapFrame | null;
  isLoading: boolean;
  error: string | null;
  onToggle: () => void;
  onHourChange: (hour: number) => void;
  onRetry: () => void;
}

const TICKS = [0, 12, 24, 36, 48];

export function HeatmapControls({
  enabled,
  hour,
  frame,
  isLoading,
  error,
  onToggle,
  onHourChange,
  onRetry,
}: HeatmapControlsProps) {
  const [playing, setPlaying] = useState(false);
  const currentFrame = frame && frame.hour === hour ? frame : null;

  useEffect(() => {
    if (!playing || !enabled) return;
    const timer = window.setInterval(() => {
      onHourChange((hour + 1) % 49);
    }, 950);
    return () => window.clearInterval(timer);
  }, [enabled, hour, onHourChange, playing]);

  useEffect(() => {
    if (!enabled || error) setPlaying(false);
  }, [enabled, error]);

  return (
    <div className={`heatmap-panel${enabled ? " heatmap-panel--open" : ""}`}>
      <div className="heatmap-panel__header">
        <div className="heatmap-panel__title">
          <span className="heatmap-panel__icon">
            <Layers size={16} />
          </span>
          <div>
            <strong>Corridor heatmap</strong>
            <small>48-hour forecast along the selected route</small>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="Toggle corridor heatmap"
          className={`switch${enabled ? " switch--on" : ""}`}
          onClick={onToggle}
        >
          <span className="switch__thumb" />
        </button>
      </div>

      {enabled && (
        <div className="heatmap-panel__body">
          <div className="heatmap-panel__controls">
            <button
              type="button"
              className="icon-button icon-button--filled"
              onClick={() => setPlaying((value) => !value)}
              disabled={isLoading || Boolean(error)}
              aria-label={playing ? "Pause forecast animation" : "Play forecast animation"}
              title={playing ? "Pause" : "Play 48-hour forecast"}
            >
              {playing ? <Pause size={15} /> : <Play size={15} />}
            </button>
            <div className="heatmap-panel__readout">
              <span>{formatHourOffset(hour)} from departure</span>
              <strong>{currentFrame ? formatDateTime(currentFrame.forecastTime) : "Forecast loading"}</strong>
            </div>
            {isLoading && <span className="spinner spinner--tiny" aria-label="Loading forecast" />}
          </div>

          <div className="range-wrap">
            <input
              className="range"
              type="range"
              min={0}
              max={48}
              step={1}
              value={hour}
              onChange={(event) => onHourChange(Number(event.target.value))}
              aria-label="Forecast hour from departure"
              aria-valuetext={`${hour} hours from departure`}
              style={{ "--range-progress": `${(hour / 48) * 100}%` } as CSSProperties}
            />
            <div className="range-ticks" aria-hidden="true">
              {TICKS.map((tick) => (
                <span key={tick}>{tick === 0 ? "Departure" : `+${tick}h`}</span>
              ))}
            </div>
          </div>

          {error ? (
            <div className="heatmap-panel__error" role="alert">
              <CircleAlert size={15} />
              <span>{error}</span>
              <button type="button" className="text-button" onClick={onRetry}>
                <RefreshCw size={13} /> Retry
              </button>
            </div>
          ) : (
            <p className="heatmap-panel__note">
              {isLoading
                ? "Building the corridor forecast. The first frame can take a few seconds."
                : "Colors show the risk at each corridor point for the selected hour."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
