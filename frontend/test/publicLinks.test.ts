import assert from "node:assert/strict";

import {
  absoluteUrl,
  isPublished,
  postPath,
  profileCardHref,
  profileDisplayName,
  profilePath,
  profileSlugForPost,
  profileSlugForProfile,
  publishButtonLabel,
} from "../src/lib/publicLinks.ts";

assert.equal(profilePath("Clevermike02"), "/profile/Clevermike02");
assert.equal(profilePath("space user"), "/profile/space%20user");
assert.equal(postPath("post-123"), "/p/post-123");
assert.equal(profileCardHref("post-123"), "/p/post-123");
assert.equal(absoluteUrl("http://localhost:5173/", "/profile/Clevermike02"), "http://localhost:5173/profile/Clevermike02");
assert.equal(absoluteUrl("http://localhost:5173", profileCardHref("post-123")), "http://localhost:5173/p/post-123");
assert.equal(publishButtonLabel(null), "Publish card");
assert.equal(isPublished(null), false);
assert.equal(
  publishButtonLabel({
    id: "post-123",
    game_id: "game-123",
    game_story_id: "story-123",
    headline: "Published card",
    visibility: "public",
  }),
  "Published",
);
assert.equal(
  isPublished({
    id: "post-123",
    game_id: "game-123",
    game_story_id: "story-123",
    headline: "Published card",
    visibility: "public",
  }),
  true,
);
assert.equal(
  profileDisplayName({
    display_name: "local-session-1781471651808-46122pw6o",
    lichess_username: "Clevermike02",
  }),
  "Clevermike02",
);
assert.equal(
  profileSlugForProfile({
    profile_slug: "local-session-1781471651808-46122pw6o",
    display_name: "local-session-1781471651808-46122pw6o",
    lichess_username: "Clevermike02",
  }),
  "Clevermike02",
);
assert.equal(
  profileSlugForPost({
    profile_slug: "local",
    display_name: "local",
    lichess_username: "Clevermike02",
  }),
  "Clevermike02",
);
assert.equal(profilePath(profileSlugForProfile({
  profile_slug: "Clevermike02",
  display_name: "Clevermike02",
  lichess_username: "Clevermike02",
})), "/profile/Clevermike02");
assert.equal(
  absoluteUrl("http://localhost:5173", profilePath(profileSlugForProfile({
    profile_slug: "local-session-1781471651808-46122pw6o",
    display_name: "local-session-1781471651808-46122pw6o",
    lichess_username: "Clevermike02",
  }))),
  "http://localhost:5173/profile/Clevermike02",
);

console.log("public link helpers ok");
