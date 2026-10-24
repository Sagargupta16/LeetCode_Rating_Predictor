// Pure helpers shared by the content script, the service worker and the tests.
// Loaded as a classic script in the extension and with require() under Node.
(function (root) {
  "use strict";

  // The model is published on the Hugging Face Hub, so a retrain reaches the
  // extension without a store release.
  const MODEL_URL =
    "https://huggingface.co/sagargupta16/leetcode-rating-predictor/resolve/main/model.json";
  const MODEL_FORMAT = "leetcode-rating-predictor/dense-v1";
  // Bumped with the model's feature_version whenever the inputs change, so an
  // old extension never feeds a new model the wrong vector.
  const FEATURE_VERSION = 1;
  const FEATURE_NAMES = [
    "rating_before",
    "rank",
    "participants",
    "rank_percent",
    "contest_index",
    "avg_solve_rate",
    "avg_finish_time",
    "recent_solve_rate",
    "recent_finish_time",
    "rating_trend",
    "max_rating",
    "log_rank",
    "rating_x_rank_share",
    "solve_rate_x_rating",
    "finish_time_share",
  ];

  // Same constants as app/services/features.py.
  const DEFAULT_RATING = 1500;
  const DEFAULT_SOLVE_RATE = 0.5;
  const DEFAULT_FINISH_TIME = 3000;
  const CONTEST_SECONDS = 5400;
  // The API refuses predictions beyond this (MAX_RATING_CHANGE); so does this.
  const MAX_RATING_CHANGE = 500;

  const HISTORY_QUERY = `query userContestRankingInfo($username: String!) {
  userContestRanking(username: $username) {
    rating
  }
  userContestRankingHistory(username: $username) {
    attended
    rating
    ranking
    problemsSolved
    totalProblems
    finishTimeInSeconds
    contest {
      titleSlug
    }
  }
}`;

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
   * from leetcode.cn are skipped: their histories are not on leetcode.com.
   */
  function ranksFromRanking(payload) {
    const ranks = new Map();
    for (const row of payload?.total_rank || []) {
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

  /** Key for one badge: the same contest, user and rank is the same answer. */
  function predictionKey(contest, username, rank) {
    return `p:${contest}:${username}:${rank}`;
  }

  /** Seconds to wait from a Retry-After header, clamped to 1-60. */
  function retryAfterSeconds(header) {
    const seconds = Number(header);
    if (!Number.isFinite(seconds) || seconds <= 0) return 5;
    return Math.min(Math.max(Math.ceil(seconds), 1), 60);
  }

  /** {history, currentRating} from a HISTORY_QUERY response, or null. */
  function parseHistoryPayload(payload) {
    const data = payload?.data;
    if (!data) return null;
    const history = Array.isArray(data.userContestRankingHistory)
      ? data.userContestRankingHistory
      : [];
    const rating = data.userContestRanking?.rating;
    // A real account before its first rated contest has no ranking; the
    // training data starts every user at 1500, like the API.
    return {
      history,
      currentRating: typeof rating === "number" ? rating : DEFAULT_RATING,
    };
  }

  // ---------------------------------------------------------------------------
  // Features: a line-by-line port of app/services/features.py. The parity
  // fixture in tests/fixtures/extension_parity.json pins this to the Python.
  // ---------------------------------------------------------------------------

  // Python's sum() over floats (3.12+) uses Neumaier compensated summation.
  // Doing the same keeps the features bit-identical to the Python ones.
  function pySum(values) {
    let total = 0;
    let compensation = 0;
    for (const x of values) {
      const t = total + x;
      if (Math.abs(total) >= Math.abs(x)) compensation += total - t + x;
      else compensation += x - t + total;
      total = t;
    }
    return compensation && Number.isFinite(compensation) ? total + compensation : total;
  }

  function avg(values, fallback) {
    return values.length ? pySum(values) / values.length : fallback;
  }

  /** Per-user model inputs from a userContestRankingHistory list. */
  function summarizeHistory(history) {
    // Entries with ranking 0 are placeholders: counted in contestIndex, but
    // left out of the averages, as in the training data.
    const attended = history.filter((h) => h.attended && h.ranking);
    const solveRates = [];
    const finishTimes = [];
    const ratings = [];
    for (const h of attended) {
      const total = h.totalProblems || 4;
      const solved = h.problemsSolved || 0;
      solveRates.push(solved / total);
      finishTimes.push(h.finishTimeInSeconds || 0);
      ratings.push(h.rating === undefined ? DEFAULT_RATING : h.rating);
    }

    // A finish time of 0 means nothing was accepted. Take the last 5 contests
    // first and only then drop the zeros, like the training script.
    const changes = [];
    for (let i = 1; i < ratings.length; i++) changes.push(ratings[i] - ratings[i - 1]);
    const allFinish = finishTimes.filter((t) => t > 0);
    const recentFinish = finishTimes.slice(-5).filter((t) => t > 0);
    return {
      avgSolveRate: avg(solveRates, DEFAULT_SOLVE_RATE),
      avgFinishTime: avg(allFinish, DEFAULT_FINISH_TIME),
      recentSolveRate: avg(solveRates.slice(-5), DEFAULT_SOLVE_RATE),
      recentFinishTime: avg(recentFinish, DEFAULT_FINISH_TIME),
      ratingTrend: avg(changes.slice(-5), 0),
      maxRating: ratings.length ? Math.max(...ratings) : DEFAULT_RATING,
      contestIndex: history.length,
    };
  }

  /** The training data's participant count: max(rank * 1.5, 10000). */
  function modelParticipants(rank) {
    return Math.max(Math.trunc(rank * 1.5), 10000);
  }

  /** The 15 inputs for one contest result, in model order. */
  function buildFeatures(user, rating, rank, contestIndex) {
    const participants = modelParticipants(rank);
    const avgSolveRate = user.avgSolveRate;
    const avgFinishTime = user.avgFinishTime;
    return [
      rating,
      rank,
      participants,
      (rank * 100) / participants,
      contestIndex,
      avgSolveRate,
      avgFinishTime,
      user.recentSolveRate,
      user.recentFinishTime,
      user.ratingTrend,
      user.maxRating,
      Math.log1p(rank),
      (rating * rank) / participants,
      avgSolveRate * rating,
      avgFinishTime / CONTEST_SECONDS,
    ];
  }

  /** Contest slug to history index, for contests LeetCode already rated. */
  function ratedPositions(history) {
    const positions = new Map();
    history.forEach((h, i) => {
      const slug = h.contest?.titleSlug;
      if (slug && h.attended && h.ranking && h.rating) positions.set(slug, i);
    });
    return positions;
  }

  /** Features for history[index] from the contests before it only. */
  function replayFeatures(history, index, rank) {
    const before = history.slice(0, index);
    const prior = before.filter((h) => h.attended && h.rating);
    const rating = prior.length ? prior[prior.length - 1].rating : DEFAULT_RATING;
    const user = summarizeHistory(before);
    return { features: buildFeatures(user, rating, rank, user.contestIndex), rating };
  }

  // ---------------------------------------------------------------------------
  // Model
  // ---------------------------------------------------------------------------

  function isNumberArray(value, length) {
    return (
      Array.isArray(value) &&
      value.length === length &&
      value.every((v) => typeof v === "number" && Number.isFinite(v))
    );
  }

  /** Throws unless `model` is a model.json this code can run. */
  function validateModel(model) {
    if (!model || typeof model !== "object") throw new Error("model is not an object");
    if (model.format !== MODEL_FORMAT) throw new Error(`unknown format ${model.format}`);
    if (model.feature_version !== FEATURE_VERSION) {
      throw new Error(`feature_version ${model.feature_version}, expected ${FEATURE_VERSION}`);
    }
    if (model.input_dim !== FEATURE_NAMES.length) {
      throw new Error(`input_dim ${model.input_dim}, expected ${FEATURE_NAMES.length}`);
    }
    if (
      !Array.isArray(model.features) ||
      model.features.length !== FEATURE_NAMES.length ||
      model.features.some((name, i) => name !== FEATURE_NAMES[i])
    ) {
      throw new Error("features do not match the inputs this extension builds");
    }
    const scaler = model.scaler || {};
    if (!isNumberArray(scaler.scale, model.input_dim) || !isNumberArray(scaler.min, model.input_dim)) {
      throw new Error("scaler does not match input_dim");
    }
    if (!Array.isArray(model.layers) || !model.layers.length) throw new Error("model has no layers");
    let width = model.input_dim;
    for (const [i, layer] of model.layers.entries()) {
      if (layer.activation !== "relu" && layer.activation !== "linear") {
        throw new Error(`layer ${i}: unsupported activation ${layer.activation}`);
      }
      const units = layer.units;
      if (!Number.isInteger(units) || !isNumberArray(layer.bias, units)) {
        throw new Error(`layer ${i}: bias does not match units`);
      }
      if (
        !Array.isArray(layer.kernel) ||
        layer.kernel.length !== width ||
        !layer.kernel.every((row) => isNumberArray(row, units))
      ) {
        throw new Error(`layer ${i}: kernel is not ${width} x ${units}`);
      }
      width = units;
    }
    if (width !== 1) throw new Error(`output width ${width}, expected 1`);
    return model;
  }

  /** Scale the inputs and run the Dense stack; returns the rating change. */
  function forward(model, features) {
    let x = features.map((v, i) => v * model.scaler.scale[i] + model.scaler.min[i]);
    for (const layer of model.layers) {
      const out = new Array(layer.units).fill(0);
      for (let i = 0; i < x.length; i++) {
        const row = layer.kernel[i];
        for (let j = 0; j < out.length; j++) out[j] += x[i] * row[j];
      }
      for (let j = 0; j < out.length; j++) {
        out[j] += layer.bias[j];
        if (layer.activation === "relu" && out[j] < 0) out[j] = 0;
      }
      x = out;
    }
    return x[0];
  }

  /**
   * Predicted change for one contest result.
   *
   * Like /api/predict: a contest LeetCode already rated is scored from the
   * history before it and reports the change LeetCode applied (`actual`);
   * otherwise it starts from the current rating and `actual` is null.
   */
  function predictContest(model, { history, currentRating, contest, rank }) {
    const index = ratedPositions(history).get(contest);
    let features;
    let before;
    let actual = null;
    if (index === undefined) {
      const user = summarizeHistory(history);
      features = buildFeatures(user, currentRating, rank, user.contestIndex);
      before = currentRating;
    } else {
      ({ features, rating: before } = replayFeatures(history, index, rank));
      actual = history[index].rating - before;
    }
    const delta = forward(model, features);
    if (!Number.isFinite(delta) || Math.abs(delta) > MAX_RATING_CHANGE) {
      throw new Error(`implausible prediction ${delta}`);
    }
    return { delta, before, after: before + delta, actual, features };
  }

  const api = {
    MODEL_URL,
    MODEL_FORMAT,
    FEATURE_VERSION,
    FEATURE_NAMES,
    DEFAULT_RATING,
    HISTORY_QUERY,
    parseRankingPath,
    rankingApiPath,
    ranksFromRanking,
    slugFromHref,
    formatDelta,
    predictionKey,
    retryAfterSeconds,
    parseHistoryPayload,
    summarizeHistory,
    modelParticipants,
    buildFeatures,
    ratedPositions,
    replayFeatures,
    validateModel,
    forward,
    predictContest,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.LRP = api;
  }
})(typeof self !== "undefined" ? self : globalThis);
