"""Zip the browser extension for the Chrome Web Store.

Writes dist/leetcode-rating-predictor-extension-<version>.zip with only the
files the extension loads (tests and the icon source stay out), after checking
that every file the manifest references is present.

Usage:
    python scripts/package_extension.py
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTENSION = REPO_ROOT / "extension"
EXCLUDE_SUFFIXES = (".test.js", ".svg")


def referenced_files(manifest: dict) -> set[str]:
    files = set(manifest.get("icons", {}).values())
    files.add(manifest["background"]["service_worker"])
    files.add(manifest["options_ui"]["page"])
    files.update(manifest["action"].get("default_icon", {}).values())
    for script in manifest.get("content_scripts", []):
        files.update(script.get("js", []))
        files.update(script.get("css", []))
    return files


def main() -> int:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    missing = sorted(
        f for f in referenced_files(manifest) if not (EXTENSION / f).is_file()
    )
    if missing:
        print(f"manifest references missing files: {missing}", file=sys.stderr)
        return 1

    out = (
        REPO_ROOT
        / "dist"
        / (f"leetcode-rating-predictor-extension-{manifest['version']}.zip")
    )
    out.parent.mkdir(exist_ok=True)
    files = sorted(
        p
        for p in EXTENSION.rglob("*")
        if p.is_file() and not p.name.endswith(EXCLUDE_SUFFIXES)
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(EXTENSION).as_posix())
    print(f"wrote {out.relative_to(REPO_ROOT)} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
