import type { FeedResponse, PostComment, PublicProfile, PublishedPost, SocialCounts } from "../types";

export const FEED_EMPTY_MESSAGE = "Follow players to see their story cards here.";

export function followButtonLabel(profile: Pick<PublicProfile, "viewer_is_following">): string {
  return profile.viewer_is_following ? "Following" : "Follow";
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
