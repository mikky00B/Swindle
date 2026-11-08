from pydantic import BaseModel


class ChessComLinkRequest(BaseModel):
    username: str


class ChessComStatus(BaseModel):
    connected: bool
    platform: str = "chesscom"
    platform_username: str | None = None
    platform_user_id: str | None = None
    last_synced_at: str | None = None
    connected_at: str | None = None
    oauth_enabled: bool = False


class ChessComLinkResponse(ChessComStatus):
    pass


class DisconnectResponse(BaseModel):
    disconnected: bool
