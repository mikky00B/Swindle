from datetime import datetime

from pydantic import BaseModel, Field


class ParsedGame(BaseModel):
    pgn: str
    white_username: str | None = None
    black_username: str | None = None
    user_color: str | None = None
    opponent_username: str | None = None
    result: str
    winner_color: str | None = None
    termination: str | None = None
    rated: bool | None = None
    speed: str | None = None
    time_control: str | None = None
    opening_name: str | None = None
    opening_eco: str | None = None
    moves_count: int = 0
    user_rating_before: int | None = None
    user_rating_after: int | None = None
    opponent_rating: int | None = None
    rating_change: int | None = None
    played_at: datetime | None = None
    final_fen: str | None = None


class GameMetrics(BaseModel):
    accuracy: float | None = None
    lowest_eval: float | None = None
    highest_eval: float | None = None
    biggest_eval_swing: float | None = None
    turning_point_move: int | None = None
    blunders_count: int | None = None
    mistakes_count: int | None = None
    inaccuracies_count: int | None = None
    captures_count: int | None = None
    checks_count: int | None = None
    user_lowest_clock_seconds: int | None = None
    moves_under_time_pressure: int | None = None
    eval_curve: list[float] | None = None
    analysis_depth: int | None = None
    analysis_source: str = "metadata_only"


class PgnStoryRequest(BaseModel):
    pgn: str = Field(min_length=1)
    username: str | None = None
    metrics: GameMetrics | None = None
