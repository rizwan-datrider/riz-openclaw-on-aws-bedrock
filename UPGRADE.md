# Upgrade Guide: v2026.3.24 → v2026.4.5

OpenClaw v2026.4.5 introduces a new model runtime (`pi-coding-agent`), plugin-based provider discovery, and memory/embeddings support. However, it includes breaking changes to Bedrock authentication and configuration that require manual steps.

Two upgrade paths:
- **[In-Place Upgrade](#option-1-in-place-upgrade-recommended)** — Preserves chat history, channel connections, skills, and config (recommended)
- **[Fresh Install](#option-2-fresh-install)** — Delete and redeploy from scratch

## What Changed in v2026.4.5

| Area | v2026.3.24 (Legacy) | v2026.4.5 (Modern) |
|------|---------------------|---------------------|
| **Config style** | `models.providers` (explicit model list) | `plugins.entries` (auto-discovers Bedrock models) |
| **Auth field** | `"auth": "aws-sdk"` (required) | Ignored — auth resolved via environment variables |
| **API field** | `"api": "bedrock-converse-stream"` | Still required if using legacy config; not needed with plugins |
| **AWS env vars** | Not required (SDK default chain works) | `AWS_PROFILE=default` required for EC2 IMDS auth |
| **Install flags** | `--ignore-scripts` on ARM64 | Must NOT use `--ignore-scripts` (needs `@buape/carbon`) |

### Known Issue: EC2 IMDS Authentication

v2026.4.5's `resolveAwsSdkAuthInfo()` checks for AWS environment variables (`AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, etc.) before falling through to the SDK default credential chain. On EC2 with IAM roles, no env vars are set — credentials come from IMDS — so auth fails with:

```
No API key found for amazon-bedrock.
```

**Workaround**: Set `AWS_PROFILE=default` in `~/.openclaw/.env`.

---

## Prerequisites

Set these variables to match your deployment before running any commands below:

```bash
STACK_NAME="openclaw-bedrock"   # ← your CloudFormation stack name
REGION="us-west-2"              # ← your deployment region
```

---

## Option 1: In-Place Upgrade (Recommended)

Preserves all your data:
- Chat history and conversation state
- Channel connections (WhatsApp, Telegram, Discord, Slack)
- SOUL.md customizations, installed skills, cron jobs
- Gateway token (no re-authentication needed)

### Connect to the instance

```bash
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text --region $REGION)

aws ssm start-session --target $INSTANCE_ID --region $REGION
sudo su - ubuntu
```

### Step 1: Back up

```bash
openclaw --version   # Confirm current version before upgrading
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
cp ~/.openclaw/.env ~/.openclaw/.env.bak 2>/dev/null || true
ls -la ~/.openclaw/*.bak
```

### Step 2: Install v2026.4.5

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Do NOT use --ignore-scripts (v2026.4.5 needs native modules)
npm install -g openclaw@2026.4.5 --timeout=300000
openclaw --version
```

### Step 3: Set up environment variables

```bash
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# .env loaded by gateway systemd service
printf 'AWS_PROFILE=default\nAWS_REGION=%s\nAWS_DEFAULT_REGION=%s\n' "$REGION" "$REGION" > ~/.openclaw/.env

# systemd user environment for non-service processes
mkdir -p ~/.config/environment.d
printf 'AWS_REGION=%s\nAWS_DEFAULT_REGION=%s\nAWS_PROFILE=default\n' "$REGION" "$REGION" > ~/.config/environment.d/aws.conf
```

### Step 4: Migrate configuration

**Option A — Modern plugin-based config (recommended):**

```bash
TOKEN=$(python3 << 'PYEOF'
import json, os
with open(os.path.expanduser('~/.openclaw/openclaw.json')) as f:
    cfg = json.load(f)
print(cfg['gateway']['auth']['token'])
PYEOF
)

MODEL=$(python3 << 'PYEOF'
import json, os
with open(os.path.expanduser('~/.openclaw/openclaw.json')) as f:
    cfg = json.load(f)
print(cfg['agents']['defaults']['model']['primary'].split('/')[-1])
PYEOF
)

cat > ~/.openclaw/openclaw.json << EOF
{
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback",
    "controlUi": { "enabled": true, "allowInsecureAuth": true },
    "auth": { "mode": "token", "token": "$TOKEN" }
  },
  "plugins": {
    "entries": {
      "amazon-bedrock": { "enabled": true }
    }
  },
  "agents": {
    "defaults": {
      "model": { "primary": "amazon-bedrock/$MODEL" },
      "memorySearch": { "provider": "bedrock", "model": "amazon.titan-embed-text-v2:0" }
    }
  }
}
EOF
```

**Option B — Keep legacy config with minimal changes:**

```bash
python3 << 'PYEOF'
import json, os, sys

cfg_path = os.path.expanduser('~/.openclaw/openclaw.json')
with open(cfg_path) as f:
    cfg = json.load(f)

provider = cfg['models']['providers']['amazon-bedrock']
provider.pop('auth', None)

if 'api' not in provider:
    print('ERROR: api field required — add: "api": "bedrock-converse-stream"')
    sys.exit(1)
if 'baseUrl' not in provider:
    print('ERROR: baseUrl field required')
    sys.exit(1)

with open(cfg_path, 'w') as f:
    json.dump(cfg, f, indent=2)
print('Config updated')
PYEOF
```

> **Important**: With Option B, the `api` field (`"bedrock-converse-stream"`) must remain. Without it, v2026.4.5 defaults to raw HTTP calls, causing "LLM request timed out" errors.

### Step 5: Restart gateway

```bash
openclaw gateway install --force
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```

### Step 6: Verify

```bash
openclaw --version
systemctl --user status openclaw-gateway.service --no-pager
journalctl --user -u openclaw-gateway.service -n 50 --no-pager
```

---

## Option 2: Fresh Install

> **Warning**: This **destroys all user data** — chat history, channel connections (must re-pair WhatsApp, Telegram, etc.), SOUL.md, skills, cron jobs, and gateway token. Even with `EnableDataProtection=true`, the retained data volume must be manually reattached — the template always creates a new volume on redeploy.

### Step 1: Delete existing stack

```bash
aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
```

### Step 2: Clean up SSM parameter

```bash
aws ssm delete-parameter \
  --name "/openclaw/$STACK_NAME/gateway-token" \
  --region $REGION 2>/dev/null || true
```

### Step 3: Redeploy with v2026.4.5

```bash
aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://clawdbot-bedrock.yaml \
  --parameters \
    ParameterKey=KeyPairName,ParameterValue=none \
    ParameterKey=OpenClawVersion,ParameterValue=2026.4.5 \
    ParameterKey=OpenClawModel,ParameterValue=global.amazon.nova-2-lite-v1:0 \
    ParameterKey=InstanceType,ParameterValue=c7g.large \
    ParameterKey=CreateVPCEndpoints,ParameterValue=true \
  --capabilities CAPABILITY_IAM \
  --region $REGION

aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION
```

The template automatically handles all v2026.4.5 configuration (modern plugin config, `AWS_PROFILE=default`, environment variables).

### Step 4: Verify and reconnect

```bash
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text --region $REGION)

