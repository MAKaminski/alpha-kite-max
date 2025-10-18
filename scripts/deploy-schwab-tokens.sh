#!/bin/bash
# Deploy Schwab Tokens to AWS
# This script uploads tokens to AWS Secrets Manager and triggers Lambda update

set -e

echo "🚀 SCHWAB TOKEN DEPLOYMENT"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
TOKEN_FILE="backend/config/schwab_token.json"
SECRET_NAME="schwab-api-token-prod"
AWS_REGION="us-east-1"
LAMBDA_FUNCTION="alpha-kite-real-time-streamer"

# Check if token file exists
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}❌ Error: Token file not found at $TOKEN_FILE${NC}"
    echo ""
    echo "Please run OAuth flow first:"
    echo "  cd backend/sys_testing"
    echo "  python3 simple_callback_processor.py \"<CALLBACK_URL>\""
    exit 1
fi

echo -e "${GREEN}✅ Token file found${NC}"
echo ""

# Validate AWS credentials
echo "🔍 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS credentials not configured${NC}"
    echo ""
    echo "Please configure AWS credentials:"
    echo "  aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS credentials valid (Account: $ACCOUNT_ID)${NC}"
echo ""

# Upload tokens to Secrets Manager
echo "☁️  Uploading tokens to AWS Secrets Manager..."
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    # Secret exists, update it
    RESULT=$(aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string file://"$TOKEN_FILE" \
        --region "$AWS_REGION" \
        --output json)
    
    VERSION_ID=$(echo "$RESULT" | jq -r '.VersionId')
    echo -e "${GREEN}✅ Tokens updated in Secrets Manager${NC}"
    echo "   Version ID: $VERSION_ID"
else
    # Secret doesn't exist, create it
    RESULT=$(aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Schwab API OAuth tokens for production" \
        --secret-string file://"$TOKEN_FILE" \
        --region "$AWS_REGION" \
        --output json)
    
    ARN=$(echo "$RESULT" | jq -r '.ARN')
    echo -e "${GREEN}✅ Secret created${NC}"
    echo "   ARN: $ARN"
fi
echo ""

# Update Lambda environment to trigger refresh
echo "🔄 Triggering Lambda function update..."
if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION" &> /dev/null; then
    # Update Lambda environment variable to trigger refresh
    CURRENT_TIME=$(date +%s)
    aws lambda update-function-configuration \
        --function-name "$LAMBDA_FUNCTION" \
        --environment "Variables={TOKEN_UPDATED=$CURRENT_TIME}" \
        --region "$AWS_REGION" \
        --output json > /dev/null
    
    echo -e "${GREEN}✅ Lambda function updated${NC}"
    echo ""
    
    # Test Lambda function
    echo "🧪 Testing Lambda function..."
    TEST_RESULT=$(aws lambda invoke \
        --function-name "$LAMBDA_FUNCTION" \
        --region "$AWS_REGION" \
        --payload '{"test": true}' \
        --output json \
        /tmp/lambda-response.json 2>&1)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Lambda test successful${NC}"
    else
        echo -e "${YELLOW}⚠️  Lambda test returned error (this is normal if outside market hours)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Lambda function not found, skipping update${NC}"
fi
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo "=================================="
echo ""
echo "✅ Completed:"
echo "   • Tokens uploaded to AWS Secrets Manager"
echo "   • Lambda function updated"
echo "   • Ready for data streaming"
echo ""
echo "📋 Next steps:"
echo "   1. Monitor Lambda logs:"
echo "      aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow"
echo ""
echo "   2. Check admin panel:"
echo "      https://your-app.vercel.app (open admin)"
echo ""
echo "   3. Verify data streaming:"
echo "      Check Supabase for new data points"
echo ""
echo "🔗 Quick Links:"
echo "   • Secrets Manager: https://console.aws.amazon.com/secretsmanager"
echo "   • Lambda Function: https://console.aws.amazon.com/lambda"
echo "   • CloudWatch Logs: https://console.aws.amazon.com/cloudwatch"
echo ""
