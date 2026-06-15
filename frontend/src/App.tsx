import { useEffect, useRef, useState } from "react";
import { ShareCard } from "./components/cards/ShareCard";
import {
  createStoryFromPgn,
  disconnectLichess,
  getImportedGameShareCard,
  getJournalGameDebug,
  getJournalGameDetail,
  getLichessStatus,
  ignoreSuggestedStory,
  importLatestLichessGames,
  connectLichessWithSession,
  listJournalGames,
  listSuggestedStories,
  reprocessAllJournalGames,
  reprocessJournalGame,
  resetIgnoredSuggestions,
} from "./lib/api";
import { exportElementAsPng } from "./lib/exportImage";
import { filterJournalGames, type JournalFilter } from "./lib/journal";
import { SAMPLE_CARDS, SAMPLE_PGN } from "./mockData";
import type { GameDebug, JournalGame, LichessStatus, ShareCardData } from "./types";

export function App() {
  const [activeView, setActiveView] = useState<"journal" | "demo">("journal");
  const [username, setUsername] = useState("clevermike");
  const [pgn, setPgn] = useState(SAMPLE_PGN);
  const [card, setCard] = useState<ShareCardData>(SAMPLE_CARDS[0].card);
  const [lichessStatus, setLichessStatus] = useState<LichessStatus | null>(null);
  const [journal, setJournal] = useState<JournalGame[]>([]);
  const [suggestedStories, setSuggestedStories] = useState<JournalGame[]>([]);
  const [selectedGame, setSelectedGame] = useState<JournalGame | null>(null);
  const [selectedCard, setSelectedCard] = useState<ShareCardData | null>(null);
  const [selectedDebug, setSelectedDebug] = useState<GameDebug | null>(null);
  const [status, setStatus] = useState("Ready");
  const [showDebug, setShowDebug] = useState(import.meta.env.DEV);
  const [journalFilter, setJournalFilter] = useState<JournalFilter>("all");
  const [journalSearch, setJournalSearch] = useState("");
  const cardRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const lichess = params.get("lichess");
    const reason = params.get("reason");
    const usernameParam = params.get("username");
    
    // Handle OAuth callback messages but don't use them as source of truth
    if (lichess === "error") {
      setStatus(reason ? `Lichess connection failed: ${reason}` : "Lichess connection failed");
      window.history.replaceState({}, "", window.location.pathname);
    } else if (lichess === "connected") {
      setStatus("Lichess connected, refreshing...");
      window.history.replaceState({}, "", window.location.pathname);
      // Small delay to ensure backend is ready
      setTimeout(() => {
        void initializeApp({ autoImportIfEmpty: true });
      }, 300);
      return;
    }
    
    // Always fetch fresh state from server
    void initializeApp();
  }, []);

  async function initializeApp(options: { autoImportIfEmpty?: boolean } = {}) {
    try {
      const [nextStatus, games, suggestions] = await loadJournalState();
      setLichessStatus(nextStatus);
      setJournal(games);
      setSuggestedStories(suggestions);

      if (options.autoImportIfEmpty && nextStatus.connected && games.length === 0) {
        setStatus("Lichess connected. Importing latest games...");
        const result = await importLatestLichessGames();
        const [importedGames, importedSuggestions] = await loadJournalLists();
        setJournal(importedGames);
        setSuggestedStories(importedSuggestions);
        if (importedGames.length > 0) {
          await loadGameAndCard(importedGames[0].id);
        }
        setStatus(importSummary(result));
        return;
      }
      
      // Auto-select and load first game if available
      if (games.length > 0) {
        await loadGameAndCard(games[0].id);
      }
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not initialize app");
    }
  }

  async function refreshLichessState() {
    try {
      const [nextStatus, games, suggestions] = await loadJournalState();
      setLichessStatus(nextStatus);
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus("Refreshed");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not refresh journal");
    }
  }

  async function loadGameAndCard(gameId: string) {
    try {
      const [detail, debug, cardData] = await Promise.all([
        getJournalGameDetail(gameId),
        getJournalGameDebug(gameId),
        getImportedGameShareCard(gameId),
      ]);
      setSelectedGame(detail);
      setSelectedDebug(debug);
      setSelectedCard(cardData);
      setStatus("Game loaded");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load game");
    }
  }

  async function handleSelectGame(gameId: string) {
    // Auto-load card when selecting game
    await loadGameAndCard(gameId);
  }

  async function handleImport() {
    setStatus("Importing latest Lichess games...");
    try {
      const result = await importLatestLichessGames();
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus(importSummary(result));
      // Auto-select and load newest imported game
      if (games.length > 0) {
        await loadGameAndCard(games[0].id);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not import games");
    }
  }

  async function handleDisconnect() {
    setStatus("Disconnecting Lichess...");
    try {
      await disconnectLichess();
      setSelectedGame(null);
      setSelectedCard(null);
      setSelectedDebug(null);
      setSuggestedStories([]);
      await refreshLichessState();
      setStatus("Lichess disconnected");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not disconnect Lichess");
    }
  }

  async function handleReprocessGame(gameId: string) {
    setStatus("Reprocessing story...");
    try {
      await reprocessJournalGame(gameId);
      // Reload everything for selected game
      await loadGameAndCard(gameId);
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus("Story reprocessed");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not reprocess game");
    }
  }

  async function handleReprocessAllGames() {
    setStatus("Reprocessing all imported games...");
    try {
      const result = await reprocessAllJournalGames();
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      // Reload currently selected game if exists
      if (selectedGame) {
        await loadGameAndCard(selectedGame.id);
      }
      setStatus(`Reprocessed ${result.processed} imported game(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not reprocess imported games");
    }
  }

  async function handleIgnoreSuggestion(storyId: string) {
    setStatus("Ignoring suggestion...");
    try {
      await ignoreSuggestedStory(storyId);
      setSuggestedStories(await listSuggestedStories());
      setStatus("Suggestion ignored");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not ignore suggestion");
    }
  }

  async function handleResetIgnoredSuggestions() {
    setStatus("Resetting ignored suggestions...");
    try {
      const result = await resetIgnoredSuggestions();
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus(`Restored ${result.restored} suggestion(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not reset ignored suggestions");
    }
  }

  async function loadJournalState(): Promise<[LichessStatus, JournalGame[], JournalGame[]]> {
    const [nextStatus, games] = await Promise.all([getLichessStatus(), listJournalGames()]);
    const suggestions = await listSuggestedStories().catch(() => []);
    return [nextStatus, games, suggestions];
  }

  async function loadJournalLists(): Promise<[JournalGame[], JournalGame[]]> {
    const games = await listJournalGames();
    const suggestions = await listSuggestedStories().catch(() => []);
    return [games, suggestions];
  }

  async function handleGenerate() {
    setStatus("Generating story...");
    try {
      const nextCard = await createStoryFromPgn(pgn, username);
      setCard(nextCard);
      setStatus("Story generated");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not generate story");
    }
  }

  function handleExport() {
    if (!cardRef.current) {
      return;
    }
    setStatus("Exporting PNG...");
    exportElementAsPng(cardRef.current, `swindle-${getCardForExport().story.primary_story}.png`)
      .then(() => setStatus("PNG exported"))
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "Share card export failed");
      });
  }

  function getCardForExport(): ShareCardData {
    if (activeView === "journal" && selectedCard) {
      return selectedCard;
    }
    return card;
  }

  return (
    <main className="app-shell">
      <nav className="top-nav">
        <div>
          <p>Swindle V1</p>
          <h1>Lichess story cards</h1>
        </div>
        <div className="view-tabs">
          <button
            type="button"
            className={activeView === "journal" ? "tab is-active" : "tab"}
            onClick={() => setActiveView("journal")}
          >
            Journal
          </button>
          <button
            type="button"
            className={activeView === "demo" ? "tab is-active" : "tab"}
            onClick={() => setActiveView("demo")}
          >
            PGN demo
          </button>
        </div>
      </nav>
      <section className="workspace">
        <div className="control-panel">
          {activeView === "journal" ? (
            <JournalControls
              lichessStatus={lichessStatus}
              journal={journal}
              suggestedStories={suggestedStories}
              selectedGame={selectedGame}
              selectedDebug={selectedDebug}
              journalFilter={journalFilter}
              journalSearch={journalSearch}
              showDebug={showDebug}
              onFilterChange={setJournalFilter}
              onSearchChange={setJournalSearch}
              onToggleDebug={() => setShowDebug(!showDebug)}
              onDisconnect={handleDisconnect}
              onImport={handleImport}
              onIgnoreSuggestion={handleIgnoreSuggestion}
              onResetIgnoredSuggestions={handleResetIgnoredSuggestions}
              onReprocessGame={handleReprocessGame}
              onReprocessAllGames={handleReprocessAllGames}
              onRefresh={refreshLichessState}
              onSelectGame={handleSelectGame}
            />
          ) : (
            <DemoControls
              username={username}
              pgn={pgn}
              onUsernameChange={setUsername}
              onPgnChange={setPgn}
              onGenerate={handleGenerate}
              onExport={handleExport}
              onSample={(sample) => {
                setCard(sample.card);
                setStatus(`Loaded sample: ${sample.name}`);
              }}
            />
          )}
          {activeView === "journal" ? (
            <div className="actions">
              <button type="button" className="secondary" onClick={handleExport}>
                Export PNG
              </button>
            </div>
          ) : null}
          <p className="status">{status}</p>
        </div>

        <div className="preview-panel">
          <div className="preview-frame">
            <div className="preview-scale">
              <ShareCard card={activeView === "journal" && selectedCard ? selectedCard : card} />
            </div>
          </div>
          <div className="export-stage" aria-hidden="true">
            <article ref={cardRef}>
              <ShareCard card={getCardForExport()} showDevDebug={false} />
            </article>
          </div>
        </div>
      </section>
    </main>
  );
}

