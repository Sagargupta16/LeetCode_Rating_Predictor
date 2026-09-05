# Changelog

## [2.3.3] - 2026-09-05

### Fixed

- **The weekly refresh aborted on a completely healthy run.** The 2026-09-03 run
  fetched all 8,000 users with **zero** failures, collected 197,991 records
  against the 244,950 committed, and tripped the 95% retention floor at 80.8%.
  The floor was right; `DEFAULT_MAX_USERS` was wrong. It was sized on an assumed
  ~90% contribution rate, but the measured rate is **68.2%**: 5,460 of 8,000
  users contributed and 2,540 have no contest history at all, so a third of
  `usernames.json` belongs to accounts that never entered a contest. 8,000
  attempts can therefore never reach the committed record count. Raised to
  **12,000** (~8,190 contributors, ~297K records, ~65 MB), which clears the
  dataset by 21% and stays well under GitHub's 100 MB per-file limit. The
  constant now carries the measured table so the next change starts from data.
- **The abort message blamed the wrong thing.** It read "0 of 8000 fetches
  failed, which usually means LeetCode throttled the run" -- on a run with no
  failures. The diagnosis now branches: with failures it points at throttling and
  suggests a re-run; with none it says plainly that throttling is not the cause
  and that `--users` is too low, explicitly steering away from lowering the floor.

## [2.3.2] - 2026-09-03

### Fixed

