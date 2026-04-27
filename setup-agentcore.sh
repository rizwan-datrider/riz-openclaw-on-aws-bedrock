#!/bin/bash
exec > >(tee /var/log/openclaw-setup.log)
exec 2>&1

echo "=========================================="
echo "OpenClaw with AgentCore Setup: $(date)"
echo "=========================================="

export DEBIAN_FRONTEND=noninteractive

# System update
echo "[1/10] Updating system..."
apt-get update
apt-get upgrade -y
apt-get install -y unzip curl jq

# Install AWS CLI v2
echo "[2/10] Installing AWS CLI..."
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
  curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
else
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
fi
unzip -q awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install SSM Agent
echo "[3/10] Configuring SSM Agent..."
snap start amazon-ssm-agent || systemctl start amazon-ssm-agent

# Install Docker via GPG-signed apt repo
echo "[4/10] Installing Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Install Node.js
echo "[5/10] Installing Node.js..."
sudo -u ubuntu bash << 'UBUNTU_SCRIPT'
set -e
cd ~

# Install NVM (download first, then execute)
NVM_VERSION="v0.40.1"
for i in 1 2 3; do
  curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o /tmp/nvm-install.sh && break
  echo "NVM download attempt $i failed, retrying in 5s..."
  sleep 5
done
bash /tmp/nvm-install.sh
rm -f /tmp/nvm-install.sh

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Install Node.js 22
nvm install 22
nvm use 22
nvm alias default 22

# Install OpenClaw AgentCore
npm config set registry https://registry.npmjs.org/
npm install -g openclaw-agentcore@latest --timeout=300000 || {
  echo "OpenClaw AgentCore installation failed, retrying..."
  npm cache clean --force
  npm install -g openclaw-agentcore@latest --timeout=300000
}

if ! grep -q 'NVM_DIR' ~/.bashrc; then
    echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> ~/.bashrc
fi
UBUNTU_SCRIPT

# Configure AWS region
echo "[6/10] Configuring AWS..."
TOKEN_IMDS=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || echo "")
if [ -n "$TOKEN_IMDS" ]; then
  REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN_IMDS" http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "")
else
  REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "")
fi

if [ -z "$REGION" ]; then
  REGION="$AWS_REGION"
fi

echo "Detected region: $REGION"
sudo -u ubuntu aws configure set region "$REGION" || echo "AWS configure failed, continuing..."
sudo -u ubuntu aws configure set output json || echo "AWS configure failed, continuing..."

# Get AgentCore Runtime ID (if enabled)
echo "[7/10] Configuring AgentCore..."
RUNTIME_ID=""
STACK_NAME_VAR="$STACK_NAME"
# Wait for runtime to be created (retry up to 5 minutes) - only if AgentCore is enabled
echo "Checking for AgentCore Runtime..."
for i in {1..30}; do
  RUNTIME_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME_VAR" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
    --output text 2>/dev/null || echo "")

  if [ -n "$RUNTIME_ID" ] && [ "$RUNTIME_ID" != "None" ] && [ "$RUNTIME_ID" != "" ]; then
    echo "AgentCore Runtime ID: $RUNTIME_ID"
    break
  fi

  if [ $i -lt 30 ]; then
    echo "Runtime not ready yet, waiting... ($i/30)"
    sleep 10
  fi
done

if [ -z "$RUNTIME_ID" ] || [ "$RUNTIME_ID" = "None" ] || [ "$RUNTIME_ID" = "" ]; then
  echo "Info: AgentCore Runtime not found (may be disabled or not yet created)"
fi

# Configure environment variables
echo "[8/10] Configuring environment variables..."
cat >> /home/ubuntu/.bashrc << 'EOF'
export AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
export AWS_PROFILE=default
export OPENCLAW_MODEL="$OPENCLAW_MODEL"
export OPENCLAW_USE_BEDROCK=true
EOF

# Enable systemd linger
loginctl enable-linger ubuntu
systemctl start user@1000.service

# Configure OpenClaw
echo "[9/10] Configuring OpenClaw..."
sudo -u ubuntu mkdir -p /home/ubuntu/.openclaw

# Generate Gateway Token
GATEWAY_TOKEN=$(openssl rand -hex 24)

# Get instance ID
TOKEN_IMDS=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
if [ -n "$TOKEN_IMDS" ]; then
  INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token: $TOKEN_IMDS" http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
else
  INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
fi

if [ -z "$INSTANCE_ID" ]; then INSTANCE_ID="unknown"; fi

