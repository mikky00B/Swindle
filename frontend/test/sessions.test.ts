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

test("Recent Sessions section renders in journal source", () => {
  assert.match(appSource, /Recent Sessions/);
  assert.match(appSource, /No sessions yet\. Import more games to generate session recaps\./);
});

test("session card shows mood headline record and export action", () => {
  assert.match(appSource, /session\.mood/);
  assert.match(appSource, /session\.summary_headline/);
  assert.match(appSource, /recordLabel\(session\)/);
  assert.match(appSource, /Export recap/);
});

test("session detail route shows games and export button", () => {
  assert.match(appSource, /function SessionDetailPage/);
  assert.match(appSource, /Games in session/);
  assert.match(appSource, /Export session recap/);
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
});

test("mobile session rows have responsive CSS hooks", () => {
  assert.match(appSource, /className="session-game-row"/);
  assert.match(appSource, /className="session-card"/);
});
