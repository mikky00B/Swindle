from pydantic import BaseModel


class GameStory(BaseModel):
    primary_story: str
    secondary_story: str | None = None
    badge_label: str
    badge_emoji: str
    headline: str
    subheadline: str | None = None
    caption: str | None = None
    mood: str | None = None
    key_move_number: int | None = None
    key_position_fen: str | None = None
    key_move_san: str | None = None
    key_move_from: str | None = None
    key_move_to: str | None = None
    template_key: str
    interesting_score: float
    confidence_score: float
    reasons: list[str]
