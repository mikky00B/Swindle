import assert from "node:assert/strict";

import {
  FEED_EMPTY_MESSAGE,
  FEED_EMPTY_TITLE,
  appendComment,
  applySocialCountsToFeed,
  applySocialCountsToPost,
  followButtonLabel,
  kudosLabel,
  navItems,
  shouldShowFollowButton,
  socialCountLabel,
} from "../src/lib/social.ts";
import type { FeedResponse, PostComment, PublicProfile, PublishedPost } from "../src/types.ts";

assert.equal(followButtonLabel(profile(false)), "Follow");
assert.equal(followButtonLabel(profile(true)), "Following");
assert.equal(shouldShowFollowButton(profile(false)), true);
assert.equal(shouldShowFollowButton({ ...profile(false), viewer_is_self: true }), false);
assert.equal(FEED_EMPTY_TITLE, "Your feed is empty.");
assert.equal(FEED_EMPTY_MESSAGE, "Follow players to see their published chess story cards here.");
assert.equal(kudosLabel(post("plain-post")), "Kudos");
assert.equal(kudosLabel({ ...post("active-post"), viewer_has_kudos: true }), "Kudos");
assert.equal(socialCountLabel(1, "comment"), "1 comment");
assert.equal(socialCountLabel(2, "comment"), "2 comments");

const nav = navItems("feed", { platform_username: "Clevermike02" });
assert.deepEqual(nav.map((item) => item.label), ["Journal", "Profile", "Feed"]);
assert.equal(nav.find((item) => item.label === "Journal")?.href, "/journal");
assert.equal(nav.find((item) => item.label === "Profile")?.href, "/profile/Clevermike02");
assert.equal(nav.find((item) => item.label === "Feed")?.active, true);
assert.equal(navItems("post", { platform_username: "Clevermike02" }).find((item) => item.label === "Feed")?.active, true);
assert.equal(navItems("journal", null).find((item) => item.label === "Profile")?.disabled, true);

const feed: FeedResponse = {
  items: [post("followed-post"), post("other-post")],
  limit: 20,
  offset: 0,
  total: 2,
};

const updatedFeed = applySocialCountsToFeed(feed, "followed-post", {
  kudos_count: 1,
  comments_count: 0,
  viewer_has_kudos: true,
});

assert.equal(updatedFeed?.items[0].kudos_count, 1);
assert.equal(updatedFeed?.items[0].viewer_has_kudos, true);
assert.equal(updatedFeed?.items[1].kudos_count, 0);

const updatedPost = applySocialCountsToPost(post("public-post"), {
  kudos_count: 3,
  comments_count: 2,
  viewer_has_kudos: true,
});

assert.equal(updatedPost.kudos_count, 3);
assert.equal(updatedPost.comments_count, 2);
assert.equal(updatedPost.viewer_has_kudos, true);

const comment = commentItem("Nice card");
const comments = appendComment([], comment);
assert.deepEqual(comments.map((item) => item.body), ["Nice card"]);

function profile(following: boolean): PublicProfile {
  return {
    display_name: "Clevermike",
    profile_slug: "Clevermike",
    lichess_username: "Clevermike",
    published_cards_count: 1,
    followers_count: following ? 1 : 0,
    following_count: 0,
    viewer_is_self: false,
    viewer_is_following: following,
    wins_shown: 1,
    losses_shown: 0,
    common_story: "swindle",
    games_imported: 1,
    posts: [],
  };
}

function post(id: string): PublishedPost {
  return {
    id,
    game_id: `${id}-game`,
    game_story_id: `${id}-story`,
    headline: "Completely lost, somehow won.",
    visibility: "public",
    display_name: "Clevermike",
    profile_slug: "Clevermike",
    lichess_username: "Clevermike",
    kudos_count: 0,
    comments_count: 0,
    viewer_has_kudos: false,
    game: {
      id: `${id}-game`,
      external_game_id: id,
      platform: "lichess",
      result: "win",
      moves_count: 48,
    },
    story: {
      id: `${id}-story`,
      primary_story: "swindle",
      badge_label: "The Swindle",
      badge_emoji: "SW",
      headline: "Completely lost, somehow won.",
      interesting_score: 0.9,
      key_position_fen: "8/8/8/8/8/8/8/8 w - - 0 1",
    },
  };
}

function commentItem(body: string): PostComment {
  return {
    id: "comment-1",
    post_id: "public-post",
    body,
    created_at: "2026-06-15T00:00:00Z",
    author: {
      display_name: "Viewer",
      profile_slug: "Viewer",
      lichess_username: "Viewer",
    },
  };
}

console.log("social helpers ok");
