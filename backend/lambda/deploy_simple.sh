#!/bin/bash

# Simple Lambda deployment script using existing package
# This script optimizes the existing package for size

set -e

echo "🚀 Optimizing existing Lambda package..."

# Clean previous builds
rm -f lambda_deployment_optimized.zip

# Create optimized package directory
mkdir -p package_optimized

# Copy only essential files
echo "📦 Copying essential files..."
cp real_time_streamer.py package_optimized/
cp -r package/schwab* package_optimized/ 2>/dev/null || echo "⚠️  schwab packages not found"
cp -r package/supabase* package_optimized/ 2>/dev/null || echo "⚠️  supabase packages not found"
cp -r package/pydantic* package_optimized/ 2>/dev/null || echo "⚠️  pydantic packages not found"
cp -r package/structlog* package_optimized/ 2>/dev/null || echo "⚠️  structlog packages not found"
cp -r package/python_dateutil* package_optimized/ 2>/dev/null || echo "⚠️  dateutil packages not found"
cp -r package/pytz* package_optimized/ 2>/dev/null || echo "⚠️  pytz packages not found"
cp -r package/boto3* package_optimized/ 2>/dev/null || echo "⚠️  boto3 packages not found"
cp -r package/botocore* package_optimized/ 2>/dev/null || echo "⚠️  botocore packages not found"

# Copy other essential packages
cp -r package/annotated_types* package_optimized/ 2>/dev/null || true
cp -r package/typing_extensions* package_optimized/ 2>/dev/null || true
cp -r package/pydantic_core* package_optimized/ 2>/dev/null || true
cp -r package/anyio* package_optimized/ 2>/dev/null || true
cp -r package/authlib* package_optimized/ 2>/dev/null || true
cp -r package/certifi* package_optimized/ 2>/dev/null || true
cp -r package/click* package_optimized/ 2>/dev/null || true
cp -r package/cryptography* package_optimized/ 2>/dev/null || true
cp -r package/deprecation* package_optimized/ 2>/dev/null || true
cp -r package/dotenv* package_optimized/ 2>/dev/null || true
cp -r package/exceptiongroup* package_optimized/ 2>/dev/null || true
cp -r package/flask* package_optimized/ 2>/dev/null || true
cp -r package/h11* package_optimized/ 2>/dev/null || true
cp -r package/h2* package_optimized/ 2>/dev/null || true
cp -r package/hpack* package_optimized/ 2>/dev/null || true
cp -r package/httpcore* package_optimized/ 2>/dev/null || true
cp -r package/httpx* package_optimized/ 2>/dev/null || true
cp -r package/hyperframe* package_optimized/ 2>/dev/null || true
cp -r package/idna* package_optimized/ 2>/dev/null || true
cp -r package/itsdangerous* package_optimized/ 2>/dev/null || true
cp -r package/jinja2* package_optimized/ 2>/dev/null || true
cp -r package/jmespath* package_optimized/ 2>/dev/null || true
cp -r package/jwt* package_optimized/ 2>/dev/null || true
cp -r package/markupsafe* package_optimized/ 2>/dev/null || true
cp -r package/multidict* package_optimized/ 2>/dev/null || true
cp -r package/multiprocess* package_optimized/ 2>/dev/null || true
cp -r package/packaging* package_optimized/ 2>/dev/null || true
cp -r package/postgrest* package_optimized/ 2>/dev/null || true
cp -r package/propcache* package_optimized/ 2>/dev/null || true
cp -r package/psutil* package_optimized/ 2>/dev/null || true
cp -r package/pycparser* package_optimized/ 2>/dev/null || true
cp -r package/pyproject_hooks* package_optimized/ 2>/dev/null || true
cp -r package/realtime* package_optimized/ 2>/dev/null || true
cp -r package/s3transfer* package_optimized/ 2>/dev/null || true
cp -r package/six* package_optimized/ 2>/dev/null || true
cp -r package/sniffio* package_optimized/ 2>/dev/null || true
cp -r package/storage3* package_optimized/ 2>/dev/null || true
cp -r package/strenum* package_optimized/ 2>/dev/null || true
cp -r package/supabase* package_optimized/ 2>/dev/null || true
cp -r package/supabase_auth* package_optimized/ 2>/dev/null || true
cp -r package/supabase_functions* package_optimized/ 2>/dev/null || true
cp -r package/tomli* package_optimized/ 2>/dev/null || true
cp -r package/tzdata* package_optimized/ 2>/dev/null || true
cp -r package/urllib3* package_optimized/ 2>/dev/null || true
cp -r package/websockets* package_optimized/ 2>/dev/null || true
cp -r package/werkzeug* package_optimized/ 2>/dev/null || true
cp -r package/yarl* package_optimized/ 2>/dev/null || true

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
cd package_optimized
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true
find . -name "*.so" -delete 2>/dev/null || true
find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "test_*" -delete 2>/dev/null || true

# Remove large unnecessary packages that aren't needed for Lambda
rm -rf pandas* numpy* 2>/dev/null || true

cd ..

# Create deployment package
echo "📦 Creating deployment package..."
zip -r lambda_deployment_optimized.zip package_optimized/ -x "*.pyc" "*/__pycache__/*" "*/tests/*" "*/test_*"

# Check package size
PACKAGE_SIZE=$(du -h lambda_deployment_optimized.zip | cut -f1)
echo "✅ Package created: lambda_deployment_optimized.zip (${PACKAGE_SIZE})"

if [ $(stat -f%z lambda_deployment_optimized.zip) -lt 5242880 ]; then
    echo "🎉 Package size is under 5MB - optimized for Lambda!"
else
    echo "⚠️  Package size is over 5MB - consider further optimization"
fi

# Clean up
rm -rf package_optimized

echo "🚀 Optimized Lambda package ready for deployment!"
