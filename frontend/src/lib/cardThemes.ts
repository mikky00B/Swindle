export type ShareCardTheme =
  | "classic"
  | "minimal"
  | "neon_blitz"
  | "newspaper"
  | "tournament"
  | "dark_glass"
  | "retro"
  | "luxury";

export type ShareCardSize = "square" | "story" | "portrait" | "landscape";

export type CardThemeDefinition = {
  id: ShareCardTheme;
  name: string;
  description: string;
  tier: "free" | "premium_coming_soon";
  defaultSize: ShareCardSize;
};

export type CardSizeDefinition = {
  id: ShareCardSize;
  name: string;
  width: number;
  height: number;
  description: string;
};

export const CARD_THEMES: Record<ShareCardTheme, CardThemeDefinition> = {
  classic: {
    id: "classic",
    name: "Classic",
    description: "Clean, balanced, and readable.",
    tier: "free",
    defaultSize: "square",
  },
  minimal: {
    id: "minimal",
    name: "Minimal",
    description: "A quiet, elegant layout for serious games.",
    tier: "free",
    defaultSize: "square",
  },
  neon_blitz: {
    id: "neon_blitz",
    name: "Neon Blitz",
    description: "High-energy theme for fast and chaotic games.",
    tier: "free",
    defaultSize: "square",
  },
  newspaper: {
    id: "newspaper",
    name: "Newspaper",
    description: "Turns your game into a dramatic chess headline.",
    tier: "free",
    defaultSize: "square",
  },
  tournament: {
    id: "tournament",
    name: "Tournament Poster",
    description: "Match-poster style for serious wins and rivalries.",
    tier: "premium_coming_soon",
    defaultSize: "portrait",
  },
  dark_glass: {
    id: "dark_glass",
    name: "Dark Glass",
    description: "Dark premium-style card with soft glass panels.",
    tier: "premium_coming_soon",
    defaultSize: "square",
  },
  retro: {
    id: "retro",
    name: "Retro Board",
    description: "Old-school chess club style.",
    tier: "premium_coming_soon",
    defaultSize: "square",
  },
  luxury: {
    id: "luxury",
    name: "Luxury Gold",
    description: "Black-and-gold premium card for big wins.",
    tier: "premium_coming_soon",
    defaultSize: "portrait",
  },
};

export const CARD_THEME_OPTIONS = Object.values(CARD_THEMES);

export const CARD_SIZES: Record<ShareCardSize, CardSizeDefinition> = {
  square: {
    id: "square",
    name: "Square",
    width: 1080,
    height: 1080,
    description: "Best for X, LinkedIn, and Instagram posts.",
  },
  story: {
    id: "story",
    name: "Story",
    width: 1080,
    height: 1920,
    description: "Best for WhatsApp status and Instagram Stories.",
  },
  portrait: {
    id: "portrait",
    name: "Portrait",
    width: 1080,
    height: 1350,
    description: "Best for portrait social feeds.",
  },
  landscape: {
    id: "landscape",
    name: "Landscape",
    width: 1200,
    height: 628,
    description: "Best for link previews and wide posts.",
  },
};

export const CARD_SIZE_OPTIONS = Object.values(CARD_SIZES);

export function isShareCardTheme(value: string | null | undefined): value is ShareCardTheme {
  return Boolean(value && value in CARD_THEMES);
}

export function normalizeShareCardTheme(value: string | null | undefined): ShareCardTheme {
  if (!isShareCardTheme(value)) {
    return "classic";
  }
  return CARD_THEMES[value].tier === "free" ? value : "classic";
}

export function themeClassName(theme: string | null | undefined): string {
  return `theme-${normalizeShareCardTheme(theme)}`;
}

export function themeFileSlug(theme: string | null | undefined): string {
  return normalizeShareCardTheme(theme).replace(/_/g, "-");
}

export function isShareCardSize(value: string | null | undefined): value is ShareCardSize {
  return Boolean(value && value in CARD_SIZES);
}

export function normalizeCardSize(value: string | null | undefined): ShareCardSize {
  return isShareCardSize(value) ? value : "square";
}