- **The weekly data refresh could delete half the training set without failing.**
  Its first successful run (PR #162) came back with 123,513 records against the
  244,950 already committed, and every check passed. Three separate causes:
  - `scripts/update_data.py` asked interactively how many users to process, so
    under CI `input()` raised `EOFError` and it silently fell back to
    `min(5000, len(usernames))`. The committed dataset was built from 6,830
    contributing users, so the cron could never reproduce it -- even a flawless
    run over 5,000 users lands ~27% short. `--users` now defaults to 8,000.
  - A throttled fetch was indistinguishable from an account with no contests:
    any non-200 returned `[]`, exactly like an empty history. 1,560 of 5,000
    users "failed" that way. Retryable statuses (429, 5xx) and network errors
    now retry with exponential backoff honouring `Retry-After`, and a failed
    fetch returns `None` so the summary counts failures apart from empty
    accounts.
  - Nothing compared the new dataset against the old before overwriting it.
    A run retaining less than `--min-retention` (default 95%) of the committed
    records now aborts with a non-zero exit instead of writing, which fails the
    workflow rather than opening a data-destroying PR. `--force` overrides it.
- `data/data.json` is written through a temp file and `os.replace`, so an
  interrupted run can no longer truncate the committed dataset.
- Dropped a `time.sleep(0.05)` in the result-consuming loop. All futures are
  submitted up front, so it throttled nothing and only added latency -- 250s of
  pure sleep across 5,000 users.

### Added

- `scripts/update_data.py` flags: `--users`, `--workers`, `--min-retention`,
  `--force`. The user cap is bounded by GitHub's 100 MB per-file hard limit:
  at ~8.3 KB per contributing user, all 43,158 usernames would produce roughly
  a 307 MB `data.json` that could never be pushed. The script logs the written
  file size and warns past 90 MB.

## [2.3.1] - 2026-09-02

### Fixed

- **`Refresh training data` workflow failed on every scheduled run since
  2026-08-17.** `peter-evans/create-pull-request` v7.0.8 runs
  `git remote prune origin` against the credentials `actions/checkout@v6`
  persists, which sends a duplicate `Authorization` header that GitHub rejects
  with HTTP 400 (`fatal: ... error: 400`, exit 128). Bumped to v8.1.1
  (SHA-pinned), which targets checkout@v6 and no longer prunes on hosted
  runners. The data-fetch step itself succeeded on every failed run; only PR
  creation broke.

### Security

- Triaged the 12 Dependabot alerts (8 keras, 4 python-multipart) that reopened
  against the stale `requirements.txt` dependency-graph snapshot
  (keras 3.13.2, python-multipart 0.0.27, tensorflow 2.20.0 -- see the note in
  `.github/dependabot.yml`). All are false positives at HEAD: keras is pinned
  at 3.15.1 (>= every first-patched version, 3.14.0/3.15.0) in
  `requirements-ml.txt`, the `ml` extra and both lock exports, and
  `python-multipart` was removed entirely in 2.2.0. Dismissed each alert with
  a per-alert justification. No dependency changed. If the frozen snapshot
  keeps spawning alerts, the remaining fixes are repo-admin actions: disable
  and re-enable the dependency graph in Settings > Security, or ask GitHub
  support to purge the stale snapshot.

## [2.3.0] - 2026-08-10

### Changed

- **Inference no longer uses TensorFlow.** The served model is a Dense stack, so
  `scripts/export_model.py` flattens it into `models/weights.npz` plus a
  `models/scaler.json` holding the `MinMaxScaler` transform vectors, and the API
  evaluates it with NumPy. TensorFlow, Keras, scikit-learn and joblib moved to
  `requirements-ml.txt` as training-only dependencies.
  - Runtime environment drops from ~1,769 MB to ~65 MB of site-packages.
  - Model + scaler load in 0.34s instead of importing TensorFlow first
    (~2.7s locally, warm); a prediction takes ~0.15ms.
  - Permanently removes the keras advisory surface from the served image.
  - Removes the `scaler.save` pickle from the serving path, and with it the
    `InconsistentVersionWarning` from loading a scikit-learn 1.8.0 pickle
    under 1.9.0.
  - Docker and Render builds no longer install the ML stack at all.
- Predictions are unchanged in substance: NumPy agrees with TensorFlow to
  2.3e-05 on the exported weights (the scaler is bit-exact), well below the two
  decimals the UI renders.
- `app/model_loader.py` no longer needs its legacy HDF5 migration path.

### Added

- **Auto-fill.** `GET /api/userContests/{username}` returns the user's recent
  attended contests with their real ranks, and the UI can fill the form from it
  instead of asking people to look their own placements up. Only slugs matching
  `(weekly|biweekly)-contest-<n>` are returned so results post straight back to
  `/api/predict`.
- **Rate limiting.** Per-IP fixed window (default 30 requests/minute) on
  `/api/predict` and `/api/userContests`, returning `429` with `Retry-After`.
  The endpoints are public and each request costs an inference plus upstream
  calls.
- **Output sanity bound.** Predictions outside +/-`MAX_RATING_CHANGE` (default
  500) or non-finite are now rejected as a 500 rather than returned.
- **Golden regression test** (`tests/test_model_artifacts.py`) pinning the real
  model's output for a fixed input. Every other backend test used dummy models,
  so nothing would have caught a dependency bump silently shifting predictions.
- Weekly `refresh-data` workflow that runs `scripts/update_data.py` and opens a
  PR. The script existed but nothing scheduled it.
- `.github/dependabot.yml` declaring the pip, npm and github-actions ecosystems
  with `open-pull-requests-limit: 0` (Renovate still owns update PRs). Once
  `uv.lock` appeared Dependabot stopped re-scanning `requirements*.txt`, leaving
  a frozen snapshot that kept generating alerts for versions no longer present.

### UI

- Auto-fill button beside the username field, with distinct messaging for
  unknown users, rate limiting and empty history.
- Shimmer skeletons while the contest list loads, instead of an empty gap.
- Signed delta bar per result and a net-change summary across multiple contests.
- Selected contests are visually highlighted; a hint shows how many are ready.
- Visible `:focus-visible` rings, `prefers-reduced-motion` support, and the
  username/auto-fill row stacks on narrow screens.
- Backend test count 34 -> 59, frontend 11 -> 19.

### Fixed

- README documented the model as 7 features and 3,137 parameters; it is
  15 features and 12,417 parameters (`15->128->64->32->1`). Also documents the
  synthetic participant-count fallback, which is the main known accuracy limit.
- `requirements-dev.txt` tooling and `.dockerignore` now exclude training-only
  artifacts from the image.

## [2.2.0] - 2026-08-10

### Security

- Resolve all 17 open Dependabot alerts:
  - Drop unused `python-multipart` (closes 4 alerts: querystring DoS, negative
    Content-Length buffering, RFC 2231/5987 parameter smuggling, semicolon
    separator smuggling). The API is JSON-only and never parsed form data.
  - `keras` 3.14.1 -> 3.15.1 (closes 6 alerts: Lambda safe-mode bypass,
    TorchModuleWrapper pickle deserialization, HDF5 link and virtual-dataset
    local file disclosure, DiskIOStore path traversal, tar symlink traversal).
  - `undici` 7.28.0 -> 8.10.0 (closes 5 alerts: retry-interceptor response
    desync, cache-directive info disclosure, CRLF injection via blob type,
    Cache-Control whitespace parsing, cookie attribute injection).
  - `postcss` 8.5.16 -> 8.5.26 (closes 1 alert: sourceMappingURL path traversal).
  - `msw` 1.3.5 -> 2.15.0, pulling `cookie` 0.4.2 -> 1.1.1 (closes 1 alert:
    out-of-bounds characters in cookie name/path/domain).
- Also picked up `nanoid` 3.3.15 -> 3.3.18 (infinite-loop DoS).
- Pin `astral-sh/setup-uv` to a full commit SHA and add least-privilege
  `permissions: contents: read` to the CI workflow.
- `npm audit` now reports 0 vulnerabilities.

### Fixed

- Correct the Python version pin: `runtime.txt` and `.python-version` claimed
  3.14.6, but TensorFlow 2.21 ships no 3.14 wheels. Both now say 3.12.10,
  matching `render.yaml` and CI. The `Dockerfile` had the same bug
  (`python:3.14-slim`) and now uses `python:3.12-slim`.
- Drop `build-essential` from the image; with `--only-binary :all:` and
  `npm ci --ignore-scripts` nothing is compiled at build time.
- Drop the obsolete `version` key from `docker-compose.yml`.
- Resolve all 22 SonarCloud issues and the 1 security hotspot:
  - Use `logger.exception()` in all 9 exception handlers so tracebacks are
    captured instead of a bare message.
  - Document the 500 response for `GET /api/contestData` in the OpenAPI schema.
  - Replace broad `pytest.raises(Exception)` with `HTTPException` and assert the
    status code; hoist setup out of `pytest.raises` blocks so each asserts a
    single throwing call.
  - Fix three WCAG AA contrast failures (button label, text input, warning
    banner) and prefer `globalThis` over `window`.
  - Drop the unvalidated `children` prop from `ErrorBoundary`.

### Changed

- Update all dependencies to latest: FastAPI 0.141.1, numpy 2.5.2,
  uvicorn 0.52.1, tqdm 4.70.0, redis 8.1.0, ruff 0.16.2, pytest 9.1.1,
  pre-commit 4.6.1, React 19.2.8, Vite 8.2.1, Vitest 4.1.10, jsdom 30.0.1,
  Testing Library jest-dom 7.0.1, prettier 3.9.6, and matching pre-commit hooks.
- CI now enforces `ruff check` (previously `|| true`) and runs both the pytest
  and Vitest suites.
- Align project version across `pyproject.toml`, `client/package.json`, and the
  FastAPI app metadata.
- Migrate the MSW test server from the v1 `rest`/`res(ctx)` API to v2
  `http`/`HttpResponse`.
- Record previously unreleased work: client migration from react-scripts to
  Vite, `client/build` output untracked, pytest moved to `requirements-dev.txt`,
  redis 8.x upgrade, Renovate/CI configuration cleanup, and README badge fixes.

Model predictions are unchanged: `model.keras` loads under keras 3.15.1 and
returns bit-identical output to keras 3.14.1 / numpy 2.4.6.

### Added

- `requirements.lock.txt` and `requirements-ml.lock.txt`, generated from
  `uv.lock` with hashes for every transitive dependency. The Docker build
  installs them with `--require-hashes --only-binary :all:` so the dependency
  tree is verified and no setup scripts run.
- An `ml` extra in `pyproject.toml` mirroring `requirements-ml.txt`, and a
  PEP 735 `dev` dependency group mirroring `requirements-dev.txt`.

## [2.1.0] - 2026-03-16

- Reclassify Jupyter notebooks as Python in language stats

## [2.0.0] - 2026-02-25

- Full-stack rewrite: FastAPI backend + React frontend
- Dense neural network (15 features, 121K records, MAE ~7.84)
- LeetCode GraphQL API integration with TTL caching
- Glassmorphism UI with streaming predictions
- Docker support, CI/CD workflow
- Deploy: Render (backend) + GitHub Pages (frontend)

## [1.1.0] - 2023-12-22

- Improve model accuracy with updated training
- Update PredictionComponent CSS and API integration

## [1.0.0] - 2023-12-19

- Initial LeetCode rating predictor
- Jupyter notebooks with Colab integration
- ML model training and evaluation
- Basic React frontend with prediction component
