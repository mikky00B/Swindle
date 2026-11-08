# Swindle

Swindle is a chess storytelling app. It imports a user's recent Lichess games, keeps them in a private chess journal, detects story-worthy moments, and turns selected games into polished chess activity cards.

The product is not a chess playing site and is not a Lichess/chess.com competitor. It is a social storytelling and visualization layer for games users already played.

## Current Functionality

- Account sign-up and sign-in with HttpOnly session cookies (register, login, logout, me). Login and register attempts are rate limited.
- Lichess OAuth connection with PKCE-style state handling and encrypted token storage.
- Chess.com public username linking for archive-based game import.
- Chess.com OAuth account linking, ready to activate once the registered Chess.com app is approved and its credentials are set.
- Recent game import from Lichess and Chess.com.
- Duplicate-safe game persistence by user, platform, and external game id.
- PGN parsing, final-position extraction, result detection, opening metadata, ratings, moves, and platform payload storage.
- Private journal for all imported games.
- Rule-based story generation with share-card data stored per game.
- Cloud-eval analysis runs as a background job with progress tracked via game processing status; unavailable cloud-eval positions are cached so re-analyses do not re-request them, and Lichess 429 responses trigger one backoff-and-retry before the run stops early.
- Suggested stories that can be published, ignored, or restored.
- Optional Lichess cloud-eval analysis for selected games.
- Eval caching for cloud-eval positions.
- Debug/mock eval endpoint in non-production environments.
- Daily session recaps grouped by played date.
- Session recap stats: record, win rate, mood, rating delta, common openings, best story, and story counts.
- Frontend PNG export for individual game cards and daily recap cards.
- Card theme and size selection.
- Public profiles containing published cards only.
- Public post pages.
- Pull-based feed from followed profiles.
- Follow/unfollow, kudos, and comments.
- Browser-session identity using the `X-Session-Id` header for local/demo usage.
- Prototype PGN-to-story endpoint for testing cards without importing an account.

## Accounts And Identity

The backend identifies users through an HttpOnly `swindle_session` cookie backed by server-side `auth_sessions` rows (30-day expiry). Passwords are hashed with bcrypt. Accounts can be created two ways with no separate identity systems:

- **Continue with Lichess** (`/auth/lichess/start`): one-tap sign-in/sign-up. First use creates the account from the Lichess identity and stores the encrypted Lichess token, so the account comes pre-connected.
- **Username + password**: classic register/login form on `/login`.

Identity rules:

- Production (`APP_ENV=production`) accepts only cookie identity; every journal, import, and publish endpoint returns 401 without a signed-in account.
- Outside production, the legacy `X-Session-Id` header (or the `local-dev-user` default) still works so local demos and tests keep functioning.
- Cross-origin state-changing requests with a disallowed `Origin` header are rejected as a CSRF guard on top of `SameSite=Lax` cookies.
- Public profiles expose published cards and follower counts only; the size of a user's private journal is never exposed.

Cookies are host-scoped, so the frontend canonicalizes the dev host to `http://localhost:5173` (127.0.0.1 redirects there) and proxies `/api` to the backend, keeping the session cookie first-party and same-origin.

## Product Model

Imported games are private by default. A game can become a suggested story, but it does not become public until the user publishes it.

```text
Imported game -> private journal
Interesting game -> private suggested story
User publishes -> public post, profile card, and feed item
```

Publishing stores the selected card theme and card size. Unpublishing changes the post visibility instead of deleting the original game or story.

## Supported Sources

### Lichess

Lichess uses OAuth.

The backend stores encrypted access tokens and fetches recent games from the Lichess API. Imports request PGN, opening data, clock data, and metadata. Users can disconnect Lichess.

### Chess.com

Chess.com uses public profile and archive APIs.

Users link a Chess.com username, then the backend fetches recent public archive games. Games without PGN are skipped. Chess.com linking does not store OAuth tokens because the integration uses public data.

## Story Engine

The story processor is deterministic and template-based. It uses parsed game metadata by default, and can use eval metrics when a game is analyzed.

Current story types include:

- `rating_milestone`
- `swindle`
- `heartbreaker`
- `turning_point`
- `giant_slayer`
- `clean_game`
- `miniature`
- `long_grind`
- `daily_activity`

Story output includes:

