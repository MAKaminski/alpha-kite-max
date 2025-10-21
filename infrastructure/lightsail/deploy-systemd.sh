#!/bin/bash
set -e

echo "🚀 Deploying Streaming Service to Lightsail (Systemd Version)"

# Configuration
LIGHTSAIL_INSTANCE_NAME="${LIGHTSAIL_INSTANCE_NAME:-equity-options-streamer}"
LIGHTSAIL_REGION="${AWS_REGION:-us-east-1}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found${NC}"
    exit 1
fi

if [ ! -f "env.template" ]; then
    echo -e "${RED}❌ env.template not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"

# Get instance IP
INSTANCE_IP=$(aws lightsail get-instance \
    --instance-name "$LIGHTSAIL_INSTANCE_NAME" \
    --region "$LIGHTSAIL_REGION" \
    --query 'instance.publicIpAddress' \
    --output text 2>/dev/null)

if [ -z "$INSTANCE_IP" ]; then
    echo -e "${RED}❌ Instance not found. Create it first with deploy.sh${NC}"
    exit 1
fi

echo -e "${GREEN}📍 Instance IP: $INSTANCE_IP${NC}"

# SSH key path
SSH_KEY_PATH="${HOME}/.ssh/LightsailDefaultKey-${LIGHTSAIL_REGION}.pem"

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}⚠️  Downloading SSH key...${NC}"
    aws lightsail download-default-key-pair \
        --region "$LIGHTSAIL_REGION" \
        --query 'privateKeyBase64' \
        --output text | base64 --decode > "$SSH_KEY_PATH"
    chmod 600 "$SSH_KEY_PATH"
fi

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p /tmp/lightsail-systemd-deploy
cp -r ../../backend /tmp/lightsail-systemd-deploy/
cp streaming_service.py /tmp/lightsail-systemd-deploy/
cp requirements.txt /tmp/lightsail-systemd-deploy/
cp env.template /tmp/lightsail-systemd-deploy/.env
cp systemd-service.service /tmp/lightsail-systemd-deploy/

cd /tmp/lightsail-systemd-deploy
tar -czf /tmp/streaming-systemd.tar.gz .

# Deploy
echo "🚢 Deploying to Lightsail..."

scp -i "$SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    /tmp/streaming-systemd.tar.gz \
    ec2-user@${INSTANCE_IP}:/tmp/

ssh -i "$SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    ec2-user@${INSTANCE_IP} << 'ENDSSH'
set -e

# Install Python and dependencies
sudo yum install -y python3 python3-pip

# Create service directory
sudo mkdir -p /opt/streaming-service
cd /opt/streaming-service

# Extract files
sudo tar -xzf /tmp/streaming-systemd.tar.gz

# Install Python packages
sudo pip3 install -r requirements.txt

# Install systemd service
sudo cp systemd-service.service /etc/systemd/system/streaming-service.service
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable streaming-service
sudo systemctl restart streaming-service

# Wait a moment
sleep 3

# Check status
sudo systemctl status streaming-service --no-pager

echo ""
echo "✅ Service deployed and started!"
echo ""
echo "⚠️  IMPORTANT: Edit /opt/streaming-service/.env with your credentials!"
echo "   sudo nano /opt/streaming-service/.env"
echo "   sudo systemctl restart streaming-service"
echo ""

ENDSSH

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📝 Useful Commands:"
echo "  View logs:    ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'sudo journalctl -u streaming-service -f'"
echo "  Status:       ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'sudo systemctl status streaming-service'"
echo "  Restart:      ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'sudo systemctl restart streaming-service'"
echo "  Stop:         ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'sudo systemctl stop streaming-service'"
echo "  Edit config:  ssh -i $SSH_KEY_PATH ec2-user@$INSTANCE_IP 'sudo nano /opt/streaming-service/.env'"
echo ""

# Cleanup
rm -f /tmp/streaming-systemd.tar.gz
rm -rf /tmp/lightsail-systemd-deploy

