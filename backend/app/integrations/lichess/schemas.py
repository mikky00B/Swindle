from pydantic import BaseModel


class LichessStatus(BaseModel):
    connected: bool
    platform: str = "lichess"
    platform_username: str | None = None
    platform_user_id: str | None = None
    scopes: list[str] = []
    connected_at: str | None = None


class DisconnectResponse(BaseModel):
    disconnected: bool


class LichessImportResponse(BaseModel):
    imported: int
    duplicates: int
    skipped: int = 0
    total_seen: int
    errors: list[str] = []
