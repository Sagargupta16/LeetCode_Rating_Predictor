// Model status page: what the extension predicts with, and a manual refresh.
const trained = document.getElementById("trained");
const revision = document.getElementById("revision");
const fetched = document.getElementById("fetched");
const refresh = document.getElementById("refresh");
const statusLine = document.getElementById("status");

function say(text, ok) {
  statusLine.textContent = text;
  statusLine.className = ok ? "ok" : "err";
}

function show(entry) {
  if (!entry?.model) return;
  trained.textContent = entry.model.trained || "unknown";
  revision.textContent = entry.revision ? entry.revision.slice(0, 7) : "unknown";
  fetched.textContent = new Date(entry.fetchedAt).toLocaleString();
}

refresh.addEventListener("click", () => {
  refresh.disabled = true;
  say("Checking Hugging Face...", true);
  chrome.runtime.sendMessage({ type: "refresh-model" }, (result) => {
    refresh.disabled = false;
    if (chrome.runtime.lastError || !result || result.error) {
      say("Could not reach Hugging Face; the extension keeps the model it has.", false);
      return;
    }
    show(result);
    say("Up to date", true);
  });
});

const { model } = await chrome.storage.local.get("model");
show(model);