# Create OpenClaw configuration
sudo -u ubuntu cat > /home/ubuntu/.openclaw/openclaw.json << JSONEOF
{
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback",
    "controlUi": {
      "enabled": true,
      "allowInsecureAuth": true,
      "root": "/home/ubuntu/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw-agentcore/dist/control-ui"
    },
    "auth": {
      "mode": "token",
      "token": "GATEWAY_TOKEN_PLACEHOLDER"
    }
  },
  "models": {
    "providers": {
      "amazon-bedrock": {
        "baseUrl": "https://bedrock-runtime.REGION_PLACEHOLDER.amazonaws.com",
        "api": "bedrock-converse-stream",
        "auth": "aws-sdk",
        "models": [
          {
            "id": "MODEL_ID_PLACEHOLDER",
            "name": "Bedrock Model",
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "amazon-bedrock/MODEL_ID_PLACEHOLDER"
      }
    }
  }
}
JSONEOF

# Replace placeholders
sed -i "s/GATEWAY_TOKEN_PLACEHOLDER/$GATEWAY_TOKEN/g" /home/ubuntu/.openclaw/openclaw.json
sed -i "s/REGION_PLACEHOLDER/$REGION/g" /home/ubuntu/.openclaw/openclaw.json
sed -i "s|MODEL_ID_PLACEHOLDER|$OPENCLAW_MODEL|g" /home/ubuntu/.openclaw/openclaw.json

# Ensure proper permissions on config file
chmod 644 /home/ubuntu/.openclaw/openclaw.json
chown ubuntu:ubuntu /home/ubuntu/.openclaw/openclaw.json
chmod 755 /home/ubuntu/.openclaw
chown ubuntu:ubuntu /home/ubuntu/.openclaw

# Add AgentCore configuration if runtime ID was found
if [ -n "$RUNTIME_ID" ] && [ "$RUNTIME_ID" != "None" ] && [ "$RUNTIME_ID" != "" ]; then
  export RUNTIME_ID
  export REGION
  python3 -c "import json, os; c=json.load(open('/home/ubuntu/.openclaw/openclaw.json')); c['agentcore']={'enabled':True,'runtimeId':os.environ['RUNTIME_ID'],'region':os.environ['REGION']}; json.dump(c,open('/home/ubuntu/.openclaw/openclaw.json','w'),indent=2)"
fi

# Set explicit UI root path for global npm installs
export NVM_DIR="/home/ubuntu/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
  NODE_VERSION=$(node --version | cut -d v -f 2)
  UI_ROOT_PATH="/home/ubuntu/.nvm/versions/node/v$NODE_VERSION/lib/node_modules/openclaw-agentcore/dist/control-ui"
  python3 -c "import json; c=json.load(open('/home/ubuntu/.openclaw/openclaw.json')); c['gateway']['controlUi']['root']='$UI_ROOT_PATH'; json.dump(c,open('/home/ubuntu/.openclaw/openclaw.json','w'),indent=2)"
  echo "Set UI root path: $UI_ROOT_PATH"

  # Create template directory and copy templates (for Gateway template resolution)
  TEMPLATE_SRC="/home/ubuntu/.nvm/versions/node/v$NODE_VERSION/lib/node_modules/openclaw-agentcore/docs/reference/templates"
  TEMPLATE_DEST="/home/ubuntu/docs/reference/templates"
  if [ -d "$TEMPLATE_SRC" ]; then
    mkdir -p "$TEMPLATE_DEST"
    cp "$TEMPLATE_SRC"/*.md "$TEMPLATE_DEST/" 2>/dev/null || echo "Warning: Could not copy templates"
    chown -R ubuntu:ubuntu "$TEMPLATE_DEST" 2>/dev/null || true
    echo "Copied templates to $TEMPLATE_DEST"
  fi

  # Initialize workspace files
  WORKSPACE_DIR="/home/ubuntu/.openclaw/workspace"
  mkdir -p "$WORKSPACE_DIR"
  if [ -d "$TEMPLATE_SRC" ]; then
    cp "$TEMPLATE_SRC/AGENTS.md" "$WORKSPACE_DIR/AGENTS.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/SOUL.md" "$WORKSPACE_DIR/SOUL.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/TOOLS.md" "$WORKSPACE_DIR/TOOLS.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/IDENTITY.md" "$WORKSPACE_DIR/IDENTITY.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/USER.md" "$WORKSPACE_DIR/USER.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/HEARTBEAT.md" "$WORKSPACE_DIR/HEARTBEAT.md" 2>/dev/null || true
    cp "$TEMPLATE_SRC/BOOTSTRAP.md" "$WORKSPACE_DIR/BOOTSTRAP.md" 2>/dev/null || true
    chown -R ubuntu:ubuntu "$WORKSPACE_DIR" 2>/dev/null || true
    echo "Initialized workspace files in $WORKSPACE_DIR"
  fi
fi

# Install daemon
sudo -H -u ubuntu XDG_RUNTIME_DIR=/run/user/1000 bash -c '
export HOME=/home/ubuntu
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
openclaw daemon install || echo "Daemon install failed"
'

# Enable messaging channels
echo "[9.5/10] Enabling messaging channels..."
sudo -H -u ubuntu bash -c '
export HOME=/home/ubuntu
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

openclaw plugins enable whatsapp || echo "WhatsApp plugin enable failed"
openclaw plugins enable telegram || echo "Telegram plugin enable failed"
openclaw plugins enable discord || echo "Discord plugin enable failed"
openclaw plugins enable slack || echo "Slack plugin enable failed"
openclaw plugins enable imessage || echo "iMessage plugin enable failed"
openclaw plugins enable googlechat || echo "Google Chat plugin enable failed"
'

# Save token to SSM
# STACK_NAME set from env
aws ssm put-parameter \
  --name "/openclaw/$STACK_NAME/gateway-token" \
  --value "$GATEWAY_TOKEN" \
  --type "SecureString" \
  --region $REGION \
  --overwrite || echo "Failed to save token to SSM"

# Save instance info (non-secret metadata only)
echo "$INSTANCE_ID" > /home/ubuntu/.openclaw/instance_id.txt
echo "$REGION" > /home/ubuntu/.openclaw/region.txt
chown ubuntu:ubuntu /home/ubuntu/.openclaw/*.txt

# Clear token from environment
unset GATEWAY_TOKEN

# Create SSM access script (retrieves token from SSM at runtime — never stored on disk)
cat > /home/ubuntu/ssm-portforward.sh << 'SSMEOF'
#!/bin/bash
IMDS_TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
STACK_NAME=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=aws:cloudformation:stack-name" --query "Tags[0].Value" --output text --region $REGION)
TOKEN=$(aws ssm get-parameter --name "/openclaw/$STACK_NAME/gateway-token" --with-decryption --query Parameter.Value --output text --region $REGION)

echo "=========================================="
echo "OpenClaw SSM Port Forwarding"
echo "=========================================="
echo ""
echo "Run on your local computer:"
echo ""
echo "aws ssm start-session \\"
echo "  --target $INSTANCE_ID \\"
echo "  --region $REGION \\"
echo "  --document-name AWS-StartPortForwardingSession \\"
echo "  --parameters '{\"portNumber\":[\"18789\"],\"localPortNumber\":[\"18789\"]}'"
echo ""
echo "Then open in browser:"
echo "http://localhost:18789/?token=$TOKEN"
echo ""
echo "=========================================="
SSMEOF
chmod +x /home/ubuntu/ssm-portforward.sh
chown ubuntu:ubuntu /home/ubuntu/ssm-portforward.sh

# Install cfn-bootstrap and signal
echo "[10/10] Installing cfn-bootstrap and signaling..."
apt-get install -y python3-pip 2>&1 | tee -a /var/log/openclaw-setup.log
pip3 install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz 2>&1 | tee -a /var/log/openclaw-setup.log

CFN_SIGNAL=$(which cfn-signal 2>/dev/null || find /usr -name cfn-signal 2>/dev/null | head -1)
COMPLETE_MSG="OpenClaw ready. Retrieve token from SSM: aws ssm get-parameter --name /openclaw/$STACK_NAME/gateway-token --with-decryption --query Parameter.Value --output text --region $REGION"

if [ -n "$CFN_SIGNAL" ]; then
  $CFN_SIGNAL -e 0 -d "$COMPLETE_MSG" -r "OpenClaw ready" "$WAIT_HANDLE"
else
  SIGNAL_JSON="{\"Status\":\"SUCCESS\",\"Reason\":\"OpenClaw ready\",\"UniqueId\":\"openclaw\",\"Data\":\"$COMPLETE_MSG\"}"
  curl -X PUT -H 'Content-Type:' --data-binary "$SIGNAL_JSON" "$WAIT_HANDLE"
fi

echo "=========================================="
echo "OpenClaw installation complete!"
echo "Token stored in SSM Parameter Store"
echo "=========================================="