- primary and secondary story labels
- badge label and badge emoji
- headline and optional subheadline
- key move metadata
- key position FEN
- interesting score
- confidence score
- reasons
- share-card payload

Suggested stories are based on interesting score. The social layer only shows public published posts.

## Share Cards

Share cards are rendered in React and exported as PNG in the browser with `html-to-image`.

Supported card sizes:

- `square`: 1080 x 1080
- `story`: 1080 x 1920
- `portrait`: 1080 x 1350
- `landscape`: 1200 x 628

Free themes:

- Classic
- Minimal
- Neon Blitz
- Newspaper

Premium-coming-soon themes are present in the UI model but normalize back to Classic when publishing/exporting:

- Tournament Poster
- Dark Glass
- Retro Board
- Luxury Gold

## Daily Recaps

Sessions are daily recaps built from imported games with `played_at` timestamps. Lichess and Chess.com games can appear in the same daily recap.

Daily recaps compute:

- games played
- wins, losses, draws, and win rate
- rating delta where available or inferable
- most common opening
- opening breakdown
- best story of the day
- mood such as `Clean climb`, `Tilt day`, or `Chaos survived`
- story counts for swindles, heartbreakers, miniatures, long grinds, giant slayers, and turning points

Recaps can be rebuilt and exported as PNG cards.

## Frontend Routes

```text
/                  landing page
/journal           private journal, imports, story cards, exports, debug data
/sessions/:id      private daily recap detail
/feed              followed-users feed
/profile/:username public profile
/p/:post_id        public post page
```

The journal screen is the main workspace. It includes account connection controls, Lichess and Chess.com imports, journal filtering/search, suggested stories, session recaps, card preview, export controls, publish/unpublish actions, reprocessing, cloud analysis, and optional debug details.

## Repository Structure

```text
backend/
  app/
    core/                    config, database, security
    games/                   PGN parsing, imports, cloud eval, repository helpers, game routes
    integrations/lichess/    Lichess OAuth, token storage, API integration
    integrations/chesscom/   Chess.com public profile/archive integration
    publishing/              public profiles, posts, feed, follows, kudos, comments
    sessions/                daily recap grouping, stats, share-card data
    share_cards/             share-card response schemas
    story/                   detectors, scoring, templates, story routes
    prototype/               PGN-to-story development endpoint
  alembic/                   database migrations
  tests/                     backend tests

frontend/
  src/
    components/cards/        share card, story badge, metrics grid
    components/chess/        board renderer
    data/                    landing/demo cards
    lib/                     API client, export, chess, themes, journal, social helpers
    App.tsx                  routes and screens
  test/                      TypeScript helper tests
```

## Environment

Copy `.env.example` to `.env` and replace placeholders:

```powershell
Copy-Item .env.example .env
```

Important variables:

- `DATABASE_URL`: PostgreSQL connection string.
- `REDIS_URL`: reserved for queued work / worker deployment.
- `APP_SECRET_KEY`: application secret.
- `JWT_SECRET_KEY`: auth token secret placeholder.
- `FRONTEND_ORIGIN`: frontend origin used for CORS and OAuth redirects.
- `CORS_ALLOWED_ORIGINS`: comma-separated frontend origins.
- `LICHESS_CLIENT_ID`: Lichess OAuth client id.
- `LICHESS_REDIRECT_URI`: backend OAuth callback URL.
- `LICHESS_SCOPES`: requested Lichess scopes.
- `LICHESS_API_BASE_URL`: Lichess API base URL.
- `CHESSCOM_API_BASE_URL`: Chess.com public API base URL.
- `CHESSCOM_CLIENT_ID` / `CHESSCOM_CLIENT_SECRET`: Chess.com OAuth app credentials. When both are set, Chess.com account linking via OAuth is offered in the journal.
- `CHESSCOM_REDIRECT_URI`: Chess.com OAuth callback URL (registered as `https://swindle.clevermike.studio/api/v1/integrations/chesscom/callback` in production).
- `TOKEN_ENCRYPTION_KEY`: Fernet key for Lichess OAuth token encryption.
- `VITE_API_BASE`: frontend API base URL.

Generate a local Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Local Development

Backend:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

Local URLs:

