import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { LANDING_DEMO_CARDS } from "../src/data/demoCards.ts";
import { routeFromPath } from "../src/lib/routes.ts";

assert.equal(routeFromPath("/").kind, "landing");
assert.equal(routeFromPath("/landing").kind, "landing");
assert.equal(routeFromPath("/journal").kind, "journal");
assert.equal(routeFromPath("/feed").kind, "feed");
assert.deepEqual(routeFromPath("/profile/Clevermike02"), { kind: "profile", username: "Clevermike02" });
assert.deepEqual(routeFromPath("/p/post-123"), { kind: "post", postId: "post-123" });

assert.equal(LANDING_DEMO_CARDS.length, 5);
assert.ok(LANDING_DEMO_CARDS.every((item) => item.card.story.headline));
assert.ok(LANDING_DEMO_CARDS.every((item) => item.card.story.key_position_fen));

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const cssSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

assert.match(appSource, /function LandingPage/);
assert.match(appSource, /const \[mobileMenuOpen, setMobileMenuOpen\]/);
assert.match(appSource, /className="landing-menu-toggle"/);
assert.match(appSource, /aria-expanded=\{mobileMenuOpen\}/);
assert.match(appSource, /landing-nav-links is-open/);
assert.match(appSource, /Your chess games have stories\./);
assert.match(appSource, /PGNs show the moves\. Swindle shows the story\./);
assert.match(appSource, /See your games as stories/);
assert.match(appSource, /Connect Lichess/);
assert.match(appSource, /window\.location\.assign\(lichessConnectUrl\(\)\)/);
assert.match(appSource, /LANDING_DEMO_CARDS/);
assert.match(appSource, /LANDING_THEMES/);
assert.match(appSource, /setSelectedTheme\(theme\)/);
assert.match(appSource, /1\. Connect Lichess/);
assert.match(appSource, /2\. Find the story/);
assert.match(appSource, /3\. Share the moment/);
assert.match(appSource, /Private chess journal/);
assert.match(appSource, /Multiple export sizes/);
assert.match(appSource, /Start with your latest Lichess games\./);
assert.match(appSource, /href="\/journal"/);
assert.match(appSource, /<ResponsiveShareCard card=\{selectedCard\} theme=\{selectedTheme\} size="square" \/>/);

assert.match(cssSource, /\.landing-page/);
assert.match(cssSource, /\.landing-hero/);
assert.match(cssSource, /\.landing-demo-layout/);
assert.match(cssSource, /\.landing-theme-switcher/);
assert.match(cssSource, /\.landing-final-cta/);
assert.match(cssSource, /\.landing-menu-toggle\s*\{[^}]*display: none;/s);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.landing-menu-toggle\s*\{[^}]*display: inline-flex;/);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.landing-nav-links/);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.landing-nav-links\.is-open\s*\{[^}]*display: grid;/);
assert.match(cssSource, /@media \(max-width: 768px\)[\s\S]*\.landing-theme-switcher/);
