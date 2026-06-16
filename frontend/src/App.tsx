import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ShareCard } from "./components/cards/ShareCard";
import { ChessBoard } from "./components/chess/ChessBoard";
import {
  addComment,
  addKudos,
  analyzeJournalGame,
  createStoryFromPgn,
  disconnectLichess,
  followProfile,
  getImportedGameShareCard,
  getJournalGameDebug,
  getJournalGameDetail,
  getLichessStatus,
  getPublicPost,
  getPublicProfile,
  ignoreSuggestedStory,
  importLatestLichessGames,
  connectLichessWithSession,
  listComments,
  listFeed,
  listJournalGames,
  listSuggestedStories,
  publishStoryCard,
  reprocessAllJournalGames,
  reprocessJournalGame,
  removeKudos,
  resetIgnoredSuggestions,
  unfollowProfile,
  unpublishStoryPost,
} from "./lib/api";
import { exportElementAsPng } from "./lib/exportImage";
import { filterJournalGames, type JournalFilter } from "./lib/journal";
import {
  absoluteUrl,
  postPath,
  profileCardHref,
  profileDisplayName,
  profilePath,
  profileSlugForPost,
  profileSlugForProfile,
  isPublished,
  publishButtonLabel,
} from "./lib/publicLinks";
import { FEED_EMPTY_MESSAGE, appendComment, applySocialCountsToFeed, applySocialCountsToPost, followButtonLabel } from "./lib/social";
import { SAMPLE_CARDS, SAMPLE_PGN } from "./mockData";
import type { FeedResponse, GameDebug, JournalGame, LichessStatus, PostComment, PublicProfile, PublishedPost, ShareCardData } from "./types";

