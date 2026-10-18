// Run with: node --test extension/
const test = require("node:test");
const assert = require("node:assert/strict");
const core = require("./core.js");

test("parses ranking paths with and without a page number", () => {
  assert.deepEqual(core.parseRankingPath("/contest/weekly-contest-524/ranking/"), {
    contest: "weekly-contest-524",
    page: 1,
  });
  assert.deepEqual(core.parseRankingPath("/contest/biweekly-contest-194/ranking/3/"), {
    contest: "biweekly-contest-194",
    page: 3,
  });
  assert.equal(core.parseRankingPath("/contest/weekly-contest-524/"), null);
  assert.equal(core.parseRankingPath("/contest/some-cup/ranking/"), null);
});

test("builds the ranking endpoint the page itself uses", () => {
  assert.equal(
    core.rankingApiPath("weekly-contest-524", 2),
    "/contest/api/ranking/weekly-contest-524/?pagination=2&region=global_v2",
  );
});

test("maps slugs to displayed rank and skips leetcode.cn accounts", () => {
  const ranks = core.ranksFromRanking({
    total_rank: [
      { username: "Display Name", user_slug: "perryz0", rank: 1427, data_region: "US" },
      { username: "drlt", user_slug: "drlt", rank: 1429, data_region: "CN" },
      { username: "bad slug!", user_slug: "bad slug!", rank: 1, data_region: "US" },
      { username: "norank", user_slug: "norank", rank: null, data_region: "US" },
    ],
  });
  assert.deepEqual([...ranks], [["perryz0", 1428]]);
  assert.equal(core.ranksFromRanking(null).size, 0);
});

test("reads the slug from profile links", () => {
  assert.equal(core.slugFromHref("/u/zee_man/"), "zee_man");
  assert.equal(core.slugFromHref("/u/zee_man"), "zee_man");
  assert.equal(core.slugFromHref("/problems/two-sum/"), null);
  assert.equal(core.slugFromHref(null), null);
});

test("formats deltas with a sign and one decimal", () => {
  assert.equal(core.formatDelta(12.345), "+12.3");
  assert.equal(core.formatDelta(-4.46), "-4.5");
  assert.equal(core.formatDelta(0.04), "0.0");
});

test("normalizes the API base and rejects non-http URLs", () => {
  assert.equal(core.normalizeApiBase(""), core.DEFAULT_API_BASE);
  assert.equal(core.normalizeApiBase(" http://localhost:8000/ "), "http://localhost:8000");
  assert.equal(core.normalizeApiBase("https://example.com/api/"), "https://example.com/api");
  assert.equal(core.normalizeApiBase("javascript:alert(1)"), null);
  assert.equal(core.normalizeApiBase("not a url"), null);
});

test("summarizes a predict response", () => {
  assert.deepEqual(
    core.summarizePrediction([
      { prediction: 21.5, rating_before_contest: 1800, rating_after_contest: 1821.5 },
    ]),
    { delta: 21.5, before: 1800, after: 1821.5 },
  );
  assert.equal(core.summarizePrediction([]), null);
  assert.equal(core.summarizePrediction({ detail: "x" }), null);
});

test("clamps Retry-After", () => {
  assert.equal(core.retryAfterSeconds("12"), 12);
  assert.equal(core.retryAfterSeconds("600"), 60);
  assert.equal(core.retryAfterSeconds(null), 5);
  assert.equal(core.retryAfterSeconds("soon"), 5);
});
