# Contributing

## Setup

1. Fork and clone the repo
2. `python -m venv venv && venv\Scripts\activate` (or `source venv/bin/activate`)
3. `pip install -r requirements.txt -r requirements-dev.txt`
4. `cd client && npm ci --ignore-scripts && cd ..`

Serving needs no ML framework. Only add `-r requirements-ml.txt` if you intend
to retrain or re-export the model.

## Model artifacts

The API reads `models/weights.npz` and `models/scaler.json`, which are generated
from `model.keras` and `scaler.save`. Retrain with `scripts/train.py` (split by
user, so the held-out score is honest), export, and backtest the result against
the current model before replacing it:

```bash
pip install -r requirements-ml.txt
python scripts/train.py --loss huber    # Hub dataset; writes model.keras, scaler.save, models/metrics.json
python scripts/export_model.py
python scripts/publish_model.py        # models/model.json, what the extension runs
python scripts/make_parity_fixture.py  # the Python outputs the extension is tested against
python scripts/backtest.py --cache   # new model
python scripts/backtest.py --cache \
  --weights .cache/old/weights.npz --scaler .cache/old/scaler.json   # previous model, same users
```

`--cache` keeps the fetched contest histories in `.cache/histories.json`
(gitignored), so both runs score the same contests. Copy the current
`models/weights.npz` and `models/scaler.json` to `.cache/old/` before exporting
the new model; `--weights` and `--scaler` must name a file under `models/` or
`.cache/`.
Only ship a model that wins on the backtest, and commit the regenerated
artifacts, `models/model.json`, `models/metrics.json` and
`tests/fixtures/extension_parity.json` together. Then publish it with
`python scripts/publish_model.py --upload` (needs `hf auth login` with write
access); installed extensions pick it up within a day.

The training records live in the Hub dataset `Sagargupta1610/leetcode-contest-rating-changes`,
which the weekly refresh updates; `train.py` reads it by default.

`tests/test_model_artifacts.py` pins the prediction for a fixed input. A
legitimate retrain will change it -- update `GOLDEN_PREDICTION` alongside the new
artifacts, and say so in the PR. An *unexpected* change means something else
moved, so investigate before touching the constant.

## Code Style

**Python**: Black, isort, Ruff -- enforced via pre-commit hooks:
```bash
pip install -r requirements-dev.txt
pre-commit install
```

**Frontend**: Prettier (`npm run format` in `client/`).

## Testing

```bash
# Backend (72 tests)
python -m pytest tests/

# Frontend (19 tests)
cd client && npm test

# Browser extension (17 tests, including the parity check against Python)
cd extension && node --test
```

All tests must pass before submitting a PR.

## Dependencies

Human-editable pins live in `requirements.txt` (runtime), `requirements-ml.txt`
(TensorFlow/Keras, plus the Hub client to read the dataset) and
`requirements-dev.txt` (tooling, and what `scripts/` needs to fetch data and
publish to the Hub). `pyproject.toml`
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
`Dockerfile`, CI) to match the Render deploy, and TensorFlow 2.21 publishes no
3.14 wheels. `renovate.json` caps Python below 3.13 so the monthly update keeps
them in sync.

## Project Layout

- `app/` -- backend package (config, schemas, services, utils)
- `main.py` -- FastAPI entry point
- `client/` -- React frontend
- `extension/` -- Chrome extension for LeetCode ranking pages (no build step)
- `scripts/` -- data fetching, training, export, backtest, extension packaging
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
