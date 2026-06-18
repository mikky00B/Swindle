import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  CARD_SIZES,
  CARD_THEMES,
  normalizeCardSize,
  normalizeShareCardTheme,
  themeClassName,
  themeFileSlug,
} from "../src/lib/cardThemes.ts";

assert.equal(CARD_THEMES.classic.tier, "free");
assert.equal(CARD_THEMES.minimal.tier, "free");
assert.equal(CARD_THEMES.neon_blitz.tier, "free");
assert.equal(CARD_THEMES.newspaper.tier, "free");

assert.equal(CARD_THEMES.tournament.tier, "premium_coming_soon");
assert.equal(CARD_THEMES.dark_glass.tier, "premium_coming_soon");
assert.equal(CARD_THEMES.retro.tier, "premium_coming_soon");
assert.equal(CARD_THEMES.luxury.tier, "premium_coming_soon");

assert.equal(normalizeShareCardTheme("minimal"), "minimal");
assert.equal(normalizeShareCardTheme("neon_blitz"), "neon_blitz");
assert.equal(normalizeShareCardTheme("newspaper"), "newspaper");
assert.equal(normalizeShareCardTheme("retro"), "classic");
assert.equal(normalizeShareCardTheme("unknown"), "classic");
assert.equal(themeClassName("newspaper"), "theme-newspaper");
assert.equal(themeFileSlug("neon_blitz"), "neon-blitz");

assert.deepEqual(
  Object.fromEntries(Object.entries(CARD_SIZES).map(([key, size]) => [key, [size.width, size.height]])),
  {
    square: [1080, 1080],
    story: [1080, 1920],
    portrait: [1080, 1350],
    landscape: [1200, 628],
  },
);
assert.equal(normalizeCardSize("square"), "square");
assert.equal(normalizeCardSize("story"), "story");
assert.equal(normalizeCardSize("portrait"), "portrait");
assert.equal(normalizeCardSize("landscape"), "landscape");
assert.equal(normalizeCardSize("unknown"), "square");

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const shareCardSource = readFileSync(new URL("../src/components/cards/ShareCard.tsx", import.meta.url), "utf8");
const exportSource = readFileSync(new URL("../src/lib/exportImage.ts", import.meta.url), "utf8");
const cssSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

assert.match(shareCardSource, /export function ShareCardRenderer/);
assert.match(shareCardSource, /data-theme=\{theme\}/);
assert.match(shareCardSource, /data-size=\{normalizedSize\}/);
assert.match(shareCardSource, /width: dimensions\.width/);
assert.match(shareCardSource, /height: dimensions\.height/);
assert.match(appSource, /<ThemeSelector/);
assert.match(appSource, /<SizeSelector/);
assert.match(appSource, /setSelectedTheme/);
assert.match(appSource, /setSelectedSize/);
assert.match(appSource, /publishStoryCard\(selectedGame\.story\.id, selectedTheme, selectedSize\)/);
assert.match(appSource, /exportFileName\(getCardForExport\(\), selectedTheme, selectedSize\)/);
assert.match(appSource, /CARD_SIZES\[selectedSize\]/);
assert.match(appSource, /Premium themes are coming soon/);
assert.match(appSource, /aria-disabled=\{locked\}/);
assert.match(appSource, /normalizeShareCardTheme\(post\.card_theme\)/);
assert.match(appSource, /normalizeCardSize\(post\.card_size\)/);
assert.match(exportSource, /width: options\.width/);
assert.match(exportSource, /height: options\.height/);

assert.match(cssSource, /\.share-card\.theme-minimal/);
assert.match(cssSource, /\.share-card\.theme-neon_blitz/);
assert.match(cssSource, /\.share-card\.theme-newspaper/);
assert.match(cssSource, /\.share-card\.size-story/);
assert.match(cssSource, /\.share-card\.size-portrait/);
assert.match(cssSource, /\.share-card\.size-landscape/);
assert.match(cssSource, /\.share-card\.size-story \.board/);
assert.match(cssSource, /\.share-card\.size-portrait \.board/);
assert.match(cssSource, /\.share-card\.size-landscape \.board/);
assert.match(cssSource, /\.theme-option\.is-locked/);
assert.match(cssSource, /\.size-option\.is-active/);
assert.match(cssSource, /\.share-card\.theme-neon_blitz \.board-square\.is-light/);
assert.match(cssSource, /\.share-card\.theme-newspaper \.board/);
