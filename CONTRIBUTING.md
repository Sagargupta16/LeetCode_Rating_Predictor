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
cd client && npx react-scripts test --watchAll=false
```

All tests must pass before submitting a PR.

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
4. Run `python -m pytest tests/` and `cd client && npx react-scripts test --watchAll=false`
5. Commit with descriptive messages (`feat:`, `fix:`, `docs:`)
6. Open a PR with a clear description

## Bug Reports

Include: steps to reproduce, expected vs actual behavior, OS/Python version, error logs.
