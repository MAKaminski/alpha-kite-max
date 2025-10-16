#!/bin/bash
set -e

echo "========================================"
echo "AWS Lambda Deployment Script"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to script directory
cd "$(dirname "$0")"

echo -e "${YELLOW}Step 1: Cleaning up old builds...${NC}"
rm -rf lambda/package
rm -f lambda/lambda_deployment.zip

echo -e "${YELLOW}Step 2: Creating package directory...${NC}"
mkdir -p lambda/package

echo -e "${YELLOW}Step 3: Installing Python dependencies...${NC}"
cd lambda
pip install -r requirements.txt -t package/ --platform manylinux2014_x86_64 --only-binary=:all:

echo -e "${YELLOW}Step 4: Copying Lambda code...${NC}"
cp *.py package/

echo -e "${YELLOW}Step 5: Copying parent modules...${NC}"
# Copy backend modules that Lambda needs
cp -r ../schwab_integration package/
cp ../supabase_client.py package/

echo -e "${YELLOW}Step 6: Creating deployment package...${NC}"
cd package
zip -r ../lambda_deployment.zip . -q

echo -e "${GREEN}✓ Lambda deployment package created: lambda/lambda_deployment.zip${NC}"
echo -e "  Size: $(du -h ../lambda_deployment.zip | cut -f1)"

cd ../../

echo -e "${YELLOW}Step 7: Checking Terraform setup...${NC}"
cd infrastructure

if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}⚠ Warning: terraform.tfvars not found${NC}"
    echo "Creating terraform.tfvars template..."
    cat > terraform.tfvars <<EOF
# AWS Configuration
aws_region = "us-east-1"
environment = "prod"
default_ticker = "QQQ"

# Supabase Configuration
supabase_url = "your-supabase-url"
supabase_key = "your-supabase-service-role-key"

# Schwab API Configuration
schwab_app_key = "your-schwab-app-key"
schwab_secret = "your-schwab-app-secret"
EOF
    echo -e "${YELLOW}Please edit infrastructure/terraform.tfvars with your credentials${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 8: Initializing Terraform...${NC}"
terraform init

echo -e "${YELLOW}Step 9: Validating Terraform configuration...${NC}"
terraform validate

if [ "$1" == "--plan-only" ]; then
    echo -e "${YELLOW}Step 10: Planning Terraform deployment...${NC}"
    terraform plan
    echo -e "${GREEN}✓ Plan complete. Run without --plan-only to deploy.${NC}"
    exit 0
fi

echo -e "${YELLOW}Step 10: Deploying to AWS...${NC}"
terraform apply

echo ""
echo -e "${GREEN}========================================"
echo "Deployment Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Set Schwab token in AWS Secrets Manager:"
echo "   aws secretsmanager put-secret-value \\"
echo "     --secret-id schwab-api-token-prod \\"
echo "     --secret-string file://backend/config/schwab_token.json"
echo ""
echo "2. Test Lambda function:"
echo "   aws lambda invoke \\"
echo "     --function-name alpha-kite-real-time-streamer \\"
echo "     --payload '{}' \\"
echo "     response.json"
echo ""
echo "3. Check CloudWatch logs:"
echo "   aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow"
echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"

