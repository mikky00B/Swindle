import type { ShareCardData } from "../types";

export function getMetricRows(card: ShareCardData): string[][] {
  const engineMetrics = [
    card.metrics.lowest_eval != null ? ["Lowest eval", formatEval(card.metrics.lowest_eval)] : null,
    card.metrics.biggest_eval_swing != null ? ["Swing", formatEval(card.metrics.biggest_eval_swing)] : null,
    card.metrics.accuracy != null ? ["Accuracy", `${card.metrics.accuracy.toFixed(1)}%`] : null,
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

  return [...engineMetrics, ...metadataMetrics].slice(0, 6);
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
