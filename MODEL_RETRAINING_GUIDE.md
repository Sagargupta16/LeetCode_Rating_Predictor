# 🔄 Model Retraining Guide

Complete guide for retraining your LeetCode Rating Predictor model with fresh data.

---

## 📋 Prerequisites

Before retraining, ensure you have:

1. ✅ **Updated training data** (`data.json`)

   - Run `python update_data_simple.py` first if you haven't
   - File should contain latest contest data

2. ✅ **ML dependencies installed**

   ```bash
   pip install -r requirements-ml.txt
   ```

   This installs: TensorFlow, Keras, scikit-learn, etc.

3. ✅ **Jupyter Notebook** (or JupyterLab)
   ```bash
   pip install jupyter
   # or
   pip install jupyterlab
   ```

---

## 🚀 Quick Retraining (3 Steps)

### **Step 1: Open the Training Notebook**

```bash
# Option A: Jupyter Notebook (classic)
jupyter notebook LC_Contest_Rating_Predictor.ipynb

# Option B: JupyterLab (modern UI)
jupyter lab LC_Contest_Rating_Predictor.ipynb

# Option C: VS Code (if you have Jupyter extension)
# Just open LC_Contest_Rating_Predictor.ipynb in VS Code
```

### **Step 2: Run All Cells**

In the Jupyter interface:

- **Classic Notebook**: `Cell` → `Run All`
- **JupyterLab**: `Run` → `Run All Cells`
- **VS Code**: Click `Run All` at the top of the notebook

⏱️ **Expected time**: 5-15 minutes (depends on data size and hardware)

### **Step 3: Verify Output Files**

After the notebook completes, check that these files were created/updated:

```
✅ model.keras      # New trained model
✅ scaler.save      # New data scaler
```

**That's it! Your model is retrained.** 🎉

---

## 📊 What Happens During Retraining?

The notebook performs these steps automatically:

1. **Load Data**

   - Reads `data.json` (your training data)
   - Parses JSON lines into DataFrame

2. **Data Preprocessing**

   - Separates features (inputs) and target (output/rating change)
   - Normalizes data using MinMaxScaler (0-1 range)
   - Splits into training (80%) and validation (20%) sets

3. **Model Architecture**

   - **Input Layer**: 5 features (rating, rank, participants, percentile, contest count)
   - **LSTM Layer**: 50 units (captures time-series patterns)
   - **Dense Layers**: Multiple layers with dropout for regularization
   - **Output Layer**: 1 value (predicted rating change)

4. **Training**

   - Optimizer: Adam
   - Loss Function: Mean Squared Error (MSE)
   - Epochs: ~100 (with early stopping)
   - Callbacks:
     - **ModelCheckpoint**: Saves best model
     - **EarlyStopping**: Stops if no improvement for 10 epochs

5. **Save Artifacts**
   - `model.keras`: Trained model weights and architecture
   - `scaler.save`: Feature scaling parameters (must use same scaler for predictions)

---

## 🔧 Advanced: Manual Retraining Steps

If you want to understand or customize the process:

### 1. **Install Dependencies**

```bash
# Core ML dependencies
pip install tensorflow==2.15.0
pip install scikit-learn==1.3.2
pip install pandas numpy joblib

# Jupyter
pip install jupyter ipykernel
```

### 2. **Prepare Data** (if not already done)

```bash
# Update training data first
python update_data_simple.py
```

Your `data.json` should look like:

```json
{"input1":1500.0,"input2":110,"input3":13038,"input4":0.8436,"input5":0,"output":320.626}
{"input1":1820.626,"input2":45,"input3":11877,"input4":0.3788,"input5":1,"output":199.425}
...
```

### 3. **Open Notebook**

```bash
jupyter notebook LC_Contest_Rating_Predictor.ipynb
```

### 4. **Run Cell-by-Cell** (for debugging/learning)

**Cell 1: Imports**

- Loads all required libraries
- Sets up TensorFlow, pandas, sklearn

**Cell 2-3: Data Collection Functions**

- (Optional) Used if fetching new usernames
- Skip if using existing `data.json`

**Cell 4: Load Training Data**

```python
# Reads data.json and creates training dataset
```

**Cell 5: Data Preprocessing**

```python
# Scales features, splits train/test
scaler = MinMaxScaler()
X_train, X_test, y_train, y_test = train_test_split(...)
```

**Cell 6: Build Model**

```python
model = Sequential([
    LSTM(50, return_sequences=True),
    Dense(25),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')
```

**Cell 7: Train Model**

```python
# This is the time-consuming step (5-10 minutes)
history = model.fit(X_train, y_train, epochs=100, validation_data=(X_test, y_test))
```

**Cell 8: Save Model**

```python
model.save('model.keras')
joblib.dump(scaler, 'scaler.save')
```

### 5. **Validate Training**

Check the output for:

- ✅ Training loss decreasing over epochs
- ✅ Validation loss not increasing (no overfitting)
- ✅ Final MAE (Mean Absolute Error) < 20
- ✅ Files `model.keras` and `scaler.save` created

