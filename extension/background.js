// Service worker: the only place that talks to the predictor API.
//
// Content scripts run under leetcode.com's origin, so a fetch from there would
// need the API to allow that origin. Host permissions let the service worker
// call the API directly, and keeping the queue here means two open ranking tabs
// share one rate-limit budget instead of racing each other.
importScripts("core.js");

const { DEFAULT_API_BASE, normalizeApiBase, predictionKey, summarizePrediction, retryAfterSeconds } =
  self.LRP;

const MAX_CONCURRENT = 2;
const MAX_NETWORK_ATTEMPTS = 3;
// The API allows 30 predictions per minute per IP, so a second ranking page in
// the same minute is expected to hit 429. Waiting out Retry-After is the normal
// path, not a failure; this only caps a server that never lets up.
const MAX_THROTTLED_WAITS = 8;

const queue = [];
let active = 0;
let pausedUntil = 0; // shared by every request once the API says 429

async function apiBase() {
  const { apiBase: stored } = await chrome.storage.sync.get("apiBase");
  return normalizeApiBase(stored) || DEFAULT_API_BASE;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function requestPrediction({ contest, username, rank }) {
  const base = await apiBase();
  let networkErrors = 0;
  let throttled = 0;
  for (;;) {
    const wait = pausedUntil - Date.now();
    if (wait > 0) await sleep(wait);

    let response;
    try {
      response = await fetch(`${base}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, contests: [{ name: contest, rank }] }),
      });
    } catch {
      networkErrors += 1;
      if (networkErrors >= MAX_NETWORK_ATTEMPTS) return { error: "unreachable" };
      await sleep(3000 * networkErrors);
      continue;
    }
    if (response.status === 429) {
      throttled += 1;
      if (throttled > MAX_THROTTLED_WAITS) return { error: "rate-limited" };
      const seconds = retryAfterSeconds(response.headers.get("Retry-After"));
      pausedUntil = Math.max(pausedUntil, Date.now() + seconds * 1000);
      continue;
    }
    if (response.status === 400 || response.status === 422) return { error: "no-history" };
    if (!response.ok) return { error: "unavailable" };
    const summary = summarizePrediction(await response.json());
    return summary || { error: "unavailable" };
  }
}

async function predict(job) {
  const key = predictionKey(job.contest, job.username, job.rank);
  const cached = (await chrome.storage.session.get(key))[key];
  if (cached) return cached;

  const result = await requestPrediction(job);
  // Only cache real answers; a cold or throttled API should be retried later.
  if (!result.error || result.error === "no-history") {
    await chrome.storage.session.set({ [key]: result });
  }
  return result;
}

// A service worker with no events for 30 s is stopped, even mid-wait. Any
// extension API call resets that timer, so tick one while work is pending: a
// cold free-tier API takes ~30 s to answer and a 429 pause can last a minute.
let keepAlive = null;

function updateKeepAlive() {
  if (active || queue.length) {
    keepAlive ??= setInterval(() => chrome.runtime.getPlatformInfo(() => {}), 20000);
  } else if (keepAlive) {
    clearInterval(keepAlive);
    keepAlive = null;
  }
}

function pump() {
  updateKeepAlive();
  while (active < MAX_CONCURRENT && queue.length) {
    const { job, resolve } = queue.shift();
    active += 1;
    predict(job)
      .catch(() => ({ error: "unavailable" }))
      .then(resolve)
      .finally(() => {
        active -= 1;
        pump();
      });
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "predict") {
    queue.push({ job: message, resolve: sendResponse });
    pump();
    return true; // keep the channel open for the async answer
  }
  return false;
});

// The toolbar button opens the settings page.
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
