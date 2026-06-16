# Swindle

Swindle is a Lichess-first chess storytelling app. V1 turns recent Lichess games into a private chess journal, detects story-worthy moments, renders shareable chess activity cards, and lets users publish selected cards to a simple social feed.

Swindle is not a chess playing site and does not compete with Lichess. It is a lightweight story and visualization layer for games users already played.

## V1 Features

- Lichess OAuth connection.
- Recent game import with deduplication.
- Private chess journal for imported games.
- Rule-based story processor with metadata and optional Lichess cloud evaluation data.
- Suggested story-worthy games without auto-publishing.
- 1080 x 1080 share-card preview and PNG export.
- Public profile with published cards only.
- Pull-based feed from followed users.
- Follow/unfollow, kudos, and comments on public posts.

Out of scope for V1: Chess.com, payments, push notifications, recommendations, mobile apps, and complex feed fan-out.

## Repository Structure

```text
backend/
  app/
    core/                 config, database, security
    games/                import, PGN parsing, game routes
    integrations/lichess/ Lichess OAuth and API integration
    publishing/           public profiles, posts, feed, social actions
    story/                story detection, scoring, templates
    prototype/            development PGN story endpoint
  alembic/                database migrations
  tests/                  backend tests

frontend/
  src/
    components/           share cards and chess board rendering
    lib/                  API, export, chess, journal, social helpers
    App.tsx               V1 application screens
  test/                   lightweight TypeScript helper tests
```

The PGN demo is kept as a development tool for testing story-card generation without importing a Lichess account.

## Environment

Copy `.env.example` to `.env` and set real values:

```powershell
Copy-Item .env.example .env
```

Important variables:

- `DATABASE_URL`: PostgreSQL connection string. Use `postgresql+psycopg://...` for the sync SQLAlchemy app.
- `FRONTEND_ORIGIN`: frontend origin allowed by CORS and OAuth redirects, usually `http://127.0.0.1:5173`.
- `CORS_ALLOWED_ORIGINS`: comma-separated local or deployed frontend origins.
- `LICHESS_CLIENT_ID`: Lichess OAuth client id.
- `LICHESS_REDIRECT_URI`: backend callback, usually `/api/v1/integrations/lichess/callback`.
- `TOKEN_ENCRYPTION_KEY`: Fernet key for encrypted OAuth token storage.
- `VITE_API_BASE`: frontend API base, usually `http://127.0.0.1:8000/api/v1`.

Generate a local token encryption key:

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
Health:      http://127.0.0.1:8000/health/live
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
npm run test:chess
npm run test:journal
npm run test:cards
npm run test:public
npm run test:social
```

## API Surface

Core endpoints use `/api/v1`.

```http
GET  /health/live

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

GET  /api/v1/stories/suggested
POST /api/v1/stories/{story_id}/publish
POST /api/v1/stories/{story_id}/ignore

GET    /api/v1/profiles/{username}
GET    /api/v1/profiles/{username}/posts
POST   /api/v1/profiles/{username}/follow
DELETE /api/v1/profiles/{username}/follow
GET    /api/v1/profiles/{username}/followers
GET    /api/v1/profiles/{username}/following

GET  /api/v1/feed
GET  /api/v1/posts/{post_id}
POST /api/v1/posts/{post_id}/unpublish
POST /api/v1/posts/{post_id}/kudos
DELETE /api/v1/posts/{post_id}/kudos
GET  /api/v1/posts/{post_id}/comments
POST /api/v1/posts/{post_id}/comments
DELETE /api/v1/comments/{comment_id}
```

## Deployment Notes

The V1 app is deployment-ready for a single VPS or small container setup:

- PostgreSQL
- FastAPI backend served by Uvicorn or Gunicorn/Uvicorn
- Vite frontend built as static files
- Nginx reverse proxy
- Redis reserved for future background workers

Deployment checklist:

1. Set production `.env` values outside the repository.
2. Run `alembic upgrade head` before starting the backend.
3. Build the frontend with `VITE_API_BASE` pointed at the deployed API.
4. Serve `frontend/dist` through Nginx or another static host.
5. Proxy `/api` traffic to the backend service.
6. Configure the Lichess OAuth app redirect URI to match production.
7. Keep `TOKEN_ENCRYPTION_KEY`, app secrets, and database credentials out of git.

## Privacy Rules

- Imported games remain private journal entries.
- Suggested posts are private until the user publishes.
- Feed shows only public published posts from followed users.
- Ignored suggestions and unpublished posts do not appear publicly.
- Kudos and comments only work on public posts.
