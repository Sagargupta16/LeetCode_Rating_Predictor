@echo off
echo 🚀 Setting up LeetCode Rating Predictor...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo 📚 Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 🌐 Setting up React frontend...
    cd client
    npm install
    cd ..
) else (
    echo ⚠️  Node.js not found. Frontend setup skipped.
    echo    Install Node.js to build the React frontend.
)

echo ✅ Setup complete!
echo.
echo 🔥 Quick Start:
echo    1. Activate virtual environment:
echo       venv\Scripts\activate.bat
echo    2. Start the API server:
echo       python main.py
echo    3. (Optional) Build and serve frontend:
echo       cd client && npm run build && cd ..
echo.
echo 📖 The API will be available at http://localhost:8000
echo 📊 API documentation at http://localhost:8000/docs
pause
