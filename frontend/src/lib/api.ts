import type {
  GameDebug,
  FeedResponse,
  ImportResponse,
  JournalGame,
  LichessStatus,
  PostComment,
  PublicProfile,
  PublishedPost,
  SessionDetail,
  SessionShareCardData,
  SessionSummary,
  ShareCardData,
  SocialCounts,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";
const SESSION_STORAGE_KEY = "swindle-session-id";

// Keep one browser identity across tabs and OAuth redirects.
function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);
  }
  if (!sessionId) {
    sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}

// Add session header to all requests
function makeHeaders(additional: Record<string, string> = {}): Record<string, string> {
  return {
    "X-Session-Id": getSessionId(),
    ...additional,
  };
}

export async function createStoryFromPgn(pgn: string, username: string): Promise<ShareCardData> {
  const response = await fetch(`${API_BASE}/prototype/pgn-story`, {
    method: "POST",
    headers: makeHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      pgn,
      username,
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Could not generate story");
  }

  return response.json();
}

export function lichessConnectUrl(): string {
  return `${API_BASE}/integrations/lichess/connect?session_id=${encodeURIComponent(getSessionId())}`;
}

export async function getLichessStatus(): Promise<LichessStatus> {
  const response = await fetch(`${API_BASE}/integrations/lichess/status`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load Lichess status");
}

export async function disconnectLichess(): Promise<void> {
  const response = await fetch(`${API_BASE}/integrations/lichess/disconnect`, {
    method: "POST",
    headers: makeHeaders(),
  });
  await readJson(response, "Could not disconnect Lichess");
}

export async function importLatestLichessGames(): Promise<ImportResponse> {
  const response = await fetch(`${API_BASE}/games/import/lichess`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not import Lichess games");
}

export async function listJournalGames(): Promise<JournalGame[]> {
  const response = await fetch(`${API_BASE}/games`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load journal");
}

export async function listSuggestedStories(): Promise<JournalGame[]> {
  const response = await fetch(`${API_BASE}/stories/suggested`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load suggested stories");
}

export async function ignoreSuggestedStory(storyId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/stories/${storyId}/ignore`, {
    method: "POST",
    headers: makeHeaders(),
  });
  await readJson(response, "Could not ignore suggestion");
}

export async function resetIgnoredSuggestions(): Promise<{ restored: number }> {
  const response = await fetch(`${API_BASE}/stories/reset-ignored`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not reset ignored suggestions");
}

export async function publishStoryCard(storyId: string, cardTheme = "classic", cardSize = "square"): Promise<PublishedPost> {
  const response = await fetch(`${API_BASE}/stories/${storyId}/publish`, {
    method: "POST",
    headers: makeHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ card_theme: cardTheme, card_size: cardSize }),
  });
  return readJson(response, "Could not publish card");
}

export async function unpublishStoryPost(postId: string): Promise<{ id: string; visibility: string; unpublished: boolean }> {
  const response = await fetch(`${API_BASE}/posts/${postId}/unpublish`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not unpublish card");
}

export async function getPublicProfile(username: string): Promise<PublicProfile> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(username)}`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load public profile");
}

export async function getPublicPost(postId: string): Promise<PublishedPost> {
  const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load public post");
}

export async function followProfile(username: string): Promise<{ following: boolean; followers_count: number }> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(username)}/follow`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not follow profile");
}

export async function unfollowProfile(username: string): Promise<{ following: boolean; followers_count: number }> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(username)}/follow`, {
    method: "DELETE",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not unfollow profile");
}

export async function listFeed(): Promise<FeedResponse> {
  const response = await fetch(`${API_BASE}/feed`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load feed");
}

export async function addKudos(postId: string): Promise<SocialCounts> {
  const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}/kudos`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not add kudos");
}

export async function removeKudos(postId: string): Promise<SocialCounts> {
  const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}/kudos`, {
    method: "DELETE",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not remove kudos");
}

export async function listComments(postId: string): Promise<PostComment[]> {
  const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}/comments`);
  return readJson(response, "Could not load comments");
}

export async function addComment(postId: string, body: string): Promise<PostComment> {
  const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}/comments`, {
    method: "POST",
    headers: makeHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ body }),
  });
  return readJson(response, "Could not add comment");
}

export async function getImportedGameShareCard(gameId: string): Promise<ShareCardData> {
  const response = await fetch(`${API_BASE}/games/${gameId}/share-card`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not open imported game");
}

export async function getJournalGameDetail(gameId: string): Promise<JournalGame> {
  const response = await fetch(`${API_BASE}/games/${gameId}`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load game detail");
}

export async function reprocessJournalGame(gameId: string): Promise<JournalGame> {
  const response = await fetch(`${API_BASE}/games/${gameId}/process`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not reprocess game");
}

export async function analyzeJournalGame(gameId: string): Promise<JournalGame> {
  const response = await fetch(`${API_BASE}/games/${gameId}/analyze`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not analyze game");
}

export async function reprocessAllJournalGames(): Promise<{ processed: number }> {
  const response = await fetch(`${API_BASE}/games/reprocess-all`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not reprocess imported games");
}

export async function getJournalGameDebug(gameId: string): Promise<GameDebug> {
  const response = await fetch(`${API_BASE}/games/${gameId}/debug`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load debug data");
}

export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE}/sessions`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load recent sessions");
}

export async function rebuildSessions(): Promise<{ sessions: number }> {
  const response = await fetch(`${API_BASE}/sessions/rebuild`, {
    method: "POST",
    headers: makeHeaders(),
  });
  return readJson(response, "Could not rebuild sessions");
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load session recap");
}

export async function getSessionShareCard(sessionId: string): Promise<SessionShareCardData> {
  const response = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/share-card`, {
    headers: makeHeaders(),
  });
  return readJson(response, "Could not load session recap card");
}

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? fallback);
  }
  return response.json();
}
