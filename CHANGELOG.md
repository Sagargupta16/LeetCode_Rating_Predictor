# Changelog

## [2.6.0] - 2026-10-24

### Added

- **The browser extension runs the model itself.** It no longer calls the
  predictor API: it reads each listed user's contest history from LeetCode
  GraphQL on the ranking page's own origin, rebuilds the 15 features in
  `extension/core.js` and runs the network from `model.json`, which it loads
  from the Hugging Face Hub, caches and re-checks daily. No Render cold start,
  no 30-requests-a-minute limit shared by every user, and a retrain reaches
  every install without a store release. A contest LeetCode already rated is
  scored from the history before it, and the tooltip shows the change LeetCode
  applied. The options page now shows the model revision and checks for a newer
  one. Checked on the live Weekly Contest 524 ranking (page 3): 23 of 23 rows
  predicted, and for 6 of them the in-browser result matched the live API
  within 1.6e-5, including two already-rated contests.
- **`models/model.json`** (159 KB): the served network and scaler in one JSON
  file, written by `scripts/publish_model.py` from `weights.npz` and
  `scaler.json`. A test fails if it drifts from them; its float64 forward pass
  matches the API's float32 one within 8e-6.
- **Model repo on the Hub**, `Sagargupta1610/leetcode-rating-predictor`:
  `scripts/publish_model.py --upload` pushes `models/`, `model.keras`,
  `docs/backtest.md` and a model card whose numbers are read from
  `models/metrics.json` and the backtest. Published at revision `4bad397`; the
  extension loaded it from there and predicted 23 of 23 rows on page 4 of the
  same ranking.
- **Dataset repo on the Hub**, `Sagargupta1610/leetcode-contest-rating-changes`
  (created private): `scripts/export_dataset.py` writes the records as Parquet,
  one file per split, with the 15 features under their names, the rating change,
  an anonymous user id and the by-user split. The 2026-10-18 training data comes
  to the same 242,108 / 26,093 / 27,698 rows as `models/metrics.json`, and
  `train.py` reads identical rows from it as from the JSON. The 295,899 records
  are 15.3 MB as Parquet against 68.5 MB as JSON. Published with that version
  tagged `training-2026-10-18` and the 2026-10-20 refresh (296,085 rows) on
  `main`; it stays private until LeetCode's terms are settled.
- `extension/inference.test.js` checks the JavaScript port against
  `tests/fixtures/extension_parity.json`, which `scripts/make_parity_fixture.py`
  generates from the Python feature code; features match exactly. CI now runs
  every extension test (`node --test`).

### Changed

- `data/data.json` is no longer committed. The weekly refresh publishes the
  records to the Hub dataset instead of opening a 65 MB PR, compares the
  retention floor with the published row count (`--baseline hub`), and only
  opens a PR for `docs/backtest.md`. It needs an `HF_TOKEN` secret with write
  access to the dataset repo.
- `scripts/train.py` reads the Hub dataset by default (`--data hub`,
  `--revision`), using the split stored with it; `--data data/data.json` still
  trains from a local fetch.
- `scripts/update_data.py` records an anonymous user id, the contest title and
  its start time with every row.
- `scripts/backtest.py` and the API share `replay_features` and the new
  `FEATURE_NAMES` in `app/services/features.py`.
- `huggingface-hub` 2.3.0 and `pyarrow` 26.0.0 join the dev group and the `ml`
  extra; the runtime dependencies are unchanged.
- Both README diagrams are redrawn for the Hub flows (orrery review 99.6 and
  97.3).
- Version 2.6.0 for the API, client and extension.

## [2.5.0] - 2026-10-24

### Fixed

- **Auto-filled contests were counted twice.** Auto-fill fills contests
  LeetCode has already rated, and `/api/predict` scored them from the current
  rating, which already includes them. A rated contest is now scored from the
  history as it stood before it (`replay_features`, the replay
  `scripts/backtest.py` uses), no longer moves the rating chain, and comes back
  with `actual_change`. Checked live on `weekly-contest-519` (rank 269): it was
  predicted from 2165.70 to 2209.32, and is now predicted from 2119.78 to
  2167.19 against the 2165.70 LeetCode gave. The UI shows the actual change and
  leaves rated contests out of the net change.
- **The form never offered the contest that just ended.** `/api/contestData`
  read only `topTwoContests`, which lists upcoming contests: on 2026-10-24 it
  returned weekly 525 and biweekly 194, so the finished weekly 524 could not be
  predicted from the web app. It now returns the two latest finished contests
  (`pastContests`) and the next two, oldest first.
- **The Docker image could not install its dependencies.** The 2.4.x
  `requirements.lock.txt` was not generated from `uv.lock`: its
  `pydantic-core 2.49.0` hashes fail `pip install --require-hashes` for Linux
  cp312, and it lacked `opentelemetry-api`, which fastapi 0.142 needs. Both
  lock files are regenerated from `uv.lock` with the CONTRIBUTING commands.
- Inputs were 15.2 px, so iOS Safari zoomed into the form on focus; they are
  16 px. Page height uses `100dvh`.
