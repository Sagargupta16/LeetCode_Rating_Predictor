// Settings page: choose which predictor API the extension calls.
const { DEFAULT_API_BASE, normalizeApiBase } = self.LRP;

const form = document.getElementById("settings");
const input = document.getElementById("apiBase");
const status = document.getElementById("status");

function say(text, ok) {
  status.textContent = text;
  status.className = ok ? "ok" : "err";
}

async function grant(base) {
  // The default host ships in host_permissions; anything else is requested on
  // save so the extension only ever reaches the server you picked.
  const origin = `${new URL(base).origin}/*`;
  if (await chrome.permissions.contains({ origins: [origin] })) return true;
  return chrome.permissions.request({ origins: [origin] });
}

async function check(base) {
  say("Checking... a sleeping free-tier server can take up to a minute.", true);
  try {
    const response = await fetch(`${base}/api/health`);
    const body = await response.json();
    if (body.status === "healthy" && body.model_loaded) {
      say(`Connected to ${base}`, true);
    } else {
      say(`${base} answered but the model is not loaded`, false);
    }
  } catch {
    say(`Could not reach ${base}`, false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const base = normalizeApiBase(input.value);
  if (!base) {
    say("Enter an http(s) URL", false);
    return;
  }
  if (!(await grant(base))) {
    say("Permission to reach that server was not granted", false);
    return;
  }
  await chrome.storage.sync.set({ apiBase: base });
  input.value = base;
  say("Saved", true);
});

document.getElementById("check").addEventListener("click", () => {
  const base = normalizeApiBase(input.value);
  if (base) check(base);
  else say("Enter an http(s) URL", false);
});

document.getElementById("reset").addEventListener("click", async () => {
  await chrome.storage.sync.remove("apiBase");
  input.value = DEFAULT_API_BASE;
  say("Using the public demo", true);
});

chrome.storage.sync.get("apiBase").then(({ apiBase }) => {
  input.value = apiBase || DEFAULT_API_BASE;
});
