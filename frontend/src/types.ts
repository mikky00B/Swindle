export type GameStory = {
  id?: string;
  primary_story: string;
  secondary_story?: string | null;
  badge_label: string;
  badge_emoji: string;
  headline: string;
  subheadline?: string | null;
  caption?: string | null;
  mood?: string | null;
  key_move_number?: number | null;
  key_position_fen?: string | null;
  key_move_san?: string | null;
  key_move_from?: string | null;
  key_move_to?: string | null;
  template_key: string;
  interesting_score: number;
  confidence_score: number;
  reasons: string[];
};

export type ShareCardData = {
  template: string;
  player: {
    username: string;
    avatar_url?: string | null;
  };
  game: {
    platform: string;
    user_color?: "white" | "black" | null;
    speed?: string | null;
    time_control?: string | null;
    opening?: string | null;
    result: string;
    moves: number;
    opponent_username?: string | null;
    opponent_rating?: number | null;
    rating_change?: number | null;
    final_fen?: string | null;
  };
  story: GameStory;
  metrics: {
    lowest_eval?: number | null;
    biggest_eval_swing?: number | null;
    accuracy?: number | null;
  };
  board_position_source: "key_position" | "final_position" | "fallback_starting_position";
};

export type LichessStatus = {
  connected: boolean;
  platform: "lichess";
  platform_username?: string | null;
  platform_user_id?: string | null;
  scopes: string[];
  connected_at?: string | null;
};

export type ImportResponse = {
  imported: number;
  duplicates: number;
  skipped: number;
  total_seen: number;
  errors: string[];
};

export type JournalGame = {
  id: string;
  external_game_id: string;
  platform: string;
  white_username?: string | null;
  black_username?: string | null;
  user_color?: string | null;
  opponent_username?: string | null;
  result: string;
  speed?: string | null;
  time_control?: string | null;
  opening_name?: string | null;
  opening_eco?: string | null;
  moves_count: number;
  user_rating_before?: number | null;
  opponent_rating?: number | null;
  rating_change?: number | null;
  played_at?: string | null;
  final_fen?: string | null;
  imported_at: string;
  processing_status: string;
  story: GameStory;
  raw_payload?: Record<string, unknown>;
  suggestion_id?: string;
  suggestion_status?: "suggested" | "ignored";
};

export type GameDebug = {
  game_id: string;
  external_game_id: string;
  user_color?: "white" | "black" | null;
  result: string;
  opponent_username?: string | null;
  opponent_rating?: number | null;
  opening_name?: string | null;
  moves_count: number;
  final_fen?: string | null;
  key_position_fen?: string | null;
  card_fen?: string | null;
  board_position_source?: string | null;
  key_move_number?: number | null;
  key_move_san?: string | null;
  story_type?: string | null;
  headline?: string | null;
  subheadline?: string | null;
};
