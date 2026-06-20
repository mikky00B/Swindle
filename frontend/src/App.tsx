import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type ReactNode, type RefObject } from "react";
import { ShareCard } from "./components/cards/ShareCard";
import { ChessBoard } from "./components/chess/ChessBoard";
import { LANDING_DEMO_CARDS } from "./data/demoCards";
import {
  addComment,
  addKudos,
  addChessComUsername,
  analyzeJournalGame,
  createStoryFromPgn,
  disconnectChessCom,
  disconnectLichess,
  followProfile,
  getChessComStatus,
  getImportedGameShareCard,
  getJournalGameDebug,
  getJournalGameDetail,
  getLichessStatus,
  getPublicPost,
  getPublicProfile,
  getSessionDetail,
  ignoreSuggestedStory,
  importLatestChessComGames,
  importLatestLichessGames,
  lichessConnectUrl,
  listComments,
  listFeed,
  listJournalGames,
  listSessions,
  listSuggestedStories,
  publishStoryCard,
  rebuildSessions,
  reprocessAllJournalGames,
  reprocessJournalGame,
  removeKudos,
  resetIgnoredSuggestions,
  unfollowProfile,
  unpublishStoryPost,
} from "./lib/api";
import { exportElementAsPng } from "./lib/exportImage";
import {
  CARD_SIZES,
  CARD_SIZE_OPTIONS,
  CARD_THEMES,
  CARD_THEME_OPTIONS,
  normalizeCardSize,
  normalizeShareCardTheme,
  themeFileSlug,
  type ShareCardSize,
  type ShareCardTheme,
} from "./lib/cardThemes";
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
import { routeFromPath } from "./lib/routes";
import {
  FEED_EMPTY_MESSAGE,
  FEED_EMPTY_TITLE,
  appendComment,
  applySocialCountsToFeed,
  applySocialCountsToPost,
  followButtonLabel,
  kudosLabel,
  navItems,
  shouldShowFollowButton,
  socialCountLabel,
} from "./lib/social";
import { SAMPLE_CARDS, SAMPLE_PGN } from "./mockData";
import type {
  ChessComStatus,
  FeedResponse,
  GameDebug,
  JournalGame,
  LichessStatus,
  PostComment,
  PublicProfile,
  PublishedPost,
  SessionDetail,
  SessionOpeningSummary,
  SessionRatingTrack,
  SessionShareCardData,
  SessionSummary,
  ShareCardData,
} from "./types";

