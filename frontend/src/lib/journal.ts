import type { JournalGame } from "../types";

export type JournalFilter = "all" | "wins" | "losses" | "draws" | "suggested" | "processed" | "failed";

export function filterJournalGames(
  games: JournalGame[],
  filter: JournalFilter,
  search: string,
  suggestedGameIds: Set<string> = new Set(),
): JournalGame[] {
  const query = search.trim().toLowerCase();
  return games.filter((game) => {
    if (filter === "wins" && game.result !== "win") return false;
    if (filter === "losses" && game.result !== "loss") return false;
    if (filter === "draws" && game.result !== "draw") return false;
    if (filter === "suggested" && !suggestedGameIds.has(game.id)) return false;
    if (filter === "processed" && game.processing_status !== "processed") return false;
    if (filter === "failed" && game.processing_status !== "failed") return false;
    if (!query) return true;
    return [game.opening_name, game.opponent_username].some((value) => value?.toLowerCase().includes(query));
  });
}
