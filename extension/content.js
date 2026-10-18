// Runs on leetcode.com contest ranking pages. Reads the page's own ranking
// JSON for the visible page, then puts a predicted rating change next to each
// name. The ranking page is a single-page app, so it re-checks on DOM changes
// and URL changes instead of only on load.
(function () {
  "use strict";

  const { parseRankingPath, rankingApiPath, ranksFromRanking, slugFromHref, formatDelta } =
    self.LRP;

  const BADGE_ATTR = "data-lrp-key";
  const rankingCache = new Map(); // "contest:page" -> Promise<Map<slug, rank>>
  const stats = { done: 0, total: 0, waking: false, failed: 0, missing: 0 };
  let pill;
  let scheduled = false;

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

  function ensurePill() {
    if (pill && pill.isConnected) return pill;
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
    if (stats.waking && stats.done === 0) text += " (waking the API, up to a minute)";
    if (stats.missing) text += `, ${stats.missing} without rated history`;
    if (stats.failed) text += `, ${stats.failed} unavailable`;
    el.textContent = text;
    el.classList.toggle(
      "lrp-pill--done",
      stats.done + stats.missing + stats.failed >= stats.total,
    );
  }

  function sendPredict(job, attempt = 1) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: "predict", ...job }, (result) => {
        if (chrome.runtime.lastError || !result) {
          // The service worker can be restarted mid-request; ask once more.
          if (attempt < 2) {
            setTimeout(() => sendPredict(job, attempt + 1).then(resolve), 2000);
          } else {
            resolve({ error: "unavailable" });
          }
          return;
        }
        resolve(result);
      });
    });
  }

  function showResult(badge, result, rank) {
    badge.classList.remove("lrp-badge--pending");
    if (result.error) {
      badge.textContent = "n/a";
      badge.classList.add("lrp-badge--na");
      badge.title =
        result.error === "no-history"
          ? "No rated contest history on leetcode.com"
          : "Predictor API unavailable, reload to retry";
      return;
    }
    badge.textContent = formatDelta(result.delta);
    badge.classList.add(result.delta >= 0 ? "lrp-badge--up" : "lrp-badge--down");
    badge.title =
      `Predicted rating change at rank ${rank}: ` +
      `${result.before.toFixed(1)} -> ${result.after.toFixed(1)}`;
  }

  // LeetCode renders the ranking as rows of flex cells (name, score, finish
  // time, one per question) under a header row with the same cells. Adding a
  // fixed-width cell after "Score" in every row and in the header gives the
  // prediction its own aligned column instead of squeezing the name. Every
  // row gets the cell, including rows without a prediction, so the columns
  // after it stay aligned. If the layout ever changes (no "Score" header or a
  // non-numeric score), no column is added and the badge sits next to the name.
  function columnSlot(link) {
    const nameCell = link.parentElement && link.parentElement.parentElement;
    const scoreCell = nameCell && nameCell.nextElementSibling;
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
      headScore.insertAdjacentElement("afterend", head);
    }

    let cell = scoreCell.nextElementSibling;
    if (!cell || !cell.classList.contains("lrp-cell")) {
      cell = document.createElement("div");
      cell.className = "lrp-cell";
      scoreCell.insertAdjacentElement("afterend", cell);
    }
    return cell;
  }

  function placeBadge(link, badge) {
    const cell = columnSlot(link);
    if (cell) {
      cell.replaceChildren(badge);
    } else {
      link.insertAdjacentElement("afterend", badge);
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
      const key = `${route.contest}:${slug}:${rank}`;
      const existing = existingBadge(link);
      if (existing && existing.getAttribute(BADGE_ATTR) === key) continue;
      if (existing) existing.remove();

      const badge = document.createElement("span");
      badge.className = "lrp-badge lrp-badge--pending";
      badge.setAttribute(BADGE_ATTR, key);
      badge.textContent = "...";
      badge.title = "Predicting rating change";
      placeBadge(link, badge);

      stats.total += 1;
      const waking = setTimeout(() => {
        stats.waking = true;
        renderPill();
      }, 5000);
      renderPill();
      sendPredict({ contest: route.contest, username: slug, rank }).then((result) => {
        clearTimeout(waking);
        if (!badge.isConnected) return;
        showResult(badge, result, rank);
        if (!result.error) stats.done += 1;
        else if (result.error === "no-history") stats.missing += 1;
        else stats.failed += 1;
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
      Object.assign(stats, { done: 0, total: 0, waking: false, failed: 0, missing: 0 });
      renderPill();
    }
    schedule();
  }).observe(document.documentElement, { childList: true, subtree: true });
  schedule();
})();
