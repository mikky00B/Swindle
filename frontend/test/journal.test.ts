import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { filterJournalGames } from "../src/lib/journal.ts";
import type { JournalGame } from "../src/types.ts";

const games: JournalGame[] = [
  game("one", "win", "Sicilian Defense", "higherRated"),
  game("two", "loss", "French Defense", "Bai_Daniil"),
  game("three", "draw", "Queen's Gambit", "equalOpponent"),
];

assert.deepEqual(
  filterJournalGames(games, "wins", "", new Set()).map((item) => item.id),
  ["one"],
);

assert.deepEqual(
  filterJournalGames(games, "losses", "", new Set()).map((item) => item.id),
  ["two"],
);

assert.deepEqual(
  filterJournalGames(games, "suggested", "", new Set(["three"])).map((item) => item.id),
  ["three"],
);

assert.deepEqual(
  filterJournalGames(games, "all", "french", new Set()).map((item) => item.id),
  ["two"],
);

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const cssSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

assert.match(appSource, /className="journal-layout"/);
assert.match(appSource, /className="control-panel journal-left"/);
assert.match(appSource, /className="preview-panel journal-right"/);
assert.match(appSource, /className="mobile-journal-preview"/);
assert.match(appSource, /<details className="detail-panel">/);
assert.match(appSource, /Analyze selected game/);
assert.match(appSource, /Export PNG/);
assert.match(appSource, /scrollIntoView\(\{ behavior: "smooth", block: "start" \}\)/);
assert.match(appSource, /window\.matchMedia\("\(max-width: 768px\)"\)/);
assert.match(cssSource, /\.journal-left\s*\{[^}]*overflow-y: auto;/s);
assert.match(cssSource, /\.journal-right\s*\{[^}]*position: sticky;/s);
assert.match(cssSource, /@media \(max-width: 900px\)[\s\S]*\.journal-right\s*\{[^}]*position: static;/);
assert.match(cssSource, /@media \(max-width: 768px\)/);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.journal-right\s*\{[^}]*display: none;/);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.mobile-journal-preview\s*\{[^}]*display: grid;/);
assert.match(cssSource, /\.mobile-action-grid\s*\{[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);/s);
assert.match(cssSource, /\.responsive-card-stage\s*\{[^}]*width: var\(--card-width\);[^}]*height: calc\(var\(--card-height\) \* var\(--card-scale\)\);/s);
assert.match(appSource, /<ResponsiveShareCard card=\{selectedCard\} theme=\{selectedTheme\} size=\{selectedSize\} \/>/);

const mobilePreviewIndex = appSource.indexOf("MobileJournalPreview");
const suggestedIndex = appSource.indexOf("Suggested Stories");
const journalIndex = appSource.indexOf("Full Journal");
assert.ok(mobilePreviewIndex > -1);
assert.ok(mobilePreviewIndex < suggestedIndex);
assert.ok(mobilePreviewIndex < journalIndex);

function game(id: string, result: string, opening: string, opponent: string): JournalGame {
  return {
    id,
    external_game_id: id,
    platform: "lichess",
    opponent_username: opponent,
    result,
    opening_name: opening,
    moves_count: 32,
    imported_at: "2026-06-15T00:00:00Z",
    processing_status: "processed",
    story: {
      primary_story: "daily_activity",
      badge_label: "Daily Game",
      badge_emoji: "DG",
      headline: "A game added to the journal.",
      template_key: "generic_square_v1",
      interesting_score: 0.15,
      confidence_score: 0.75,
      reasons: ["journal_entry"],
    },
  };
}