Example good output:

```
Epoch 50/100
loss: 0.0235 - val_loss: 0.0298
...
Model saved to model.keras
Scaler saved to scaler.save
```

---

## 🔄 After Retraining

### **Option 1: Automatic (Recommended)**

The FastAPI server automatically loads the latest model on startup:

```bash
# Just restart your server
uvicorn main:app --reload
```

No code changes needed! The API will use the new `model.keras` and `scaler.save`.

### **Option 2: Docker**

If using Docker:

```bash
# Rebuild the image to include new model files
docker-compose down
docker-compose up --build
```

### **Option 3: Production Deployment**

```bash
# 1. Copy new model files to production server
scp model.keras user@server:/path/to/app/
scp scaler.save user@server:/path/to/app/

# 2. Restart the service
systemctl restart leetcode-predictor
```

---

## 📈 Model Performance Evaluation

After retraining, test the model:

### **1. Check Metrics**

Look at the notebook output for:

| Metric                    | Good Value  | Excellent Value |
| ------------------------- | ----------- | --------------- |
| Training Loss             | < 0.05      | < 0.02          |
| Validation Loss           | < 0.06      | < 0.03          |
| MAE (Mean Absolute Error) | < 20 points | < 15 points     |
| R² Score                  | > 0.75      | > 0.85          |

### **2. Test Predictions**

```bash
# Test with a real username
python check.py
```

Or use the API:

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "contestRank": 1500,
    "totalParticipants": 10000
  }'
```

### **3. Compare Old vs New Model**

Keep the old model as backup:

```bash
cp model.keras model.keras.backup
cp scaler.save scaler.save.backup
```

Test both and compare prediction accuracy.

---

## 🐛 Troubleshooting

### **Issue: "Module not found" errors**

```bash
# Install missing dependencies
pip install -r requirements-ml.txt
```

### **Issue: CUDA/GPU errors**

TensorFlow trying to use GPU but failing:

```bash
# Force CPU-only training
export TF_FORCE_GPU_ALLOW_GROWTH=false
# or edit the notebook to add:
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
```

### **Issue: Out of memory**

```python
# In the notebook, reduce batch size:
model.fit(X_train, y_train, batch_size=16)  # Default is 32
```

### **Issue: Training takes too long**

```python
# Reduce epochs or enable early stopping more aggressively:
early_stop = EarlyStopping(patience=5)  # Stop after 5 epochs with no improvement
```

### **Issue: Poor model performance**

1. **Check data quality**

   ```python
   # In notebook, inspect data:
   print(df.describe())
   print(df.isnull().sum())
   ```

2. **Need more data**

   ```bash
   # Fetch more users
   python update_data_simple.py
   # Enter a larger number like 10000
   ```

3. **Try different hyperparameters**
   - Increase LSTM units: `LSTM(100)` instead of `LSTM(50)`
   - Add more layers
   - Adjust learning rate

---

## 📝 Retraining Checklist

Before deploying the new model:

- [ ] Fresh training data collected (`data.json` updated)
- [ ] Notebook ran successfully without errors
- [ ] `model.keras` and `scaler.save` files created
- [ ] Training/validation loss are reasonable
- [ ] Tested predictions with sample data
- [ ] Backed up old model files
- [ ] Restarted API server
- [ ] Verified API predictions are working

---

## ⏰ Recommended Retraining Schedule

| Frequency                        | Use Case                                 |
| -------------------------------- | ---------------------------------------- |
| **Weekly**                       | High-traffic app, want latest meta       |
| **Monthly**                      | Standard usage, balanced freshness       |
| **Quarterly**                    | Low traffic, stable predictions          |
| **After major LeetCode changes** | New contest format, rating system update |

---

## 🎯 Quick Commands Summary

```bash
# 1. Update data
python update_data_simple.py

# 2. Install ML dependencies (first time only)
pip install -r requirements-ml.txt

# 3. Retrain model
jupyter notebook LC_Contest_Rating_Predictor.ipynb
# Then: Run → Run All Cells

# 4. Restart API
# Press Ctrl+C in terminal running the server, then:
uvicorn main:app --reload
```

---

## 💡 Pro Tips

1. **Backup before retraining**

   ```bash
   cp model.keras model_$(date +%Y%m%d).keras
   ```

2. **Track model versions**

   - Add git tags for each retrain
   - Note the data.json size/date
   - Save training metrics in a log

3. **A/B testing**

   - Keep old and new models
   - Compare predictions side-by-side
   - Deploy the better performer

4. **Automated retraining**
   - Schedule weekly data updates
   - Auto-retrain with GitHub Actions
   - Deploy only if metrics improve

---

**Need help?** Check:

- Jupyter notebook output for error messages
- `requirements-ml.txt` for dependency versions
- TensorFlow documentation for model issues

**Ready to retrain?** Run:

```bash
jupyter notebook LC_Contest_Rating_Predictor.ipynb
```

Then click `Run All`! 🚀