- `docker-compose.yml` mounted the whole repo over `/app`, hiding the
  `client/build` the image compiled. It now mounts `main.py`, `app/` and
  `models/` only.

### Security

- The rate limiter keyed on the first `X-Forwarded-For` entry, which the
  caller controls, so sending a new value per request skipped the limit (60 of
  60 passed locally). It now keys on `CLIENT_IP_HEADER`, default
  `cf-connecting-ip` (Cloudflare sets it in front of Render), or the socket
  peer.
- `/api/predict` accepted any number of contests, each a LeetCode call for one
  rate-limit hit (500 contests made 500 upstream calls). It takes at most 20,
  and `/api/contestData` is rate limited too.
- Dependency alerts: certifi 2026.10.23 in all three lock files (renovate #180
  had bumped one), black 26.10.1, virtualenv 21.14.13, filelock 4.2.4,
  setuptools 84.2.1, opentelemetry-api 1.45.1, and `npm audit fix` in the
  client (undici 8.12.3, vitest 4.1.12).
- `scripts/backtest.py` reads `--weights` and `--scaler` only from files that
  exist under `models/` or `.cache/`.

### Changed

- `requests` and `tqdm` leave the runtime dependencies: only `scripts/`
  imports them, so they move to the dev group and `requirements-dev.txt`. The
  runtime lock also moves to current starlette 1.9.0, anyio 4.15.1 and
  websockets 17.3.
- `render.yaml` installs the hash-pinned `requirements.lock.txt`. The live
  Render service is not Blueprint-managed, so its dashboard build command still
  decides what production installs.
