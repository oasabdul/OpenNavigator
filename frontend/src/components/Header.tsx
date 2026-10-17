import { Compass, Info } from "lucide-react";

interface HeaderProps {
  onOpenRules: () => void;
}

export function Header({ onOpenRules }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand__mark" aria-hidden="true">
          <Compass size={25} strokeWidth={1.8} />
          <span className="brand__route" />
        </div>
        <div className="brand__copy">
          <div className="brand__name">OpenNavigator</div>
          <div className="brand__tagline">Weather-aware truck routing</div>
        </div>
      </div>
      <div className="header-actions">
        <span className="live-pill">
          <span className="live-pill__dot" />
          Live forecasts
        </span>
        <button type="button" className="button button--ghost" onClick={onOpenRules}>
          <Info size={16} />
          <span>Risk model</span>
        </button>
      </div>
    </header>
  );
}
