import { Truck } from "lucide-react";

interface LoadingOverlayProps {
  stage: string;
}

export function LoadingOverlay({ stage }: LoadingOverlayProps) {
  return (
    <div className="map-loading" role="status" aria-live="polite">
      <div className="map-loading__card">
        <div className="map-loading__track" aria-hidden="true">
          <span className="map-loading__line" />
          <span className="map-loading__truck">
            <Truck size={19} />
          </span>
        </div>
        <strong>{stage}</strong>
        <span>Checking forecasts at each arrival time along the corridor.</span>
      </div>
    </div>
  );
}
