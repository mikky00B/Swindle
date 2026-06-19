import { ChessBoard } from "../chess/ChessBoard";
import { MetricsGrid } from "./MetricsGrid";
import { StoryBadge } from "./StoryBadge";
import type { ShareCardData } from "../../types";
import { positionLabel } from "../../lib/boardLabels";
import { CARD_SIZES, normalizeCardSize, themeClassName, type ShareCardSize, type ShareCardTheme } from "../../lib/cardThemes";

type ShareCardProps = {
  card: ShareCardData;
  theme?: ShareCardTheme;
  size?: ShareCardSize;
  showDevDebug?: boolean;
};

export function ShareCardRenderer({ card, theme = "classic", size = "square", showDevDebug = true }: ShareCardProps) {
  void showDevDebug;
  const normalizedSize = normalizeCardSize(size);
  const dimensions = CARD_SIZES[normalizedSize];
  const detail = [
    card.player.username,
    platformLabel(card.game.platform),
    card.game.speed,
    card.game.time_control,
  ].filter(Boolean);
  const headlineClass = getHeadlineSizeClass(card.story.headline);

  return (
    <article
      className={`share-card ${themeClassName(theme)} size-${normalizedSize} template-${card.template}`}
      data-theme={theme}
      data-size={normalizedSize}
      style={{ width: dimensions.width, height: dimensions.height }}
    >
      <header className="card-header">
        <div>
          <p className="brand">Swindle</p>
          <p className="game-detail">{detail.join(" / ")}</p>
        </div>
        <div className="score-pill">
          <span>Story score</span>
          <strong>{Math.round(card.story.interesting_score * 100)}%</strong>
        </div>
      </header>

      <section className="story-section">
        <StoryBadge label={card.story.badge_label} emoji={card.story.badge_emoji} />
        <h1 className={headlineClass}>{card.story.headline}</h1>
        {card.story.subheadline ? <p>{card.story.subheadline}</p> : null}
      </section>

      <section className="lower-section">
        <div className="metrics-column">
          <MetricsGrid card={card} />
        </div>

        <div className="board-shell">
          <div className="board-frame">
            <ChessBoard
              fen={card.story.key_position_fen}
              from={card.story.key_move_from}
              to={card.story.key_move_to}
              orientation={card.game.user_color}
            />
          </div>
          <div className="board-caption">
            <span>{positionLabel(card.board_position_source)}</span>
            {card.story.key_move_number ? <strong>Move {card.story.key_move_number}</strong> : null}
          </div>
        </div>
      </section>

      <footer className="card-footer">
        <span>{platformStoryCardLabel(card.game.platform)} story card</span>
        <strong>swindle.app/{card.player.username}</strong>
      </footer>
    </article>
  );
}

export function ShareCard(props: ShareCardProps) {
  return <ShareCardRenderer {...props} />;
}

export function getHeadlineSizeClass(headline: string): string {
  if (headline.length > 92) {
    return "headline headline-compact";
  }
  if (headline.length > 62) {
    return "headline headline-medium";
  }
  return "headline headline-large";
}

function platformLabel(platform?: string | null): string {
  if (platform === "chesscom") return "Chess.com";
  if (platform === "lichess") return "Lichess";
  return platform ?? "";
}

function platformStoryCardLabel(platform?: string | null): string {
  if (platform === "chesscom") return "chess.com";
  if (platform === "lichess") return "lichess";
  return platform ?? "chess";
}
