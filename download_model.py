"""Download model artifacts (model.keras, scaler.save) from manifest or env vars.

Usage:
    python download_model.py

Set `MODEL_URL` and `SCALER_URL` environment variables to override manifest.
"""

import os
import sys
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent
MANIFEST_PATH = ROOT / "models" / "manifest.json"


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")

    # support a simple GitHub shorthand: gh:owner/repo/releases/tag/asset_name
    if url.startswith("gh:"):
        # format: gh:owner/repo/releases/tag/<tag>/<asset>
        parts = url[3:].split("/")
        if len(parts) < 5 or parts[2] != "releases" or parts[3] != "tag":
            raise ValueError(
                "Invalid gh: URL format. Use gh:owner/repo/releases/tag/<tag>/<asset_name>"
            )
        owner = parts[0]
        repo = parts[1]
        tag = parts[4]
        asset_name = parts[5] if len(parts) > 5 else None
        if not asset_name:
            raise ValueError("gh: URL must include asset name")

        # Use GitHub API to locate asset id for the given tag
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
        headers = {}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
        r = requests.get(api_url, headers=headers)
        r.raise_for_status()
        release = r.json()
        assets = release.get("assets", [])
        download_url = None
        for a in assets:
            if a.get("name") == asset_name:
                download_url = a.get("browser_download_url")
                break
        if not download_url:
            raise ValueError(f"Asset {asset_name} not found in release {tag}")

        r = requests.get(download_url, headers=headers, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return

    # normal URL
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


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
