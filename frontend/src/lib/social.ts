import type { FeedResponse, LichessStatus, PostComment, PublicProfile, PublishedPost, SocialCounts } from "../types";

export type NavPage = "journal" | "profile" | "feed" | "post";

export const FEED_EMPTY_TITLE = "Your feed is empty.";
export const FEED_EMPTY_MESSAGE = "Follow players to see their published chess story cards here.";

export function followButtonLabel(profile: Pick<PublicProfile, "viewer_is_following">): string {
  return profile.viewer_is_following ? "Following" : "Follow";
}

export function shouldShowFollowButton(profile: Pick<PublicProfile, "viewer_is_self">): boolean {
  return !profile.viewer_is_self;
}

export function kudosLabel(post: Pick<PublishedPost, "viewer_has_kudos">): string {
  return post.viewer_has_kudos ? "Kudos" : "Kudos";
}

export function socialCountLabel(count: number, singular: string): string {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

export function navItems(
  activePage: NavPage,
  status?: Pick<LichessStatus, "platform_username"> | null,
  fallbackProfileSlug?: string | null,
): Array<{ label: "Journal" | "Profile" | "Feed"; href?: string; active: boolean; disabled?: boolean }> {
  const profileSlug = status?.platform_username ?? fallbackProfileSlug ?? null;
  return [
    { label: "Journal", href: "/journal", active: activePage === "journal" },
    {
      label: "Profile",
      href: profileSlug ? `/profile/${encodeURIComponent(profileSlug)}` : undefined,
      active: activePage === "profile",
      disabled: !profileSlug,
    },
    { label: "Feed", href: "/feed", active: activePage === "feed" || activePage === "post" },
  ];
}

export function applySocialCountsToPost<T extends Pick<PublishedPost, "id">>(
  post: T,
  counts: SocialCounts,
): T & SocialCounts {
  return { ...post, ...counts };
}

export function applySocialCountsToFeed(feed: FeedResponse | null, postId: string, counts: SocialCounts): FeedResponse | null {
  if (!feed) return feed;
  return {
    ...feed,
    items: feed.items.map((post) => (post.id === postId ? applySocialCountsToPost(post, counts) : post)),
  };
}

export function appendComment(comments: PostComment[], comment: PostComment): PostComment[] {
  return [...comments, comment];
}
