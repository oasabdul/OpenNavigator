import { useEffect, useRef } from "react";
import { ShieldCheck, X } from "lucide-react";

import { RISK_META, RISK_ORDER } from "../lib/risk";

interface RulesDialogProps {
  open: boolean;
  onClose: () => void;
}

const WIND_ROWS = [
  ["< 25 mph", "25–34", "35–44", "45–54", "≥ 55"],
  ["< 0.10 in/hr", "0.10–0.25", "0.25–0.50", "0.50–1.00", "> 1.00"],
  ["< 0.5 in/hr", "0.5–1.0", "1.0–2.0", "2.0–3.0", "> 3.0"],
];

export function RulesDialog({ open, onClose }: RulesDialogProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    closeRef.current?.focus();
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rules-title"
      >
        <div className="dialog__header">
          <div className="dialog__title">
            <span className="dialog__icon">
              <ShieldCheck size={20} />
            </span>
            <div>
              <h2 id="rules-title">How OpenNavigator decides</h2>
              <p>The safety model used for every checkpoint and recommendation.</p>
            </div>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close risk model"
          >
            <X size={19} />
          </button>
        </div>

        <div className="dialog__body">
          <section>
            <h3>Weather thresholds</h3>
            <p>
              Each checkpoint is classified by the worst of wind, rain, and snow. Boundary
              values roll up to the higher risk category.
            </p>
            <div className="threshold-table" role="table" aria-label="Weather risk thresholds">
              <div className="threshold-table__head" role="row">
                <span role="columnheader">Condition</span>
                {RISK_ORDER.map((level) => (
                  <span key={level} role="columnheader">
                    <i style={{ background: RISK_META[level].color }} />
                    {RISK_META[level].label}
                  </span>
                ))}
              </div>
              {["Wind", "Rain", "Snow"].map((label, rowIndex) => (
                <div className="threshold-table__row" role="row" key={label}>
                  <span role="cell">{label}</span>
                  {WIND_ROWS[rowIndex]?.map((value, index) => (
                    <span role="cell" key={`${label}-${index}`}>
                      {value}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3>Load rules</h3>
            <ul className="rule-list">
              <li>
                <span className="rule-list__badge rule-list__badge--no-travel">No Travel</span>
                Wind at or above 55 mph, for any load.
              </li>
              <li>
                <span className="rule-list__badge rule-list__badge--no-travel">No Travel</span>
                45–54 mph wind with more than 30,000 lb.
              </li>
              <li>
                <span className="rule-list__badge rule-list__badge--severe">Severe</span>
                35–44 mph wind with more than 40,000 lb.
              </li>
            </ul>
          </section>

          <section>
            <h3>Recommendation order</h3>
            <ol className="ordered-list">
              <li>Routes with No Travel conditions are deprioritized when a safer option exists.</li>
              <li>Fewest severe miles.</li>
              <li>Fewest high miles.</li>
              <li>Lowest mileage-weighted average risk.</li>
              <li>Shortest travel time.</li>
            </ol>
            <p className="dialog__note">
              Weather is sampled every 10, 25, or 50 miles using the truck&apos;s estimated
              arrival time at each checkpoint. Forecasts come from Open-Meteo; routing and
              geocoding use OSRM and OpenStreetMap Nominatim.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
