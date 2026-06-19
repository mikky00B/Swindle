from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class ChessComClientError(ValueError):
    pass


class ChessComNotFound(ChessComClientError):
    pass


class ChessComUnavailable(ChessComClientError):
    pass


class ChessComClient:
    def __init__(self, *, timeout: int = 20) -> None:
        self.timeout = timeout

    async def get_player(self, username: str) -> dict[str, Any]:
        return await self._get_json(f"/player/{_clean_username(username)}")

    async def get_archives(self, username: str) -> list[str]:
        payload = await self._get_json(f"/player/{_clean_username(username)}/games/archives")
        archives = payload.get("archives")
        if not isinstance(archives, list):
            raise ChessComUnavailable("Chess.com archives response was malformed.")
        return [item for item in archives if isinstance(item, str)]

    async def get_games_from_archive(self, archive_url: str) -> list[dict[str, Any]]:
        payload = await self._get_json_url(archive_url)
        games = payload.get("games")
        if not isinstance(games, list):
            raise ChessComUnavailable("Chess.com archive response was malformed.")
        return [item for item in games if isinstance(item, dict)]

    async def get_latest_games(self, username: str, limit: int = 20) -> list[dict[str, Any]]:
        archives = await self.get_archives(username)
        if not archives:
            return []
        games: list[dict[str, Any]] = []
        for archive_url in reversed(archives):
            archive_games = await self.get_games_from_archive(archive_url)
            games.extend(reversed(archive_games))
            if len(games) >= limit:
                break
        return games[:limit]

    async def _get_json(self, path: str) -> dict[str, Any]:
        return await self._get_json_url(chesscom_api_url(path))

    async def _get_json_url(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            try:
                response = await client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise ChessComNotFound("Chess.com username not found.") from exc
                if status == 429:
                    raise ChessComUnavailable("Chess.com API rate limit reached. Wait a moment before importing again.") from exc
                raise ChessComUnavailable(f"Chess.com API request failed with status {status}.") from exc
            except httpx.HTTPError as exc:
                raise ChessComUnavailable("Could not reach Chess.com. Check your connection and try again.") from exc
            data = response.json()
            if not isinstance(data, dict):
                raise ChessComUnavailable("Chess.com API response was malformed.")
            return data


def chesscom_api_url(path: str) -> str:
    base = get_settings().chesscom_api_base_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _clean_username(username: str) -> str:
    value = username.strip()
    if not value:
        raise ChessComClientError("Chess.com username is required.")
    return value