type JournalControlsProps = {
  lichessStatus: LichessStatus | null;
  journal: JournalGame[];
  suggestedStories: JournalGame[];
  selectedGame: JournalGame | null;
  selectedDebug: GameDebug | null;
  journalFilter: JournalFilter;
  journalSearch: string;
  showDebug: boolean;
  onFilterChange: (filter: JournalFilter) => void;
  onSearchChange: (value: string) => void;
  onToggleDebug: () => void;
  onDisconnect: () => void;
  onImport: () => void;
  onIgnoreSuggestion: (storyId: string) => void;
  onResetIgnoredSuggestions: () => void;
  onReprocessGame: (gameId: string) => void;
  onReprocessAllGames: () => void;
  onRefresh: () => void;
  onSelectGame: (gameId: string) => void;
};

const JOURNAL_FILTERS: Array<{ value: JournalFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "wins", label: "Wins" },
  { value: "losses", label: "Losses" },
  { value: "draws", label: "Draws" },
  { value: "suggested", label: "Suggested" },
  { value: "processed", label: "Processed" },
  { value: "failed", label: "Failed" },
];

function JournalControls({
  lichessStatus,
  journal,
  suggestedStories,
  selectedGame,
  selectedDebug,
  journalFilter,
  journalSearch,
  showDebug,
  onFilterChange,
  onSearchChange,
  onToggleDebug,
  onDisconnect,
  onImport,
  onIgnoreSuggestion,
  onResetIgnoredSuggestions,
  onReprocessGame,
  onReprocessAllGames,
  onRefresh,
  onSelectGame,
}: JournalControlsProps) {
  const suggestedIds = new Set(suggestedStories.map((game) => game.id));
  const filteredJournal = filterJournalGames(journal, journalFilter, journalSearch, suggestedIds);

  return (
    <>
      <div className="panel-heading">
        <p>Milestone 3</p>
        <h1>Private chess journal</h1>
      </div>

      <div className="account-box">
        <span>Account</span>
        <strong>{lichessStatus?.connected ? lichessStatus.platform_username : "Not connected"}</strong>
      </div>

      <div className="actions">
        {lichessStatus?.connected ? (
          <>
            <button type="button" onClick={onImport}>
              Import latest
            </button>
            <button type="button" className="secondary" onClick={onDisconnect}>
              Disconnect
            </button>
          </>
        ) : (
          <button type="button" onClick={() => {
            void (async () => {
              const redirectUrl = await connectLichessWithSession();
              window.location.href = redirectUrl;
            })();
          }}>
            Connect Lichess
          </button>
        )}
        <button type="button" className="secondary" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      <section className="suggested-section" aria-label="Suggested Stories">
        <div className="section-heading">
          <div>
            <p>Suggested Stories</p>
            <h2>{suggestedStories.length} story-worthy game{suggestedStories.length === 1 ? "" : "s"}</h2>
          </div>
          {import.meta.env.DEV ? (
            <button type="button" className="secondary compact-button" onClick={onResetIgnoredSuggestions}>
              Reset ignored
            </button>
          ) : null}
        </div>
        {suggestedStories.length === 0 ? (
          <p className="empty-state">Nothing story-worthy yet. Import more games or open any journal game as a card.</p>
        ) : (
          <div className="suggested-list">
            {suggestedStories.map((game) => (
              <article
                className={`suggested-card ${selectedGame?.id === game.id ? "is-selected" : ""}`}
                key={game.id}
                onClick={() => onSelectGame(game.id)}
              >
                <div className="suggested-card-top">
                  <span className="story-chip">
                    {game.story.badge_label} {game.story.badge_emoji}
                  </span>
                  <strong>{Math.round(game.story.interesting_score * 100)}%</strong>
                </div>
                <h3>{game.story.headline}</h3>
                <dl className="story-facts">
                  <div>
                    <dt>Result</dt>
                    <dd>{game.result}</dd>
                  </div>
                  <div>
                    <dt>Moves</dt>
                    <dd>{game.moves_count}</dd>
                  </div>
                  <div>
                    <dt>Opponent</dt>
                    <dd>{game.opponent_username ?? "Unknown"}</dd>
                  </div>
                  <div>
                    <dt>Opening</dt>
                    <dd>{game.opening_name ?? "Unknown"}</dd>
                  </div>
                </dl>
                <div className="suggested-actions">
                  <button
                    type="button"
                    className="secondary compact-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectGame(game.id);
                    }}
                  >
                    Preview card
                  </button>
                  <button
                    type="button"
                    className="ghost compact-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      if (game.story.id) onIgnoreSuggestion(game.story.id);
                    }}
                    disabled={!game.story.id}
                  >
                    Ignore
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="journal-section" aria-label="Full Journal">
        <div className="section-heading">
          <div>
            <p>Full Journal</p>
            <h2>{journal.length} imported game{journal.length === 1 ? "" : "s"}</h2>
          </div>
        </div>
        <div className="journal-tools">
          <div className="filter-tabs" aria-label="Journal filters">
            {JOURNAL_FILTERS.map((filter) => (
              <button
                type="button"
                className={journalFilter === filter.value ? "filter-tab is-active" : "filter-tab"}
                key={filter.value}
                onClick={() => onFilterChange(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <label className="search-label">
            Search
            <input
              value={journalSearch}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Opening or opponent"
            />
          </label>
        </div>

      <div className="journal-list">
        {journal.length === 0 ? (
          <p className="empty-state">Connect Lichess and import your latest games to start building your chess journal.</p>
        ) : filteredJournal.length === 0 ? (
          <p className="empty-state">No games match this journal filter.</p>
        ) : (
          filteredJournal.map((game) => (
            <button 
              type="button" 
              className={`journal-item ${selectedGame?.id === game.id ? 'is-selected' : ''}`}
              key={game.id} 
              onClick={() => onSelectGame(game.id)}
            >
              <span>
                {game.result.toUpperCase()} / {game.moves_count} moves
              </span>
              <strong>{game.story.badge_label}</strong>
              <em>{game.opening_name ?? "Unknown opening"}</em>
              {selectedGame?.id === game.id && <span className="selected-indicator">✓</span>}
            </button>
          ))
        )}
      </div>
      </section>

      {selectedGame ? (
        <div className="detail-panel">
          <div className="panel-heading compact">
            <p>Game detail</p>
            <h1>{selectedGame.story.badge_label}</h1>
          </div>
          <dl>
            <div>
              <dt>Opponent</dt>
              <dd>{selectedGame.opponent_username ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Result</dt>
              <dd>{selectedGame.result}</dd>
            </div>
            <div>
              <dt>Speed</dt>
              <dd>{selectedGame.speed ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Opening</dt>
              <dd>{selectedGame.opening_name ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Moves</dt>
              <dd>{selectedGame.moves_count}</dd>
            </div>
            <div>
              <dt>Story</dt>
              <dd>{selectedGame.story.primary_story}</dd>
            </div>
          </dl>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => onReprocessGame(selectedGame.id)}>
              Reprocess story
            </button>
            {lichessUrl(selectedGame.external_game_id) ? (
              <a className="button-link" href={lichessUrl(selectedGame.external_game_id)} target="_blank" rel="noreferrer">
                Open on Lichess
              </a>
            ) : null}
          </div>
        </div>
      ) : null}

      {import.meta.env.DEV && (
        <div className="debug-controls">
          <button type="button" className="secondary debug-toggle" onClick={onToggleDebug}>
            {showDebug ? "Hide" : "Show"} debug
          </button>
        </div>
      )}

      {import.meta.env.DEV && showDebug && (
        <>
          <button type="button" className="secondary" onClick={onReprocessAllGames}>
            Reprocess all
          </button>
          {selectedDebug ? (
            <div className="debug-panel">
              <div className="panel-heading compact">
                <p>Debug</p>
                <h1>Board audit</h1>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => selectedDebug.card_fen && navigator.clipboard.writeText(selectedDebug.card_fen)}
              >
                Copy FEN
              </button>
              <dl>
                {debugRows(selectedDebug).map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd title={String(value ?? "")}>{String(value ?? "None")}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
        </>
      )}
    </>
  );
}

function lichessUrl(externalGameId: string): string | undefined {
  return externalGameId ? `https://lichess.org/${externalGameId}` : undefined;
}

function debugRows(debug: GameDebug): Array<[string, unknown]> {
  return [
    ["game_id", debug.game_id],
    ["external_game_id", debug.external_game_id],
    ["user_color", debug.user_color],
    ["result", debug.result],
    ["opponent_username", debug.opponent_username],
    ["opponent_rating", debug.opponent_rating],
    ["opening_name", debug.opening_name],
    ["moves_count", debug.moves_count],
    ["final_fen", debug.final_fen],
    ["key_position_fen", debug.key_position_fen],
    ["card_fen", debug.card_fen],
    ["board_position_source", debug.board_position_source],
    ["key_move_number", debug.key_move_number],
    ["key_move_san", debug.key_move_san],
    ["story_type", debug.story_type],
    ["headline", debug.headline],
    ["subheadline", debug.subheadline],
  ];
}

type DemoControlsProps = {
  username: string;
  pgn: string;
  onUsernameChange: (value: string) => void;
  onPgnChange: (value: string) => void;
  onGenerate: () => void;
  onExport: () => void;
  onSample: (sample: (typeof SAMPLE_CARDS)[number]) => void;
};

function DemoControls({
  username,
  pgn,
  onUsernameChange,
  onPgnChange,
  onGenerate,
  onExport,
  onSample,
}: DemoControlsProps) {
  return (
    <>
      <div className="panel-heading">
        <p>Milestone 1</p>
        <h1>PGN to story card</h1>
      </div>

      <label>
        Lichess username
        <input value={username} onChange={(event) => onUsernameChange(event.target.value)} />
      </label>

      <label>
        PGN
        <textarea value={pgn} onChange={(event) => onPgnChange(event.target.value)} />
      </label>

      <div className="actions">
        <button type="button" onClick={onGenerate}>
          Generate
        </button>
        <button type="button" className="secondary" onClick={onExport}>
          Export PNG
        </button>
      </div>
      <div className="sample-actions" aria-label="Sample cards">
        {SAMPLE_CARDS.map((sample) => (
          <button type="button" className="sample-button" key={sample.name} onClick={() => onSample(sample)}>
            {sample.name}
          </button>
        ))}
      </div>
    </>
  );
}

function importSummary(result: { imported: number; duplicates: number; skipped: number; errors: string[] }) {
  const summary = `Imported ${result.imported}; skipped ${result.duplicates} duplicate(s), ${result.skipped} invalid game(s).`;
  if (result.errors.length === 0) {
    return summary;
  }
  return `${summary} ${result.errors.slice(0, 2).join(" ")}`;
}
