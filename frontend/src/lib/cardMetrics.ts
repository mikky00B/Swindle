import type { ShareCardData } from "../types";

export function getMetricRows(card: ShareCardData): string[][] {
  const evalPoints = getEvalPointCount(card);
  const canShowEngineMetrics = hasUsableEngineMetrics(card);
  const engineMetrics = [
    card.metrics.lowest_eval != null ? ["Lowest eval", formatEval(card.metrics.lowest_eval)] : null,
    card.metrics.biggest_eval_swing != null ? ["Swing", formatEval(card.metrics.biggest_eval_swing)] : null,
    card.metrics.accuracy != null ? ["Accuracy", `${card.metrics.accuracy.toFixed(1)}%`] : null,
    card.story.key_move_number != null ? ["Turning point", `Move ${card.story.key_move_number}`] : null,
  ].filter(Boolean) as string[][];
  const metadataMetrics = [
    ["Result", title(card.game.result)],
    ["Moves", String(card.game.moves)],
    ["Opponent", card.game.opponent_username ?? "Unknown"],
    ["Opp. rating", card.game.opponent_rating != null ? String(card.game.opponent_rating) : "Unknown"],
    ["Opening", card.game.opening ?? "Unknown"],
    ["Speed", card.game.speed ?? "Unknown"],
    ["Time control", card.game.time_control ?? "Unknown"],
    ...(card.game.rating_change != null ? [["Rating diff", formatSigned(card.game.rating_change)]] : []),
  ];

  if (canShowEngineMetrics && engineMetrics.length > 0) {
    return [...engineMetrics, ...metadataMetrics].slice(0, 6);
  }
  void evalPoints;
  return metadataMetrics.slice(0, 6);
}

export function hasUsableEngineMetrics(card: ShareCardData): boolean {
  return isCloudAnalysisAvailable(card) && getEvalPointCount(card) >= 2;
}

export function getEvalPointCount(card: ShareCardData): number {
  return card.metrics.eval_points ?? 0;
}

export function analysisNotice(card: ShareCardData): string | null {
  const status = card.metrics.analysis_status ?? "none";
  if (status === "partial" && getEvalPointCount(card) >= 2) {
    return "Partial engine analysis available";
  }
  if (status === "complete" && getEvalPointCount(card) >= 2) {
    return "Engine analysis available";
  }
  if (status === "unavailable") {
    return "No cloud eval found for this game yet";
  }
  if (isCloudAnalysisAvailable(card) && getEvalPointCount(card) < 2) {
    return "Not enough cloud eval data for this game";
  }
  return "Engine analysis not available yet";
}

function isCloudAnalysisAvailable(card: ShareCardData): boolean {
  return card.metrics.analysis_status === "partial" || card.metrics.analysis_status === "complete";
}

function formatEval(value?: number | null): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return value > 0 ? `+${value.toFixed(1)}` : value.toFixed(1);
}

function title(value: string): string {
  return value.slice(0, 1).toUpperCase() + value.slice(1);
}

function formatSigned(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}
