import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { routeFromPath } from "../src/lib/routes.ts";

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const apiSource = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const typesSource = readFileSync(new URL("../src/types.ts", import.meta.url), "utf8");

test("session route parses session detail urls", () => {
  assert.deepEqual(routeFromPath("/sessions/session-123"), { kind: "session", sessionId: "session-123" });
});

test("Daily Recaps section renders in journal source", () => {
  assert.match(appSource, /Daily Recaps/);
  assert.match(appSource, /No daily recaps yet\. Import games to generate daily recaps\./);
});

test("session card shows mood headline record and export action", () => {
  assert.match(appSource, /session\.mood/);
  assert.match(appSource, /session\.summary_headline/);
  assert.match(appSource, /recordLabel\(recap\)/);
  assert.match(appSource, /RECAP_WINDOWS/);
  assert.match(appSource, /Choose recap timeframe/);
  assert.match(appSource, /windowOption\.label\} details/);
  assert.match(appSource, /Openings played/);
  assert.match(appSource, /combineSessionOpenings/);
  assert.match(appSource, /aggregateSessionRatingDelta/);
  assert.match(appSource, /Export \{windowOption\.label\} recap/);
});

test("session detail route shows games and export button", () => {
  assert.match(appSource, /function SessionDetailPage/);
  assert.match(appSource, /className="session-detail-hero"/);
  assert.match(appSource, /className="session-detail-kicker"/);
  assert.match(appSource, /games this day/);
  assert.match(appSource, /Export daily recap/);
  assert.match(appSource, /gameOpeningLabel\(game\)/);
  assert.match(appSource, /Opening results today/);
  assert.match(appSource, /formatPercent\(opening\.win_rate\)/);
});

test("session API helpers are available", () => {
  assert.match(apiSource, /export async function listSessions/);
  assert.match(apiSource, /export async function rebuildSessions/);
  assert.match(apiSource, /export async function getSessionDetail/);
  assert.match(apiSource, /export async function getSessionShareCard/);
});

test("session recap card data is typed", () => {
  assert.match(typesSource, /export type SessionSummary/);
  assert.match(typesSource, /export type SessionShareCardData/);
  assert.match(typesSource, /kind: "session_recap"/);
  assert.match(typesSource, /platform: string;/);
  assert.match(typesSource, /export type SessionOpeningSummary/);
  assert.match(typesSource, /openings\?: SessionOpeningSummary\[\];/);
  assert.match(typesSource, /export type SessionRatingTrack/);
  assert.match(typesSource, /rating_tracks\?: SessionRatingTrack\[\];/);
  assert.match(typesSource, /openings\?: SessionOpeningSummary\[\]/);
});

test("session recap card renders opening breakdown instead of one mixed opening stat", () => {
  assert.match(appSource, /Openings today/);
  assert.match(appSource, /card\.stats\.openings/);
  assert.doesNotMatch(appSource, /<dt>Opening<\/dt>\s*<dd>\{card\.stats\.most_common_opening/);
  assert.doesNotMatch(appSource, /session\.summary_subheadline \? <span>\{session\.summary_subheadline\}<\/span>/);
});

test("session recap card has size-specific layout safeguards", () => {
  const stylesSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(stylesSource, /\.session-recap-card\.size-square|\.session-recap-card \{/);
  assert.match(stylesSource, /\.session-recap-card\.size-story \.session-recap-opening-row/);
  assert.match(stylesSource, /\.session-recap-card\.size-portrait \.session-recap-opening-row/);
  assert.match(stylesSource, /\.session-recap-card\.size-landscape \.session-recap-openings/);
  assert.match(stylesSource, /grid-row: 3;/);
});

test("mobile session rows have responsive CSS hooks", () => {
  const stylesSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(appSource, /className="session-game-row"/);
  assert.match(appSource, /className="session-card session-window-card"/);
  assert.match(stylesSource, /\.recap-window-tabs\s*\{[\s\S]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\);/);
  assert.match(stylesSource, /\.responsive-card-stage\s*\{[\s\S]*width: calc\(var\(--card-width\) \* var\(--card-scale\)\);/);
  assert.match(stylesSource, /\.session-detail-main,[\s\S]*\.session-detail-card\s*\{[\s\S]*min-width: 0;/);
  assert.match(stylesSource, /@media \(max-width: 900px\)[\s\S]*\.session-detail-card \.responsive-card-preview,[\s\S]*\.session-detail-card \.preview-actions,[\s\S]*\.session-detail-card \.theme-selector,[\s\S]*\.session-detail-card \.size-selector\s*\{[\s\S]*max-width: 100%;/);
  assert.match(stylesSource, /@media \(max-width: 900px\)[\s\S]*\.session-detail-hero h1\s*\{[\s\S]*font-size: 44px;[\s\S]*overflow-wrap: anywhere;/);
  assert.match(stylesSource, /@media \(max-width: 900px\)[\s\S]*\.session-detail-hero p:not\(\.session-detail-kicker\)\s*\{[\s\S]*line-height: 1\.45;[\s\S]*overflow-wrap: anywhere;/);
  assert.match(stylesSource, /@media \(max-width: 768px\)[\s\S]*\.top-nav\s*\{[\s\S]*display: grid;[\s\S]*grid-template-columns: minmax\(0, 1fr\) auto;/);
  assert.match(stylesSource, /@media \(max-width: 768px\)[\s\S]*\.public-shell \.top-nav > div\s*\{[\s\S]*max-width: 100%;/);
  assert.match(stylesSource, /@media \(max-width: 768px\)[\s\S]*\.session-detail-card \.theme-options,[\s\S]*\.session-detail-card \.size-options\s*\{[\s\S]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);/);
  assert.doesNotMatch(stylesSource, /\.export-stage\s*\{[\s\S]*left:\s*-200vw;/);
  assert.doesNotMatch(stylesSource, /@media \(max-width: 768px\)[\s\S]*\.session-detail-hero h1\s*\{/);
});
