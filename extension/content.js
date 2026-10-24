// Runs on leetcode.com contest ranking pages. Reads the page's own ranking
// JSON for the visible page, reads each listed user's contest history from
// LeetCode's GraphQL endpoint (same origin, like the site itself does), and
// runs the model in the browser to put a predicted rating change next to each
// name. Nothing is sent anywhere but leetcode.com; the model comes from the
// service worker. The ranking page is a single-page app, so it re-checks on
// DOM changes and URL changes instead of only on load.
(function () {
  "use strict";

  const {
    HISTORY_QUERY,
    parseRankingPath,
    rankingApiPath,
    ranksFromRanking,
    slugFromHref,
    formatDelta,
    predictionKey,
    retryAfterSeconds,
    parseHistoryPayload,
    predictContest,
  } = self.LRP;

  const BADGE_ATTR = "data-lrp-key";
  const HISTORY_TTL_MS = 60 * 60 * 1000;
  const MAX_CONCURRENT_HISTORY = 2;
  const MAX_HISTORY_ATTEMPTS = 4;

  const rankingCache = new Map(); // "contest:page" -> Promise<Map<slug, rank>>
  const historyCache = new Map(); // username -> Promise<{history, currentRating}>
  const stats = { done: 0, total: 0, failed: 0 };
  let pill;
  let scheduled = false;
  let modelPromise = null;

  const ERROR_TITLES = {
    "model-unavailable": "Could not load the model from Hugging Face, reload to retry",
    "history-unavailable": "Could not read this user's contest history from LeetCode, reload to retry",
    invalid: "The model gave an implausible result for this user",
  };

  function loadRanks(contest, page) {
    const key = `${contest}:${page}`;
    if (!rankingCache.has(key)) {
      const request = fetch(rankingApiPath(contest, page), { credentials: "include" })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
        .then(ranksFromRanking)
        .catch((error) => {
          rankingCache.delete(key);
          throw error;
        });
      rankingCache.set(key, request);
    }
    return rankingCache.get(key);
  }

  // --- Model (from the service worker) ------------------------------------

  function askServiceWorker(message, attempt = 1) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(message, (result) => {
        if (chrome.runtime.lastError || !result) {
          // The service worker can be restarted mid-request; ask once more.
          if (attempt < 2) {
            setTimeout(() => askServiceWorker(message, attempt + 1).then(resolve), 1000);
          } else {
            resolve({ error: "model-unavailable" });
          }
          return;
        }
        resolve(result);
      });
    });
  }

  function loadModel() {
    modelPromise ??= askServiceWorker({ type: "model" }).then((result) => {
      if (result.error || !result.model) {
        modelPromise = null; // let the next pass try again
        throw new Error("model-unavailable");
      }
      return result.model;
    });
    return modelPromise;
  }

  // --- Histories (from leetcode.com/graphql) ------------------------------

  const queue = [];
  let active = 0;
  let pausedUntil = 0; // shared by every request once LeetCode says 429

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function csrfToken() {
    const match = /(?:^|;\s*)csrftoken=([^;]+)/.exec(document.cookie);
    return match ? decodeURIComponent(match[1]) : null;
  }

  async function fetchHistory(username) {
    const headers = { "Content-Type": "application/json" };
    const csrf = csrfToken();
    if (csrf) headers["x-csrftoken"] = csrf;
    const body = JSON.stringify({ query: HISTORY_QUERY, variables: { username } });

    for (let attempt = 1; attempt <= MAX_HISTORY_ATTEMPTS; attempt++) {
      const wait = pausedUntil - Date.now();
      if (wait > 0) await sleep(wait);

      let response = null;
      try {
        response = await fetch("/graphql/", {
          method: "POST",
          credentials: "include",
          headers,
          body,
        });
      } catch {
        await sleep(2000 * attempt); // network blip
        continue;
      }
      if (response.ok) {
        const parsed = parseHistoryPayload(await response.json());
        if (parsed) return parsed;
        throw new Error("history-unavailable");
      }
      if (response.status !== 429 && response.status < 500) break;
      const seconds = retryAfterSeconds(response.headers.get("Retry-After"));
      pausedUntil = Math.max(pausedUntil, Date.now() + seconds * 1000);
    }
    throw new Error("history-unavailable");
  }

  function pump() {
    while (active < MAX_CONCURRENT_HISTORY && queue.length) {
      const { username, resolve, reject } = queue.shift();
      active += 1;
      fetchHistory(username)
        .then(resolve, reject)
        .finally(() => {
          active -= 1;
          pump();
        });
    }
  }

  // Session storage is a cache only: if it is unreachable (the service worker
  // has not granted access yet), fall through to a fetch.
  async function readSession(key) {
    try {
      return (await chrome.storage.session.get(key))[key];
    } catch {
      return undefined;
    }
  }

  async function cachedHistory(username) {
    const key = `h:${username}`;
    const entry = await readSession(key);
    if (entry && Date.now() - entry.fetchedAt < HISTORY_TTL_MS) return entry.record;
    const record = await new Promise((resolve, reject) => {
      queue.push({ username, resolve, reject });
      pump();
    });
    // A failed write only costs a refetch later, so it is ignored.
    try {
      await chrome.storage.session.set({ [key]: { record, fetchedAt: Date.now() } });
    } catch {
      // not cached
    }
    return record;
  }

  function loadHistory(username) {
    if (!historyCache.has(username)) {
      historyCache.set(
        username,
        cachedHistory(username).catch((error) => {
          historyCache.delete(username); // retry on the next pass
          throw error;
        }),
      );
    }
    return historyCache.get(username);
  }

  async function predict(contest, username, rank) {
    let model;
    try {
      model = await loadModel();
    } catch {
      return { error: "model-unavailable" };
    }
    let record;
    try {
      record = await loadHistory(username);
    } catch {
      return { error: "history-unavailable" };
    }
    try {
      return predictContest(model, { ...record, contest, rank });
    } catch {
      return { error: "invalid" };
    }
  }

  // --- Page ---------------------------------------------------------------

  function ensurePill() {
    if (pill?.isConnected) return pill;
    pill = document.createElement("div");
    pill.className = "lrp-pill";
    pill.setAttribute("role", "status");
    document.body.appendChild(pill);
    return pill;
  }

  function renderPill() {
    const el = ensurePill();
    if (!stats.total) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    let text = `Rating predictor: ${stats.done}/${stats.total}`;
    if (stats.failed) text += `, ${stats.failed} unavailable`;
    el.textContent = text;
    el.classList.toggle("lrp-pill--done", stats.done + stats.failed >= stats.total);
  }

  function showResult(badge, result, rank) {
    badge.classList.remove("lrp-badge--pending");
    if (result.error) {
      badge.textContent = "n/a";
      badge.classList.add("lrp-badge--na");
      badge.title = ERROR_TITLES[result.error] || ERROR_TITLES.invalid;
      return;
    }
    badge.textContent = formatDelta(result.delta);
    badge.classList.add(result.delta >= 0 ? "lrp-badge--up" : "lrp-badge--down");
    let title =
      `Predicted rating change at rank ${rank}: ` +
      `${result.before.toFixed(1)} -> ${result.after.toFixed(1)}`;
    if (result.actual !== null) {
      title += `. Already rated: LeetCode applied ${formatDelta(result.actual)}`;
    }
    badge.title = title;
  }

  // LeetCode renders the ranking as rows of flex cells (name, score, finish
  // time, one per question) under a header row with the same cells. Adding a
  // fixed-width cell after "Score" in every row and in the header gives the
  // prediction its own aligned column instead of squeezing the name. Every
  // row gets the cell, including rows without a prediction, so the columns
  // after it stay aligned. If the layout ever changes (no "Score" header or a
  // non-numeric score), no column is added and the badge sits next to the name.
  function columnSlot(link) {
    const nameCell = link.parentElement?.parentElement;
    const scoreCell = nameCell?.nextElementSibling;
    if (!scoreCell || !/^\d+(\.\d+)?$/.test(scoreCell.textContent.trim())) return null;

    const table = nameCell.parentElement?.parentElement?.parentElement;
    const headScore = table?.firstElementChild?.children[1];
    if (!headScore) return null;
    if (!headScore.nextElementSibling?.classList.contains("lrp-cell")) {
      if (headScore.textContent.trim() !== "Score") return null;
      const head = document.createElement("div");
      head.className = "lrp-cell lrp-head";
      head.textContent = "Predicted";
      head.title = "Predicted rating change (LeetCode Rating Predictor extension)";
      headScore.after(head);
    }

    let cell = scoreCell.nextElementSibling;
    if (!cell?.classList.contains("lrp-cell")) {
      cell = document.createElement("div");
      cell.className = "lrp-cell";
      scoreCell.after(cell);
    }
    return cell;
  }

  function placeBadge(link, badge) {
    const cell = columnSlot(link);
    if (cell) {
      cell.replaceChildren(badge);
    } else {
      link.after(badge);
    }
  }

  function existingBadge(link) {
    const cell = columnSlot(link);
    const scope = cell || link.parentElement;
    return scope.querySelector(`[${BADGE_ATTR}]`);
  }

  async function decorate() {
    scheduled = false;
    const route = parseRankingPath(location.pathname);
    if (!route) return;

    let ranks;
    try {
      ranks = await loadRanks(route.contest, route.page);
    } catch {
      return; // ranking not published yet or the endpoint changed
    }

    // Profile links include leetcode.cn accounts ("https://leetcode.cn/u/x"),
    // which get an empty cell but no prediction. existingBadge() adds that
    // cell, and removing the badge clears one left from a reused row.
    for (const link of document.querySelectorAll('a[href*="/u/"]')) {
      const slug = slugFromHref(link.getAttribute("href"));
      const rank = slug && ranks.get(slug);
      if (!rank) {
        existingBadge(link)?.remove();
        continue;
      }
      const key = predictionKey(route.contest, slug, rank);
      const existing = existingBadge(link);
      if (existing?.getAttribute(BADGE_ATTR) === key) continue;
      if (existing) existing.remove();

      const badge = document.createElement("span");
      badge.className = "lrp-badge lrp-badge--pending";
      badge.setAttribute(BADGE_ATTR, key);
      badge.textContent = "...";
      badge.title = "Predicting rating change";
      placeBadge(link, badge);

      stats.total += 1;
      renderPill();
      void predict(route.contest, slug, rank).then((result) => {
        if (!badge.isConnected) return;
        showResult(badge, result, rank);
        if (result.error) stats.failed += 1;
        else stats.done += 1;
        renderPill();
      });
    }
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(decorate, 300);
  }

  let lastPath = location.pathname;
  new MutationObserver(() => {
    if (location.pathname !== lastPath) {
      lastPath = location.pathname;
      Object.assign(stats, { done: 0, total: 0, failed: 0 });
      renderPill();
    }
    schedule();
  }).observe(document.documentElement, { childList: true, subtree: true });
  schedule();
})();
