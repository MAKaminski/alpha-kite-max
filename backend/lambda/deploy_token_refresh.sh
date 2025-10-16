#!/bin/bash

# Deploy Token Refresh Lambda Function
# This function handles token refresh requests from the admin panel

set -e

echo "🚀 Deploying Token Refresh Lambda Function"
echo "=========================================="

# Configuration
FUNCTION_NAME="alpha-kite-token-refresh"
REGION="us-east-1"
ROLE_NAME="alpha-kite-lambda-role"

# Check if we're in the right directory
if [ ! -f "token_refresh.py" ]; then
    echo "❌ Error: token_refresh.py not found. Run this script from the lambda/ directory."
    exit 1
fi

echo "📦 Creating deployment package..."

# Create package directory
mkdir -p package
cd package

# Copy the token refresh function
cp ../token_refresh.py ./lambda_function.py

# Install dependencies
echo "📥 Installing dependencies..."
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install --no-cache-dir boto3 requests structlog

# Copy packages to package directory
cp -r venv/lib/python*/site-packages/* .

# Clean up unnecessary files to reduce package size
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Create deployment zip
echo "📦 Creating deployment zip..."
zip -r ../token_refresh_deployment.zip . -q
cd ..

echo "✅ Package created: token_refresh_deployment.zip"
echo "📊 Package size: $(du -h token_refresh_deployment.zip | cut -f1)"

# Check if Lambda function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "📝 Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://token_refresh_deployment.zip \
        --region $REGION
    
    echo "✅ Lambda function updated successfully!"
else
    echo "🆕 Creating new Lambda function..."
    
    # Create IAM role if it doesn't exist
    if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "🔧 Creating IAM role..."
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }'
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
        
        echo "⏳ Waiting for role to be ready..."
        sleep 10
    fi
    
    # Get role ARN
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    
    # Create Lambda function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.10 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://token_refresh_deployment.zip \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION \
        --description "Token refresh endpoint for Schwab API"
    
    echo "✅ Lambda function created successfully!"
fi

# Configure function settings
echo "⚙️  Configuring function settings..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout 30 \
    --memory-size 256 \
    --region $REGION

# Create API Gateway endpoint (optional)
echo "🌐 Setting up API Gateway endpoint..."
API_NAME="alpha-kite-api"

# Check if API Gateway exists
if aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text | grep -q .; then
    API_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text)
    echo "📝 Using existing API Gateway: $API_ID"
else
    echo "🆕 Creating new API Gateway..."
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "API for Alpha Kite trading system" \
        --query 'id' --output text)
fi

# Get Lambda function ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

# Create resource and method
echo "🔗 Creating API Gateway resource..."
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[?path==`/`].id' --output text)

# Create token-refresh resource
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part token-refresh \
    --query 'id' --output text)

# Create POST method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"

# Add Lambda permission for API Gateway
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id "api-gateway-invoke" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:*:$API_ID/*/*" \
    --region $REGION

# Deploy API
STAGE_NAME="prod"
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE_NAME \
    --description "Production deployment"

# Get API Gateway URL
API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/token-refresh"

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo ""
echo "📋 Function Details:"
echo "   Name: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Runtime: Python 3.10"
echo "   Memory: 256 MB"
echo "   Timeout: 30 seconds"
echo ""
echo "🌐 API Gateway Endpoint:"
echo "   URL: $API_URL"
echo "   Method: POST"
echo ""
echo "📝 Usage:"
echo "   curl -X POST $API_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"action\": \"check_token_status\"}'"
echo ""
echo "🔧 Next Steps:"
echo "   1. Update frontend API route with the endpoint URL above"
echo "   2. Test the endpoint: curl -X POST $API_URL -H 'Content-Type: application/json' -d '{\"action\": \"check_token_status\"}'"
echo "   3. Deploy frontend changes to Vercel"
echo ""

# Clean up
rm -rf package
rm -f token_refresh_deployment.zip

echo "🧹 Cleanup complete!"
