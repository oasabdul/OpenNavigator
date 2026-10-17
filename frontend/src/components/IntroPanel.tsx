import { CloudSun, Route, ShieldCheck } from "lucide-react";

export function IntroPanel() {
  return (
    <section className="intro-panel" aria-label="What OpenNavigator does">
      <div className="intro-panel__stats">
        <div>
          <span className="intro-panel__icon">
            <Route size={17} />
          </span>
          <b>3</b>
          <small>route options</small>
        </div>
        <div>
          <span className="intro-panel__icon">
            <CloudSun size={17} />
          </span>
          <b>48h</b>
          <small>corridor forecast</small>
        </div>
        <div>
          <span className="intro-panel__icon">
            <ShieldCheck size={17} />
          </span>
          <b>4</b>
          <small>risk tiers</small>
        </div>
      </div>
      <p>
        We sample wind, rain, and snow at your estimated arrival time, apply load-specific
        limits, then rank routes by safety before speed.
      </p>
    </section>
  );
}
