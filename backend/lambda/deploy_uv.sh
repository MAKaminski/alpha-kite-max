#!/bin/bash

# Optimized Lambda deployment script using uv
# This script creates a minimal Lambda package under 5MB

set -e

echo "🚀 Building Lambda package with uv..."

# Clean previous builds
rm -rf package lambda_deployment.zip

# Create package directory
mkdir -p package

# Copy source files
echo "📦 Copying source files..."
cp real_time_streamer.py package/
cp -r ../schwab_integration package/ 2>/dev/null || echo "⚠️  schwab_integration not found, skipping..."
cp ../supabase_client.py package/ 2>/dev/null || echo "⚠️  supabase_client.py not found, skipping..."
cp ../token_manager.py package/ 2>/dev/null || echo "⚠️  token_manager.py not found, skipping..."
cp monitoring.py package/ 2>/dev/null || echo "⚠️  monitoring.py not found, skipping..."

# Create minimal requirements.txt for Lambda (only runtime dependencies)
echo "📋 Creating minimal requirements for Lambda..."
cat > package/requirements.txt << EOF
# Core dependencies only - optimized for Lambda
schwab-py==1.5.1
supabase==2.11.0
pydantic==2.12.2
pydantic-settings==2.11.0
python-dotenv==1.1.1
structlog==25.4.0
python-dateutil==2.9.0
pytz==2025.2
boto3==1.40.53
EOF

# Install dependencies using uv (much faster than pip)
echo "⚡ Installing dependencies with uv..."
cd package

# Create a virtual environment with Python 3.10+ for Lambda compatibility
uv venv --python 3.10
source .venv/bin/activate

# Install only the most critical dependencies to keep size down
uv pip install \
    schwab-py==1.5.1 \
    supabase==2.11.0 \
    pydantic==2.12.2 \
    pydantic-settings==2.11.0 \
    python-dotenv==1.1.1 \
    structlog==25.4.0 \
    python-dateutil==2.9.0 \
    pytz==2025.2 \
    boto3==1.40.53

# Copy packages to the package directory for Lambda
cp -r .venv/lib/python3.10/site-packages/* .
rm -rf .venv

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true
find . -name "*.so" -delete 2>/dev/null || true
find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "test_*" -delete 2>/dev/null || true

# Remove large unnecessary packages
rm -rf pandas* numpy* 2>/dev/null || true

cd ..

# Create deployment package
echo "📦 Creating deployment package..."
zip -r lambda_deployment.zip package/ -x "*.pyc" "*/__pycache__/*" "*/tests/*" "*/test_*"

# Check package size
PACKAGE_SIZE=$(du -h lambda_deployment.zip | cut -f1)
echo "✅ Package created: lambda_deployment.zip (${PACKAGE_SIZE})"

if [ $(stat -f%z lambda_deployment.zip) -lt 5242880 ]; then
    echo "🎉 Package size is under 5MB - optimized for Lambda!"
else
    echo "⚠️  Package size is over 5MB - consider further optimization"
fi

echo "🚀 Lambda package ready for deployment!"
