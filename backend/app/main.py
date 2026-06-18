from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.games.routes import router as games_router
from app.integrations.lichess.routes import router as lichess_router
from app.publishing.routes import router as publishing_router
from app.sessions.routes import router as sessions_router
from app.prototype.routes import router as prototype_router
from app.story.routes import router as story_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prototype_router, prefix=settings.api_v1_prefix)
app.include_router(lichess_router, prefix=settings.api_v1_prefix)
app.include_router(games_router, prefix=settings.api_v1_prefix)
app.include_router(story_router, prefix=settings.api_v1_prefix)
app.include_router(publishing_router, prefix=settings.api_v1_prefix)
app.include_router(sessions_router, prefix=settings.api_v1_prefix)


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}
