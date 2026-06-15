import type { PublicProfile, PublishedPost, PublishedPostSummary } from "../types";

export function profilePath(username: string): string {
  return `/profile/${encodeURIComponent(username)}`;
}

export function postPath(postId: string): string {
  return `/p/${encodeURIComponent(postId)}`;
}

export function profileCardHref(postId: string): string {
  return postPath(postId);
}

export function absoluteUrl(origin: string, path: string): string {
  return `${origin.replace(/\/$/, "")}${path}`;
}

export function publishButtonLabel(post?: PublishedPostSummary | null): string {
  return post?.visibility === "public" ? "Published" : "Publish card";
}

export function isPublished(post?: PublishedPostSummary | null): boolean {
  return post?.visibility === "public";
}

export function profileDisplayName(profile: Pick<PublicProfile, "display_name" | "lichess_username">): string {
  return publicName(profile.display_name, profile.lichess_username);
}

export function profileSlugForProfile(profile: Pick<PublicProfile, "profile_slug" | "display_name" | "lichess_username">): string {
  return publicName(profile.profile_slug, profile.display_name, profile.lichess_username);
}

export function profileSlugForPost(post: Pick<PublishedPost, "profile_slug" | "display_name" | "lichess_username">): string {
  return publicName(post.profile_slug, post.display_name, post.lichess_username);
}

function publicName(...values: Array<string | null | undefined>): string {
  const value = values.find((candidate) => candidate && !isInternalLocalName(candidate));
  return value ?? "Player";
}

function isInternalLocalName(value: string): boolean {
  const lowered = value.toLowerCase();
  return lowered === "local" || lowered.startsWith("local-") || lowered.startsWith("session-");
}
