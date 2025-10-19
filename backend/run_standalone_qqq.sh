#!/bin/bash
# Quick runner script for the standalone QQQ downloader

cd "$(dirname "$0")"

echo "=========================================="
echo "  QQQ Data Downloader - Quick Start"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo ""
    echo "Creating .env from template..."
    
    if [ -f "env.template" ]; then
        cp env.template .env
        echo "✅ Created .env file from template"
    else
        cat > .env << 'EOF'
# Schwab API Credentials
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here
EOF
        echo "✅ Created new .env file"
    fi
    
    echo ""
    echo "📝 Please edit .env and add your Schwab credentials:"
    echo "   SCHWAB_APP_KEY=your_actual_app_key"
    echo "   SCHWAB_APP_SECRET=your_actual_app_secret"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q schwab-py python-dotenv pandas
    echo "✅ Dependencies installed"
else
    echo "✅ Virtual environment found"
    source venv/bin/activate
fi

echo ""
echo "🚀 Starting QQQ data download..."
echo ""

# Run the standalone script
python standalone_qqq_download.py

echo ""
echo "=========================================="

