// Pure helpers shared by the content script, the service worker and the tests.
// Loaded as a classic script in the extension and with require() under Node.
(function (root) {
  "use strict";

  const DEFAULT_API_BASE = "https://leetcode-rating-predictor.onrender.com";
  const RANKING_PATH_RE =
    /^\/contest\/((?:weekly|biweekly)-contest-\d+)\/ranking(?:\/(\d+))?\/?$/;
  const PROFILE_HREF_RE = /^\/u\/([^/?#]+)\/?$/;
  const USERNAME_RE = /^[a-zA-Z0-9_-]{1,50}$/;

  /** Contest slug and page number from a ranking page path, or null. */
  function parseRankingPath(pathname) {
    const match = RANKING_PATH_RE.exec(pathname);
    if (!match) return null;
    return { contest: match[1], page: match[2] ? Number(match[2]) : 1 };
  }

  /** The JSON endpoint LeetCode's own ranking page reads for one page. */
  function rankingApiPath(contest, page) {
    return `/contest/api/ranking/${contest}/?pagination=${page}&region=global_v2`;
  }

  /**
   * Map of user slug to displayed rank for one ranking page.
   *
   * The endpoint's `rank` is zero-based (the page shows rank + 1). Accounts
   * from leetcode.cn are skipped: the predictor reads histories from
   * leetcode.com, where those slugs do not exist.
   */
  function ranksFromRanking(payload) {
    const ranks = new Map();
    for (const row of (payload && payload.total_rank) || []) {
      if (row.data_region && row.data_region !== "US") continue;
      const slug = row.user_slug || row.username;
      if (!USERNAME_RE.test(slug || "") || !Number.isInteger(row.rank)) continue;
      ranks.set(slug, row.rank + 1);
    }
    return ranks;
  }

  /** User slug from a profile link like "/u/name/", or null. */
  function slugFromHref(href) {
    const match = PROFILE_HREF_RE.exec(href || "");
    return match ? decodeURIComponent(match[1]) : null;
  }

  /** "+12.3" / "-4.5" / "0.0". */
  function formatDelta(value) {
    const rounded = Math.round(value * 10) / 10;
    if (rounded > 0) return `+${rounded.toFixed(1)}`;
    if (rounded < 0) return rounded.toFixed(1);
    return "0.0";
  }

  /** Trimmed http(s) origin plus optional path, without a trailing slash. */
  function normalizeApiBase(value) {
    const text = String(value || "").trim();
    if (!text) return DEFAULT_API_BASE;
    let url;
    try {
      url = new URL(text);
    } catch {
      return null;
    }
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    return `${url.origin}${url.pathname}`.replace(/\/+$/, "");
  }

  /** Cache key for one prediction. */
  function predictionKey(contest, username, rank) {
    return `p:${contest}:${username}:${rank}`;
  }

  /** Reduce an /api/predict response to what a badge shows. */
  function summarizePrediction(body) {
    const first = Array.isArray(body) ? body[0] : null;
    if (!first || typeof first.prediction !== "number") return null;
    return {
      delta: first.prediction,
      before: first.rating_before_contest,
      after: first.rating_after_contest,
    };
  }

  /** Seconds to wait from a Retry-After header, clamped to 1-60. */
  function retryAfterSeconds(header) {
    const seconds = Number(header);
    if (!Number.isFinite(seconds) || seconds <= 0) return 5;
    return Math.min(Math.max(Math.ceil(seconds), 1), 60);
  }

  const api = {
    DEFAULT_API_BASE,
    parseRankingPath,
    rankingApiPath,
    ranksFromRanking,
    slugFromHref,
    formatDelta,
    normalizeApiBase,
    predictionKey,
    summarizePrediction,
    retryAfterSeconds,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.LRP = api;
  }
})(typeof self !== "undefined" ? self : globalThis);
