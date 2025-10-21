#!/bin/bash
set -e

echo "🚀 Deploying Equity/Options Streaming Service to AWS Lightsail"

# Configuration
LIGHTSAIL_INSTANCE_NAME="${LIGHTSAIL_INSTANCE_NAME:-equity-options-streamer}"
LIGHTSAIL_REGION="${AWS_REGION:-us-east-1}"
LIGHTSAIL_BLUEPRINT="amazon_linux_2"
LIGHTSAIL_BUNDLE="nano_2_0"  # $3.50/month

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Please create one from .env.example${NC}"
    echo "cp .env.example .env"
    echo "Then edit .env with your credentials"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"

# Create Lightsail instance if it doesn't exist
echo "🔍 Checking if Lightsail instance exists..."

if aws lightsail get-instance --instance-name "$LIGHTSAIL_INSTANCE_NAME" --region "$LIGHTSAIL_REGION" &> /dev/null; then
    echo -e "${YELLOW}Instance already exists${NC}"
else
    echo "🆕 Creating new Lightsail instance..."
    
    # Create startup script
    cat > lightsail-startup.sh <<'EOF'
#!/bin/bash
# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/streaming-service
cd /opt/streaming-service

echo "Lightsail instance ready for deployment"
EOF
    
    aws lightsail create-instances \
        --instance-names "$LIGHTSAIL_INSTANCE_NAME" \
        --availability-zone "${LIGHTSAIL_REGION}a" \
        --blueprint-id "$LIGHTSAIL_BLUEPRINT" \
        --bundle-id "$LIGHTSAIL_BUNDLE" \
        --user-data file://lightsail-startup.sh \
        --region "$LIGHTSAIL_REGION"
    
    echo -e "${GREEN}✓ Instance created. Waiting for it to be running...${NC}"
    sleep 30
fi

# Get instance IP
INSTANCE_IP=$(aws lightsail get-instance \
    --instance-name "$LIGHTSAIL_INSTANCE_NAME" \
    --region "$LIGHTSAIL_REGION" \
    --query 'instance.publicIpAddress' \
    --output text)

echo -e "${GREEN}📍 Instance IP: $INSTANCE_IP${NC}"

# Wait for instance to be fully ready
echo "⏳ Waiting for instance to be ready..."
sleep 60

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p /tmp/lightsail-deploy
cp -r ../../backend /tmp/lightsail-deploy/
cp streaming_service.py /tmp/lightsail-deploy/
cp requirements.txt /tmp/lightsail-deploy/
cp docker-compose.yml /tmp/lightsail-deploy/
cp Dockerfile /tmp/lightsail-deploy/
cp .env /tmp/lightsail-deploy/

# Create tarball
cd /tmp/lightsail-deploy
tar -czf /tmp/streaming-service.tar.gz .

# Get SSH key path
SSH_KEY_PATH="${HOME}/.ssh/LightsailDefaultKey-${LIGHTSAIL_REGION}.pem"

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}⚠️  Downloading SSH key...${NC}"
    aws lightsail download-default-key-pair \
        --region "$LIGHTSAIL_REGION" \
        --query 'privateKeyBase64' \
        --output text | base64 --decode > "$SSH_KEY_PATH"
    chmod 600 "$SSH_KEY_PATH"
fi

# Deploy to Lightsail
echo "🚢 Deploying to Lightsail instance..."

# Copy deployment package
scp -i "$SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    /tmp/streaming-service.tar.gz \
    ec2-user@${INSTANCE_IP}:/tmp/

# Extract and run on instance
ssh -i "$SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    ec2-user@${INSTANCE_IP} << 'ENDSSH'
set -e

# Extract deployment
cd /opt/streaming-service
sudo tar -xzf /tmp/streaming-service.tar.gz

# Stop existing containers
sudo docker-compose down || true

# Build and start containers
sudo docker-compose up -d --build

# Show logs
sudo docker-compose logs -f --tail=50

ENDSSH

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Service Information:"
echo "  Instance Name: $LIGHTSAIL_INSTANCE_NAME"
echo "  Instance IP: $INSTANCE_IP"
echo "  Region: $LIGHTSAIL_REGION"
echo ""
echo "📝 Useful Commands:"
echo "  View logs:    ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'cd /opt/streaming-service && sudo docker-compose logs -f'"
echo "  Restart:      ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'cd /opt/streaming-service && sudo docker-compose restart'"
echo "  Stop:         ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'cd /opt/streaming-service && sudo docker-compose down'"
echo "  SSH access:   ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP"
echo ""
echo -e "${GREEN}🎉 Streaming service is now running!${NC}"

# Cleanup
rm -f /tmp/streaming-service.tar.gz
rm -f lightsail-startup.sh
rm -rf /tmp/lightsail-deploy

