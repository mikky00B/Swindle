import assert from "node:assert/strict";
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
