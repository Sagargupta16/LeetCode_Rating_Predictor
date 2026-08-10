#!/bin/bash

# LeetCode Rating Predictor - Setup Script
echo "🚀 Setting up LeetCode Rating Predictor..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install Python dependencies. --only-binary keeps pip from running setup
# scripts out of source distributions.
echo "📚 Installing Python dependencies..."
pip install --upgrade --only-binary :all: pip
pip install --only-binary :all: -r requirements.txt

# Check if Node.js is installed for frontend
if command -v node &> /dev/null; then
    echo "🌐 Setting up React frontend..."
    cd client
    npm install --ignore-scripts
    cd ..
else
    echo "⚠️  Node.js not found. Frontend setup skipped."
    echo "   Install Node.js to build the React frontend."
fi

echo "✅ Setup complete!"
echo ""
echo "🔥 Quick Start:"
echo "   1. Activate virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "      source venv/Scripts/activate"
else
    echo "      source venv/bin/activate"
fi
echo "   2. Start the API server:"
echo "      python main.py"
echo "   3. (Optional) Build and serve frontend:"
echo "      cd client && npm run build && cd .."
echo ""
echo "📖 The API will be available at http://localhost:8000"
echo "📊 API documentation at http://localhost:8000/docs"
