import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { analysisNotice, getMetricRows, hasUsableEngineMetrics } from "../src/lib/cardMetrics.ts";
import type { ShareCardData } from "../src/types.ts";

const partial = card({
  lowest_eval: -4.2,
  biggest_eval_swing: 5.1,
  analysis_status: "partial",
  analysis_source: "lichess_cloud_eval",
  eval_points: 3,
});

assert.equal(analysisNotice(partial), "Partial engine analysis available");
assert.equal(hasUsableEngineMetrics(partial), true);
assert.deepEqual(getMetricRows(partial).slice(0, 2), [
  ["Lowest eval", "-4.2"],
  ["Swing", "+5.1"],
]);

const tooFew = card({
  lowest_eval: -4.2,
  biggest_eval_swing: 5.1,
  analysis_status: "partial",
  analysis_source: "lichess_cloud_eval",
  eval_points: 1,
});

assert.equal(analysisNotice(tooFew), "Not enough cloud eval data for this game");
assert.equal(hasUsableEngineMetrics(tooFew), false);
assert.deepEqual(getMetricRows(tooFew).slice(0, 2), [
  ["Result", "Win"],
  ["Moves", "42"],
]);

const unavailable = card({
  analysis_status: "unavailable",
  analysis_source: "metadata_only",
  eval_points: 0,
});

assert.equal(analysisNotice(unavailable), "No cloud eval found for this game yet");

const metadataRows = getMetricRows(unavailable);
assert.deepEqual(metadataRows.find(([label]) => label === "Format"), ["Format", "blitz"]);
assert.equal(metadataRows.some(([label]) => label === "Speed"), false);

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
assert.match(appSource, /<dt>Format<\/dt>/);
assert.doesNotMatch(appSource, /<dt>Speed<\/dt>/);

const shareCardSource = readFileSync(new URL("../src/components/cards/ShareCard.tsx", import.meta.url), "utf8");
assert.match(shareCardSource, /platformStoryCardLabel\(card\.game\.platform\)/);
assert.match(shareCardSource, /if \(platform === "chesscom"\) return "chess\.com";/);
assert.doesNotMatch(shareCardSource, /<span>lichess story card<\/span>/);

function card(metrics: ShareCardData["metrics"]): ShareCardData {
  return {
    template: "generic_square_v1",
    player: { username: "clevermike" },
    game: {
      platform: "lichess",
      result: "win",
      moves: 42,
      opponent_username: "opponent",
      opponent_rating: 1500,
      opening: "Sicilian Defense",
      speed: "blitz",
      time_control: "5+0",
    },
    story: {
      primary_story: "daily_activity",
      badge_label: "Daily Game",
      badge_emoji: "DG",
      headline: "A game added to the journal.",
      key_move_number: 24,
      template_key: "generic_square_v1",
      interesting_score: 0.2,
      confidence_score: 0.75,
      reasons: ["journal_entry"],
    },
    metrics,
    board_position_source: "final_position",
  };
}
