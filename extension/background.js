// Service worker: owns the model.
//
// Predictions run in the browser, so the only thing fetched here is the model
// itself, from the Hugging Face Hub. It is cached in chrome.storage.local and
// re-checked once a day, which lets a retrain reach every install without a
// store release while ranking pages keep working offline from the cache.
importScripts("core.js");

const { MODEL_URL, validateModel } = self.LRP;

const MODEL_KEY = "model";
const MAX_AGE_MS = 24 * 60 * 60 * 1000;
// After a failed refresh, keep serving the cached model and wait this long
// before asking the Hub again, instead of retrying on every page view.
const RETRY_AFTER_FAILURE_MS = 10 * 60 * 1000;

let inflight = null;
let lastFailure = 0;

// The content script caches contest histories in session storage, which only
// extension pages can reach by default.
void chrome.storage.session
  .setAccessLevel({ accessLevel: "TRUSTED_AND_UNTRUSTED_CONTEXTS" })
  .catch(() => {});

async function fetchModel() {
  const response = await fetch(MODEL_URL, { cache: "no-cache" });
  if (!response.ok) throw new Error(`model fetch failed: HTTP ${response.status}`);
  const model = validateModel(await response.json());
  const entry = {
    model,
    revision: response.headers.get("X-Repo-Commit"),
    fetchedAt: Date.now(),
  };
  await chrome.storage.local.set({ [MODEL_KEY]: entry });
  return entry;
}

async function cachedModel() {
  const entry = (await chrome.storage.local.get(MODEL_KEY))[MODEL_KEY];
  if (!entry) return null;
  try {
    // A cache written by an older extension version may not fit this one.
    validateModel(entry.model);
    return entry;
  } catch {
    return null;
  }
}

async function getModel(force) {
  const cached = await cachedModel();
  const stale = !cached || Date.now() - cached.fetchedAt > MAX_AGE_MS;
  const backingOff = Date.now() - lastFailure < RETRY_AFTER_FAILURE_MS;
  if (cached && !force && (!stale || backingOff)) return cached;

  inflight ??= fetchModel().finally(() => {
    inflight = null;
  });
  try {
    return await inflight;
  } catch (error) {
    lastFailure = Date.now();
    // Pages keep predicting from the cache; an explicit check reports failure.
    if (cached && !force) return cached;
    throw error;
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "model" && message?.type !== "refresh-model") return false;
  getModel(message.type === "refresh-model")
    .then(({ model, revision, fetchedAt }) => sendResponse({ model, revision, fetchedAt }))
    .catch(() => sendResponse({ error: "model-unavailable" }));
  return true; // keep the channel open for the async answer
});

// The toolbar button opens the model status page.
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
