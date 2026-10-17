import { ChevronDown } from "lucide-react";

import type { RouteOption } from "../types";
import { formatPrecip, formatTime, formatWind } from "../lib/format";
import { RISK_META } from "../lib/risk";

interface CheckpointListProps {
  route: RouteOption;
  samplingIntervalMiles: number;
}

export function CheckpointList({ route, samplingIntervalMiles }: CheckpointListProps) {
  return (
    <details className="checkpoint-panel" open>
      <summary className="checkpoint-panel__summary">
        <span>
          <span className="eyebrow">Selected route</span>
          <strong>Checkpoint log</strong>
        </span>
        <span className="checkpoint-panel__meta">
          {route.checkpoints.length} samples · every {samplingIntervalMiles} mi
          <ChevronDown size={16} className="checkpoint-panel__chevron" />
        </span>
      </summary>

      <div className="checkpoint-table-wrap">
        <table className="checkpoint-table">
          <thead>
            <tr>
              <th scope="col">Mile</th>
              <th scope="col">ETA</th>
              <th scope="col">Wind</th>
              <th scope="col">Rain</th>
              <th scope="col">Snow</th>
              <th scope="col">Risk</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((checkpoint) => {
              const meta = RISK_META[checkpoint.risk.level];
              return (
                <tr
                  key={`${checkpoint.mile}-${checkpoint.eta}`}
                  className={checkpoint.risk.level === "no_travel" ? "checkpoint-row--alert" : undefined}
                  title={checkpoint.risk.reasons.join(" · ")}
                >
                  <td>{Math.round(checkpoint.mile)}</td>
                  <td>{formatTime(checkpoint.eta)}</td>
                  <td>{formatWind(checkpoint.weather.windMph)}</td>
                  <td>{formatPrecip(checkpoint.weather.rainInPerHour)}</td>
                  <td>{formatPrecip(checkpoint.weather.snowInPerHour)}</td>
                  <td>
                    <span
                      className="risk-badge"
                      style={{
                        color: meta.text,
                        background: meta.soft,
                        borderColor: `${meta.color}40`,
                      }}
                    >
                      <i style={{ background: meta.color }} />
                      {meta.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