export function App() {
  const route = currentRoute();
  if (route.kind === "profile") {
    return <PublicProfilePage username={route.username} />;
  }
  if (route.kind === "post") {
    return <PublicPostPage postId={route.postId} />;
  }
  if (route.kind === "feed") {
    return <FeedPage />;
  }

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
      return cardData;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load game");
      return null;
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

  async function handleAnalyzeGame(gameId: string) {
    setStatus("Analyzing with Lichess cloud eval...");
    try {
      await analyzeJournalGame(gameId);
      const cardData = await loadGameAndCard(gameId);
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus(analysisStatusMessage(cardData));
    } catch (error) {
      setStatus(error instanceof Error ? `Cloud eval analysis failed: ${error.message}` : "Cloud eval analysis failed");
    }
  }

  async function handlePublishSelectedGame() {
    if (!selectedGame?.story.id) {
      setStatus("Select a story card before publishing");
      return;
    }
    setStatus("Publishing card...");
    try {
      const post = await publishStoryCard(selectedGame.story.id);
      await loadGameAndCard(selectedGame.id);
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus(`Published successfully. ${absoluteUrl(window.location.origin, postPath(post.id))}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not publish card");
    }
  }

  async function handleUnpublishSelectedGame() {
    const postId = selectedGame?.published_post?.id;
    if (!selectedGame || !postId) {
      return;
    }
    setStatus("Unpublishing card...");
    try {
      await unpublishStoryPost(postId);
      await loadGameAndCard(selectedGame.id);
      const [games, suggestions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setStatus("Card unpublished");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not unpublish card");
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
          {lichessStatus?.platform_username ? (
            <a className="tab" href={profilePath(lichessStatus.platform_username)}>
              Profile
            </a>
          ) : (
            <button type="button" className="tab" disabled title="Connect Lichess to create a public profile">
              Profile
            </button>
          )}
          <a className="tab" href="/feed">
            Feed
          </a>
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
              onAnalyzeGame={handleAnalyzeGame}
              onPublishSelectedGame={handlePublishSelectedGame}
              onUnpublishSelectedGame={handleUnpublishSelectedGame}
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
          {activeView === "journal" && import.meta.env.DEV ? (
            <div className="preview-dev-tools">
              <button
                type="button"
                className="secondary"
                onClick={() => selectedGame && handleAnalyzeGame(selectedGame.id)}
                disabled={!selectedGame}
              >
                Analyze selected game
              </button>
              <p>{evalDebugLine(selectedCard)}</p>
            </div>
          ) : null}
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
  onAnalyzeGame: (gameId: string) => void;
  onPublishSelectedGame: () => void;
  onUnpublishSelectedGame: () => void;
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
  onAnalyzeGame,
  onPublishSelectedGame,
  onUnpublishSelectedGame,
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
      {import.meta.env.DEV ? (
        <p className="dev-notice">Dev mode: using default local user. Public profile uses connected Lichess username.</p>
      ) : null}

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
            <div>
              <dt>Analysis</dt>
              <dd>{selectedGame.metrics?.analysis_status ?? "none"}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{selectedGame.metrics?.analysis_source ?? "metadata_only"}</dd>
            </div>
            <div>
              <dt>Eval points</dt>
              <dd>{selectedGame.metrics?.eval_points ?? 0}</dd>
            </div>
            <div>
              <dt>Lowest eval</dt>
              <dd>{formatMaybeEval(selectedGame.metrics?.lowest_eval)}</dd>
            </div>
            <div>
              <dt>Highest eval</dt>
              <dd>{formatMaybeEval(selectedGame.metrics?.highest_eval)}</dd>
            </div>
            <div>
              <dt>Biggest swing</dt>
              <dd>{formatMaybeEval(selectedGame.metrics?.biggest_eval_swing)}</dd>
            </div>
            <div>
              <dt>Turn point</dt>
              <dd>{selectedGame.metrics?.turning_point_move ?? "None"}</dd>
            </div>
          </dl>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => onReprocessGame(selectedGame.id)}>
              Reprocess story
            </button>
            {import.meta.env.DEV ? (
              <button type="button" className="secondary" onClick={() => onAnalyzeGame(selectedGame.id)}>
                Analyze with cloud eval
              </button>
            ) : null}
            {lichessUrl(selectedGame.external_game_id) ? (
              <a className="button-link" href={lichessUrl(selectedGame.external_game_id)} target="_blank" rel="noreferrer">
                Open on Lichess
              </a>
            ) : null}
          </div>
          <PublicCardActions
            selectedGame={selectedGame}
            lichessUsername={lichessStatus?.platform_username}
            onPublish={onPublishSelectedGame}
            onUnpublish={onUnpublishSelectedGame}
          />
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

function PublicCardActions({
  selectedGame,
  lichessUsername,
  onPublish,
  onUnpublish,
}: {
  selectedGame: JournalGame;
  lichessUsername?: string | null;
  onPublish: () => void;
  onUnpublish: () => void;
}) {
  const publishedPost = selectedGame.published_post;
  const published = isPublished(publishedPost);
  const profileUsername = lichessUsername ?? publicPlayerName(selectedGame);
  const profileUrl = absoluteUrl(window.location.origin, profilePath(profileUsername));
  const publicPostUrl = publishedPost ? absoluteUrl(window.location.origin, postPath(publishedPost.id)) : null;

  return (
    <div className="public-actions">
      <div>
        <p>Public sharing</p>
        <strong>{published ? "Published" : "Private journal card"}</strong>
      </div>
      <div className="actions">
        {published ? (
          <span className="published-pill">{publishButtonLabel(publishedPost)}</span>
        ) : (
          <button type="button" onClick={onPublish} disabled={!selectedGame.story.id}>
            Publish card
          </button>
        )}
        {published ? (
          <button type="button" className="secondary" onClick={onUnpublish}>
            Unpublish
          </button>
        ) : null}
      </div>
      {published && publishedPost ? (
        <div className="public-links">
          <a className="button-link" href={profilePath(profileUsername)}>
            View profile
          </a>
          <a className="button-link" href={postPath(publishedPost.id)}>
            View public post
          </a>
          <button type="button" className="secondary compact-button" onClick={() => copyToClipboard(profileUrl)}>
            Copy profile link
          </button>
          {publicPostUrl ? (
            <button type="button" className="secondary compact-button" onClick={() => copyToClipboard(publicPostUrl)}>
              Copy post link
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function PublicProfilePage({ username }: { username: string }) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [status, setStatus] = useState("Loading profile...");

  useEffect(() => {
    void loadProfile();
  }, [username]);

  async function loadProfile() {
    try {
      const nextProfile = await getPublicProfile(username);
      setProfile(nextProfile);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load profile");
    }
  }

  async function handleFollowToggle() {
    if (!profile) return;
    setStatus(profile.viewer_is_following ? "Unfollowing..." : "Following...");
    try {
      if (profile.viewer_is_following) {
        await unfollowProfile(username);
      } else {
        await followProfile(username);
      }
      await loadProfile();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update follow");
    }
  }

  if (!profile) {
    return <PublicShell title={username} status={status} />;
  }

  const displayName = profileDisplayName(profile);
  const profileSlug = profileSlugForProfile(profile);
  const profileUrl = absoluteUrl(window.location.origin, profilePath(profileSlug));

  return (
    <PublicShell title={displayName} status={status}>
      <section className="profile-header">
        <div>
          <p>Public profile</p>
          <h1>{displayName}</h1>
          <span>Lichess: {profile.lichess_username ?? "Not connected"}</span>
        </div>
        <div className="profile-actions">
          {!profile.viewer_is_self ? (
            <button
              type="button"
              className={profile.viewer_is_following ? "secondary" : ""}
              onClick={handleFollowToggle}
            >
              {followButtonLabel(profile)}
            </button>
          ) : null}
          <button type="button" className="secondary" onClick={() => copyToClipboard(profileUrl)}>
            Copy profile link
          </button>
        </div>
      </section>
      <section className="profile-stats" aria-label="Profile stats">
        <Stat label="Published cards" value={profile.published_cards_count} />
        <Stat label="Followers" value={profile.followers_count} />
        <Stat label="Following" value={profile.following_count} />
        <Stat label="Wins shown" value={profile.wins_shown} />
        <Stat label="Losses shown" value={profile.losses_shown} />
        <Stat label="Common story" value={storyLabel(profile.common_story)} />
        <Stat label="Games imported" value={profile.games_imported ?? 0} />
      </section>
      <section className="public-post-grid" aria-label="Published story cards">
        {profile.posts.length === 0 ? (
          <div className="empty-state profile-empty">
            <strong>No published story cards yet.</strong>
            <span>Published cards will appear here.</span>
          </div>
        ) : (
          profile.posts.map((post) => <ProfilePostCard key={post.id} post={post} />)
        )}
      </section>
    </PublicShell>
  );
}

function FeedPage() {
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [status, setStatus] = useState("Loading feed...");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const nextFeed = await listFeed();
      setFeed(nextFeed);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load feed");
    }
  }

  async function handleKudos(post: PublishedPost) {
    try {
      const counts = post.viewer_has_kudos ? await removeKudos(post.id) : await addKudos(post.id);
      setFeed((current) => applySocialCountsToFeed(current, post.id, counts));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update kudos");
    }
  }

  return (
    <PublicShell title="Feed" status={status}>
      <section className="feed-page" aria-label="Feed">
        {!feed ? (
          <p className="empty-state">Loading feed...</p>
        ) : feed.items.length === 0 ? (
          <div className="empty-state profile-empty">
            <strong>{FEED_EMPTY_MESSAGE}</strong>
            <span>Published public cards from followed profiles will appear in this feed.</span>
          </div>
        ) : (
          feed.items.map((post) => <FeedPostCard key={post.id} post={post} onKudos={() => handleKudos(post)} />)
        )}
      </section>
    </PublicShell>
  );
}

function PublicPostPage({ postId }: { postId: string }) {
  const [post, setPost] = useState<PublishedPost | null>(null);
  const [comments, setComments] = useState<PostComment[]>([]);
  const [commentBody, setCommentBody] = useState("");
  const [status, setStatus] = useState("Loading post...");

  useEffect(() => {
    void (async () => {
      try {
        const [nextPost, nextComments] = await Promise.all([getPublicPost(postId), listComments(postId)]);
        setPost(nextPost);
        setComments(nextComments);
        setStatus("Ready");
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not load post");
      }
    })();
  }, [postId]);

  async function handleKudos() {
    if (!post) return;
    try {
      const counts = post.viewer_has_kudos ? await removeKudos(post.id) : await addKudos(post.id);
      setPost(applySocialCountsToPost(post, counts));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update kudos");
    }
  }

  async function handleCommentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!post) return;
    setStatus("Posting comment...");
    try {
      const comment = await addComment(post.id, commentBody);
      setComments((current) => appendComment(current, comment));
      setPost({ ...post, comments_count: post.comments_count + 1 });
      setCommentBody("");
      setStatus("Comment posted");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not post comment");
    }
  }

  if (!post) {
    return <PublicShell title="Story card" status={status} />;
  }

  const displayName = profileDisplayName(post);
  const profileUsername = profileSlugForPost(post);
  const currentPostUrl = absoluteUrl(window.location.origin, postPath(post.id));

  return (
    <PublicShell title={post.headline} status={status}>
      <section className="public-post-page">
        <div className="public-card-frame">
          {post.share_card ? <ShareCard card={post.share_card} /> : <p className="empty-state">Share card unavailable.</p>}
        </div>
        <aside className="public-post-meta">
          <span className="story-chip">
            {post.story?.badge_label} {post.story?.badge_emoji}
          </span>
          <h1>{post.headline}</h1>
          <p className="public-byline">{displayName}</p>
          <SocialActions post={post} onKudos={handleKudos} />
          <dl>
            <div>
              <dt>Result</dt>
              <dd>{post.game?.result ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Opening</dt>
              <dd>{post.game?.opening_name ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Opponent</dt>
              <dd>{post.game?.opponent_username ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Moves</dt>
              <dd>{post.game?.moves_count ?? 0}</dd>
            </div>
          </dl>
          <div className="actions">
            <a className="button-link" href={profilePath(profileUsername)}>
              Back to profile
            </a>
            <button type="button" className="secondary" onClick={() => copyToClipboard(currentPostUrl)}>
              Copy post link
            </button>
            {post.game?.external_game_id ? (
              <a className="button-link" href={lichessUrl(post.game.external_game_id)} target="_blank" rel="noreferrer">
                Open on Lichess
              </a>
            ) : null}
          </div>
          <section className="comments-panel" aria-label="Comments">
            <h2>Comments</h2>
            {comments.length === 0 ? (
              <p className="empty-state">No comments yet.</p>
            ) : (
              <div className="comment-list">
                {comments.map((comment) => (
                  <article className="comment-item" key={comment.id}>
                    <strong>{profileDisplayName(comment.author)}</strong>
                    <p>{comment.body}</p>
                  </article>
                ))}
              </div>
            )}
            <form className="comment-form" onSubmit={handleCommentSubmit}>
              <label>
                Add comment
                <textarea value={commentBody} onChange={(event) => setCommentBody(event.target.value)} />
              </label>
              <button type="submit" disabled={!commentBody.trim()}>
                Submit
              </button>
            </form>
          </section>
        </aside>
      </section>
    </PublicShell>
  );
}

function FeedPostCard({ post, onKudos }: { post: PublishedPost; onKudos: () => void }) {
  const profileUsername = profileSlugForPost(post);
  return (
    <article className="feed-card">
      <div className="feed-card-main">
        {post.story?.key_position_fen ? (
          <a className="feed-card-board" href={postPath(post.id)} aria-label={`Open post: ${post.headline}`}>
            <ChessBoard fen={post.story.key_position_fen} />
          </a>
        ) : null}
        <div className="feed-card-copy">
          <p>
            <a href={profilePath(profileUsername)}>{profileDisplayName(post)}</a>
            <span>{post.game?.opening_name ?? "Unknown opening"}</span>
          </p>
          <span className="story-chip">
            {post.story?.badge_label} {post.story?.badge_emoji}
          </span>
          <h2>
            <a href={postPath(post.id)}>{post.headline}</a>
          </h2>
          <dl className="story-facts">
            <div>
              <dt>Result</dt>
              <dd>{post.game?.result ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Moves</dt>
              <dd>{post.game?.moves_count ?? 0}</dd>
            </div>
            <div>
              <dt>Eval swing</dt>
              <dd>{formatMaybeEval(post.metrics?.biggest_eval_swing)}</dd>
            </div>
          </dl>
        </div>
      </div>
      <SocialActions post={post} onKudos={onKudos} />
    </article>
  );
}

function ProfilePostCard({ post }: { post: PublishedPost }) {
  const href = profileCardHref(post.id);
  return (
    <a className="profile-post-card" href={href} aria-label={`View card: ${post.headline}`}>
      {post.story?.key_position_fen ? (
        <div className="profile-card-board" aria-hidden="true">
          <ChessBoard fen={post.story.key_position_fen} />
        </div>
      ) : null}
      <div className="suggested-card-top">
        <span className="story-chip">
          {post.story?.badge_label} {post.story?.badge_emoji}
        </span>
        <strong>{Math.round((post.story?.interesting_score ?? 0) * 100)}%</strong>
      </div>
      <h2>{post.headline}</h2>
      <dl className="story-facts">
        <div>
          <dt>Result</dt>
          <dd>{post.game?.result ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Opening</dt>
          <dd>{post.game?.opening_name ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Opponent</dt>
          <dd>{post.game?.opponent_username ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Moves</dt>
          <dd>{post.game?.moves_count ?? 0}</dd>
        </div>
      </dl>
      <span className="post-social-line">{post.kudos_count} kudos · {post.comments_count} comments</span>
      <span className="view-card-action">View card</span>
    </a>
  );
}

function SocialActions({ post, onKudos }: { post: Pick<PublishedPost, "kudos_count" | "comments_count" | "viewer_has_kudos">; onKudos: () => void }) {
  return (
    <div className="social-actions">
      <button type="button" className={post.viewer_has_kudos ? "is-active" : "secondary"} onClick={onKudos}>
        Kudos {post.kudos_count}
      </button>
      <span>{post.comments_count} comment{post.comments_count === 1 ? "" : "s"}</span>
    </div>
  );
}


function PublicShell({ title, status, children }: { title: string; status: string; children?: ReactNode }) {
  return (
    <main className="app-shell public-shell">
      <nav className="top-nav">
        <div>
          <p>Swindle V1</p>
          <h1>{title}</h1>
        </div>
        <div className="view-tabs">
          <a className="tab" href="/">
            Journal
          </a>
          <a className="tab" href="/feed">
            Feed
          </a>
        </div>
      </nav>
      {children}
      <p className="status">{status}</p>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function currentRoute():
  | { kind: "journal" }
  | { kind: "feed" }
  | { kind: "profile"; username: string }
  | { kind: "post"; postId: string } {
  const path = window.location.pathname;
  if (path === "/feed") {
    return { kind: "feed" };
  }
  if (path.startsWith("/profile/")) {
    return { kind: "profile", username: decodeURIComponent(path.replace("/profile/", "")) };
  }
  if (path.startsWith("/p/")) {
    return { kind: "post", postId: decodeURIComponent(path.replace("/p/", "")) };
  }
  return { kind: "journal" };
}

function copyToClipboard(value: string) {
  void navigator.clipboard?.writeText(value);
}

function storyLabel(value?: string | null): string {
  return value ? value.replace(/_/g, " ") : "None";
}

function publicPlayerName(game: JournalGame): string {
  if (game.user_color === "white" && game.white_username) return game.white_username;
  if (game.user_color === "black" && game.black_username) return game.black_username;
  return "Player";
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
    ["analysis_status", debug.metrics?.analysis_status],
    ["analysis_source", debug.metrics?.analysis_source],
    ["eval_points", debug.metrics?.eval_points],
    ["lowest_eval", debug.metrics?.lowest_eval],
    ["highest_eval", debug.metrics?.highest_eval],
    ["biggest_eval_swing", debug.metrics?.biggest_eval_swing],
    ["turning_point_move", debug.metrics?.turning_point_move],
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

function analysisStatusMessage(card: ShareCardData | null): string {
  const status = card?.metrics.analysis_status ?? "unavailable";
  const points = card?.metrics.eval_points ?? 0;
  if (status === "partial" && points >= 2) return "Partial engine analysis available";
  if (status === "complete" && points >= 2) return "Engine analysis complete";
  if (status === "partial" || status === "complete") return "Not enough cloud eval data for this game";
  if (status === "unavailable") return "No cloud eval found for this game yet";
  return "Cloud eval analysis complete";
}

function evalDebugLine(card: ShareCardData | null): string {
  const points = card?.metrics.eval_points ?? 0;
  const status = card?.metrics.analysis_status ?? "none";
  const source = card?.metrics.analysis_source ?? "metadata_only";
  const story = card?.story.primary_story ?? "none";
  const lowest = formatMaybeEval(card?.metrics.lowest_eval);
  const highest = formatMaybeEval(card?.metrics.highest_eval);
  const swing = formatMaybeEval(card?.metrics.biggest_eval_swing);
  const turn = card?.story.key_move_number ?? "None";
  const board = card?.board_position_source ?? "none";
  return `Story: ${story} / Eval points: ${points} / Status: ${status} / Source: ${source} / Low: ${lowest} / High: ${highest} / Swing: ${swing} / Turn: ${turn} / Board: ${board}`;
}

function formatMaybeEval(value: number | null | undefined): string {
  if (value == null) return "None";
  return value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}
