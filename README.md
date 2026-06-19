# Swindle

Swindle is a Lichess-first chess storytelling app. It imports a user's recent Lichess games, keeps them in a private chess journal, detects story-worthy moments, and turns selected games into polished chess activity cards.

The product is not a chess playing site and is not a Lichess competitor. It is a social storytelling and visualization layer for games users already played.

## V1 Promise

Connect your Lichess account and turn your most interesting games into beautiful chess story cards.

V1 focuses on:

- Lichess OAuth connection.
- Recent Lichess game import.
- Private chess journal for all imported games.
- PGN parsing and normalized game storage.
- Rule-based story generation.
- Suggested share-worthy posts that stay private until published.
- In-app story cards and PNG share-card export.
- Public profile, pull-based feed, follows, kudos, and comments.

Out of scope for V1:

- Chess.com integration.
- Mobile apps.
- Payments or subscriptions.
- Push notifications.
- Real-time Lichess streaming.
- Global leaderboards.
- Tournament features.
- Game playing inside Swindle.
- Deep Stockfish analysis for every imported game.

## Product Rules

- Imported games always start as private journal entries.
- Story-worthy games become private suggestions, not public posts.
- Users explicitly choose what to publish.
- Public profiles expose published posts only.
- Share-card PNG export is rendered by the frontend from stable card data.
- Lichess tokens must be encrypted at rest and never exposed to the frontend.

## Repository Structure

```text
backend/
  app/
    core/                 config, database, security
    games/                import, PGN parsing, game routes
    integrations/lichess/ Lichess OAuth and API integration
    publishing/           public profiles, posts, feed, social actions
    sessions/             private session recaps and share-card data
    share_cards/          share-card response schemas and services
    story/                story detection, scoring, templates
    prototype/            development PGN story endpoint
  alembic/                database migrations
  tests/                  backend tests

frontend/
  src/
    components/           chess boards, feed cards, share cards
    lib/                  API, export, chess, journal, social helpers
    App.tsx               V1 application screens
  test/                   TypeScript helper tests
```

## Story Engine

The story processor turns game data into structured story objects. It starts with deterministic rules so V1 remains fast, cheap, and testable.

Minimum V1 story types:

- `giant_slayer`
- `swindle`
- `heartbreaker`
- `clean_game`
- `miniature`
- `long_grind`
- `rating_milestone`

Suggested posts are created when a story is interesting enough, but they are not auto-published.

## Environment

Copy `.env.example` to `.env` and replace placeholders:

```powershell
Copy-Item .env.example .env
```

Important variables:

- `DATABASE_URL`: PostgreSQL connection string.
- `REDIS_URL`: Redis connection string for queued work.
- `APP_SECRET_KEY`: application secret.
- `JWT_SECRET_KEY`: auth token secret.
- `FRONTEND_ORIGIN`: frontend origin allowed by CORS and redirects.
- `CORS_ALLOWED_ORIGINS`: comma-separated frontend origins.
- `LICHESS_CLIENT_ID`: Lichess OAuth client id.
- `LICHESS_REDIRECT_URI`: backend OAuth callback URL.
- `TOKEN_ENCRYPTION_KEY`: Fernet key for OAuth token encryption.
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
Frontend:    http://127.0.0.1:5173
Backend API: http://127.0.0.1:8000
```

Primary frontend routes:

```text
/                  landing page
/journal           private journal and share-card workspace
/sessions/:id      private session recap detail
/feed              public feed
/profile/:username public profile
/p/:post_id        public post page
```

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

## API Surface

Core endpoints use `/api/v1`.

```http
GET  /api/v1/integrations/lichess/connect
GET  /api/v1/integrations/lichess/connect-url
GET  /api/v1/integrations/lichess/callback
GET  /api/v1/integrations/lichess/status
POST /api/v1/integrations/lichess/disconnect

POST /api/v1/games/import/lichess
GET  /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/process
POST /api/v1/games/{game_id}/analyze
GET  /api/v1/games/{game_id}/share-card

GET  /api/v1/sessions
GET  /api/v1/sessions/{session_id}
POST /api/v1/sessions/rebuild
GET  /api/v1/sessions/{session_id}/share-card

GET  /api/v1/stories/suggested
PATCH /api/v1/stories/{story_id}
POST /api/v1/stories/{story_id}/publish
POST /api/v1/stories/{story_id}/ignore

GET    /api/v1/profiles/{username}
GET    /api/v1/profiles/{username}/posts
POST   /api/v1/profiles/{username}/follow
DELETE /api/v1/profiles/{username}/follow
GET    /api/v1/profiles/{username}/followers
GET    /api/v1/profiles/{username}/following

GET    /api/v1/feed
GET    /api/v1/posts/{post_id}
PATCH  /api/v1/posts/{post_id}
POST   /api/v1/posts/{post_id}/unpublish
POST   /api/v1/posts/{post_id}/kudos
DELETE /api/v1/posts/{post_id}/kudos
GET    /api/v1/posts/{post_id}/comments
POST   /api/v1/posts/{post_id}/comments
DELETE /api/v1/comments/{comment_id}
```

## Deployment Notes

V1 should be deployable on a VPS or small container setup:

- PostgreSQL
- Redis
- FastAPI backend served by Uvicorn or Gunicorn/Uvicorn
- Background worker for imports and story processing
- Vite frontend built as static files
- Nginx reverse proxy

Deployment checklist:

1. Set production environment values outside the repository.
2. Run `alembic upgrade head` before starting the backend.
3. Build the frontend with `VITE_API_BASE` pointed at the deployed API.
4. Serve `frontend/dist` through Nginx or another static host.
5. Proxy `/api` traffic to the backend service.
6. Configure the Lichess OAuth redirect URI to match production.
7. Keep `TOKEN_ENCRYPTION_KEY`, app secrets, and database credentials out of git.

## Privacy Rules

- Imported games remain private journal entries.
- Suggested posts remain private until the user publishes.
- Feed shows only public published posts from followed users.
- Ignored suggestions and unpublished posts do not appear publicly.
- Kudos and comments apply to public posts.
