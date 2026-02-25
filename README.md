# LeetCode Contest Rating Predictor

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.133.0-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://reactjs.org)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.20.0-orange.svg)](https://tensorflow.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Predict your LeetCode contest rating changes using a Dense neural network trained on 121,000+ contest records. Enter your username, select a contest, and get a prediction.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/Sagargupta16/LeetCode_Rating_Predictor.git
cd LeetCode_Rating_Predictor

# Python environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# Install and run
pip install -r requirements.txt
pip install -r requirements-ml.txt   # For model loading (TensorFlow)
python main.py
# Open http://localhost:8000
```

## Architecture

```
React Frontend (port 3000)  -->  FastAPI Backend (port 8000)
                                    |
                                    +-- LeetCode GraphQL API
                                    +-- Dense Neural Network (model.keras)
```

All LeetCode data is fetched via **GraphQL** (the REST ranking API is blocked).

## Project Structure

```
main.py                          # FastAPI entry point
app/                             # Backend package
  config.py                      #   Environment variables, constants
  schemas.py                     #   Pydantic request/response models
  model_loader.py                #   Keras model loader (handles legacy HDF5)
  services/
    leetcode.py                  #   LeetCode GraphQL client
    prediction.py                #   ML prediction logic
  utils/
    cache.py                     #   TTLCache / RedisCache
scripts/
  download_model.py              # Download model artifacts from URLs
  update_data.py                 # Fetch training data from LeetCode
  check.py                       # Smoke test the running API
notebooks/
  LC_Contest_Rating_Predictor.ipynb  # Training notebook
data/                            # Training data (gitignored)
models/                          # Model manifest
tests/                           # 34 backend tests
client/                          # React frontend (11 tests)
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

### `GET /api/contestData`

Returns the latest contests (via GraphQL `topTwoContests`).

### `GET /api/health`

Health check with model/scaler/client status.

## ML Model

### Architecture

Dense neural network (replaced LSTM since input is tabular, not sequential):

```
Dense(64, relu) -> Dropout(0.2) -> Dense(32, relu) -> Dropout(0.2) -> Dense(16, relu) -> Dense(1)
```

3,137 parameters. Trained with Adam (lr=0.001), MSE loss, early stopping (patience=10).

### 7 Input Features

| # | Feature | Correlation with output |
|---|---------|------------------------|
| 1 | Current rating | -0.148 |
| 2 | Contest rank | -0.474 |
| 3 | Total participants | -0.308 |
| 4 | Rank percentage (rank*100/participants) | -0.495 |
| 5 | Attended contests count | -0.115 |
| 6 | log(1 + rank) | **-0.508** |
| 7 | Rating * percentile | **-0.555** |

Features 6 and 7 are engineered and provide the strongest signal.

### Performance

| Metric | Value |
|--------|-------|
| Test MAE | **7.84 rating points** |
| Test RMSE | 12.26 |
| Test MSE | 150.34 |
| Training data | 121,241 records |
| Early stopped at | Epoch 38/200 |

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
cd "/mnt/c/Code/GitHub/My Repos/ml-ai/LeetCode_Rating_Predictor"
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
pip install "tensorflow[and-cuda]==2.20.0" joblib scikit-learn numpy
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
- Node.js 20+

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
npx react-scripts test --watchAll=false
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
| `REACT_APP_API_BASE_URL` | *(auto-detected)* | Frontend API endpoint |

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

## License

MIT - see [LICENSE](LICENSE).

---

Made by [Sagar Gupta](https://github.com/Sagargupta16)
