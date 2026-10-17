import { RISK_META, RISK_ORDER } from "../lib/risk";

export function RiskLegend() {
  return (
    <div className="risk-legend" aria-label="Risk legend">
      <span className="risk-legend__title">Risk</span>
      {RISK_ORDER.map((level) => (
        <span className="risk-legend__item" key={level}>
          <i style={{ background: RISK_META[level].color }} />
          {RISK_META[level].label}
        </span>
      ))}
    </div>
  );
}
