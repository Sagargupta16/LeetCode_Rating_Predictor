"""Download model artifacts (model.keras, scaler.save) from manifest or env vars.

Usage:
    python download_model.py

Set `MODEL_URL` and `SCALER_URL` environment variables to override manifest.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent.parent  # project root (one level up from scripts/)
MANIFEST_PATH = ROOT / "models" / "manifest.json"

# Only allow http(s) schemes
ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """Reject non-http(s) URLs to prevent local file access."""
    if url.startswith("gh:"):
        return  # GitHub shorthand handled separately
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. Use http or https."
        )


def _stream_to_file(url: str, dest: Path, headers: dict | None = None):
    """Download a URL to a local file using streaming."""
    r = requests.get(url, headers=headers or {}, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def _resolve_gh_url(gh_url: str) -> tuple[str, dict]:
    """Parse a gh: shorthand URL and return (download_url, headers)."""
    parts = gh_url[3:].split("/")
    if len(parts) < 6 or parts[2] != "releases" or parts[3] != "tag":
        raise ValueError(
            "Invalid gh: URL format. Use gh:owner/repo/releases/tag/<tag>/<asset_name>"
        )
    owner, repo, tag, asset_name = parts[0], parts[1], parts[4], parts[5]

    # Validate owner/repo to prevent injection
    for label, value in [("owner", owner), ("repo", repo)]:
        if not re.match(r"^[a-zA-Z0-9_.-]+$", value):
            raise ValueError(f"Invalid GitHub {label} format")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    r = requests.get(api_url, headers=headers, timeout=30)
    r.raise_for_status()
    assets = r.json().get("assets", [])
    for a in assets:
        if a.get("name") == asset_name:
            return a["browser_download_url"], headers

    raise ValueError(f"Asset {asset_name} not found in release {tag}")


def download(url: str, dest: Path):
    _validate_url(url)
    # Resolve dest and ensure it stays within the project root
    resolved = dest.resolve()
    if not str(resolved).startswith(str(ROOT.resolve())):
        raise ValueError(f"Destination {dest} is outside the project root")

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")

    if url.startswith("gh:"):
        download_url, headers = _resolve_gh_url(url)
        _stream_to_file(download_url, resolved, headers)
    else:
        _stream_to_file(url, resolved)


def main():
    model_url = os.environ.get("MODEL_URL")
    scaler_url = os.environ.get("SCALER_URL")

    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        model_url = model_url or manifest.get("model.keras", {}).get("url")
        scaler_url = scaler_url or manifest.get("scaler.save", {}).get("url")

    if not model_url or not scaler_url:
        print(
            "Model or scaler URL not provided. Set MODEL_URL/SCALER_URL or update models/manifest.json"
        )
        sys.exit(1)

    try:
        download(model_url, ROOT / "model.keras")
        download(scaler_url, ROOT / "scaler.save")
    except Exception as e:
        print(f"Failed to download artifacts: {e}")
        sys.exit(2)

    print("Done. Model artifacts saved to ./model.keras and ./scaler.save")


if __name__ == "__main__":
    main()
