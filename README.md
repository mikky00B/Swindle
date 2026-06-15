# Swindle

Swindle is a Lichess-first chess storytelling app. V1 turns imported chess games into private journal entries, suggests the most story-worthy ones, and renders shareable chess cards.

This repository currently contains the Milestone 1, 2, and 2.5 foundation:

- FastAPI backend endpoint for pasted PGNs.
- Rule-based story processor with metadata and optional metric inputs.
- React share-card prototype with PNG export.
- Lichess OAuth Authorization Code + PKCE connect flow.
- PostgreSQL-backed persistence for users, connected Lichess accounts, games, game stories, game metrics, and share-card data.
- Latest Lichess game import with deduplication and missing-field handling.
- Imported games can be opened as share-card data.
- Imported games can be manually reprocessed without duplicating story records.

## Local Ports

Use these ports for local development:

```text
Backend API: http://127.0.0.1:8000
Frontend:    http://127.0.0.1:5173
```

Port `8000` is the standard backend port. The earlier `8001` server was temporary during development and has been stopped.

## Backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

The app reads PostgreSQL from `DATABASE_URL` in the root `.env`. See `.env.example` for the expected local environment variables. Because the backend uses sync SQLAlchemy sessions, prefer `postgresql+psycopg://...`; `postgresql+asyncpg://...` is normalized to `psycopg` at runtime.

If you started the backend before running Alembic and tables already exist, baseline the current schema once:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic stamp head
```

After that, use `alembic upgrade head` for normal migrations.
The frontend defaults to `http://localhost:8000/api/v1`; set `VITE_API_BASE=http://127.0.0.1:8000/api/v1` if you want it explicit.

API:

```http
POST /api/v1/prototype/pgn-story
GET  /api/v1/integrations/lichess/connect
GET  /api/v1/integrations/lichess/callback
GET  /api/v1/integrations/lichess/status
POST /api/v1/integrations/lichess/disconnect
POST /api/v1/games/import/lichess
GET  /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/process
GET  /api/v1/games/{game_id}/share-card
```

Required Lichess env vars are listed in `.env.example`. For local development, `LICHESS_REDIRECT_URI` should point to the backend callback URL and `FRONTEND_ORIGIN` should point to the Vite dev server.

## Frontend

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

The frontend has two views:

- Journal: connect Lichess, import latest games, open imported games as story cards.
- PGN demo: keep using the original paste-PGN prototype.
