import type { ShareCardData } from "../../types";
import { getMetricRows } from "../../lib/cardMetrics";

type MetricsGridProps = {
  card: ShareCardData;
};

export function MetricsGrid({ card }: MetricsGridProps) {
  const hasEngineMetrics =
    card.metrics.lowest_eval != null || card.metrics.biggest_eval_swing != null || card.metrics.accuracy != null;
  const metrics = getMetricRows(card);

  return (
    <>
      {!hasEngineMetrics ? <div className="engine-note">Engine analysis not available yet</div> : null}
      <div className="metrics-grid">
        {metrics.map(([label, value]) => (
          <div className="metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}
