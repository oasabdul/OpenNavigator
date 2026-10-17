import { Compass } from "lucide-react";

export function EmptyMapState() {
  return (
    <div className="map-empty" aria-hidden="true">
      <div className="map-empty__card">
        <span className="map-empty__icon">
          <Compass size={23} />
        </span>
        <span className="eyebrow">Ready when you are</span>
        <h2>Weather changes the best route.</h2>
        <p>
          Enter a trip to compare three road routes, inspect every checkpoint, and watch the
          corridor forecast move through the next 48 hours.
        </p>
      </div>
    </div>
  );
}
