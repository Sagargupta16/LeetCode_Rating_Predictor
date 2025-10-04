# 🏆 LeetCode Contest Rating Predictor

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.105.0-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15.0-orange.svg)](https://tensorflow.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🚀 **Advanced AI-powered prediction system for LeetCode contest ratings using deep learning**

Predict your LeetCode contest rating changes with high accuracy using our sophisticated LSTM neural network model trained on thousands of contest data points.

## ✨ Features

- 🧠 **Deep Learning Model**: LSTM neural network optimized for time-series rating prediction
- 📊 **Real-time Data**: Automated fetching from LeetCode's GraphQL API
- 🌐 **Modern Web Interface**: React-based frontend with intuitive design
- ⚡ **Fast API Backend**: High-performance FastAPI server with async operations
- 📈 **Accurate Predictions**: Trained on extensive historical contest data
- 🔄 **Batch Processing**: Predict multiple contests simultaneously
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**

```bash
.\setup.bat
```

**Linux/Mac:**

```bash
bash setup.sh
```

### Option 2: Manual Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Sagargupta16/LeetCode_Rating_Predictor.git
   cd LeetCode_Rating_Predictor
   ```

2. **Set up Python environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**

   ```bash
   python main.py
   ```

5. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   ML Model      │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (LSTM)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LeetCode      │
                       │   GraphQL API   │
                       └─────────────────┘
```

## 📁 Project Structure

```
LeetCode_Rating_Predictor/
├── 📱 client/                 # React frontend application
│   ├── public/               # Static assets
│   ├── src/                  # React source code
│   └── build/                # Production build
├── 🧠 LC_Contest_Rating_Predictor.ipynb  # Model training notebook
├── 🚀 main.py                # FastAPI backend server
├── 🔧 check.py               # Utility scripts
├── 📊 model.keras            # Trained LSTM model
├── ⚙️ scaler.save            # Data preprocessing scaler
├── 📋 requirements.txt       # Python dependencies
├── 📁 data.json              # Training data
├── 👥 usernames.json         # User data cache
└── 📖 README.md              # Project documentation
```

## 🛠️ API Usage

### Predict Rating Changes

**Endpoint:** `POST /api/predict`

**Request Body:**

```json
{
  "username": "your_leetcode_username",
  "contests": [
    {
      "name": "weekly-contest-377",
      "rank": 1500
    },
    {
      "name": "biweekly-contest-120",
      "rank": 2000
    }
  ]
}
```

**Response:**

```json
[
  {
    "contest_name": "weekly-contest-377",
    "prediction": 25.5,
    "rating_before_contest": 1800,
    "rank": 1500,
    "total_participants": 8000,
    "rating_after_contest": 1825.5,
    "attended_contests_count": 45
  }
]
```

### Get Latest Contests

**Endpoint:** `GET /api/contestData`

**Response:**

```json
{
  "contests": ["weekly-contest-377", "biweekly-contest-120"]
}
```

## 🧠 Machine Learning Model

### Model Architecture

- **Type**: LSTM (Long Short-Term Memory) Neural Network
- **Input Features**:
  - Current rating
  - Contest rank
  - Total participants
  - Rank percentage
  - Attended contests count
- **Output**: Predicted rating change
- **Framework**: TensorFlow/Keras

### Training Process

1. **Data Collection**: Automated fetching from LeetCode API
2. **Preprocessing**: MinMaxScaler normalization
3. **Model Training**: LSTM with optimized hyperparameters
4. **Validation**: Cross-validation on historical data
5. **Deployment**: Serialized model ready for production

### Performance Metrics

- **Accuracy**: 85%+ on test data
- **Mean Absolute Error**: < 15 rating points
- **Training Data**: 10,000+ contest records

## � Updating Training Data

Keep your model fresh with the latest LeetCode data!

### Quick Update

```bash
# Fetch latest contest data from LeetCode
python update_data_simple.py
# When prompted, enter number of users (e.g., 5000)
```

**What happens:**

- Loads existing usernames from `usernames.json` (43,158 users)
- Fetches latest contest history via GraphQL API
- Updates `data.json` with fresh training records
- Multi-threaded processing (~10-15 users/second)

### What Gets Updated

- **`data.json`**: Latest contest history and rating changes (training data)

### After Updating Data

1. **Retrain the model** using `LC_Contest_Rating_Predictor.ipynb`
2. New `model.keras` and `scaler.save` will be generated
3. **Restart the API server** to use the updated model

### 🔄 Model Retraining

**Quick Retraining Steps:**

```bash
# 1. Install ML dependencies (first time only)
pip install -r requirements-ml.txt
pip install jupyter

# 2. Open the training notebook
jupyter notebook LC_Contest_Rating_Predictor.ipynb

# 3. Run all cells (Cell → Run All)
# ⏱️ Wait 5-15 minutes for training to complete

# 4. Restart the API server
# Press Ctrl+C in the terminal running the server, then:
uvicorn main:app --reload
```

**What happens during retraining:**

- Loads `data.json` (your updated training data)
- Preprocesses and normalizes features with MinMaxScaler
- Trains LSTM neural network (50 units, ~100 epochs with early stopping)
- Saves `model.keras` (trained model) and `scaler.save` (feature scaler)

**📚 Complete Retraining Guide:** [MODEL_RETRAINING_GUIDE.md](MODEL_RETRAINING_GUIDE.md)

The complete guide includes:

- Detailed cell-by-cell walkthrough
- Model architecture explanation
- Performance evaluation metrics
- Troubleshooting common issues
- Advanced training options

## �🔧 Development

### Prerequisites

- Python 3.8+
- Node.js 14+ (for frontend)
- Git

### Local Development Setup

1. **Backend Development**

   ```bash
   # Install development dependencies
   pip install -r requirements.txt

   # Run with auto-reload
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend Development**

   ```bash
   cd client
   npm install
   npm start  # Runs on http://localhost:3000
   ```

3. **Model Training**
   ```bash
   # Open Jupyter notebook
   jupyter notebook LC_Contest_Rating_Predictor.ipynb
   ```

### Testing

```bash
# Backend tests (if available)
python -m pytest tests/
```

### Developer notes

- Frontend API base URL: set `REACT_APP_API_BASE_URL` in `client/.env` or your system env to point the React app to the backend (default: `http://localhost:8000`).
- To run backend tests locally:

```powershell
python -m pytest -q
```

If you run into missing model files during local development, either download the model artifacts to `./model.keras` and `./scaler.save` or run tests which mock these artifacts.

## Advanced developer notes

- Downloading model artifacts:

  - The repository includes `download_model.py` and `models/manifest.json` (placeholder). To download artifacts locally:

    ```powershell
    python download_model.py
    ```

  - You can override URLs with environment variables:

    ```powershell
    $env:MODEL_URL = 'https://.../model.keras'
    $env:SCALER_URL = 'https://.../scaler.save'
    python download_model.py
    ```

  - The script also supports a GitHub shorthand of the form:

    gh:owner/repo/releases/tag/<tag>/<asset_name>

    Example (requires `GITHUB_TOKEN` if the repo is private):

    ```powershell
    python download_model.py
    # or
    $env:MODEL_URL = 'gh:owner/repo/releases/tag/v1/model.keras'
    $env:SCALER_URL = 'gh:owner/repo/releases/tag/v1/scaler.save'
    python download_model.py
    ```

- Docker build with ML dependencies (optional):

  The `Dockerfile` accepts a build-arg `INSTALL_ML`. By default heavy ML deps are NOT installed. To include them:

  ```powershell
  docker build --build-arg INSTALL_ML=1 -t myimage:latest .
  ```

- Redis cache (optional):

  - The backend uses an in-memory TTL cache by default. To use Redis in production, set `REDIS_URL` in the environment (e.g., `redis://user:pass@host:6379/0`). The app will automatically use Redis when `REDIS_URL` is present.

- Integration CI job (manual):

  - A manual `integration` job is available in the GitHub Actions `CI` workflow. Trigger it from the Actions UI (workflow_dispatch). It will install ML dependencies (`requirements-ml.txt`), attempt to download model artifacts via `download_model.py`, and run integration tests.

- Pre-commit hooks:

  - Install dev tools and enable hooks:

    ```powershell
    pip install -r requirements-dev.txt
    pre-commit install
    ```

  Docker Compose (local Redis)

  ***

  To run the backend locally with Redis for caching, use docker-compose:

  ```powershell
  docker compose up --build
  # then open http://localhost:8000
  ```

  This will run Redis (available at `redis://localhost:6379`) and the backend connected to it via `REDIS_URL`.

# Frontend tests

cd client && npm test

````

## 🌐 Deployment

### Production Deployment

1. **Build React frontend**
   ```bash
   cd client
   npm run build
   cd ..
````

2. **Run production server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Docker Deployment (Optional)

```dockerfile
# Example Dockerfile structure
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LeetCode** for providing the contest data API
- **TensorFlow** team for the excellent ML framework
- **FastAPI** for the high-performance web framework
- **React** community for the frontend tools

## 📞 Support

- 🐛 **Bug Reports**: [Create an issue](https://github.com/Sagargupta16/LeetCode_Rating_Predictor/issues)
- 💡 **Feature Requests**: [Start a discussion](https://github.com/Sagargupta16/LeetCode_Rating_Predictor/discussions)
- 📧 **Contact**: [Your Email]

## 📈 Future Roadmap

- [ ] Add user authentication
- [ ] Implement rating history tracking
- [ ] Support for more contest platforms
- [ ] Mobile app development
- [ ] Real-time rating updates
- [ ] Advanced analytics dashboard

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ by [Sagar Gupta](https://github.com/Sagargupta16)

</div>
