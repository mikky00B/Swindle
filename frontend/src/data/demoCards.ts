import type { ShareCardData } from "../types";

const demoFen = "r2q1rk1/pp2bppp/2n1pn2/2bp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 9";

export const LANDING_DEMO_CARDS: Array<{ name: string; card: ShareCardData }> = [
  {
    name: "The Swindle",
    card: demoCard({
      story: "swindle",
      badge: "The Swindle",
      emoji: "SW",
      headline: "Completely lost, somehow walked out with the full point.",
      subheadline: "A 42-move Sicilian turned into chaos.",
      result: "win",
      opening: "Sicilian Defense",
      moves: 42,
      lowestEval: -5.2,
      swing: 7.4,
      ratingChange: 14,
    }),
  },
  {
    name: "Giant Slayer",
    card: demoCard({
      story: "giant_slayer",
      badge: "Giant Slayer",
      emoji: "GS",
      headline: "Took down a much higher-rated opponent.",
      subheadline: "Rating gap ignored in a sharp attacking game.",
      result: "win",
      opening: "Queen's Gambit Declined",
      moves: 51,
      opponentRating: 1786,
      ratingChange: 18,
      swing: 4.6,
    }),
  },
  {
    name: "Heartbreaker",
    card: demoCard({
      story: "heartbreaker",
      badge: "Heartbreaker",
      emoji: "HB",
      headline: "Had the game in hand, then watched it slip away.",
      subheadline: "One endgame decision changed the story.",
      result: "loss",
      opening: "Caro-Kann Defense",
      moves: 64,
      highestEval: 6.1,
      swing: 8.2,
      ratingChange: -11,
    }),
  },
  {
    name: "Long Grind",
    card: demoCard({
      story: "long_grind",
      badge: "Long Grind",
      emoji: "LG",
      headline: "A marathon endgame that went the distance.",
      subheadline: "Eighty-three moves, one stubborn conversion.",
      result: "win",
      opening: "English Opening",
      moves: 83,
      swing: 3.1,
      ratingChange: 8,
    }),
  },
  {
    name: "Miniature",
    card: demoCard({
      story: "miniature",
      badge: "Miniature",
      emoji: "MN",
      headline: "Ended things before the game even settled down.",
      subheadline: "A quick tactical strike decided everything.",
      result: "win",
      opening: "Italian Game",
      moves: 19,
      swing: 5.3,
      ratingChange: 7,
    }),
  },
];

function demoCard({
  story,
  badge,
  emoji,
  headline,
  subheadline,
  result,
  opening,
  moves,
  lowestEval = null,
  highestEval = null,
  swing = null,
  opponentRating = 1650,
  ratingChange,
}: {
  story: string;
  badge: string;
  emoji: string;
  headline: string;
  subheadline: string;
  result: string;
  opening: string;
  moves: number;
  lowestEval?: number | null;
  highestEval?: number | null;
  swing?: number | null;
  opponentRating?: number;
  ratingChange: number;
}): ShareCardData {
  return {
    template: `${story}_square_v1`,
    player: {
      username: "Clevermike02",
    },
    game: {
      platform: "lichess",
      user_color: "white",
      speed: "blitz",
      time_control: "5+0",
      opening,
      result,
      moves,
      opponent_username: "higherRated",
      opponent_rating: opponentRating,
      rating_change: ratingChange,
      final_fen: demoFen,
    },
    story: {
      primary_story: story,
      badge_label: badge,
      badge_emoji: emoji,
      headline,
      subheadline,
      key_move_number: Math.min(31, moves),
      key_position_fen: demoFen,
      key_move_san: "Nxe5",
      key_move_from: "f3",
      key_move_to: "e5",
      template_key: `${story}_square_v1`,
      interesting_score: 0.9,
      confidence_score: 0.86,
      reasons: ["demo_card"],
    },
    metrics: {
      lowest_eval: lowestEval,
      highest_eval: highestEval,
      biggest_eval_swing: swing,
      accuracy: result === "win" ? 86.4 : 72.1,
    },
    board_position_source: "key_position",
  };
}