export function App() {
  const route = currentRoute();
  if (route.kind === "landing") {
    return <LandingPage />;
  }
  if (route.kind === "profile") {
    return <PublicProfilePage username={route.username} />;
  }
  if (route.kind === "post") {
    return <PublicPostPage postId={route.postId} />;
  }
  if (route.kind === "feed") {
    return <FeedPage />;
  }
  if (route.kind === "session") {
    return <SessionDetailPage sessionId={route.sessionId} />;
  }

  const [activeView, setActiveView] = useState<"journal" | "demo">("journal");
  const [username, setUsername] = useState("clevermike");
  const [pgn, setPgn] = useState(SAMPLE_PGN);
  const [card, setCard] = useState<ShareCardData>(SAMPLE_CARDS[0].card);
  const [lichessStatus, setLichessStatus] = useState<LichessStatus | null>(null);
  const [chesscomStatus, setChesscomStatus] = useState<ChessComStatus | null>(null);
  const [chesscomUsername, setChesscomUsername] = useState("");
  const [journal, setJournal] = useState<JournalGame[]>([]);
  const [suggestedStories, setSuggestedStories] = useState<JournalGame[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedGame, setSelectedGame] = useState<JournalGame | null>(null);
  const [selectedCard, setSelectedCard] = useState<ShareCardData | null>(null);
  const [sessionExportCard, setSessionExportCard] = useState<SessionShareCardData | null>(null);
  const [selectedTheme, setSelectedTheme] = useState<ShareCardTheme>("classic");
  const [selectedSize, setSelectedSize] = useState<ShareCardSize>("square");
  const [selectedDebug, setSelectedDebug] = useState<GameDebug | null>(null);
  const [status, setStatus] = useState("Ready");
  const [showDebug, setShowDebug] = useState(false);
  const [journalFilter, setJournalFilter] = useState<JournalFilter>("all");
  const [journalSearch, setJournalSearch] = useState("");
  const cardRef = useRef<HTMLElement | null>(null);
  const sessionCardRef = useRef<HTMLElement | null>(null);
  const mobilePreviewRef = useRef<HTMLElement>(null);

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
      const [nextStatus, nextChesscomStatus, games, suggestions, nextSessions] = await loadJournalState();
      setLichessStatus(nextStatus);
      setChesscomStatus(nextChesscomStatus);
      setChesscomUsername(nextChesscomStatus.platform_username ?? "");
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);

      if (options.autoImportIfEmpty && nextStatus.connected && games.length === 0) {
        setStatus("Lichess connected. Importing latest games...");
        const result = await importLatestLichessGames();
        const [importedGames, importedSuggestions, importedSessions] = await loadJournalLists();
        setJournal(importedGames);
        setSuggestedStories(importedSuggestions);
        setSessions(importedSessions);
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
      const [nextStatus, nextChesscomStatus, games, suggestions, nextSessions] = await loadJournalState();
      setLichessStatus(nextStatus);
      setChesscomStatus(nextChesscomStatus);
      setChesscomUsername(nextChesscomStatus.platform_username ?? "");
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
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
      setSelectedTheme(normalizeShareCardTheme(detail.published_post?.card_theme));
      setSelectedSize(normalizeCardSize(detail.published_post?.card_size));
      setStatus("Game loaded");
      return cardData;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load game");
      return null;
    }
  }

  async function handleSelectGame(gameId: string) {
    setStatus("Loading story card...");
    await loadGameAndCard(gameId);
    if (window.matchMedia("(max-width: 768px)").matches) {
      mobilePreviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function handleImport() {
    setStatus("Importing latest Lichess games...");
    try {
      const result = await importLatestLichessGames();
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
      setStatus(importSummary(result));
      // Auto-select and load newest imported game
      if (games.length > 0) {
        await loadGameAndCard(games[0].id);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not import games");
    }
  }

  async function handleAddChessComUsername(event?: FormEvent) {
    event?.preventDefault();
    const nextUsername = chesscomUsername.trim();
    if (!nextUsername) {
      setStatus("Enter a Chess.com username first");
      return;
    }
    setStatus("Adding Chess.com username...");
    try {
      const nextStatus = await addChessComUsername(nextUsername);
      setChesscomStatus(nextStatus);
      setChesscomUsername(nextStatus.platform_username ?? nextUsername);
      setStatus(`Chess.com username added: ${nextStatus.platform_username ?? nextUsername}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not add Chess.com username");
    }
  }

  async function handleImportChessComGames() {
    setStatus("Importing Chess.com games...");
    try {
      const result = await importLatestChessComGames();
      const [games, suggestions, nextSessions] = await loadJournalLists();
      const nextChesscomStatus = await getChessComStatus().catch(() => chesscomStatus);
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
      if (nextChesscomStatus) setChesscomStatus(nextChesscomStatus);
      setStatus(importSummary(result));
      if (games.length > 0) {
        await loadGameAndCard(games[0].id);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not import Chess.com games");
    }
  }

  async function handleDisconnectChessCom() {
    setStatus("Removing Chess.com username...");
    try {
      await disconnectChessCom();
      const nextStatus = await getChessComStatus();
      setChesscomStatus(nextStatus);
      setChesscomUsername("");
      setStatus("Chess.com username removed");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not remove Chess.com username");
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
      setSessions([]);
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
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
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
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
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
      const post = await publishStoryCard(selectedGame.story.id, selectedTheme, selectedSize);
      await loadGameAndCard(selectedGame.id);
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
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
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
      setStatus("Card unpublished");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not unpublish card");
    }
  }

  async function handleReprocessAllGames() {
    setStatus("Reprocessing all imported games...");
    try {
      const result = await reprocessAllJournalGames();
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
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
      const [games, suggestions, nextSessions] = await loadJournalLists();
      setJournal(games);
      setSuggestedStories(suggestions);
      setSessions(nextSessions);
      setStatus(`Restored ${result.restored} suggestion(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not reset ignored suggestions");
    }
  }

  async function loadJournalState(): Promise<[LichessStatus, ChessComStatus, JournalGame[], JournalGame[], SessionSummary[]]> {
    const [nextStatus, nextChesscomStatus, games, nextSessions] = await Promise.all([
      getLichessStatus(),
      getChessComStatus(),
      listJournalGames(),
      listSessions().catch(() => []),
    ]);
    const suggestions = await listSuggestedStories().catch(() => []);
    return [nextStatus, nextChesscomStatus, games, suggestions, nextSessions];
  }

  async function loadJournalLists(): Promise<[JournalGame[], JournalGame[], SessionSummary[]]> {
    const [games, nextSessions] = await Promise.all([listJournalGames(), listSessions().catch(() => [])]);
    const suggestions = await listSuggestedStories().catch(() => []);
    return [games, suggestions, nextSessions];
  }

  async function handleRebuildSessions() {
    setStatus("Rebuilding daily recaps...");
    try {
      const result = await rebuildSessions();
      setSessions(await listSessions());
      setStatus(`Rebuilt ${result.sessions} daily recap${result.sessions === 1 ? "" : "s"}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not rebuild sessions");
    }
  }

  async function handleExportSessionWindow(recapCard: SessionShareCardData) {
    setStatus("Exporting recap...");
    try {
      await exportSessionCard(recapCard);
      setStatus("Recap exported");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Recap export failed");
    }
  }

  async function exportSessionCard(recapCard: SessionShareCardData) {
    setSessionExportCard(recapCard);
    await nextFrame();
    if (!sessionCardRef.current) {
      throw new Error("Daily recap card is not ready");
    }
    await exportElementAsPng(
      sessionCardRef.current,
      sessionExportFileName(recapCard, selectedTheme, selectedSize),
      CARD_SIZES[selectedSize],
    );
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
    exportElementAsPng(cardRef.current, exportFileName(getCardForExport(), selectedTheme, selectedSize), CARD_SIZES[selectedSize])
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
      <TopNav title="Chess story cards" activePage="journal" lichessStatus={lichessStatus}>
        {import.meta.env.DEV ? (
          <button
            type="button"
            className={activeView === "demo" ? "tab is-active" : "tab"}
            onClick={() => setActiveView("demo")}
          >
            PGN demo
          </button>
        ) : null}
      </TopNav>
      <section className="journal-layout">
        <div className="control-panel journal-left">
          {activeView === "journal" ? (
            <JournalControls
              lichessStatus={lichessStatus}
              chesscomStatus={chesscomStatus}
              chesscomUsername={chesscomUsername}
              journal={journal}
              suggestedStories={suggestedStories}
              sessions={sessions}
              selectedGame={selectedGame}
              selectedCard={selectedCard}
              selectedDebug={selectedDebug}
              status={status}
              mobilePreviewRef={mobilePreviewRef}
              journalFilter={journalFilter}
              journalSearch={journalSearch}
              showDebug={showDebug}
              onFilterChange={setJournalFilter}
              onSearchChange={setJournalSearch}
              onChessComUsernameChange={setChesscomUsername}
              onAddChessComUsername={handleAddChessComUsername}
              onImportChessComGames={handleImportChessComGames}
              onDisconnectChessCom={handleDisconnectChessCom}
              onToggleDebug={() => setShowDebug(!showDebug)}
              selectedTheme={selectedTheme}
              selectedSize={selectedSize}
              onThemeChange={setSelectedTheme}
              onSizeChange={setSelectedSize}
              onLockedThemeClick={() => setStatus("Premium themes are coming soon")}
              onDisconnect={handleDisconnect}
              onImport={handleImport}
              onIgnoreSuggestion={handleIgnoreSuggestion}
              onResetIgnoredSuggestions={handleResetIgnoredSuggestions}
              onRebuildSessions={handleRebuildSessions}
              onExportSessionWindow={handleExportSessionWindow}
              onReprocessGame={handleReprocessGame}
              onReprocessAllGames={handleReprocessAllGames}
              onAnalyzeGame={handleAnalyzeGame}
              onExport={handleExport}
              onPublishSelectedGame={handlePublishSelectedGame}
              onUnpublishSelectedGame={handleUnpublishSelectedGame}
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
          {status !== "Ready" ? <p className="status">{status}</p> : null}
        </div>

        <div className="preview-panel journal-right">
          {activeView === "journal" ? (
            <>
              <div className="preview-frame">
                {selectedCard ? (
                  <ResponsiveShareCard card={selectedCard} theme={selectedTheme} size={selectedSize} />
                ) : (
                  <p className="preview-placeholder">Select a game to preview its story card.</p>
                )}
              </div>
              <ThemeSelector
                selectedTheme={selectedTheme}
                onThemeChange={setSelectedTheme}
                onLockedThemeClick={() => setStatus("Premium themes are coming soon")}
              />
              <SizeSelector selectedSize={selectedSize} onSizeChange={setSelectedSize} />
              <div className="preview-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => selectedGame && handleAnalyzeGame(selectedGame.id)}
                  disabled={!selectedGame}
                >
                  Analyze selected game
                </button>
                <button type="button" className="secondary" onClick={handleExport} disabled={!selectedCard}>
                  Export PNG
                </button>
                {selectedGame ? (
                  <>
                    <PublicCardActions
                      selectedGame={selectedGame}
                      lichessUsername={lichessStatus?.platform_username}
                      onPublish={handlePublishSelectedGame}
                      onUnpublish={handleUnpublishSelectedGame}
                    />
                    {gameUrl(selectedGame) ? (
                      <a className="button-link" href={gameUrl(selectedGame)} target="_blank" rel="noreferrer">
                        Open on {platformLabel(selectedGame.platform)}
                      </a>
                    ) : null}
                  </>
                ) : null}
                <p>
                  {status === "Loading story card..." || status.startsWith("Analyzing")
                    ? status
                    : analysisStatusMessage(selectedCard)}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="preview-frame">
                <ResponsiveShareCard card={card} theme={selectedTheme} size={selectedSize} />
              </div>
              <div className="preview-actions">
                <button type="button" className="secondary" onClick={handleExport}>
                  Export PNG
                </button>
              </div>
            </>
          )}
          <div
            className="export-stage"
            aria-hidden="true"
            style={
              {
                "--export-width": `${CARD_SIZES[selectedSize].width}px`,
                "--export-height": `${CARD_SIZES[selectedSize].height}px`,
              } as CSSProperties
            }
          >
            <article ref={cardRef}>
              <ShareCard card={getCardForExport()} theme={selectedTheme} size={selectedSize} showDevDebug={false} />
            </article>
            {sessionExportCard ? (
              <article ref={sessionCardRef}>
                <SessionRecapCard card={sessionExportCard} theme={selectedTheme} size={selectedSize} />
              </article>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}

type JournalControlsProps = {
  lichessStatus: LichessStatus | null;
  chesscomStatus: ChessComStatus | null;
  chesscomUsername: string;
  journal: JournalGame[];
  suggestedStories: JournalGame[];
  sessions: SessionSummary[];
  selectedGame: JournalGame | null;
  selectedCard: ShareCardData | null;
  selectedDebug: GameDebug | null;
  status: string;
  mobilePreviewRef: RefObject<HTMLElement>;
  journalFilter: JournalFilter;
  journalSearch: string;
  showDebug: boolean;
  selectedTheme: ShareCardTheme;
  selectedSize: ShareCardSize;
  onFilterChange: (filter: JournalFilter) => void;
  onSearchChange: (value: string) => void;
  onChessComUsernameChange: (value: string) => void;
  onAddChessComUsername: (event?: FormEvent) => void;
  onImportChessComGames: () => void;
  onDisconnectChessCom: () => void;
  onToggleDebug: () => void;
  onThemeChange: (theme: ShareCardTheme) => void;
  onSizeChange: (size: ShareCardSize) => void;
  onLockedThemeClick: () => void;
  onDisconnect: () => void;
  onImport: () => void;
  onIgnoreSuggestion: (storyId: string) => void;
  onResetIgnoredSuggestions: () => void;
  onRebuildSessions: () => void;
  onExportSessionWindow: (card: SessionShareCardData) => void;
  onReprocessGame: (gameId: string) => void;
  onReprocessAllGames: () => void;
  onAnalyzeGame: (gameId: string) => void;
  onExport: () => void;
  onPublishSelectedGame: () => void;
  onUnpublishSelectedGame: () => void;
  onRefresh: () => void;
  onSelectGame: (gameId: string) => void;
};

const JOURNAL_FILTERS: Array<{ value: JournalFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "lichess", label: "Lichess" },
  { value: "chesscom", label: "Chess.com" },
  { value: "wins", label: "Wins" },
  { value: "losses", label: "Losses" },
  { value: "draws", label: "Draws" },
  { value: "suggested", label: "Suggested" },
  { value: "processed", label: "Processed" },
  { value: "failed", label: "Failed" },
];

function JournalControls({
  lichessStatus,
  chesscomStatus,
  chesscomUsername,
  journal,
  suggestedStories,
  sessions,
  selectedGame,
  selectedCard,
  selectedDebug,
  status,
  mobilePreviewRef,
  journalFilter,
  journalSearch,
  showDebug,
  selectedTheme,
  selectedSize,
  onFilterChange,
  onSearchChange,
  onChessComUsernameChange,
  onAddChessComUsername,
  onImportChessComGames,
  onDisconnectChessCom,
  onToggleDebug,
  onThemeChange,
  onSizeChange,
  onLockedThemeClick,
  onDisconnect,
  onImport,
  onIgnoreSuggestion,
  onResetIgnoredSuggestions,
  onRebuildSessions,
  onExportSessionWindow,
  onReprocessGame,
  onReprocessAllGames,
  onAnalyzeGame,
  onExport,
  onPublishSelectedGame,
  onUnpublishSelectedGame,
  onRefresh,
  onSelectGame,
}: JournalControlsProps) {
  const suggestedIds = new Set(suggestedStories.map((game) => game.id));
  const filteredJournal = filterJournalGames(journal, journalFilter, journalSearch, suggestedIds);

  return (
    <>
      <div className="panel-heading">
        <p>Chess story cards</p>
        <h1>Private chess journal</h1>
      </div>

      <div className="account-box">
        <span>Lichess</span>
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
          <button type="button" onClick={() => window.location.assign(lichessConnectUrl())}>
            Connect Lichess
          </button>
        )}
        <button type="button" className="secondary" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      <form className="account-box chesscom-box" onSubmit={onAddChessComUsername}>
        <span>Chess.com</span>
        <strong>{chesscomStatus?.connected ? chesscomStatus.platform_username : "No username added"}</strong>
        <p>Chess.com imports use public game archives. No password required.</p>
        <label>
          Chess.com username
          <input
            value={chesscomUsername}
            onChange={(event) => onChessComUsernameChange(event.target.value)}
            placeholder="Chess.com username"
          />
        </label>
        {chesscomStatus?.last_synced_at ? <small>Last imported {formatDate(chesscomStatus.last_synced_at)}</small> : null}
        <div className="actions">
          <button type="submit">Add Chess.com username</button>
          <button type="button" className="secondary" onClick={onImportChessComGames} disabled={!chesscomStatus?.connected}>
            Import Chess.com games
          </button>
          {chesscomStatus?.connected ? (
            <button type="button" className="ghost" onClick={onDisconnectChessCom}>
              Remove
            </button>
          ) : null}
        </div>
      </form>

      <MobileJournalPreview
        selectedGame={selectedGame}
        selectedCard={selectedCard}
        status={status}
        previewRef={mobilePreviewRef}
        onAnalyze={onAnalyzeGame}
        onExport={onExport}
        onPublish={onPublishSelectedGame}
        onUnpublish={onUnpublishSelectedGame}
        selectedTheme={selectedTheme}
        selectedSize={selectedSize}
        onThemeChange={onThemeChange}
        onSizeChange={onSizeChange}
        onLockedThemeClick={onLockedThemeClick}
      />

      <RecentSessionsSection
        sessions={sessions}
        username={lichessStatus?.platform_username ?? chesscomStatus?.platform_username ?? "Player"}
        onRebuild={onRebuildSessions}
        onExportWindow={onExportSessionWindow}
      />

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
          <p className="empty-state">No games imported yet. Connect Lichess and import your latest games.</p>
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
                <span className={`platform-badge platform-${game.platform}`}>{platformLabel(game.platform)}</span>
                {game.result.toUpperCase()} / {game.moves_count} moves / {game.processing_status}
              </span>
              <strong>{game.story.badge_label}</strong>
              <em>{game.opening_name ?? "Unknown opening"}</em>
              <small>{game.opponent_username ?? "Unknown opponent"}</small>
              {selectedGame?.id === game.id && <span className="selected-indicator">✓</span>}
            </button>
          ))
        )}
      </div>
      </section>

      {selectedGame ? (
        <details className="detail-panel">
          <summary>
            <span>Game details</span>
            <strong>{selectedGame.story.badge_label}</strong>
          </summary>
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
              <dt>Format</dt>
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
        </details>
      ) : null}

      {import.meta.env.DEV && (
        <div className="debug-controls">
          <button type="button" className="secondary debug-toggle" onClick={onToggleDebug}>
            {showDebug ? "Hide" : "Show"} debug
          </button>
        </div>
      )}

      {import.meta.env.DEV && showDebug && (
        <details className="debug-panel" open>
          <summary>
            <span>Debug tools</span>
            <strong>Development only</strong>
          </summary>
          <button type="button" className="secondary" onClick={onReprocessAllGames}>
            Reprocess all
          </button>
          {selectedGame ? (
            <button type="button" className="secondary" onClick={() => onReprocessGame(selectedGame.id)}>
              Reprocess selected story
            </button>
          ) : null}
          {selectedDebug ? (
            <div className="debug-audit">
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
        </details>
      )}
    </>
  );
}

type RecapWindow = {
  days: 1 | 2 | 7;
  label: string;
  eyebrow: string;
};

const RECAP_WINDOWS: RecapWindow[] = [
  { days: 1, label: "1 day", eyebrow: "Latest day" },
  { days: 2, label: "2 days", eyebrow: "Last 2 days" },
  { days: 7, label: "Week", eyebrow: "Last 7 days" },
];

function RecentSessionsSection({
  sessions,
  username,
  onRebuild,
  onExportWindow,
}: {
  sessions: SessionSummary[];
  username: string;
  onRebuild: () => void;
  onExportWindow: (card: SessionShareCardData) => void;
}) {
  const [selectedWindow, setSelectedWindow] = useState<RecapWindow["days"]>(1);
  const [showDetails, setShowDetails] = useState(false);
  const windowOption = RECAP_WINDOWS.find((option) => option.days === selectedWindow) ?? RECAP_WINDOWS[0];
  const recapCard = buildRecapWindowCard(sessions, windowOption, username);
  const recap = recapCard?.session ?? null;
  const selectedSessions = sessionsInWindow(sessions, windowOption.days);
  const openings = recapCard?.stats.openings ?? [];
  const ratingBreakdown = ratingBreakdownFromTracks(recapCard?.stats.rating_tracks ?? recap?.rating_tracks);

  return (
    <section className="sessions-section" aria-label="Daily Recaps">
      <div className="section-heading">
        <div>
          <p>Recap Window</p>
          <h2>{windowOption.label} recap</h2>
        </div>
        <button type="button" className="secondary compact-button" onClick={onRebuild}>
          Rebuild daily recaps
        </button>
      </div>
      <div className="recap-window-tabs" aria-label="Choose recap timeframe">
        {RECAP_WINDOWS.map((option) => (
          <button
            type="button"
            className={option.days === selectedWindow ? "is-active" : ""}
            onClick={() => {
              setSelectedWindow(option.days);
              setShowDetails(false);
            }}
            key={option.days}
          >
            <span>{option.label}</span>
            <small>{option.eyebrow}</small>
          </button>
        ))}
      </div>
      {sessions.length === 0 ? (
        <p className="empty-state">No daily recaps yet. Import games to generate daily recaps.</p>
      ) : recap === null || recapCard === null ? (
        <p className="empty-state">No games found for this timeframe yet.</p>
      ) : (
        <article className="session-card session-window-card">
          <div className="session-card-top">
            <strong>{recap.games_count} games</strong>
          </div>
          <h3>{recap.summary_headline}</h3>
          <p>{recapSummarySubheadline(recap.summary_subheadline)}</p>
          <dl className="story-facts">
            <div>
              <dt>Record</dt>
              <dd>{recordLabel(recap)}</dd>
            </div>
            <div>
              <dt>Opening</dt>
              <dd>{recap.most_common_opening ?? "Mixed openings"}</dd>
            </div>
          </dl>
          <RatingDeltaGrid rows={ratingBreakdown} />
          <div className="suggested-actions">
            <button type="button" className="compact-button" onClick={() => setShowDetails((open) => !open)}>
              {showDetails ? "Hide" : "View"} {windowOption.label} details
            </button>
            <button type="button" className="secondary compact-button" onClick={() => onExportWindow(recapCard)}>
              Export {windowOption.label} recap
            </button>
          </div>
          {showDetails ? (
            <div className="recap-window-details">
              <section aria-label="Openings in selected recap timeframe">
                <div className="recap-detail-heading">
                  <span>Openings played</span>
                  <strong>{openings.length}</strong>
                </div>
                {openings.length === 0 ? (
                  <p>No opening data found for this timeframe.</p>
                ) : (
                  <div className="recap-opening-list">
                    {openings.map((opening) => (
                      <div className="recap-opening-row" key={opening.name}>
                        <span>{opening.name}</span>
                        <small>{opening.games} game{opening.games === 1 ? "" : "s"} · {opening.record}</small>
                        <strong>{formatPercent(opening.win_rate)}</strong>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section aria-label="Daily recaps included in selected timeframe">
                <div className="recap-detail-heading">
                  <span>Days included</span>
                  <strong>{selectedSessions.length}</strong>
                </div>
                <div className="recap-day-list">
                  {selectedSessions.map((session) => (
                    <div className="recap-day-row" key={session.id}>
                      <span>{session.started_at ? formatDate(session.started_at) : "Recent day"}</span>
                      <small>{recordLabel(session)} · {session.games_count} games</small>
                      <a href={`/sessions/${encodeURIComponent(session.id)}`}>Open day</a>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : null}
        </article>
      )}
    </section>
  );
}

const FRONTEND_STORY_PRIORITY: Record<string, number> = {
  rating_milestone: 110,
  swindle: 100,
  heartbreaker: 95,
  giant_slayer: 90,
  turning_point: 85,
  clean_game: 80,
  miniature: 70,
  long_grind: 60,
  opening_win: 50,
  daily_activity: 20,
};

function buildRecapWindowCard(
  sessions: SessionSummary[],
  windowOption: RecapWindow,
  username: string,
): SessionShareCardData | null {
  const selectedSessions = sessionsInWindow(sessions, windowOption.days);
  if (selectedSessions.length === 0) return null;

  const newest = selectedSessions[0];
  const oldest = selectedSessions[selectedSessions.length - 1];
  const gamesCount = selectedSessions.reduce((total, session) => total + session.games_count, 0);
  const wins = selectedSessions.reduce((total, session) => total + session.wins_count, 0);
  const losses = selectedSessions.reduce((total, session) => total + session.losses_count, 0);
  const draws = selectedSessions.reduce((total, session) => total + session.draws_count, 0);
  const bestStory = bestStoryForSessions(selectedSessions);
  const ratingDelta = aggregateSessionRatingDelta(selectedSessions);
  const ratingTracks = aggregateSessionRatingTracks(selectedSessions);
  const openings = combineSessionOpenings(selectedSessions);
  const mostCommonOpening = openings[0]?.name ?? "Mixed openings";
  const mood = windowOption.days === 1 ? (newest.mood ?? "Daily recap") : `${windowOption.label} recap`;
  const dateRange = sessionDateRangeLabel(oldest.started_at, newest.ended_at ?? newest.started_at);
  const summaryHeadline =
    windowOption.days === 1
      ? newest.summary_headline
      : `${windowOption.label} recap: ${gamesCount} games, ${wins} wins, ${losses} losses.`;
  const summarySubheadline =
    windowOption.days === 1
      ? newest.summary_subheadline
      : `${dateRange}. Rating ${formatRatingDelta(ratingDelta)}.`;

  const summary: SessionSummary = {
    id: `window-${windowOption.days}-${newest.id}`,
    started_at: oldest.started_at,
    ended_at: newest.ended_at,
    games_count: gamesCount,
    wins_count: wins,
    losses_count: losses,
    draws_count: draws,
    win_rate: gamesCount ? wins / gamesCount : 0,
    best_story_type: bestStory,
    best_game_id: newest.best_game_id,
    best_game_story_id: newest.best_game_story_id,
    most_common_opening: mostCommonOpening,
    rating_delta: ratingDelta,
    mood,
    summary_headline: summaryHeadline,
    summary_subheadline: summarySubheadline,
    swindle_count: sumSessionCount(selectedSessions, "swindle_count"),
    heartbreaker_count: sumSessionCount(selectedSessions, "heartbreaker_count"),
    miniature_count: sumSessionCount(selectedSessions, "miniature_count"),
    long_grind_count: sumSessionCount(selectedSessions, "long_grind_count"),
    giant_slayer_count: sumSessionCount(selectedSessions, "giant_slayer_count"),
    turning_point_count: sumSessionCount(selectedSessions, "turning_point_count"),
    rating_tracks: ratingTracks,
  };

  return {
    kind: "session_recap",
    template: "session_recap_square_v1",
    player: { username },
    session: summary,
    stats: {
      record: recordLabel(summary),
      games_count: gamesCount,
      most_common_opening: mostCommonOpening,
      openings,
      rating_tracks: ratingTracks,
      rating_delta: ratingDelta,
    },
  };
}

function sessionsInWindow(sessions: SessionSummary[], days: RecapWindow["days"]): SessionSummary[] {
  const ordered = orderedSessions(sessions);
  const newest = ordered[0];
  if (!newest?.started_at) return ordered.slice(0, days);
  const newestDate = startOfLocalDay(newest.started_at);
  if (!newestDate) return ordered.slice(0, days);
  const cutoff = new Date(newestDate);
  cutoff.setDate(cutoff.getDate() - (days - 1));
  return ordered.filter((session) => {
    const sessionDate = startOfLocalDay(session.started_at);
    return sessionDate ? sessionDate >= cutoff && sessionDate <= newestDate : false;
  });
}

function orderedSessions(sessions: SessionSummary[]): SessionSummary[] {
  return [...sessions].sort((left, right) => dateTimeValue(right.started_at) - dateTimeValue(left.started_at));
}

function bestStoryForSessions(sessions: SessionSummary[]): string | null {
  const stories = sessions.map((session) => session.best_story_type).filter((value): value is string => Boolean(value));
  if (stories.length === 0) return null;
  return stories.reduce((best, story) =>
    (FRONTEND_STORY_PRIORITY[story] ?? 0) > (FRONTEND_STORY_PRIORITY[best] ?? 0) ? story : best,
  );
}

function combineSessionOpenings(sessions: SessionSummary[]): SessionOpeningSummary[] {
  const grouped = new Map<string, SessionOpeningSummary>();
  for (const session of sessions) {
    for (const opening of session.openings ?? []) {
      const item =
        grouped.get(opening.name) ??
        ({
          name: opening.name,
          games: 0,
          wins: 0,
          losses: 0,
          draws: 0,
          record: "0W - 0L - 0D",
          win_rate: 0,
        } satisfies SessionOpeningSummary);
      item.games += opening.games;
      item.wins += opening.wins;
      item.losses += opening.losses;
      item.draws += opening.draws;
      grouped.set(opening.name, item);
    }
  }
  return [...grouped.values()]
    .map((opening) => ({
      ...opening,
      record: `${opening.wins}W - ${opening.losses}L - ${opening.draws}D`,
      win_rate: opening.games ? opening.wins / opening.games : 0,
    }))
    .sort((left, right) => right.games - left.games || right.wins - left.wins || left.name.localeCompare(right.name));
}

function aggregateSessionRatingTracks(sessions: SessionSummary[]): SessionRatingTrack[] {
  const grouped = new Map<string, SessionRatingTrack[]>();
  for (const track of sessions.flatMap((session) => session.rating_tracks ?? [])) {
    const key = ratingTrackKey(track);
    grouped.set(key, [...(grouped.get(key) ?? []), track]);
  }

  return [...grouped.values()].map((group) => {
    const orderedSnapshots = group
      .flatMap((track) => [
        ratingSnapshot(track.first_rating, track.first_played_at),
        ratingSnapshot(track.last_rating, track.last_played_at),
      ])
      .filter((snapshot): snapshot is { rating: number; playedAt: number } => snapshot !== null)
      .sort((left, right) => left.playedAt - right.playedAt);
    const distinctSnapshots = orderedSnapshots.filter(
      (snapshot, index) =>
        index === 0 || snapshot.playedAt !== orderedSnapshots[index - 1].playedAt || snapshot.rating !== orderedSnapshots[index - 1].rating,
    );
    const inferredDelta =
      distinctSnapshots.length >= 2
        ? distinctSnapshots[distinctSnapshots.length - 1].rating - distinctSnapshots[0].rating
        : group.some((track) => track.inferred_delta != null)
          ? group.reduce((total, track) => total + (track.inferred_delta ?? 0), 0)
          : null;
    return {
      platform: group[0].platform,
      speed: group[0].speed,
      explicit_delta: group.reduce((total, track) => total + (track.has_explicit ? track.explicit_delta : 0), 0),
      has_explicit: group.some((track) => track.has_explicit),
      first_rating: distinctSnapshots[0]?.rating ?? null,
      last_rating: distinctSnapshots[distinctSnapshots.length - 1]?.rating ?? null,
      first_played_at: null,
      last_played_at: null,
      inferred_delta: inferredDelta,
    };
  });
}

function aggregateSessionRatingDelta(sessions: SessionSummary[]): number | null {
  const tracks = sessions.flatMap((session) => session.rating_tracks ?? []);
  if (tracks.length === 0) {
    return sessions.some((session) => session.rating_delta != null)
      ? sessions.reduce((total, session) => total + (session.rating_delta ?? 0), 0)
      : null;
  }

  const explicitDelta = tracks.reduce((total, track) => total + (track.has_explicit ? track.explicit_delta : 0), 0);
  const hasExplicit = tracks.some((track) => track.has_explicit);
  let inferredDelta = 0;
  let hasInferred = false;
  const grouped = new Map<string, SessionRatingTrack[]>();
  for (const track of tracks) {
    grouped.set(ratingTrackKey(track), [...(grouped.get(ratingTrackKey(track)) ?? []), track]);
  }
  for (const group of grouped.values()) {
    const snapshots = group
      .flatMap((track) => [
        ratingSnapshot(track.first_rating, track.first_played_at),
        ratingSnapshot(track.last_rating, track.last_played_at),
      ])
      .filter((snapshot): snapshot is { rating: number; playedAt: number } => snapshot !== null)
      .sort((left, right) => left.playedAt - right.playedAt);
    const distinctSnapshots = snapshots.filter(
      (snapshot, index) =>
        index === 0 || snapshot.playedAt !== snapshots[index - 1].playedAt || snapshot.rating !== snapshots[index - 1].rating,
    );
    if (distinctSnapshots.length >= 2) {
      inferredDelta += distinctSnapshots[distinctSnapshots.length - 1].rating - distinctSnapshots[0].rating;
      hasInferred = true;
    }
  }

  if (!hasExplicit && !hasInferred) return null;
  return explicitDelta + inferredDelta;
}

function ratingTrackKey(track: SessionRatingTrack): string {
  return `${track.platform}:${track.speed ?? ""}`;
}

function ratingSnapshot(rating?: number | null, playedAt?: string | null): { rating: number; playedAt: number } | null {
  if (rating == null || !playedAt) return null;
  const time = dateTimeValue(playedAt);
  return time ? { rating, playedAt: time } : null;
}

type RatingBreakdownRow = {
  speed: "rapid" | "blitz" | "bullet";
  lichess: number | null;
  chesscom: number | null;
};

function ratingBreakdownFromTracks(tracks: SessionRatingTrack[] | undefined): RatingBreakdownRow[] {
  return (["rapid", "blitz", "bullet"] as const).map((speed) => ({
    speed,
    lichess: combinedTrackDelta(tracks, "lichess", speed),
    chesscom: combinedTrackDelta(tracks, "chesscom", speed),
  }));
}

function combinedTrackDelta(
  tracks: SessionRatingTrack[] | undefined,
  platform: "lichess" | "chesscom",
  speed: "rapid" | "blitz" | "bullet",
): number | null {
  const matches = (tracks ?? []).filter(
    (track) => normalizeRatingPlatform(track.platform) === platform && (track.speed ?? "").toLowerCase() === speed,
  );
  if (matches.length === 0) return null;
  let total = 0;
  let hasDelta = false;
  for (const track of matches) {
    const delta = track.has_explicit ? track.explicit_delta : track.inferred_delta;
    if (delta != null) {
      total += delta;
      hasDelta = true;
    }
  }
  return hasDelta ? total : null;
}

function normalizeRatingPlatform(platform: string): "lichess" | "chesscom" | string {
  const value = platform.toLowerCase();
  if (value === "chess.com" || value === "chesscom") return "chesscom";
  return value;
}

function recapSummarySubheadline(value: string | null | undefined): string | null {
  if (!value) return null;
  const cleaned = value.replace(/\s*Best story:\s*[^.]+\.?/i, "").replace(/\s{2,}/g, " ").trim();
  return cleaned || null;
}

function sumSessionCount(sessions: SessionSummary[], key: keyof SessionSummary): number {
  return sessions.reduce((total, session) => total + Number(session[key] ?? 0), 0);
}

function sessionDateRangeLabel(start?: string | null, end?: string | null): string {
  if (!start && !end) return "Recent games";
  if (!start || start === end) return start ? formatDate(start) : formatDate(end as string);
  return `${formatDate(start)} to ${formatDate(end as string)}`;
}

function startOfLocalDay(value?: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function dateTimeValue(value?: string | null): number {
  if (!value) return 0;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? 0 : time;
}

function MobileJournalPreview({
  selectedGame,
  selectedCard,
  status,
  previewRef,
  onAnalyze,
  onExport,
  onPublish,
  onUnpublish,
  selectedTheme,
  selectedSize,
  onThemeChange,
  onSizeChange,
  onLockedThemeClick,
}: {
  selectedGame: JournalGame | null;
  selectedCard: ShareCardData | null;
  status: string;
  previewRef: RefObject<HTMLElement>;
  onAnalyze: (gameId: string) => void;
  onExport: () => void;
  onPublish: () => void;
  onUnpublish: () => void;
  selectedTheme: ShareCardTheme;
  selectedSize: ShareCardSize;
  onThemeChange: (theme: ShareCardTheme) => void;
  onSizeChange: (size: ShareCardSize) => void;
  onLockedThemeClick: () => void;
}) {
  const publishedPost = selectedGame?.published_post;
  const published = isPublished(publishedPost);

  return (
    <section className="mobile-journal-preview" ref={previewRef} aria-label="Selected card preview">
      {selectedCard ? (
        <ResponsiveShareCard card={selectedCard} theme={selectedTheme} size={selectedSize} />
      ) : (
        <div className="mobile-card-empty">Select a game to preview its story card.</div>
      )}
      <ThemeSelector selectedTheme={selectedTheme} onThemeChange={onThemeChange} onLockedThemeClick={onLockedThemeClick} />
      <SizeSelector selectedSize={selectedSize} onSizeChange={onSizeChange} />
      <div className="mobile-action-grid">
        {published && publishedPost ? (
          <>
            <a className="button-link" href={postPath(publishedPost.id)}>
              View post
            </a>
            <button type="button" className="secondary" onClick={onUnpublish}>
              Unpublish
            </button>
            <button type="button" className="secondary" onClick={onExport} disabled={!selectedCard}>
              Export PNG
            </button>
            {selectedGame && gameUrl(selectedGame) ? (
              <a className="button-link secondary-link" href={gameUrl(selectedGame)} target="_blank" rel="noreferrer">
                Open on {platformLabel(selectedGame.platform)}
              </a>
            ) : (
              <button type="button" className="secondary" disabled>
                Open game
              </button>
            )}
          </>
        ) : (
          <>
            <button
              type="button"
              className="secondary"
              onClick={() => selectedGame && onAnalyze(selectedGame.id)}
              disabled={!selectedGame}
            >
              Analyze
            </button>
            <button type="button" className="secondary" onClick={onExport} disabled={!selectedCard}>
              Export PNG
            </button>
            <button type="button" onClick={onPublish} disabled={!selectedGame?.story.id}>
              Publish
            </button>
            {selectedGame && gameUrl(selectedGame) ? (
              <a className="button-link secondary-link" href={gameUrl(selectedGame)} target="_blank" rel="noreferrer">
                Open on {platformLabel(selectedGame.platform)}
              </a>
            ) : (
              <button type="button" className="secondary" disabled>
                Open game
              </button>
            )}
          </>
        )}
      </div>
      <p className="mobile-card-status">
        {status === "Loading story card..." || status.startsWith("Analyzing") ? status : analysisStatusMessage(selectedCard)}
      </p>
    </section>
  );
}

function ResponsiveShareCard({
  card,
  theme,
  size,
}: {
  card: ShareCardData;
  theme: ShareCardTheme;
  size: ShareCardSize;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(0.32);
  const dimensions = CARD_SIZES[size];

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const updateScale = () => {
      setScale(Math.min(1, element.clientWidth / dimensions.width));
    };
    updateScale();
    const observer = new ResizeObserver(updateScale);
    observer.observe(element);
    return () => observer.disconnect();
  }, [dimensions.width]);

  return (
    <div className="responsive-card-preview" ref={containerRef}>
      <div
        className="responsive-card-stage"
        style={
          {
            "--card-scale": scale,
            "--card-width": `${dimensions.width}px`,
            "--card-height": `${dimensions.height}px`,
          } as CSSProperties
        }
      >
        <ShareCard card={card} theme={theme} size={size} />
      </div>
    </div>
  );
}

function ResponsiveSessionRecapCard({
  card,
  theme,
  size,
}: {
  card: SessionShareCardData;
  theme: ShareCardTheme;
  size: ShareCardSize;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(0.32);
  const dimensions = CARD_SIZES[size];

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const updateScale = () => {
      setScale(Math.min(1, element.clientWidth / dimensions.width));
    };
    updateScale();
    const observer = new ResizeObserver(updateScale);
    observer.observe(element);
    return () => observer.disconnect();
  }, [dimensions.width]);

  return (
    <div className="responsive-card-preview" ref={containerRef}>
      <div
        className="responsive-card-stage"
        style={
          {
            "--card-scale": scale,
            "--card-width": `${dimensions.width}px`,
            "--card-height": `${dimensions.height}px`,
          } as CSSProperties
        }
      >
        <SessionRecapCard card={card} theme={theme} size={size} />
      </div>
    </div>
  );
}

function SessionRecapCard({
  card,
  theme,
  size,
}: {
  card: SessionShareCardData;
  theme: ShareCardTheme;
  size: ShareCardSize;
}) {
  const dimensions = CARD_SIZES[size];
  const normalizedTheme = normalizeShareCardTheme(theme);
  const normalizedSize = normalizeCardSize(size);
  const session = card.session;
  const ratingBreakdown = ratingBreakdownFromTracks(card.stats.rating_tracks ?? session.rating_tracks);
  return (
    <div
      className={`session-recap-card theme-${normalizedTheme} size-${normalizedSize}`}
      style={
        {
          width: `${dimensions.width}px`,
          height: `${dimensions.height}px`,
        } as CSSProperties
      }
    >
      <div className="session-recap-brand">
        <span>Swindle</span>
        <strong>Daily Recap</strong>
      </div>
      <div className="session-recap-main">
        <h1>{session.summary_headline}</h1>
      </div>
      <dl className="session-recap-stats">
        <div>
          <dt>Record</dt>
          <dd>{card.stats.record}</dd>
        </div>
        <div>
          <dt>Games</dt>
          <dd>{card.stats.games_count}</dd>
        </div>
      </dl>
      <RatingDeltaGrid rows={ratingBreakdown} />
      <section className="session-recap-openings" aria-label="Openings played today">
        <div className="session-recap-openings-heading">
          <span>Openings today</span>
          <strong>Win rate</strong>
        </div>
        {(card.stats.openings ?? []).slice(0, 4).map((opening) => (
          <div className="session-recap-opening-row" key={opening.name}>
            <span>{opening.name}</span>
            <small>{opening.record}</small>
            <strong>{formatPercent(opening.win_rate)}</strong>
          </div>
        ))}
      </section>
      <footer>swindle.app/{card.player.username}</footer>
    </div>
  );
}

function RatingDeltaGrid({ rows }: { rows: RatingBreakdownRow[] }) {
  return (
    <section className="rating-delta-grid" aria-label="Rating changes by platform and time control">
      <div className="rating-delta-heading">
        <span>Rating +/-</span>
        <strong>Lichess</strong>
        <strong>Chess.com</strong>
      </div>
      {rows.map((row) => (
        <div className="rating-delta-row" key={row.speed}>
          <span>{row.speed}</span>
          <strong>{formatRatingDelta(row.lichess)}</strong>
          <strong>{formatRatingDelta(row.chesscom)}</strong>
        </div>
      ))}
    </section>
  );
}

function ThemeSelector({
  selectedTheme,
  onThemeChange,
  onLockedThemeClick,
}: {
  selectedTheme: ShareCardTheme;
  onThemeChange: (theme: ShareCardTheme) => void;
  onLockedThemeClick: () => void;
}) {
  return (
    <section className="theme-selector" aria-label="Card theme selector">
      <div>
        <p>Theme</p>
        <strong>{CARD_THEME_OPTIONS.find((theme) => theme.id === selectedTheme)?.name ?? "Classic"}</strong>
      </div>
      <div className="theme-options">
        {CARD_THEME_OPTIONS.map((theme) => {
          const locked = theme.tier === "premium_coming_soon";
          return (
            <button
              type="button"
              className={`theme-option ${selectedTheme === theme.id ? "is-active" : ""} ${locked ? "is-locked" : ""}`}
              key={theme.id}
              aria-disabled={locked}
              title={locked ? "Premium themes are coming soon" : theme.description}
              onClick={() => {
                if (locked) {
                  onLockedThemeClick();
                  return;
                }
                onThemeChange(theme.id);
              }}
            >
              <span>{theme.name}</span>
              {locked ? <small>Premium coming soon</small> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SizeSelector({
  selectedSize,
  onSizeChange,
}: {
  selectedSize: ShareCardSize;
  onSizeChange: (size: ShareCardSize) => void;
}) {
  const selected = CARD_SIZES[selectedSize];
  return (
    <section className="size-selector" aria-label="Card size selector">
      <div>
        <p>Size</p>
        <strong>{selected.name}</strong>
        <span>{selected.description}</span>
      </div>
      <div className="size-options">
        {CARD_SIZE_OPTIONS.map((size) => (
          <button
            type="button"
            className={`size-option ${selectedSize === size.id ? "is-active" : ""}`}
            key={size.id}
            title={size.description}
            onClick={() => onSizeChange(size.id)}
          >
            <span>{size.name}</span>
            <small>
              {size.width} x {size.height}
            </small>
          </button>
        ))}
      </div>
    </section>
  );
}

const LANDING_THEMES: ShareCardTheme[] = ["classic", "minimal", "neon_blitz", "newspaper"];

function LandingPage() {
  const [selectedTheme, setSelectedTheme] = useState<ShareCardTheme>("classic");
  const [selectedDemo, setSelectedDemo] = useState(0);
  const [lichessStatus, setLichessStatus] = useState<LichessStatus | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const selectedCard = LANDING_DEMO_CARDS[selectedDemo]?.card ?? LANDING_DEMO_CARDS[0].card;
  const connected = Boolean(lichessStatus?.connected);

  useEffect(() => {
    void getLichessStatus()
      .then(setLichessStatus)
      .catch(() => setLichessStatus(null));
  }, []);

  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <a className="landing-logo" href="/">
          Swindle
        </a>
        <button
          type="button"
          className="landing-menu-toggle"
          aria-expanded={mobileMenuOpen}
          aria-controls="landing-menu"
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          Menu
        </button>
        <div className={mobileMenuOpen ? "landing-nav-links is-open" : "landing-nav-links"} id="landing-menu">
          <a href="#example-cards">Example Cards</a>
          <a href="#how-it-works">How it Works</a>
          <a href="/feed">Feed</a>
          {connected ? (
            <>
              <a href="/journal">Journal</a>
              {lichessStatus?.platform_username ? <a href={profilePath(lichessStatus.platform_username)}>Profile</a> : null}
            </>
          ) : null}
          <button type="button" onClick={connectLichess}>
            Connect Lichess
          </button>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <p className="landing-kicker">PGNs show the moves. Swindle shows the story.</p>
          <h1>Your chess games have stories.</h1>
          <p>
            Swindle turns your Lichess games into beautiful story cards from ridiculous escapes to painful heartbreakers,
            giant-slaying wins, and long endgame grinds.
          </p>
          <div className="landing-actions">
            {connected ? (
              <a className="button-link landing-primary" href="/journal">
                Open Journal
              </a>
            ) : (
              <button type="button" className="landing-primary" onClick={connectLichess}>
                Connect Lichess
              </button>
            )}
            <a className="button-link secondary-link" href="#example-cards">
              View example cards
            </a>
          </div>
        </div>
        <div className="landing-hero-card" aria-label="Featured story card example">
          <ResponsiveShareCard card={selectedCard} theme={selectedTheme} size="square" />
        </div>
      </section>

      <section className="landing-section landing-examples" id="example-cards">
        <div className="landing-section-heading">
          <p>Example cards</p>
          <h2>See your games as stories</h2>
        </div>
        <div className="landing-theme-switcher" aria-label="Demo card theme selector">
          {LANDING_THEMES.map((theme) => (
            <button
              type="button"
              className={selectedTheme === theme ? "landing-theme is-active" : "landing-theme"}
              key={theme}
              onClick={() => setSelectedTheme(theme)}
            >
              {CARD_THEMES[theme].name}
            </button>
          ))}
        </div>
        <div className="landing-demo-layout">
          <div className="landing-demo-preview">
            <ResponsiveShareCard card={selectedCard} theme={selectedTheme} size="square" />
          </div>
          <div className="landing-demo-list">
            {LANDING_DEMO_CARDS.map((item, index) => (
              <button
                type="button"
                className={selectedDemo === index ? "landing-demo-item is-active" : "landing-demo-item"}
                key={item.name}
                onClick={() => setSelectedDemo(index)}
              >
                <span>{item.card.story.badge_label}</span>
                <strong>{item.card.story.headline}</strong>
                <small>
                  {item.card.game.result} / {item.card.game.opening} / {item.card.game.moves} moves
                </small>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section" id="how-it-works">
        <div className="landing-section-heading">
          <p>How it works</p>
          <h2>From recent games to shareable moments</h2>
        </div>
        <div className="landing-steps">
          <LandingInfoCard title="1. Connect Lichess" body="Securely connect your Lichess account and import your recent games." />
          <LandingInfoCard
            title="2. Find the story"
            body="Swindle finds giant slayers, long grinds, miniatures, swindles, heartbreakers, and turning points."
          />
          <LandingInfoCard title="3. Share the moment" body="Publish cards to your profile, share links, or download PNGs." />
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-section-heading">
          <p>Features</p>
          <h2>Built around the moments worth remembering</h2>
        </div>
        <div className="landing-feature-grid">
          {[
            "Private chess journal",
            "Suggested story-worthy games",
            "Lichess cloud eval turning points",
            "Multiple card themes",
            "Multiple export sizes",
            "Public profiles",
            "Feed, kudos, and comments",
          ].map((feature) => (
            <div className="landing-feature" key={feature}>
              {feature}
            </div>
          ))}
        </div>
      </section>

      <section className="landing-final-cta">
        <h2>Start with your latest Lichess games.</h2>
        <button type="button" onClick={connectLichess}>
          Connect Lichess
        </button>
        <p>Free to try. Lichess only for now.</p>
      </section>
    </main>
  );
}

function LandingInfoCard({ title, body }: { title: string; body: string }) {
  return (
    <article className="landing-info-card">
      <h3>{title}</h3>
      <p>{body}</p>
    </article>
  );
}

function connectLichess() {
  window.location.assign(lichessConnectUrl());
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

function SessionDetailPage({ sessionId }: { sessionId: string }) {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [status, setStatus] = useState("Loading daily recap...");
  const [selectedTheme, setSelectedTheme] = useState<ShareCardTheme>("classic");
  const [selectedSize, setSelectedSize] = useState<ShareCardSize>("square");
  const cardRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    void load();
  }, [sessionId]);

  async function load() {
    try {
      const nextDetail = await getSessionDetail(sessionId);
      setDetail(nextDetail);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load daily recap");
    }
  }

  async function handleExport() {
    if (!detail?.share_card || !cardRef.current) return;
    setStatus("Exporting daily recap...");
    try {
      await exportElementAsPng(cardRef.current, sessionExportFileName(detail.share_card, selectedTheme, selectedSize), CARD_SIZES[selectedSize]);
      setStatus("Daily recap exported");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Daily recap export failed");
    }
  }

  if (!detail) {
    return <PublicShell title="Daily recap" status={status} />;
  }

  return (
    <PublicShell title={detail.mood ?? "Daily recap"} status={status}>
      <section className="session-detail-page">
        <div className="session-detail-main">
          <header className="session-detail-hero">
            <p className="session-detail-kicker">Daily Recap</p>
            <h1>{detail.summary_headline}</h1>
            {recapSummarySubheadline(detail.summary_subheadline) ? <p>{recapSummarySubheadline(detail.summary_subheadline)}</p> : null}
          </header>
          <dl className="profile-stats session-detail-stats">
            <Stat label="Record" value={recordLabel(detail)} />
            <Stat label="Games" value={detail.games_count} />
          </dl>
          <RatingDeltaGrid rows={ratingBreakdownFromTracks(detail.rating_tracks)} />
          <section className="session-openings-detail" aria-label="Openings played today">
            <div className="section-heading">
              <div>
                <p>Openings</p>
                <h2>Opening results today</h2>
              </div>
            </div>
            <div className="session-opening-list">
              {(detail.openings ?? []).map((opening) => (
                <article className="session-opening-row" key={opening.name}>
                  <strong>{opening.name}</strong>
                  <span>{opening.games} game{opening.games === 1 ? "" : "s"}</span>
                  <span>{opening.record}</span>
                  <em>{formatPercent(opening.win_rate)}</em>
                </article>
              ))}
            </div>
          </section>
          <section className="session-games" aria-label="Games in session">
            <div className="section-heading">
              <div>
                <p>Games</p>
                <h2>{detail.games.length} games this day</h2>
              </div>
            </div>
            <div className="session-game-list">
              {detail.games.map((game) => (
                <article className="session-game-row" key={game.id}>
                  <strong>{game.result.toUpperCase()}</strong>
                  <span>{gameOpeningLabel(game)}</span>
                  <span>{game.opponent_username ?? "Unknown opponent"}</span>
                  <span>{game.moves_count ?? 0} moves</span>
                  <em>{game.story ? `${game.story.badge_label} ${game.story.badge_emoji}` : "No story"}</em>
                </article>
              ))}
            </div>
          </section>
        </div>
        <aside className="session-detail-card">
          {detail.share_card ? (
            <>
              <ResponsiveSessionRecapCard card={detail.share_card} theme={selectedTheme} size={selectedSize} />
              <ThemeSelector
                selectedTheme={selectedTheme}
                onThemeChange={setSelectedTheme}
                onLockedThemeClick={() => setStatus("Premium themes are coming soon")}
              />
              <SizeSelector selectedSize={selectedSize} onSizeChange={setSelectedSize} />
              <div className="preview-actions">
                <button type="button" className="secondary" onClick={handleExport}>
                  Export daily recap
                </button>
                <a className="button-link secondary-link" href="/journal">
                  Back to journal
                </a>
              </div>
              <div
                className="export-stage"
                aria-hidden="true"
                style={
                  {
                    "--export-width": `${CARD_SIZES[selectedSize].width}px`,
                    "--export-height": `${CARD_SIZES[selectedSize].height}px`,
                  } as CSSProperties
                }
              >
                <article ref={cardRef}>
                  <SessionRecapCard card={detail.share_card} theme={selectedTheme} size={selectedSize} />
                </article>
              </div>
            </>
          ) : (
            <p className="empty-state">Daily recap card unavailable.</p>
          )}
        </aside>
      </section>
    </PublicShell>
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
    <PublicShell title={displayName} status={status} activePage="profile" profileSlug={profileSlug}>
      <section className="profile-header">
        <div>
          <p>Public profile</p>
          <h1>{displayName}</h1>
          <span>Lichess: {profile.lichess_username ?? "Not connected"}</span>
        </div>
        <div className="profile-actions">
          {shouldShowFollowButton(profile) ? (
            <button
              type="button"
              className={profile.viewer_is_following ? "secondary" : ""}
              onClick={handleFollowToggle}
            >
              {followButtonLabel(profile)}
            </button>
          ) : (
            <button type="button" className="secondary" disabled>
              Your profile
            </button>
          )}
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
  const [profileSlug, setProfileSlug] = useState<string | null>(null);
  const [status, setStatus] = useState("Loading feed...");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [nextFeed, nextStatus] = await Promise.all([listFeed(), getLichessStatus().catch(() => null)]);
      setFeed(nextFeed);
      setProfileSlug(nextStatus?.platform_username ?? null);
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
    <PublicShell title="Feed" status={status} activePage="feed">
      <section className="feed-page" aria-label="Feed">
        {!feed ? (
          <p className="empty-state">Loading feed...</p>
        ) : feed.items.length === 0 ? (
          <div className="empty-state profile-empty">
            <strong>{FEED_EMPTY_TITLE}</strong>
            <span>{FEED_EMPTY_MESSAGE}</span>
            <div className="empty-actions">
              <a className="button-link" href="/journal">
                Go to journal
              </a>
              <a className="button-link secondary-link" href={profileSlug ? profilePath(profileSlug) : "/journal"}>
                Go to your profile
              </a>
            </div>
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
    <PublicShell title={post.headline} status={status} activePage="post">
      <section className="public-post-page">
        <div className="public-card-frame">
          {post.share_card ? (
            <ResponsiveShareCard
              card={post.share_card}
              theme={normalizeShareCardTheme(post.card_theme)}
              size={normalizeCardSize(post.card_size)}
            />
          ) : (
            <p className="empty-state">Share card unavailable.</p>
          )}
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
              View profile
            </a>
            <a className="button-link secondary-link" href="/feed">
              Feed
            </a>
            <button type="button" className="secondary" onClick={() => copyToClipboard(currentPostUrl)}>
              Copy post link
            </button>
            {post.game ? (
              <a className="button-link" href={gameUrl(post.game)} target="_blank" rel="noreferrer">
                Open on {platformLabel(post.game.platform)}
              </a>
            ) : null}
          </div>
          <section className="comments-panel" aria-label="Comments">
            <div className="comments-heading">
              <h2>Comments</h2>
              <span>{socialCountLabel(comments.length, "comment")}</span>
            </div>
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
                <textarea
                  value={commentBody}
                  placeholder="Add a comment..."
                  onChange={(event) => setCommentBody(event.target.value)}
                />
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
  const postHref = postPath(post.id);
  const boardFen = post.story?.key_position_fen ?? post.game?.final_fen;
  return (
    <article className="feed-card">
      <div className="feed-card-main">
        {boardFen ? (
          <a className="feed-card-board" href={postHref} aria-label={`Open post: ${post.headline}`}>
            <ChessBoard fen={boardFen} />
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
            <a href={postHref}>{post.headline}</a>
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
      <div className="feed-card-footer">
        <SocialActions post={post} onKudos={onKudos} postHref={postHref} />
        <a className="view-card-action" href={postHref}>
          View card
        </a>
      </div>
    </article>
  );
}

function ProfilePostCard({ post }: { post: PublishedPost }) {
  const href = profileCardHref(post.id);
  const boardFen = post.story?.key_position_fen ?? post.game?.final_fen;
  return (
    <a className="profile-post-card" href={href} aria-label={`View card: ${post.headline}`}>
      {boardFen ? (
        <div className="profile-card-board" aria-hidden="true">
          <ChessBoard fen={boardFen} />
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

function SocialActions({
  post,
  onKudos,
  postHref,
}: {
  post: Pick<PublishedPost, "kudos_count" | "comments_count" | "viewer_has_kudos">;
  onKudos: () => void;
  postHref?: string;
}) {
  return (
    <div className="social-actions">
      <button type="button" className={post.viewer_has_kudos ? "is-active" : "secondary"} onClick={onKudos}>
        <span>{kudosLabel(post)}</span>
        <strong>{post.kudos_count}</strong>
      </button>
      {postHref ? (
        <a href={postHref}>{socialCountLabel(post.comments_count, "comment")}</a>
      ) : (
        <span>{socialCountLabel(post.comments_count, "comment")}</span>
      )}
    </div>
  );
}


function PublicShell({
  title,
  status,
  activePage,
  profileSlug,
  children,
}: {
  title: string;
  status: string;
  activePage?: "profile" | "feed" | "post";
  profileSlug?: string | null;
  children?: ReactNode;
}) {
  const [lichessStatus, setLichessStatus] = useState<LichessStatus | null>(null);

  useEffect(() => {
    void getLichessStatus()
      .then(setLichessStatus)
      .catch(() => setLichessStatus(null));
  }, []);

  return (
    <main className="app-shell public-shell">
      <TopNav
        title={title}
        activePage={activePage ?? "journal"}
        lichessStatus={lichessStatus}
        fallbackProfileSlug={profileSlug}
      />
      {children}
      <p className="status">{status}</p>
    </main>
  );
}

function TopNav({
  title,
  activePage,
  lichessStatus,
  fallbackProfileSlug,
  children,
}: {
  title: string;
  activePage: "journal" | "profile" | "feed" | "post";
  lichessStatus?: LichessStatus | null;
  fallbackProfileSlug?: string | null;
  children?: ReactNode;
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const menuId = `top-nav-menu-${activePage}`;

  return (
    <nav className="top-nav">
      <div>
        <p>Swindle V1</p>
        <h1>{title}</h1>
      </div>
      <button
        type="button"
        className="top-menu-toggle"
        aria-expanded={mobileMenuOpen}
        aria-controls={menuId}
        onClick={() => setMobileMenuOpen((open) => !open)}
      >
        Menu
      </button>
      <div className={mobileMenuOpen ? "view-tabs is-open" : "view-tabs"} id={menuId}>
        {navItems(activePage, lichessStatus, fallbackProfileSlug).map((item) =>
          item.disabled ? (
            <button type="button" className={item.active ? "tab is-active" : "tab"} disabled key={item.label}>
              {item.label}
            </button>
          ) : (
            <a className={item.active ? "tab is-active" : "tab"} href={item.href} key={item.label}>
              {item.label}
            </a>
          ),
        )}
        {children}
      </div>
    </nav>
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
  | { kind: "landing" }
  | { kind: "journal" }
  | { kind: "feed" }
  | { kind: "session"; sessionId: string }
  | { kind: "profile"; username: string }
  | { kind: "post"; postId: string } {
  return routeFromPath(window.location.pathname);
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

function gameUrl(game: { platform: string; external_game_id: string }): string | undefined {
  if (!game.external_game_id) return undefined;
  if (game.platform === "chesscom") {
    return game.external_game_id.startsWith("http") ? game.external_game_id : undefined;
  }
  return `https://lichess.org/${game.external_game_id}`;
}

function platformLabel(platform?: string | null): string {
  if (platform === "chesscom") return "Chess.com";
  if (platform === "lichess") return "Lichess";
  return platform ?? "Unknown";
}

function gameOpeningLabel(game: Pick<SessionDetail["games"][number], "opening_name" | "platform">): string {
  return game.opening_name ?? `${platformLabel(game.platform)} game`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
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
        <p>Development tool</p>
        <h1>PGN demo story card</h1>
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

function exportFileName(card: ShareCardData, theme: ShareCardTheme, size: ShareCardSize): string {
  const player = slugPart(card.player.username);
  const story = slugPart(card.story.primary_story);
  return `swindle-${player}-${story}-${themeFileSlug(theme)}-${size}.png`;
}

function sessionExportFileName(card: SessionShareCardData, theme: ShareCardTheme, size: ShareCardSize): string {
  const player = slugPart(card.player.username);
  const mood = slugPart(card.session.mood ?? "session");
  return `swindle-${player}-session-${mood}-${themeFileSlug(theme)}-${size}.png`;
}

function recordLabel(session: Pick<SessionSummary, "wins_count" | "losses_count" | "draws_count">): string {
  return `${session.wins_count}W - ${session.losses_count}L - ${session.draws_count}D`;
}

function formatRatingDelta(value: number | null | undefined): string {
  if (value == null) return "None";
  if (value === 0) return "0";
  return value > 0 ? `+${value}` : String(value);
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) return "0%";
  return `${Math.round(value * 100)}%`;
}

function nextFrame(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

function slugPart(value: string | null | undefined): string {
  const cleaned = (value ?? "card")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "card";
}

function formatMaybeEval(value: number | null | undefined): string {
  if (value == null) return "None";
  return value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}
