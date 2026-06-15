import chess
from pydantic import BaseModel

from app.games.schemas import GameMetrics, ParsedGame
from app.story.schemas import GameStory

STARTING_FEN = chess.STARTING_FEN


class ShareCardPlayer(BaseModel):
    username: str
    avatar_url: str | None = None


class ShareCardGame(BaseModel):
    platform: str = "lichess"
    user_color: str | None = None
    speed: str | None = None
    time_control: str | None = None
    opening: str | None = None
    result: str
    moves: int
    opponent_username: str | None = None
    opponent_rating: int | None = None
    rating_change: int | None = None
    final_fen: str | None = None


class ShareCardMetrics(BaseModel):
    lowest_eval: float | None = None
    biggest_eval_swing: float | None = None
    accuracy: float | None = None


class ShareCardData(BaseModel):
    template: str
    player: ShareCardPlayer
    game: ShareCardGame
    story: GameStory
    metrics: ShareCardMetrics
    board_position_source: str


def build_share_card_data(
    game: ParsedGame,
    story: GameStory,
    metrics: GameMetrics | None,
    username: str | None,
) -> ShareCardData:
    metrics = metrics or GameMetrics()
    board_fen, source = resolve_board_position(story, game)
    story = story.model_copy(update={"key_position_fen": board_fen})
    return ShareCardData(
        template=story.template_key,
        player=ShareCardPlayer(username=username or "Player"),
        game=ShareCardGame(
            user_color=game.user_color,
            speed=game.speed,
            time_control=game.time_control,
            opening=game.opening_name,
            result=game.result,
            moves=game.moves_count,
            opponent_username=game.opponent_username,
            opponent_rating=game.opponent_rating,
            rating_change=game.rating_change,
            final_fen=game.final_fen,
        ),
        story=story,
        metrics=ShareCardMetrics(
            lowest_eval=metrics.lowest_eval,
            biggest_eval_swing=metrics.biggest_eval_swing,
            accuracy=metrics.accuracy,
        ),
        board_position_source=source,
    )


def resolve_board_position(story: GameStory, game: ParsedGame) -> tuple[str, str]:
    if story.key_move_number is not None and _is_valid_fen(story.key_position_fen):
        return str(story.key_position_fen), "key_position"
    if _is_valid_fen(game.final_fen):
        return str(game.final_fen), "final_position"
    return STARTING_FEN, "fallback_starting_position"


def _is_valid_fen(fen: str | None) -> bool:
    if not fen:
        return False
    try:
        chess.Board(fen)
    except ValueError:
        return False
    return True
