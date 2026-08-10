# Contributing

## Setup

1. Fork and clone the repo
2. `python -m venv venv && venv\Scripts\activate` (or `source venv/bin/activate`)
3. `pip install -r requirements.txt -r requirements-dev.txt`
4. `cd client && npm ci && cd ..`

## Code Style

**Python**: Black, isort, Ruff -- enforced via pre-commit hooks:
```bash
pip install -r requirements-dev.txt
pre-commit install
```

**Frontend**: Prettier (`npm run format` in `client/`).

## Testing

```bash
# Backend (34 tests)
python -m pytest tests/

# Frontend (11 tests)
cd client && npm test
```

All tests must pass before submitting a PR.

## Dependencies

Human-editable pins live in `requirements.txt` (runtime), `requirements-ml.txt`
(TensorFlow/Keras) and `requirements-dev.txt` (tooling). `pyproject.toml`
mirrors them so `uv.lock` can resolve the full tree.

`requirements.lock.txt` and `requirements-ml.lock.txt` are generated and carry
hashes for every transitive dependency; the Docker build installs them with
`--require-hashes`. After changing any pin, refresh them:

```bash
uv lock
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.lock.txt
uv export --no-dev --no-emit-project --extra ml --format requirements-txt -o requirements-ml.lock.txt
```

Python is pinned to 3.12 (`runtime.txt`, `.python-version`, `render.yaml`,
`Dockerfile`) because TensorFlow 2.21 publishes no 3.13+ wheels. Keep those in
sync.

## Project Layout

- `app/` -- backend package (config, schemas, services, utils)
- `main.py` -- FastAPI entry point
- `client/` -- React frontend
- `scripts/` -- utility scripts (data fetching, model download)
- `notebooks/` -- training notebook
- `tests/` -- pytest test suite

## Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes, write tests
3. Run `pre-commit run --all-files`
4. Run `python -m pytest tests/` and `cd client && npm test`
5. Commit with descriptive messages (`feat:`, `fix:`, `docs:`)
6. Open a PR with a clear description

## Bug Reports

Include: steps to reproduce, expected vs actual behavior, OS/Python version, error logs.
