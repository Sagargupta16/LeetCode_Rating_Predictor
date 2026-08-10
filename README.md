# LeetCode Contest Rating Predictor

![GitHub stars](https://img.shields.io/github/stars/Sagargupta16/LeetCode_Rating_Predictor?style=flat-square&cacheSeconds=86400)
![GitHub forks](https://img.shields.io/github/forks/Sagargupta16/LeetCode_Rating_Predictor?style=flat-square&cacheSeconds=86400)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/Sagargupta16/LeetCode_Rating_Predictor?style=flat-square&cacheSeconds=86400)
![Demo](https://img.shields.io/badge/demo-live-brightgreen?style=flat-square)

**[View Live Demo](https://leetcode-rating-predictor.onrender.com/)** -- free-tier instance, first load may take ~1 minute to wake

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev)
[![NumPy](https://img.shields.io/badge/inference-NumPy-orange.svg)](https://numpy.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Predict your LeetCode contest rating changes using a Dense neural network trained on 121,000+ contest records. Enter your username, hit **Auto-fill** to pull your real ranks from past contests, and get a prediction.

The trained network is a small Dense stack, so the API evaluates it with NumPy against exported weights. Serving needs no TensorFlow, Keras, scikit-learn or joblib: the runtime environment is ~65 MB instead of ~1.8 GB, and those frameworks are only required to retrain.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/Sagargupta16/LeetCode_Rating_Predictor.git
cd LeetCode_Rating_Predictor

# Python environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# Install and run -- no ML framework needed to serve predictions
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

Retraining or re-exporting the model additionally needs `pip install -r requirements-ml.txt`.

## Architecture

```
React Frontend (port 3000)  -->  FastAPI Backend (port 8000)
                                    |
                                    +-- LeetCode GraphQL API
                                    +-- NumPy Dense network
                                        (models/weights.npz + scaler.json)
```

All LeetCode data is fetched via **GraphQL** (the REST ranking API is blocked).

## Project Structure

```
main.py                          # FastAPI entry point
app/                             # Backend package
  config.py                      #   Environment variables, constants
  schemas.py                     #   Pydantic request/response models
  model_loader.py                #   NumPy Dense network + scaler loader
  services/
    leetcode.py                  #   LeetCode GraphQL client
    prediction.py                #   Prediction + output sanity bounds
  utils/
    cache.py                     #   TTLCache / RedisCache
    ratelimit.py                 #   Per-IP fixed-window rate limiting
scripts/
  export_model.py                # model.keras/scaler.save -> models/*.npz|json
  download_model.py              # Download model artifacts from URLs
  update_data.py                 # Fetch training data from LeetCode
  check.py                       # Smoke test the running API
notebooks/
  LC_Contest_Rating_Predictor.ipynb  # Training notebook
data/                            # Training data
models/                          # Exported weights + scaler (served artifacts)
tests/                           # 59 backend tests
client/                          # React frontend (19 tests)
```

## API

### `POST /api/predict`

```json
{
  "username": "your_username",
  "contests": [
    { "name": "weekly-contest-490", "rank": 1500 }
  ]
}
```

**Response:**

```json
[
  {
    "contest_name": "weekly-contest-490",
    "prediction": 25.5,
    "rating_before_contest": 1800,
    "rank": 1500,
    "total_participants": 42002,
    "rating_after_contest": 1825.5,
    "attended_contests_count": 45
  }
]
```

### `GET /api/userContests/{username}`

Returns the user's recent attended contests with the ranks they actually got, so
the UI can prefill the form instead of asking people to look their own
placements up:

```json
[
  {
    "name": "weekly-contest-490",
    "title": "Weekly Contest 490",
    "rank": 742,
    "rating_after": 1825.5
  }
]
```

Only contests whose slug matches `(weekly|biweekly)-contest-<n>` are returned,
so results can be posted straight back to `/api/predict`.

### `GET /api/contestData`

Returns the latest contests (via GraphQL `topTwoContests`).

### `GET /api/health`

Health check with model/scaler/client status.

### Rate limiting

`/api/predict` and `/api/userContests/{username}` allow 30 requests per minute
per client IP by default (`RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW`), and
return `429` with a `Retry-After` header once exceeded.

## ML Model

### Architecture

Dense neural network (replaced LSTM since input is tabular, not sequential):

```
Dense(128, relu) -> Dropout(0.3) -> Dense(64, relu) -> Dropout(0.2) -> Dense(32, relu) -> Dense(1)
```

12,417 parameters. Trained with Adam, MSE loss, early stopping.

### Serving

Dropout is the identity at inference, so the served model is four matrix
multiplies. `scripts/export_model.py` flattens the Keras model into
`models/weights.npz` and reduces the pickled `MinMaxScaler` to its two transform
vectors in `models/scaler.json`:

```bash
pip install -r requirements-ml.txt
python scripts/export_model.py
```

The NumPy path agrees with TensorFlow to within 2.3e-05 on the served weights
(the scaler is exact), which is far below the two decimals the UI renders. A
golden test in `tests/test_model_artifacts.py` pins the output so a dependency
bump or re-export cannot silently change predictions.

### 15 Input Features

| # | Feature |
|---|---------|
| 1 | Current rating |
| 2 | Contest rank |
| 3 | Total participants |
| 4 | Rank percentage (rank*100/participants) |
| 5 | Attended contests count |
| 6 | Average solve rate |
| 7 | Average finish time |
| 8 | Recent solve rate (last 5) |
| 9 | Recent finish time (last 5) |
| 10 | Rating trend (last 5) |
| 11 | Max rating |
| 12 | log(1 + rank) |
| 13 | Rating * percentile |
| 14 | Average solve rate * current rating |
| 15 | Average finish time / 5400 |

Features 12 and 13 are engineered and historically carried the strongest signal.

### Performance

| Metric | Value |
|--------|-------|
| Test MAE | **7.84 rating points** |
| Test RMSE | 12.26 |
| Test MSE | 150.34 |
| Training data | 121,241 records |

Caveat: `registerUserNum` from GraphQL is a pre-registration count, so when a
contest reports zero participants the API substitutes `max(rank * 1.5, 10000)`
to match how the training data was built. Participant count feeds features 3, 4
and 13, so improving that source is the most promising accuracy work left.

## Updating Training Data

```bash
python scripts/update_data.py
# Enter number of users when prompted (e.g., 5000)
```

This fetches contest history via GraphQL and writes to `data/data.json`.

## Model Retraining

### Quick Retraining (CPU)

```bash
pip install -r requirements-ml.txt
pip install jupyter
cd notebooks
jupyter notebook LC_Contest_Rating_Predictor.ipynb
# Run All Cells -> model.keras and scaler.save saved to project root
```

### GPU Retraining (WSL2 + NVIDIA)

TensorFlow on native Windows is CPU-only. For GPU, use WSL2:

```bash
# In Ubuntu (WSL2):
source ~/tf-gpu/bin/activate
cd /mnt/c/path/to/LeetCode_Rating_Predictor
jupyter notebook notebooks/LC_Contest_Rating_Predictor.ipynb
```

Setup WSL2 GPU (one-time):
```bash
# PowerShell (admin):
wsl --install -d Ubuntu

# Inside Ubuntu:
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
python3 -m venv ~/tf-gpu
source ~/tf-gpu/bin/activate
pip install "tensorflow[and-cuda]==2.21.0" joblib scikit-learn numpy
```

### After Retraining

Restart the server to pick up the new model:
```bash
python main.py
```

### Retraining Checklist

- [ ] Run `python scripts/update_data.py` for fresh data
- [ ] Run all notebook cells
- [ ] Verify `model.keras` and `scaler.save` created at project root
- [ ] Check test MAE < 15 in notebook output
- [ ] Restart API server
- [ ] Test a prediction via the UI or `python scripts/check.py`

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `Module not found` | `pip install -r requirements-ml.txt` |
| GPU not detected (Windows) | Use WSL2 (see above) |
| Out of memory | Reduce `batch_size` in notebook (default: 64) |
| Poor performance | Fetch more data: `python scripts/update_data.py` with more users |

## Development

### Prerequisites

- Python 3.11+
- Node.js 22+

### Backend

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd client
npm ci
npm start    # Dev server on port 3000
```

### Testing

```bash
# Backend (34 tests)
python -m pytest tests/

# Frontend (11 tests)
cd client
npm test
```

### Linting

```bash
black .
isort .
ruff check .
# Or all at once:
pre-commit run --all-files
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL_PATH` | `./model.keras` | Path to model file |
| `SCALER_PATH` | `./scaler.save` | Path to scaler file |
| `API_HOST` | `0.0.0.0` | Server bind host |
| `API_PORT` | `8000` | Server bind port |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `REDIS_URL` | *(empty)* | Redis URL for caching (optional) |
| `CACHE_TTL` | `300` | Cache TTL in seconds |
| `VITE_API_BASE_URL` | *(auto-detected)* | Frontend API endpoint |

## Deployment

### Docker

```bash
# With Redis caching
docker-compose up --build

# Standalone with ML deps
docker build --build-arg INSTALL_ML=1 -t leetcode-predictor .
docker run -p 8000:8000 leetcode-predictor
```

### Production

```bash
cd client && npm run build && cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Model Artifacts

Download from a release or URL:
```bash
MODEL_URL=https://... SCALER_URL=https://... python scripts/download_model.py
```

GitHub release shorthand:
```bash
MODEL_URL=gh:owner/repo/releases/tag/v1/model.keras python scripts/download_model.py
```

## CI Pipeline

GitHub Actions: **Lint** (Black, isort, Ruff) -> **Python tests** (pytest) -> **Frontend tests** (npm test, npm build) -> **Integration** (manual, downloads model + full test suite).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## More Projects

| Project | Description |
|---------|-------------|
| [Financial Dashboard](https://github.com/Sagargupta16/Financial-Dashboard) | Modern React financial dashboard with analytics and data visualization |
| [InstagramLikesLeaderboard](https://github.com/Sagargupta16/InstagramLikesLeaderboard) | Browser tool showing who likes your Instagram posts the most |
| [claude-cost-optimizer](https://github.com/Sagargupta16/claude-cost-optimizer) | Save 30-60% on Claude Code costs - proven strategies and benchmarks |
| [Contact Manager](https://github.com/Sagargupta16/Contact-Manager-Mern) | Full-stack MERN contact manager with CRUD and dark mode |

## License

MIT - see [LICENSE](LICENSE).

---

Made by [Sagar Gupta](https://github.com/Sagargupta16)