aws ssm start-session --target $INSTANCE_ID --region $REGION
sudo su - ubuntu
openclaw --version
systemctl --user status openclaw-gateway.service
```

Reconnect messaging channels through the Control UI — see [DEPLOYMENT.md](DEPLOYMENT.md#connecting-messaging-platforms).

---

## Troubleshooting

### "No API key found for amazon-bedrock"

```bash
cat ~/.openclaw/.env  # Should contain AWS_PROFILE=default
# If missing:
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
printf 'AWS_PROFILE=default\nAWS_REGION=%s\nAWS_DEFAULT_REGION=%s\n' "$REGION" "$REGION" > ~/.openclaw/.env
systemctl --user restart openclaw-gateway.service
```

### "LLM request timed out"

Legacy config missing `api` field:
```bash
python3 << 'PYEOF'
import json, os

cfg_path = os.path.expanduser('~/.openclaw/openclaw.json')
with open(cfg_path) as f:
    cfg = json.load(f)
cfg['models']['providers']['amazon-bedrock']['api'] = 'bedrock-converse-stream'
with open(cfg_path, 'w') as f:
    json.dump(cfg, f, indent=2)
print('Fixed')
PYEOF
systemctl --user restart openclaw-gateway.service
```

### "Cannot find module '@buape/carbon'"

Reinstall without `--ignore-scripts`:
```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
npm install -g openclaw@2026.4.5 --timeout=300000
openclaw gateway install --force
systemctl --user daemon-reload && systemctl --user restart openclaw-gateway.service
```

### Rollback to v2026.3.24

```bash
cp ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json
cp ~/.openclaw/.env.bak ~/.openclaw/.env 2>/dev/null || true
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
ARCH=$(uname -m); IGNORE_FLAG=""; [ "$ARCH" = "aarch64" ] && IGNORE_FLAG="--ignore-scripts"
npm install -g openclaw@2026.3.24 --timeout=300000 $IGNORE_FLAG
openclaw gateway install --force
systemctl --user daemon-reload && systemctl --user restart openclaw-gateway.service
```
