import type { ShareCardData } from "./types";

export const MOCK_CARD: ShareCardData = {
  template: "swindle_square_v1",
  player: {
    username: "clevermike",
  },
  game: {
    platform: "lichess",
    user_color: "white",
    speed: "blitz",
    time_control: "5+0",
    opening: "Sicilian Defense",
    result: "win",
    moves: 48,
    opponent_username: "higherRated",
    opponent_rating: 1650,
    rating_change: 14,
    final_fen: "r2q1rk1/pp2bppp/2n1pn2/2bp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 9",
  },
  story: {
    primary_story: "swindle",
    secondary_story: "giant_slayer",
    badge_label: "The Swindle",
    badge_emoji: "SW",
    headline: "Completely lost, somehow walked out with the full point.",
    subheadline: "The game flipped around move 31.",
    key_move_number: 31,
    key_position_fen: "r2q1rk1/pp2bppp/2n1pn2/2bp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 9",
    key_move_san: "Nxe5",
    key_move_from: "f3",
    key_move_to: "e5",
    template_key: "swindle_square_v1",
    interesting_score: 0.92,
    confidence_score: 0.88,
    reasons: ["lowest_eval_below_minus_3", "won_game", "big_eval_swing"],
  },
  metrics: {
    lowest_eval: -5.2,
    biggest_eval_swing: 7.4,
    accuracy: 84.2,
  },
  board_position_source: "key_position",
};

export const SAMPLE_CARDS: Array<{ name: string; card: ShareCardData }> = [
  {
    name: "Base swindle",
    card: MOCK_CARD,
  },
  {
    name: "Long headline",
    card: {
      ...MOCK_CARD,
      story: {
        ...MOCK_CARD.story,
        headline:
          "Completely lost in the middlegame, still found enough counterplay to turn a disaster into a full point.",
      },
    },
  },
  {
    name: "Missing opening",
    card: {
      ...MOCK_CARD,
      game: {
        ...MOCK_CARD.game,
        opening: null,
      },
    },
  },
  {
    name: "Missing accuracy",
    card: {
      ...MOCK_CARD,
      metrics: {
        ...MOCK_CARD.metrics,
        accuracy: null,
      },
    },
  },
  {
    name: "No key move",
    card: {
      ...MOCK_CARD,
      story: {
        ...MOCK_CARD.story,
        key_move_number: null,
        key_move_san: null,
        key_move_from: null,
        key_move_to: null,
      },
    },
  },
  {
    name: "Long opening",
    card: {
      ...MOCK_CARD,
      game: {
        ...MOCK_CARD.game,
        opening: "King's Indian Defense: Fianchetto Variation, Classical Main Line",
      },
    },
  },
];

export const SAMPLE_PGN = `[Event "Rated blitz game"]
[Site "https://lichess.org/example"]
[Date "2026.06.14"]
[White "clevermike"]
[Black "higherRated"]
[Result "1-0"]
[UTCDate "2026.06.14"]
[UTCTime "10:15:00"]
[WhiteElo "1392"]
[BlackElo "1560"]
[ECO "B20"]
[Opening "Sicilian Defense"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6 6. Be3 Be7 7. f3 O-O
8. Qd2 Nc6 9. O-O-O a6 10. g4 Qc7 11. h4 b5 12. h5 Nd7 13. g5 Nxd4
14. Qxd4 Bb7 15. h6 e5 16. Qd2 g6 17. Kb1 Rac8 18. Bh3 Rfd8 19. Rh2 b4
20. Nd5 Bxd5 21. Qxd5 Rb8 22. f4 Rb5 23. Qb3 Nc5 24. Bxc5 dxc5 25. Rxd8+
Bxd8 26. Rd2 exf4 27. Qd5 Rb8 28. e5 Bxg5 29. e6 Bxh6 30. exf7+ Qxf7
31. Be6 1-0`;
