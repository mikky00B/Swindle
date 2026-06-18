export type AppRoute =
  | { kind: "landing" }
  | { kind: "journal" }
  | { kind: "feed" }
  | { kind: "session"; sessionId: string }
  | { kind: "profile"; username: string }
  | { kind: "post"; postId: string };

export function routeFromPath(path: string): AppRoute {
  if (path === "/journal") {
    return { kind: "journal" };
  }
  if (path === "/feed") {
    return { kind: "feed" };
  }
  if (path.startsWith("/sessions/")) {
    return { kind: "session", sessionId: decodeURIComponent(path.replace("/sessions/", "")) };
  }
  if (path.startsWith("/profile/")) {
    return { kind: "profile", username: decodeURIComponent(path.replace("/profile/", "")) };
  }
  if (path.startsWith("/p/")) {
    return { kind: "post", postId: decodeURIComponent(path.replace("/p/", "")) };
  }
  return { kind: "landing" };
}
