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
    highest_eval?: number | null;
    biggest_eval_swing?: number | null;
    accuracy?: number | null;
    analysis_status?: string | null;
    analysis_source?: string | null;
    eval_points?: number | null;
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

export type ChessComStatus = {
  connected: boolean;
  platform: "chesscom";
  platform_username?: string | null;
  platform_user_id?: string | null;
  last_synced_at?: string | null;
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
  metrics?: GameAnalysisMetrics;
  raw_payload?: Record<string, unknown>;
  suggestion_id?: string;
  suggestion_status?: "suggested" | "ignored";
  published_post?: PublishedPostSummary | null;
};

export type SessionGameSummary = {
  id: string;
  platform: string;
  result: string;
  opening_name?: string | null;
  opponent_username?: string | null;
  moves_count?: number | null;
  played_at?: string | null;
  story?: {
    id: string;
    primary_story: string;
    badge_label: string;
    badge_emoji: string;
    headline: string;
  } | null;
};

export type SessionSummary = {
  id: string;
  started_at?: string | null;
  ended_at?: string | null;
  games_count: number;
  wins_count: number;
  losses_count: number;
  draws_count: number;
  win_rate: number;
  best_story_type?: string | null;
  best_game_id?: string | null;
  best_game_story_id?: string | null;
  most_common_opening?: string | null;
  rating_delta?: number | null;
  mood?: string | null;
  summary_headline: string;
  summary_subheadline?: string | null;
  swindle_count?: number;
  heartbreaker_count?: number;
  miniature_count?: number;
  long_grind_count?: number;
  giant_slayer_count?: number;
  turning_point_count?: number;
  openings?: SessionOpeningSummary[];
  rating_tracks?: SessionRatingTrack[];
};

export type SessionShareCardData = {
  kind: "session_recap";
  template: string;
  player: {
    username: string;
    avatar_url?: string | null;
  };
  session: SessionSummary;
  stats: {
    record: string;
    games_count: number;
    most_common_opening?: string | null;
    openings?: SessionOpeningSummary[];
    rating_tracks?: SessionRatingTrack[];
    rating_delta?: number | null;
  };
};

export type SessionDetail = SessionSummary & {
  games: SessionGameSummary[];
  openings?: SessionOpeningSummary[];
  best_game?: SessionGameSummary | null;
  share_card?: SessionShareCardData;
};

export type SessionOpeningSummary = {
  name: string;
  games: number;
  wins: number;
  losses: number;
  draws: number;
  record: string;
  win_rate: number;
};

export type SessionRatingTrack = {
  platform: string;
  speed?: string | null;
  explicit_delta: number;
  has_explicit: boolean;
  first_rating?: number | null;
  last_rating?: number | null;
  first_played_at?: string | null;
  last_played_at?: string | null;
  inferred_delta?: number | null;
};

export type GameAnalysisMetrics = {
  accuracy?: number | null;
  lowest_eval?: number | null;
  highest_eval?: number | null;
  biggest_eval_swing?: number | null;
  turning_point_move?: number | null;
  turning_point_fen?: string | null;
  turning_point_san?: string | null;
  analysis_depth?: number | null;
  analysis_source?: string | null;
  analysis_status?: string | null;
  eval_points: number;
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
  metrics?: GameAnalysisMetrics;
};

export type PublishedPostSummary = {
  id: string;
  game_id: string;
  game_story_id: string;
  headline: string;
  caption?: string | null;
  card_theme?: string | null;
  card_size?: string | null;
  visibility: "public" | "unpublished";
  created_at?: string | null;
  updated_at?: string | null;
};

export type PublishedPost = PublishedPostSummary & {
  display_name: string;
  profile_slug: string;
  lichess_username?: string | null;
  kudos_count: number;
  comments_count: number;
  viewer_has_kudos: boolean;
  game?: {
    id: string;
    external_game_id: string;
    platform: string;
    result: string;
    opening_name?: string | null;
    opponent_username?: string | null;
    moves_count: number;
    speed?: string | null;
    time_control?: string | null;
    played_at?: string | null;
    final_fen?: string | null;
  } | null;
  story?: {
    id: string;
    primary_story: string;
    badge_label: string;
    badge_emoji: string;
    headline: string;
    interesting_score: number;
    key_position_fen?: string | null;
  } | null;
  metrics?: {
    accuracy?: number | null;
    lowest_eval?: number | null;
    highest_eval?: number | null;
    biggest_eval_swing?: number | null;
    turning_point_move?: number | null;
    analysis_source?: string | null;
    analysis_status?: string | null;
  } | null;
  share_card?: ShareCardData;
};

export type PublicProfile = {
  display_name: string;
  profile_slug: string;
  lichess_username?: string | null;
  published_cards_count: number;
  followers_count: number;
  following_count: number;
  viewer_is_self: boolean;
  viewer_is_following: boolean;
  wins_shown: number;
  losses_shown: number;
  common_story?: string | null;
  games_imported?: number;
  posts: PublishedPost[];
};

export type FeedResponse = {
  items: PublishedPost[];
  limit: number;
  offset: number;
  total: number;
};

export type SocialCounts = {
  kudos_count: number;
  comments_count: number;
  viewer_has_kudos: boolean;
};

export type CommentAuthor = {
  display_name: string;
  profile_slug: string;
  lichess_username?: string | null;
};

export type PostComment = {
  id: string;
  post_id: string;
  body: string;
  created_at?: string | null;
  author: CommentAuthor;
};
