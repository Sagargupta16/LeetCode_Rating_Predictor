# Changelog

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