- `scripts/update_data.py` writes records in `usernames.json` order rather
  than in the order fetches finish, so a weekly refresh rewrites only the lines
  that changed (#175). The next refresh reorders the file once.
- The in-memory cache and the rate limiter drop expired entries once per TTL
  or window, instead of keeping one per username and client forever.
- `/api/predict` fetches contest details concurrently.
- Removed `scripts/download_model.py` and `models/manifest.json`: the manifest
  pointed at `example.com` placeholders, and the files it fetched are not the
  ones the API serves.
- Removed the `prefers-reduced-motion` override from the web app's CSS.
- API, client and extension report 2.5.0 (they still said 2.4.0).

## [2.4.2] - 2026-10-24

### Docs

- Redrew both README diagrams with orrery 0.12.0, which draws icons at 64 px
  instead of 48. The serving figure now uses `layout.spacing: 0.6` instead of
  `compact`, so the bigger tiles still fit a 1159 px canvas (was 1222) and
  read at 880 px; nodes, edges and evidence are unchanged.

## [2.4.1] - 2026-10-21

### Docs

- README: the Mermaid chart in Architecture is replaced by two figures drawn
  with [orrery](https://github.com/Sagargupta16/orrery), each in a light and a
  dark SVG: the serving path (browser, the one Render web service, LeetCode)
  and the data and model lifecycle (weekly refresh PR, manual retrain and
  export, backtest gate). Their specs live in `docs/diagrams/`, and every node
  and edge names the file and line it comes from (`orrery verify` checks
  them). The serving figure adds two flows the chart left out: the extension
  reading ranks from the ranking page JSON, and the keep-warm job. The GraphQL
  bullet under it now says that is the API's path, since the extension reads
  the ranking JSON in the browser.

## [2.4.0] - 2026-10-18

### Added

- **Browser extension** (`extension/`, Manifest V3). Adds a **Predicted**
  column to LeetCode contest ranking pages, reading ranks from the page's own
  ranking JSON and predictions from the API through the service worker, with a
  shared queue that waits out the API's 429s. An options page points it at a
  self-hosted API. `scripts/package_extension.py` builds the store zip. Checked
  end to end in Chromium on the live Weekly Contest 524 ranking: 23 of 23 rows
  predicted on pages 3 and 4, and on pages 40 and 41 (1280 and 390 px) all 25
  rows per page line up with the header, including the 4 leetcode.cn rows that
  get an empty cell.
- **`scripts/backtest.py`.** Replays the last 5 rated contests (past year) of
  users outside the training slice, through the same feature code the API
  serves. The weekly data refresh now runs it and commits
  [docs/backtest.md](docs/backtest.md) in the same PR. Users are ordered by a
  hash of the seed and the username. The report goes to stdout (`--markdown`
  for the docs format), `--cache` reuses `.cache/histories.json` so two models
  score the same contests, and `--weights` / `--scaler` must stay inside the
  repository.
- **`scripts/train.py`.** Retrains with a train/validation/test split by user
  (user boundaries recovered from the rating chain in `data/data.json`) and the
  scaler fit on training users only, and writes `models/metrics.json`.
- **First-contest predictions.** Accounts with no rated contest yet now get a
  prediction from a 1500 rating and an empty history, which is how the training
  data starts every user, instead of a 400. Unknown usernames still return 400.
- **Keep-warm workflow** pinging `/api/health` every 10 minutes during the
  weekly and biweekly contest windows (12 hours a week).
- README: desktop, phone and extension screenshots, a Deploy to Render button,
  and a measured cold start (31 s on 2026-10-18).

### Changed

- **Retrained model (Huber loss, split by user, 242,108 training records).**
  On two backtest samples of 50 unseen users, drawn after the model was
  picked, MAE stayed at 9.11 (173 contests) and went from 7.78 to 7.58 (139
  contests); RMSE from 20.08 to 19.85 and from 11.54 to 11.42. Held-out users: MAE 14.14 (the previous model scores
  14.22 on the same users). `GOLDEN_PREDICTION` is now 55.0113.
- **One feature module for the API and the backtest**
  (`app/services/features.py`). The served history summary now matches
  `scripts/update_data.py` exactly: placeholder history entries with rank 0 no
  longer count as a 0% solve rate, and the recent finish time takes the last 5
  contests before dropping zero finish times. A test rebuilds the training
  record and checks all 15 features. Feature 5 now uses the training definition
  (position in the history).
- The web app shows the pre-contest rating to 2 decimals.

### Docs

- README: the 7.84 test MAE headline is replaced by the backtest and held-out
  user numbers. It came from a random record split, and the 2.3.5 model scores
  14.22 when split by user on current data.
- README: the "feature 5 skew" note was wrong. The contest history only lists
  attended contests (17,329 of 17,329 entries in 664 sampled histories), so the
  served and trained values already agreed.
- README and CONTRIBUTING: retraining now goes through `scripts/train.py`, then
  a backtest against the current model before replacing it. Test counts are 68
  backend, 19 frontend and 8 extension.

## [2.3.5] - 2026-10-18

### Fixed

- **Predictions fed the model a participant count it never trained on.** The
  training data in `scripts/update_data.py` always uses `max(rank * 1.5, 10000)`
  for features 3, 4 and 13, but the API used GraphQL `registerUserNum`
  (30k-50k for recent contests). A backtest over the last 5 rated contests of 16
  users (57 contests) measured MAE **38.76** with the served path and **12.46**
  with the training formula. The API now builds those features with the training
  formula and still returns the registered count in `total_participants` for
  display.
- **Rating trend and max rating were constant for every user.** The serving
  GraphQL query did not request `rating` in `userContestRankingHistory`, so
  feature 10 was always `0` and feature 11 always `1500` (a 2166-rated account
  was scored as if its peak were 1500). The query now asks for it, matching the
  training script.
- **Self-hosted builds called the public demo.** Outside `localhost` the client
  hard-coded `https://leetcode-rating-predictor.onrender.com`, so a Docker or
  LAN deployment sent every request to Render. It now uses the same origin, and
  the Vite dev server on port 3000 targets port 8000 on the same host.
- **Python version drift.** The monthly update moved `.python-version` to
  3.14.7 and the Docker base to `python:3.14-slim` while Render, `runtime.txt`
  and CI stay on 3.12, and TensorFlow 2.21 ships no 3.14 wheels. Both are back
  on 3.12, and `renovate.json` now caps Python below 3.13.
- **Version strings.** The FastAPI app and `client/package.json` reported 2.3.1;
  all three manifests now say 2.3.5.

### Changed

- Docker publish workflow actions moved to their current majors (Node 24
  runtime): `setup-qemu-action` v4.4.0, `setup-buildx-action` v4.4.1,
  `login-action` v4.6.0, `build-push-action` v7.4.0, still pinned by SHA.
- Removed the unused `INSTALL_ML` build arg from `docker-compose.yml`; the
  Dockerfile never declared it.

### Docs

- README: added a Why section, a mermaid architecture diagram covering serving
  and offline training, a design decisions table, and the backtest numbers.
- README: listed the remaining feature 5 skew (training counts every contest in
  the history, serving counts attended contests only) as open work.
- README: corrected the environment variable table (`WEIGHTS_PATH`, not
  `MODEL_PATH`, plus the rate limit, `MAX_RATING_CHANGE` and GraphQL URL
  settings), test counts (59 backend, 19 frontend), the Python requirement
  (3.12), the data refresh default (12,000 users), the CI description, the
  Docker instructions, and the post-retrain steps, which now include
  `scripts/export_model.py`.

## [2.3.4] - 2026-09-21

### Security

- **anyio 4.13.0 to 4.14.2**, closing Dependabot alerts #128, #129, #131 and #133.
  Two advisories: a critical one where `TLSStream` encodes host names with IDNA
  2003, which can let a certificate for a different name validate as a match, and
  a medium one where process-pool workers block indefinitely on undrained stderr.
  anyio is transitive, reaching the tree through the served FastAPI stack, so the
  fix is a lockfile move with no pin change in `requirements*.txt`.
- **Fixed lockfile drift that hid half the exposure.** `requirements.lock.txt`
  already carried 4.14.2 while `uv.lock` and `requirements-ml.lock.txt` were still
  on 4.13.0, so an earlier per-manifest fix had landed on one file and left the
  other two behind. All three now agree, regenerated with the documented
  `uv lock` plus both `uv export` commands. Re-exporting `requirements.lock.txt`
  produced no diff, which confirms the export is reproducible and only anyio moved.

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