```text
Frontend:    http://localhost:5173   (canonical host; 127.0.0.1 redirects here)
Backend API: http://127.0.0.1:8000
Health:      http://127.0.0.1:8000/health/live
```

In development the frontend proxies `/api` to the backend (same-origin), so no `VITE_API_BASE` is needed for local runs.

## Verification

Backend tests:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

Frontend build and tests:

```powershell
cd frontend
npm run build
npm run test
```

Frontend test scripts are split by area:

```text
npm run test:chess
npm run test:journal
npm run test:cards
npm run test:themes
npm run test:landing
npm run test:public
npm run test:social
npm run test:sessions
```

## API Surface

Core endpoints use `/api/v1`.

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
GET  /api/v1/auth/lichess/start

GET  /api/v1/integrations/lichess/connect
GET  /api/v1/integrations/lichess/connect-url
GET  /api/v1/integrations/lichess/callback
GET  /api/v1/integrations/lichess/status
POST /api/v1/integrations/lichess/disconnect

GET  /api/v1/integrations/chesscom/connect
GET  /api/v1/integrations/chesscom/callback
POST /api/v1/integrations/chesscom/link
GET  /api/v1/integrations/chesscom/status
POST /api/v1/integrations/chesscom/disconnect

GET  /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/import/lichess
POST /api/v1/games/import/chesscom
POST /api/v1/games/reprocess-all
POST /api/v1/games/{game_id}/process
POST /api/v1/games/{game_id}/analyze
GET  /api/v1/games/{game_id}/share-card
GET  /api/v1/games/{game_id}/debug
POST /api/v1/games/{game_id}/debug-eval

GET  /api/v1/stories/suggested
POST /api/v1/stories/reset-ignored
POST /api/v1/stories/{story_id}/publish
POST /api/v1/stories/{story_id}/ignore

GET  /api/v1/sessions
POST /api/v1/sessions/rebuild
GET  /api/v1/sessions/{session_id}
GET  /api/v1/sessions/{session_id}/share-card

GET    /api/v1/profiles/{username}
GET    /api/v1/profiles/{username}/posts
POST   /api/v1/profiles/{username}/follow
DELETE /api/v1/profiles/{username}/follow
GET    /api/v1/profiles/{username}/followers
GET    /api/v1/profiles/{username}/following

GET    /api/v1/feed
GET    /api/v1/posts/{post_id}
POST   /api/v1/posts/{post_id}/unpublish
POST   /api/v1/posts/{post_id}/kudos
DELETE /api/v1/posts/{post_id}/kudos
GET    /api/v1/posts/{post_id}/comments
POST   /api/v1/posts/{post_id}/comments
DELETE /api/v1/comments/{comment_id}

POST /api/v1/prototype/pgn-story
```

## Persistence

The database currently stores:

- users
- OAuth states
- chess accounts
- imported games
- game metrics
- game stories
- suggested posts
- eval cache
- published posts
- daily game sessions and session-game links
- follows
- kudos
- comments

Migrations live in `backend/alembic/versions`.

## Privacy And Publishing Rules

- Imported games are private journal entries.
- Suggested posts are private until published.
- Ignored suggestions can be restored.
- Published posts appear on public profiles and in follower feeds.
- Unpublished posts no longer appear publicly.
- Public profiles do not expose private journal entries.
- Chess.com imports use public archive data only.
- Lichess tokens are encrypted at rest and are not returned by API responses.

## Deployment Notes

The app is shaped for a small VPS or container deployment:

- PostgreSQL
- FastAPI backend served by Uvicorn or Gunicorn/Uvicorn
- Vite frontend built as static files
- Nginx reverse proxy
- Redis reserved for worker-backed jobs as the app grows

Deployment checklist:

1. Set production environment values outside the repository. `APP_ENV=production` makes the backend refuse to start while `TOKEN_ENCRYPTION_KEY` or `LICHESS_CLIENT_ID` still use their development defaults.
2. Run `alembic upgrade head` before starting the backend.
3. Build the frontend with `VITE_API_BASE` pointed at the deployed API.
4. Serve `frontend/dist` through Nginx or another static host.
5. Proxy `/api` traffic to the backend service.
6. Configure the Lichess OAuth redirect URI to match production.
7. Keep `TOKEN_ENCRYPTION_KEY`, app secrets, OAuth settings, and database credentials out of git.
