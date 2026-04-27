#!/bin/bash
# macOS setup script for OpenClaw

exec > /tmp/openclaw-setup.log 2>&1

echo "=========================================="
echo "OpenClaw AWS Mac Setup: $(date)"
echo "Instance Type: ${MacInstanceType}"
echo "=========================================="

# Wait for system to be ready
sleep 30

# Get current user (ec2-user on Mac instances)
CURRENT_USER="ec2-user"
USER_HOME="/Users/$CURRENT_USER"

# Detect region and instance ID once (IMDSv2)
echo "[*] Detecting instance metadata..."
IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || echo "")
if [ -n "$IMDS_TOKEN" ]; then
  AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "")
  INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "")
else
  AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "")
  INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "")
fi
AWS_REGION=${AWS_REGION:-"$AWS_REGION"}
INSTANCE_ID=${INSTANCE_ID:-"unknown"}
echo "Region: $AWS_REGION | Instance: $INSTANCE_ID"

# System update via softwareupdate
echo "[1/9] Checking for system updates..."
softwareupdate --list 2>/dev/null || true

# Install Homebrew if not present
echo "[2/9] Installing Homebrew..."
if ! command -v brew &> /dev/null; then
  sudo -u $CURRENT_USER /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/null

  # Add Homebrew to PATH for Apple Silicon
  if [[ $(uname -m) == "arm64" ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $USER_HOME/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi

# Source Homebrew for current session
if [[ $(uname -m) == "arm64" ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
else
  eval "$(/usr/local/bin/brew shellenv)"
fi

# Install AWS CLI
echo "[3/9] Installing AWS CLI..."
sudo -u $CURRENT_USER brew install awscli || true

# Install SSM Agent for macOS
echo "[3.5/9] Installing SSM Agent..."
# Download and install SSM Agent for macOS
if [[ $(uname -m) == "arm64" ]]; then
  curl -o /tmp/amazon-ssm-agent.pkg "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/darwin_arm64/amazon-ssm-agent.pkg"
else
  curl -o /tmp/amazon-ssm-agent.pkg "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/darwin_amd64/amazon-ssm-agent.pkg"
fi
installer -pkg /tmp/amazon-ssm-agent.pkg -target /
rm -f /tmp/amazon-ssm-agent.pkg

# Start SSM Agent
launchctl load -w /Library/LaunchDaemons/com.amazon.aws.ssm.plist || true
launchctl start com.amazon.aws.ssm || true

# Install Node.js via NVM
echo "[4/9] Installing Node.js..."
sudo -u $CURRENT_USER bash << 'USERSCRIPT'
cd ~

# Install NVM (download first, then execute)
NVM_VERSION="v0.40.1"
curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o /tmp/nvm-install.sh
bash /tmp/nvm-install.sh
rm -f /tmp/nvm-install.sh

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Install Node.js 22
nvm install 22
nvm use 22
nvm alias default 22

# Install OpenClaw
# arm64 (Apple Silicon) has no prebuilt @discordjs/opus binary, use --ignore-scripts
npm config set registry https://registry.npmjs.org/
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  echo "Apple Silicon detected, installing with --ignore-scripts..."
  npm install -g openclaw@latest --timeout=300000 --ignore-scripts || {
    echo "OpenClaw installation failed on arm64, retrying..."
    npm cache clean --force
    npm install -g openclaw@latest --timeout=300000 --ignore-scripts
  }
else
  npm install -g openclaw@latest --timeout=300000 || {
    echo "OpenClaw installation failed, retrying..."
    npm cache clean --force
    npm install -g openclaw@latest --timeout=300000
  }
fi

# Add NVM to shell profile
if ! grep -q 'NVM_DIR' ~/.zshrc 2>/dev/null; then
  echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zshrc
  echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> ~/.zshrc
fi
USERSCRIPT

# Verify openclaw installed
OPENCLAW_MJS=$(find $USER_HOME/.nvm -path "*/node_modules/openclaw/openclaw.mjs" 2>/dev/null | head -1)
NODE_BIN=$(find $USER_HOME/.nvm -name node -type f 2>/dev/null | head -1)
if [ -z "$OPENCLAW_MJS" ] || [ -z "$NODE_BIN" ]; then
  echo "FATAL: openclaw or node not found - npm install likely failed"
  exit 1
fi
echo "openclaw found: $OPENCLAW_MJS"

# Configure AWS region
echo "[5/9] Configuring AWS..."
sudo -u $CURRENT_USER mkdir -p $USER_HOME/.aws
sudo -u $CURRENT_USER bash -c "printf '[default]\nregion = %s\noutput = json\n' \"$AWS_REGION\" > $USER_HOME/.aws/config"
chown -R $CURRENT_USER:staff $USER_HOME/.aws
chmod 600 $USER_HOME/.aws/config

# Configure environment variables
echo "[6/9] Configuring environment variables..."
{
  echo "export AWS_REGION=$AWS_REGION"
  echo "export AWS_DEFAULT_REGION=$AWS_REGION"
  echo "export AWS_PROFILE=default"
  echo "export OPENCLAW_MODEL=${OpenClawModel}"
  echo "export OPENCLAW_USE_BEDROCK=true"
} >> $USER_HOME/.zshrc

# Configure OpenClaw
echo "[7/9] Configuring OpenClaw..."

# Create config directory
sudo -u $CURRENT_USER mkdir -p $USER_HOME/.openclaw

# Generate Gateway Token
GATEWAY_TOKEN=$(openssl rand -hex 24)

# Create Bedrock configuration file (write as ec2-user to ensure correct ownership)
sudo -u $CURRENT_USER tee $USER_HOME/.openclaw/openclaw.json > /dev/null << 'JSONEOF'
{
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback",
    "controlUi": {
      "enabled": true,
      "allowInsecureAuth": true
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
sed -i '' "s/GATEWAY_TOKEN_PLACEHOLDER/$GATEWAY_TOKEN/g" $USER_HOME/.openclaw/openclaw.json
sed -i '' "s/REGION_PLACEHOLDER/$AWS_REGION/g" $USER_HOME/.openclaw/openclaw.json
sed -i '' "s|MODEL_ID_PLACEHOLDER|$OPENCLAW_MODEL|g" $USER_HOME/.openclaw/openclaw.json

# Install and start OpenClaw gateway using launchd (macOS native)
echo "[8/9] Installing OpenClaw gateway service..."

# Build absolute paths for launchd (cannot rely on nvm in launchd env)
OPENCLAW_MJS_PATH=$(find $USER_HOME/.nvm -path "*/node_modules/openclaw/openclaw.mjs" 2>/dev/null | head -1)
NODE_BIN_PATH=$(find $USER_HOME/.nvm -name node -type f 2>/dev/null | head -1)

# Write plist with absolute paths using echo (avoids heredoc YAML issues)
PLIST_FILE="/Library/LaunchDaemons/com.openclaw.gateway.plist"
echo '<?xml version="1.0" encoding="UTF-8"?>' > $PLIST_FILE
echo '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' >> $PLIST_FILE
echo '<plist version="1.0"><dict>' >> $PLIST_FILE
echo '<key>Label</key><string>com.openclaw.gateway</string>' >> $PLIST_FILE
echo '<key>ProgramArguments</key><array>' >> $PLIST_FILE
echo "<string>$NODE_BIN_PATH</string>" >> $PLIST_FILE
echo "<string>$OPENCLAW_MJS_PATH</string>" >> $PLIST_FILE
echo '</array>' >> $PLIST_FILE
echo "<key>UserName</key><string>$CURRENT_USER</string>" >> $PLIST_FILE
echo "<key>WorkingDirectory</key><string>$USER_HOME</string>" >> $PLIST_FILE
echo '<key>EnvironmentVariables</key><dict>' >> $PLIST_FILE
echo "<key>HOME</key><string>$USER_HOME</string>" >> $PLIST_FILE
echo "<key>AWS_REGION</key><string>$AWS_REGION</string>" >> $PLIST_FILE
echo '</dict>' >> $PLIST_FILE
echo '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>' >> $PLIST_FILE
echo '<key>StandardOutPath</key><string>/tmp/openclaw-gateway.log</string>' >> $PLIST_FILE
echo '<key>StandardErrorPath</key><string>/tmp/openclaw-gateway.err</string>' >> $PLIST_FILE
echo '</dict></plist>' >> $PLIST_FILE

launchctl load -w $PLIST_FILE || true
# Enable messaging channels
echo "[8.5/9] Enabling messaging channels..."
sudo -u $CURRENT_USER bash << 'CHANNELSCRIPT'
export HOME=/Users/ec2-user
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Enable WhatsApp
openclaw plugins enable whatsapp || echo "WhatsApp plugin enable failed"

# Enable Telegram
openclaw plugins enable telegram || echo "Telegram plugin enable failed"

# Enable Discord
openclaw plugins enable discord || echo "Discord plugin enable failed"

# Enable Slack
openclaw plugins enable slack || echo "Slack plugin enable failed"

# Enable iMessage
openclaw plugins enable imessage || echo "iMessage plugin enable failed"

# Enable Google Chat
openclaw plugins enable googlechat || echo "Google Chat plugin enable failed"
CHANNELSCRIPT

# Wait for port 18789 to be ready
echo "Waiting for OpenClaw gateway to start..."
for i in $(seq 1 30); do
  if lsof -i :18789 > /dev/null 2>&1; then
    echo "OpenClaw gateway is up on port 18789"
    break
  fi
  echo "Attempt $i/30: port 18789 not ready yet, waiting..."
  sleep 2
done

if ! lsof -i :18789 > /dev/null 2>&1; then
  echo "WARNING: Gateway did not start within 60s, check /tmp/openclaw-gateway.err"
fi

# Save token to SSM Parameter Store (encrypted, never written to disk)
# STACK_NAME set from env
aws ssm put-parameter \
  --name "/openclaw/$STACK_NAME/gateway-token" \
  --value "$GATEWAY_TOKEN" \
  --type "SecureString" \
  --region $AWS_REGION \
  --overwrite || echo "Failed to save token to SSM"
unset GATEWAY_TOKEN

# Save instance info (non-secret metadata only)
echo "$INSTANCE_ID" > $USER_HOME/.openclaw/instance_id.txt
echo "$AWS_REGION" > $USER_HOME/.openclaw/region.txt

# Create SSM access script (retrieves token from SSM at runtime — never stored on disk)
cat > $USER_HOME/ssm-portforward.sh << 'SSMEOF'
#!/bin/bash
IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
STACK_NAME=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=aws:cloudformation:stack-name" --query "Tags[0].Value" --output text --region $REGION)
TOKEN=$(aws ssm get-parameter --name "/openclaw/$STACK_NAME/gateway-token" --with-decryption --query Parameter.Value --output text --region $REGION)

echo "=========================================="
echo "OpenClaw SSM Port Forwarding (Mac)"
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
chmod +x $USER_HOME/ssm-portforward.sh
chown $CURRENT_USER:staff $USER_HOME/ssm-portforward.sh

# Complete
echo "[9/9] Complete!"
echo "SUCCESS" > $USER_HOME/.openclaw/setup_status.txt
echo "Setup completed: $(date)" >> $USER_HOME/.openclaw/setup_status.txt
echo "Mac Instance Type: $MAC_INSTANCE_TYPE" >> $USER_HOME/.openclaw/setup_status.txt

# Signal CloudFormation (token NOT included — retrieve from SSM)
COMPLETE_MSG="OpenClaw ready. Retrieve token from SSM: aws ssm get-parameter --name /openclaw/$STACK_NAME/gateway-token --with-decryption --query Parameter.Value --output text --region $AWS_REGION"

# Use curl to signal (cfn-signal not available on macOS by default)
SIGNAL_JSON="{\"Status\":\"SUCCESS\",\"Reason\":\"OpenClaw ready on Mac\",\"UniqueId\":\"openclaw-mac\",\"Data\":\"$COMPLETE_MSG\"}"
curl -X PUT -H "Content-Type:" --data-binary "$SIGNAL_JSON" "$WAIT_HANDLE"

echo "Signal sent successfully"

echo "=========================================="
echo "OpenClaw Mac installation complete!"
echo "Instance Type: ${MacInstanceType}"
echo "Token stored in SSM Parameter Store"
echo "=========================================="
