import type { ShareCardData } from "../../types";
import { analysisNotice, getMetricRows, hasUsableEngineMetrics } from "../../lib/cardMetrics";

type MetricsGridProps = {
  card: ShareCardData;
};

export function MetricsGrid({ card }: MetricsGridProps) {
  const hasEngineMetrics = hasUsableEngineMetrics(card);
  const metrics = getMetricRows(card);
  const notice = analysisNotice(card);

  return (
    <>
      {notice ? <div className={hasEngineMetrics ? "engine-note is-ready" : "engine-note"}>{notice}</div> : null}
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
