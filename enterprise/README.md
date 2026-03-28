# OpenClaw Enterprise on AgentCore

Turn [OpenClaw](https://github.com/openclaw/openclaw) from a personal AI assistant into an enterprise-grade digital workforce platform — without modifying a single line of OpenClaw source code.

---

## Serverless Economics: ~97% Cheaper Than Dedicated EC2

Most enterprise AI deployments either charge per seat or run dedicated compute per employee. AgentCore Firecracker microVMs change the economics entirely — agents **scale to zero between conversations**, so you only pay for the seconds an agent is actually responding.

| | Dedicated EC2 per Employee | ChatGPT Team | **OpenClaw on AgentCore** |
|---|---|---|---|
| 50 employees | 50 × $52 = $2,600/mo | 50 × $25 = $1,250/mo | **~$65/mo** |
| Per person / month | $52 | $25 | **~$1.30** |
| Savings | — | — | **~97% vs EC2 · ~95% vs ChatGPT** |

One gateway EC2 ($52/mo) serves your entire organization. Every other agent is serverless — no idle cost.

---

## Elastic Capacity: ~6s Activation, Scales to Zero

| | Behavior |
|-|---------|
| **Cold start** | ~6s — Firecracker microVM spins up, SOUL assembled, Bedrock responds |
| **Warm session** | Near-instant — session stays active during a conversation |
| **Idle cost** | Zero — microVM terminates between conversations, nothing to pay |
| **Always-on agents** | 0ms cold start — assign high-traffic agents (help desk, HR bot) to persistent Docker mode |
| **Per-agent standby** | Configure from Agent Factory → Shared Agents tab. No infrastructure change needed |

Personal employee agents spin up on demand. Shared team agents pin as always-on Docker containers. Your infrastructure matches actual usage — not the worst-case headroom you'd provision for EC2.

---

## Security: Hardware-Level Isolation at Every Layer

Every agent invocation runs in an isolated Firecracker microVM — the same hypervisor technology powering AWS Lambda. No amount of prompt engineering can break L3 or L4.

| Layer | Mechanism | Bypassed by prompt injection? |
|-------|-----------|-------------------------------|
| L1 — Prompt | SOUL.md rules ("Finance never uses shell") | ⚠️ Theoretically possible |
| L2 — Application | Skills manifest `allowedRoles`/`blockedRoles` | ⚠️ Code bug risk |
| **L3 — IAM** | **Runtime role has no permission on target resource** | **Impossible** |
| **L4 — Compute** | **Firecracker microVM per invocation, isolated at hypervisor level** | **Impossible** |

Each runtime tier has its own Docker image, its own IAM role, and its own Firecracker boundary. An intern's agent IAM role literally cannot read the exec S3 bucket — even if the LLM tries.

Additional controls: no public ports (SSM only) · IAM roles throughout, no hardcoded credentials · gateway token in SSM SecureString, never on disk · VPC isolation between runtimes.

---

## Auditable and Governed from Day One

| Control | What IT Gets |
|---------|-------------|
| **SOUL Editor** | Global rules locked by IT. Finance cannot touch shell. Engineering cannot leak PII. Employees cannot override the global layer. |
| **Skill Governance** | 26 skills with `allowedRoles`/`blockedRoles`. Employees cannot install unapproved skills. |
| **Audit Center** | Every invocation, tool call, permission denial, SOUL change, and IM pairing → DynamoDB |
| **Usage & Cost** | Per-employee, per-department breakdown. Daily/weekly/monthly trends with model pricing |
| **IM Management** | Every employee's connected IM accounts visible to admin. One-click revoke. |
| **Security Center** | Live ECR images, IAM roles, VPC security groups with AWS Console deep links |
| **RBAC** | Admin (full org) · Manager (department-scoped) · Employee (portal only) |

---

## What Makes This Different

> Most enterprise AI platforms give everyone the same generic assistant.
> This one gives each employee **a personal AI agent with their own identity, memory, tools, and boundaries** — while giving IT the governance controls above.

### Flagship Features

| Feature | What It Does |
|---------|-------------|
| **Digital Twin** | Employee turns on a public link. Anyone with the URL can chat with their AI agent while they're away — agent responds using their SOUL, memory, and expertise |
| **Always-on Team Agents** | Shared agents run as persistent Docker containers on EC2. No cold start for help desks, HR bots, or onboarding assistants — instant response, shared memory |
| **Three-Layer SOUL** | Global (IT) → Position (dept admin) → Personal (employee). 3 stakeholders, 3 layers, one merged identity. Same LLM — Finance Analyst vs SDE have completely different personalities and permissions |
| **Self-Service IM Pairing** | Employee scans QR code from Portal → connects Telegram / Feishu / Discord in 30 seconds. No IT ticket, no admin approval |
| **Multi-Runtime Architecture** | Standard tier (Nova 2 Lite, scoped IAM) vs Executive tier (Claude Sonnet 4.6, full access). Different Docker images, different models, different IAM roles — infrastructure-level isolation |
| **Org Directory KB** | Company directory (every employee, R&R, contact, agent capabilities) seeded from org data and injected into every agent — agents know who to contact and can draft messages for you |
| **Position → Runtime Routing** | 3-tier routing chain: employee override → position rule → default. Assign positions to runtimes from Security Center UI, propagates to all members automatically |
| **Per-Employee Model Config** | Override model, context window, compaction settings, and response language at position OR employee level from Agent Factory → Configuration tab |
| **IM Channel Management** | Admin sees every employee's IM connections grouped by channel — when they paired, session count, last active, one-click disconnect |
| **Security Center** | Live AWS resource browser — ECR images, IAM roles, VPC security groups with console links. Configure runtime images and IAM roles from the UI |
| **Three-Layer Memory Guarantee** | Per-turn S3 checkpoint (1-message sessions), SIGTERM flush (idle timeout), Gateway compaction (long sessions). Same memory across Discord, Telegram, Feishu, and Portal |
| **Dynamic Config, Zero Redeploy** | Change model, tool permissions, SOUL content, or KB assignments → takes effect on next cold start. No container rebuild, no runtime update |

---

## Live Demo

> **https://openclaw.awspsa.com**
>
> A real running instance with 15 departments, 12 positions, 27 employees, 29 AI agents, 5 IM channels (Telegram, Feishu, Discord + Portal), multi-runtime architecture, and 2 live always-on shared agents — all backed by DynamoDB + S3 on AWS.
>
> **Everything here is real.** Every button works. Every chart reads from real data. Every agent runs on Bedrock AgentCore in isolated Firecracker microVMs.
>
> **Try the Digital Twin:** Login as any employee → Portal → My Profile → Toggle **Digital Twin** ON → get a public URL → open it in an incognito window and chat with the AI version of that employee.
>
> Need a demo account? Contact [wjiad@aws](mailto:wjiad@amazon.com) to get access.

### Screenshots

| Admin Dashboard | Employee Portal + Digital Twin |
|:-:|:-:|
| ![Admin Dashboard](demo/images/04-admin-dashboard.jpeg) | ![Portal Chat](demo/images/01-portal-chat-permission-denied.jpeg) |

| Agent Factory — Configuration | IM Channels — Per-Channel Management |
|:-:|:-:|
| ![Agent Factory](demo/images/03-agent-factory-list.jpeg) | ![SOUL Editor](demo/images/05-workspace-manager-soul.jpeg) |

| Usage & Cost — Model Pricing | Security Center — Runtime Management |
|:-:|:-:|
| ![Usage & Cost](demo/images/02-usage-cost-dashboard.jpeg) | ![Skill Platform](demo/images/08-skill-platform-catalog.jpeg) |

---

## The Problem

OpenClaw is one of the most capable open-source AI agent platforms (200k+ GitHub stars). It excels at personal productivity: connecting AI to WhatsApp, Telegram, Discord, running browser automation, managing calendars. But enterprise deployments need:

- **Multi-tenant isolation** — each employee gets their own agent with separate identity, memory, and permissions
- **Role-based access control** — interns can't run shell commands, finance can't access engineering data
- **Centralized governance** — IT controls agent behavior, skills, and model selection across the organization
- **Audit & compliance** — every agent action logged, PII detection, data sovereignty
- **Cost management** — per-department budgets, model routing, usage tracking

## The Solution

A management layer that wraps OpenClaw with enterprise controls, deployed on AWS Bedrock AgentCore. No fork, no patch, no vendor lock-in — just configuration files and AWS-native services.

### Design Principles

#### 1. Zero Invasion to OpenClaw

We don't fork, patch, or modify a single line of OpenClaw source code. Instead, we control agent behavior entirely through OpenClaw's native workspace file system:

```
workspace/
├── SOUL.md      ← Agent identity & rules (assembled from 3 layers)
├── AGENTS.md    ← Workflow definitions
├── TOOLS.md     ← Tool permissions
├── USER.md      ← Employee preferences
├── MEMORY.md    ← Persistent memory
├── memory/      ← Daily memory files (per-turn checkpoint)
├── knowledge/   ← Position-scoped + global documents (KB-injected)
└── skills/      ← Role-filtered skill packages
```

The `workspace_assembler` merges Global + Position + Personal layers into these files before OpenClaw reads them. OpenClaw doesn't know it's running in an enterprise context — it just reads its workspace as usual.

#### 2. Serverless-First + Always-on Hybrid

**Personal agents** run in isolated Firecracker microVMs via Bedrock AgentCore. Stateless, disposable, auto-scaling to zero.

**Team / Shared agents** run as persistent Docker containers on the gateway EC2 — same image, always-on, no cold starts. Tenant Router automatically routes employees to their correct tier.

```
Request
  ↓
Tenant Router — 3-tier routing:
  1. Employee override (SSM /tenants/{emp_id}/always-on-agent)
     → routes to localhost:PORT (Docker container)
  2. Position rule (SSM /positions/{pos_id}/runtime-id)
     → routes to AgentCore Runtime for that position
  3. Default AgentCore Runtime
```

| | Personal Agent (AgentCore) | Team Agent (Docker) |
|-|---------------------------|---------------------|
| Cold start | ~10-25s first message | None — always running |
| Memory | Per-employee, private | Shared across team |
| Scaling | Auto to zero | Fixed container |
| Best for | Individual employees | Help desks, HR bots |

#### 2.1 Multi-Runtime Architecture (Defense in Depth)

Different employee groups can be assigned to different AgentCore Runtimes, each backed by its own Docker image and IAM role:

```
Runtime: Standard (Engineering / Sales / HR)
  ├── Docker:  standard-agent:latest
  │   └── Skills: web-search, jina-reader, deep-research, github-pr, slack
  ├── Model:   Amazon Nova 2 Lite (cost-optimized)
  └── IAM:     Own S3 workspace only · Own DynamoDB partition

Runtime: Executive (C-Suite / Senior Leadership)
  ├── Docker:  exec-agent:latest (all skills pre-installed)
  ├── Model:   Claude Sonnet 4.6 (highest capability)
  └── IAM:     Full S3 access · Cross-department DynamoDB read · All Bedrock models
```

**Security layers:**

| Layer | Mechanism | Can LLM bypass? |
|-------|-----------|----------------|
| L1 — Prompt | SOUL.md rules ("don't access finance data") | ⚠️ Possible via injection |
| L2 — Application | Skills manifest `allowedRoles`/`blockedRoles` | ⚠️ Code bug risk |
| **L3 — IAM** | **Runtime role has no permission on target resource** | **✅ Impossible** |
| L4 — Network | VPC isolation between Runtimes | ✅ Infrastructure-level |

#### 3. Digital Twin — AI Availability Beyond Office Hours

Every employee can generate a public shareable URL for their agent:

```
Employee toggles Digital Twin ON
  ↓
Gets: https://your-domain.com/twin/{secure-token}
  ↓
Anyone with the link can chat (no login required)
  ↓
Agent responds using employee's SOUL + memory + expertise
Agent introduces itself: "I'm [Name]'s AI assistant..."
  ↓
Employee turns it OFF → link immediately revoked
```

**Use cases:** Out-of-office assistant · Sales agent always available · Technical SME accessible to anyone · Async collaboration across timezones

#### 4. Three-Layer SOUL Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: GLOBAL (IT locked — CISO + CTO approval)      │
│  Company policies, security red lines, data handling     │
│  "Never share customer PII. Never execute rm -rf."       │
├─────────────────────────────────────────────────────────┤
│  Layer 2: POSITION (Department admin managed)            │
│  Role expertise, tool permissions, knowledge scope       │
│  "You are a Finance Analyst. Use excel-gen, not shell."  │
├─────────────────────────────────────────────────────────┤
│  Layer 3: PERSONAL (Employee self-service)               │
│  Communication preferences, custom instructions          │
│  "I prefer concise answers. Always use TypeScript."      │
└─────────────────────────────────────────────────────────┘
                        ↓ merge
              Final SOUL.md (what OpenClaw reads)
```

#### 5. Knowledge Assembly at Session Start

When an agent starts a new session, `workspace_assembler` injects:

1. **Global KB** (org directory, company policies) — available to every agent
2. **Position KB** (Engineering docs for SAs, Finance docs for FAs) — scoped by role
3. **Employee KB** — individual overrides

The org directory KB (seeded via `seed_knowledge_docs.py`, refreshed by re-running the script after org changes) gives every agent the ability to answer: *"Who should I contact for X?"* and *"How do I reach [name]?"*

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Admin Console (React + FastAPI)                                 │
│  ├── 25+ pages: Dashboard, Agent Factory, Security Center,       │
│  │   IM Channels, Monitor, Audit, Usage & Cost, Settings         │
│  ├── Employee Portal: Chat, Profile, Skills, Requests, Connect   │
│  │   IM, Digital Twin toggle                                      │
│  ├── 3-role RBAC (admin / manager / employee)                    │
│  └── IT Admin Assistant (Claude API, 10 whitelisted tools)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PATH A: Personal Employee Agents                                │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  IM Message (Discord/Telegram/Feishu/Slack/Portal)     │      │
│  │    ↓ OpenClaw Gateway (port 18789)                     │      │
│  │    ↓ H2 Proxy (port 8091) — extracts sender_id        │      │
│  │    ↓ Tenant Router — 3-tier routing                    │      │
│  │      1. always-on agent? → Docker container (no wait) │      │
│  │      2. position rule?   → Assigned AgentCore Runtime  │      │
│  │      3. default          → Standard AgentCore Runtime  │      │
│  │    ↓ AgentCore (Firecracker microVM per tenant)        │      │
│  │    ↓ workspace_assembler: SOUL merge + KB inject       │      │
│  │    ↓ OpenClaw + Bedrock → Response                     │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                  │
│  PATH B: Digital Twin (no auth required)                         │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  GET /twin/{token} → public HTML chat page             │      │
│  │  POST /public/twin/{token}/chat                        │      │
│  │    ↓ Lookup token → employee_id                        │      │
│  │    ↓ Tenant Router (channel=twin)                      │      │
│  │    ↓ Agent gets "DIGITAL TWIN MODE" injected in SOUL   │      │
│  │    ↓ Responds as employee's AI representative          │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                  │
│  PATH C: Always-on Shared Agents                                 │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  Same Docker image, `docker run` on EC2 with:          │      │
│  │    SESSION_ID=shared__{agent_id}                       │      │
│  │    SHARED_AGENT_ID={agent_id}                          │      │
│  │  Container registers endpoint in SSM                   │      │
│  │  Tenant Router detects → routes to localhost:PORT      │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  AWS Services                                                    │
│  ├── DynamoDB — org, agents, bindings, audit, usage, config,     │
│  │              Digital Twin tokens, KB assignments              │
│  ├── S3 — SOUL templates, skills, workspaces, knowledge,        │
│  │         org directory, per-employee memory                    │
│  ├── SSM — tenant→position, position→runtime, user-mappings,    │
│  │          permissions, always-on endpoints                     │
│  ├── Bedrock — LLM inference (Nova 2 Lite default, Sonnet 4.6  │
│  │              for exec tier, per-position overrides supported) │
│  └── CloudWatch — agent invocation logs, runtime events         │
└─────────────────────────────────────────────────────────────────┘
```

## Gateway Architecture: One Bot, All Employees

A single OpenClaw Gateway on EC2 serves as the unified IM connection layer for the entire organization.

```
IT Admin (one-time setup):
  Discord  → Create 1 Bot "ACME Agent" → Connect to Gateway
  Telegram → Create 1 Bot @acme_bot    → Connect to Gateway
  Feishu   → Create 1 Enterprise Bot   → Connect to Gateway

All employees use the same Bot, but each gets their own Agent:

  Carol DMs @ACME Agent → H2 Proxy extracts user_id → Tenant Router
    → pos-fa → Standard Runtime → Finance Analyst SOUL → Bedrock → reply

  WJD DMs @ACME Agent → H2 Proxy extracts user_id → Tenant Router
    → pos-exec → Executive Runtime → Sonnet 4.6 → full tools → reply
```

### Employee Self-Service IM Onboarding

```
Step 1: Employee opens Portal → Connect IM
Step 2: Selects channel (Telegram / Feishu / Discord)
Step 3: Scans QR code with their phone → bot opens automatically
Step 4: Bot sends /start TOKEN → paired instantly, no admin approval
Step 5: Employee chats with their AI agent directly in their IM app
```

Zero IT friction. Employees self-service in 30 seconds. Admins see all connections in IM Channels page and can revoke any connection.

## Key Features

| Feature | How It Works |
|---------|-------------|
| **Digital Twin** | Employee toggles ON → gets a public URL. Anyone chats with their AI agent, no login required. Agent uses employee's SOUL + memory. Toggle OFF revokes instantly |
| **Always-on Team Agents** | `docker run` same image on EC2 with `SHARED_AGENT_ID`. Container registered in SSM. Tenant Router routes matched employees to `localhost:PORT` directly |
| **SOUL Injection** | 3-layer merge (Global + Position + Personal) at session start. Position SOUL warnings in editor when edits affect N agents |
| **Permission Control** | SOUL.md defines allowed/blocked tools per role. Plan A (pre-execution) + Plan E (post-audit). Exec profile bypasses Plan A entirely |
| **Multi-Runtime** | Standard (Nova 2 Lite, scoped IAM) and Executive (Sonnet 4.6, full IAM) runtimes. Assign positions to runtimes from Security Center UI |
| **Self-service IM Pairing** | QR code scan + `/start TOKEN` → SSM mapping written instantly. Supports Telegram, Feishu, Discord |
| **Org Directory KB** | Seeded from org data via `seed_knowledge_docs.py`. Injected into every agent's workspace. Agents know who to contact for what |
| **Per-employee Config** | Override model, `recentTurnsPreserve`, `maxTokens`, response language at position OR employee level. Zero redeploy |
| **Position → Runtime Routing** | 3-tier: employee SSM override → position SSM rule → default. UI in Security Center assigns positions |
| **Memory Persistence** | Three-layer: per-turn S3 checkpoint + SIGTERM flush + Gateway compaction. Cross-channel (IM + Portal share same S3 path) |
| **IM Channel Management** | Per-channel employee table: paired date, session count, last active, disconnect button |
| **Knowledge Base** | Markdown files in S3. Assign KBs to positions from Knowledge Base → Assignments tab. Injected at session start |
| **Skill Filtering** | 26 skills with `allowedRoles`/`blockedRoles`. Finance gets excel-gen, SDE gets github-pr, DevOps gets aws-cli |
| **Agent Config** | Memory compaction, context window, language per position → Agent Factory → Configuration tab |
| **IT Admin Assistant** | Floating chat bubble (admin only). Claude API + 10 whitelisted tools. No shell, no subprocess |
| **Security Center** | Live AWS resource browser: ECR images, IAM roles, VPC security groups with console deep-links |

## Security Model

| Layer | Mechanism | Detail |
|-------|-----------|--------|
| **Network** | No open ports | SSM port forwarding or CloudFront (origin restricted) |
| **Credentials** | AWS SSM SecureString | `ADMIN_PASSWORD`, `JWT_SECRET`, Digital Twin tokens encrypted in SSM |
| **Compute** | Firecracker microVM isolation | Each personal agent in its own microVM. Always-on agents in separate Docker containers |
| **IAM** | Least privilege + runtime tiers | Standard role: own S3/DynamoDB only. Executive role: cross-department. Can't escalate via prompt |
| **Data** | Role-based scoping | Admin: all. Manager: own dept (BFS rollup). Employee: own only. API-enforced |
| **Agent** | SOUL permission control | Plan A pre-execution allowlist. Plan E post-response audit. Exec profile opts out |
| **Audit** | Comprehensive logging | Every invocation, tool call, permission denial, SOUL change, IM pairing → DynamoDB |
| **Digital Twin** | Token-based access | Secure token in URL, stored in DynamoDB. Employee revokes instantly. View/chat counts tracked |

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| AWS CLI | v2.27+ | `bedrock-agentcore-control` requires 2.27+ |
| Docker | Any | `--platform linux/arm64` support needed |
| Node.js | 18+ | For Admin Console frontend build |
| Python | 3.10+ | For seed scripts and backend |
| SSM Plugin | Latest | [Install guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) |

**AWS requirements:**
- Bedrock model access for Nova models (default) + Anthropic Claude (for Admin Assistant and exec tier)
- Bedrock AgentCore available in `us-east-1` and `us-west-2`
- IAM: `cloudformation:*`, `ec2:*`, `iam:*`, `ecr:*`, `s3:*`, `ssm:*`, `bedrock:*`, `dynamodb:*`

### Step 1: Deploy Infrastructure + AgentCore Runtime

```bash
cd enterprise   # from repo root
bash deploy-multitenancy.sh openclaw-multitenancy us-east-1
# Takes ~15 minutes
```

Creates: EC2 (gateway) · ECR (agent image) · S3 (workspaces) · IAM roles · AgentCore Runtime · SSM config

```bash
STACK_NAME="openclaw-multitenancy"
REGION="us-east-1"
DYNAMODB_REGION="us-east-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

INSTANCE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' --output text)
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`TenantWorkspaceBucketName`].OutputValue' --output text)
```

### Step 2: Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name openclaw-enterprise \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=GSI1PK,AttributeType=S \
    AttributeName=GSI1SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes '[{
    "IndexName":"GSI1",
    "KeySchema":[
      {"AttributeName":"GSI1PK","KeyType":"HASH"},
      {"AttributeName":"GSI1SK","KeyType":"RANGE"}
    ],
    "Projection":{"ProjectionType":"ALL"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --region $DYNAMODB_REGION
```

### Step 3: Seed Sample Organization

```bash
cd enterprise/admin-console/server
pip install boto3 requests

python3 seed_dynamodb.py         --region $DYNAMODB_REGION
python3 seed_roles.py            --region $DYNAMODB_REGION
python3 seed_settings.py         --region $DYNAMODB_REGION
python3 seed_audit_approvals.py  --region $DYNAMODB_REGION
python3 seed_usage.py            --region $DYNAMODB_REGION
python3 seed_routing_conversations.py --region $DYNAMODB_REGION
python3 seed_knowledge.py        --region $DYNAMODB_REGION
python3 seed_ssm_tenants.py --region $REGION --stack $STACK_NAME

export S3_BUCKET=$S3_BUCKET
python3 seed_skills_final.py
python3 seed_workspaces.py
python3 seed_all_workspaces.py   --bucket $S3_BUCKET
python3 seed_knowledge_docs.py   --bucket $S3_BUCKET
```

### Step 4: Deploy Admin Console

```bash
cd enterprise/admin-console
npm install && npm run build
cd ../..

COPYFILE_DISABLE=1 tar czf /tmp/admin-deploy.tar.gz -C enterprise/admin-console dist server
aws s3 cp /tmp/admin-deploy.tar.gz "s3://${S3_BUCKET}/_deploy/admin-deploy.tar.gz"

aws ssm send-command --instance-ids $INSTANCE_ID --region $REGION \
  --document-name AWS-RunShellScript \
  --parameters "{\"commands\":[
    \"python3 -m venv /opt/admin-venv\",
    \"/opt/admin-venv/bin/pip install fastapi uvicorn boto3 requests python-multipart anthropic\",
    \"aws s3 cp s3://${S3_BUCKET}/_deploy/admin-deploy.tar.gz /tmp/admin-deploy.tar.gz --region $REGION\",
    \"mkdir -p /opt/admin-console && tar xzf /tmp/admin-deploy.tar.gz -C /opt/admin-console\",
    \"chown -R ubuntu:ubuntu /opt/admin-console /opt/admin-venv\",
    \"printf '[Unit]\\\\nDescription=OpenClaw Admin Console\\\\nAfter=network.target\\\\n[Service]\\\\nType=simple\\\\nUser=ubuntu\\\\nWorkingDirectory=/opt/admin-console/server\\\\nEnvironmentFile=-/etc/openclaw/env\\\\nExecStart=/opt/admin-venv/bin/python main.py\\\\nRestart=always\\\\nRestartSec=5\\\\n[Install]\\\\nWantedBy=multi-user.target' > /etc/systemd/system/openclaw-admin.service\",
    \"systemctl daemon-reload && systemctl enable openclaw-admin && systemctl start openclaw-admin\"
  ]}"
```

Store secrets in SSM:
```bash
aws ssm put-parameter --name "/openclaw/${STACK_NAME}/admin-password" \
  --value "<YOUR_PASSWORD>" --type SecureString --overwrite --region $REGION

aws ssm put-parameter --name "/openclaw/${STACK_NAME}/jwt-secret" \
  --value "$(openssl rand -hex 32)" --type SecureString --overwrite --region $REGION
```

### Step 5: Deploy and Start Gateway Services

```bash
# Upload gateway files to S3 (run from repo root)
aws s3 cp enterprise/gateway/tenant_router.py       "s3://${S3_BUCKET}/_deploy/tenant_router.py"
aws s3 cp enterprise/gateway/bedrock_proxy_h2.js    "s3://${S3_BUCKET}/_deploy/bedrock_proxy_h2.js"
aws s3 cp enterprise/gateway/bedrock-proxy-h2.service "s3://${S3_BUCKET}/_deploy/bedrock-proxy-h2.service"
aws s3 cp enterprise/gateway/tenant-router.service  "s3://${S3_BUCKET}/_deploy/tenant-router.service"

# Install gateway files on EC2 and start services
aws ssm send-command --instance-ids $INSTANCE_ID --region $REGION \
  --document-name AWS-RunShellScript \
  --parameters "{\"commands\":[
    \"mkdir -p /etc/openclaw && printf 'STACK_NAME=${STACK_NAME}\\nAWS_REGION=${REGION}\\nGATEWAY_INSTANCE_ID=${INSTANCE_ID}\\nECS_CLUSTER_NAME=${STACK_NAME}-always-on\\nECS_SUBNET_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} --query Stacks[0].Outputs[?OutputKey==\\'AlwaysOnSubnetId\\'].OutputValue --output text)\\nECS_TASK_SG_ID=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} --query Stacks[0].Outputs[?OutputKey==\\'AlwaysOnTaskSecurityGroupId\\'].OutputValue --output text)\\n' > /etc/openclaw/env\",
    \"pip3 install boto3 requests\",
    \"aws s3 cp s3://${S3_BUCKET}/_deploy/tenant_router.py /home/ubuntu/tenant_router.py --region $REGION\",
    \"aws s3 cp s3://${S3_BUCKET}/_deploy/bedrock_proxy_h2.js /home/ubuntu/bedrock_proxy_h2.js --region $REGION\",
    \"aws s3 cp s3://${S3_BUCKET}/_deploy/bedrock-proxy-h2.service /etc/systemd/system/bedrock-proxy-h2.service --region $REGION\",
    \"aws s3 cp s3://${S3_BUCKET}/_deploy/tenant-router.service /etc/systemd/system/tenant-router.service --region $REGION\",
    \"chown ubuntu:ubuntu /home/ubuntu/tenant_router.py /home/ubuntu/bedrock_proxy_h2.js\",
    \"systemctl daemon-reload && systemctl enable bedrock-proxy-h2 tenant-router && systemctl start bedrock-proxy-h2 tenant-router\"
  ]}"
```

### Step 6: Access Admin Console

```bash
aws ssm start-session --target $INSTANCE_ID --region $REGION \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8099"],"localPortNumber":["8199"]}'
```

Open **http://localhost:8199** → login with `emp-z3` (admin) and the password from Step 4.

> **Public access:** Use CloudFront with an Elastic IP on the EC2. Set `PUBLIC_URL` in `/etc/openclaw/env` (e.g. `PUBLIC_URL=https://your-domain.com`) for correct Digital Twin URLs — the admin console reads this file via `EnvironmentFile` in the systemd service.

### Step 7: Connect IM Channels (Optional)

```bash
# Get gateway token
aws ssm get-parameter --name "/openclaw/${STACK_NAME}/gateway-token" \
  --with-decryption --query Parameter.Value --output text --region $REGION

# Open gateway UI
aws ssm start-session --target $INSTANCE_ID --region $REGION \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["18789"],"localPortNumber":["18789"]}'
# http://localhost:18789/?token=<token>
```

Employees self-service pair via Portal → Connect IM (QR code). No admin approval needed.

---

## What to Test

### 1. SOUL Injection (core differentiator)
Login as Carol (Finance) → Chat → "Who are you?" → **"ACME Corp Finance Analyst"**
Login as Wang Wu (SDE) → Chat → "Who are you?" → **"ACME Corp Software Engineer"**
Same LLM. Completely different identities.

### 2. Digital Twin
Login as any employee → **Portal → My Profile → Digital Twin toggle**
Turn ON → copy the URL → open in incognito → chat with the AI version of that employee
Turn OFF → incognito tab gets 404 immediately

### 3. Org Directory (Knowledge Base)
Ask any agent: *"认识 Peter 吗？他负责什么？"* or *"I need a code review — who should I contact?"*
→ Agent reads `kb-org-directory` (seeded into every position) and answers with the right person's name, role, IM channel, and agent capabilities
→ Works out-of-box after running `seed_knowledge_docs.py` — no manual KB assignment needed

### 4. Permission Boundaries
Carol: "Run git status" → **Refused** (Finance, no shell)
Wang Wu: "Run git status" → **Executed** (SDE, has shell)
WJD / Ada: Any command → **Executed** (Executive tier, zero restrictions, Sonnet 4.6)

### 5. Multi-Runtime
Login as **Ada** or **WJD** → these route to the Executive AgentCore Runtime:
- Model: Claude Sonnet 4.6 (vs Nova 2 Lite for standard)
- Tools: all unlocked
- IAM: full S3, all Bedrock models, cross-dept DynamoDB

### 6. Memory Persistence
Chat as Peter Wu (Discord) → come back after 15 min → **agent recalls previous conversation**
Same memory shared across Discord, Telegram, and Portal.

> **How it works:** Each turn is synced to S3 immediately after the response (not just on session end). The next microVM downloads the workspace at session start and has full context. If memory doesn't appear, re-run `seed_all_workspaces.py` to reset S3 workspace state.

### 7. IM Channel Management (Admin)
Admin Console → **IM Channels** → select Discord tab → see JiaDe, David, Peter connected
→ view pairing date, session count, last active
→ click **Disconnect** on any employee

### 8. Security Center
Security Center → **Infrastructure tab** → see real ECR images, IAM roles, VPC security groups
Security Center → **Runtimes → Position Assignments** → change which runtime a position routes to

### 9. Agent Configuration
Agent Factory → **Configuration tab** → set Sonnet 4.5 for Solutions Architect
→ set `recentTurnsPreserve: 20` for Executive positions
→ set `language: 中文` for any position → agents default to Chinese

### 10. Knowledge Base Assignments
Knowledge Base → **Assignments tab** → all positions are pre-assigned these KBs by default:

| KB | Scope | What agents get |
|----|-------|----------------|
| `kb-org-directory` | All | Full employee directory — who does what, how to reach them |
| `kb-policies` | All | Data handling, security baseline, code of conduct |
| `kb-onboarding` | All | New hire checklist, setup guide |
| `kb-arch` / `kb-runbooks` | Engineering | Architecture standards, runbooks |
| `kb-finance` | Finance | Financial reports and policies |
| `kb-hr` | HR | HR policies |

To add a new KB: Admin Console → Knowledge Base → upload Markdown → Assignments tab → assign to positions → agents pick it up on next cold start.

## Demo Accounts

> **Executive accounts (Ada, WJD)** run on the Executive AgentCore Runtime with Claude Sonnet 4.6, zero tool restrictions, and a full-access IAM role.

| Employee ID | Name | Role | Runtime | What They Experience |
|-------------|------|------|---------|---------------------|
| **emp-ada** | **Ada** | **Executive** | **exec-agent · Sonnet 4.6** | **All tools · Full IAM · Feishu + Telegram 🔓** |
| **emp-wjd** | **WJD** | **Executive** | **exec-agent · Sonnet 4.6** | **All tools · Full IAM · Feishu + Telegram 🔓** |
| emp-z3 | Zhang San | Admin | standard | Full Admin Console |
| emp-jiade | JiaDe Wang | Admin | standard | Discord → SA Agent ✨ |
| emp-peter | Peter Wu | Manager | standard | Portal/Discord → Executive Agent ✨ |
| emp-lin | Lin Xiaoyu | Manager | standard | Product dept view only |
| emp-david | David Park | Employee | standard | Portal/Discord → Finance Agent ✨ |
| emp-w5 | Wang Wu | Employee | standard | Telegram → SDE Agent (shell/code) |
| emp-carol | Carol Zhang | Employee | standard | Telegram → Finance Agent |
| **emp-admin** | **Demo Admin** | **Employee** | **exec-agent** | **Unrestricted test account · All tools · install_skill** |

> 🔓 = No tool restrictions · ✨ = Cross-session memory via S3

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_PASSWORD` | Yes | Login password. Production: store in SSM SecureString |
| `JWT_SECRET` | Yes | JWT signing key. Generate: `openssl rand -hex 32` |
| `AWS_REGION` | Yes | Deployment region for EC2, SSM, ECR, AgentCore (default: `us-east-1`) |
| `GATEWAY_INSTANCE_ID` | Yes | EC2 instance ID — required for always-on container start/stop via SSM. Set in `/etc/openclaw/env`. Falls back to IMDSv2 if not set. |
| `PUBLIC_URL` | No | Base URL for Digital Twin links (default: `https://openclaw.awspsa.com`) — **set this** for correct twin URLs |
| `AGENT_ECR_IMAGE` | No | ECR image URI for always-on containers. Auto-built from `$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$STACK_NAME-multitenancy-agent:latest` if not set. |
| `CONSOLE_PORT` | No | Admin Console port (default: `8099`) |
| `TENANT_ROUTER_URL` | No | Tenant Router URL (default: `http://localhost:8090`) |
| `DYNAMODB_TABLE` | No | Table name (default: `openclaw-enterprise`) |
| `DYNAMODB_REGION` | No | DynamoDB region if different from `AWS_REGION` (default: `us-east-2`) |

## Sample Organization

| | Count | Details |
|-|-------|---------|
| Departments | 15 | 7 top-level + 8 sub-departments including Admin Lab |
| Positions | 12 | SA, SDE, DevOps, QA, AE, PM, FA, HR, CSM, Legal, Executive, Platform Admin |
| Employees | 27 | Each with workspace files in S3 |
| Agents | 29 | Personal + shared |
| IM Channels | 5 | Telegram, Feishu, Discord, Portal, + always-on |
| Skills | 26 | Role-scoped skill packages |
| Knowledge Docs | 14 | 11 topic KBs + company-directory.md (org directory, auto-assigned to all positions) |
| SOUL Templates | 12 | 1 global + 11 position-specific |
| RBAC Roles | 3 | Admin, Manager, Employee |

## Cost Estimate

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| EC2 (c7g.large) | ~$52 | Gateway + Tenant Router + Admin Console + always-on containers |
| DynamoDB | ~$1 | Pay-per-request |
| S3 | < $1 | Workspaces, KBs, org directory |
| Bedrock (Nova 2 Lite) | ~$5-15 | ~100 conversations/day |
| AgentCore | Included | Firecracker microVMs, pay per invocation |
| **Total** | **~$60-70/mo** | For 27 agents, ~100 conversations/day |

vs ChatGPT Team ($25/user × 27 = $675/month) → **90% cheaper** with full enterprise controls.

## How It Compares

| Capability | ChatGPT Team | Microsoft Copilot | OpenClaw Enterprise |
|-----------|-------------|-------------------|-------------------|
| Per-employee identity | ❌ Same for all | ❌ Same for all | ✅ 3-layer SOUL per role |
| Tool permissions per role | ❌ | ❌ | ✅ Plan A + Plan E |
| Department data scoping | ❌ | Partial | ✅ API-level BFS rollup |
| Memory persistence | ❌ Session only | ❌ | ✅ S3 writeback, cross-session |
| **Digital Twin (public agent URL)** | ❌ | ❌ | ✅ Shareable, revocable |
| **Always-on team agents** | ❌ | ❌ | ✅ Docker on EC2, 0ms cold start |
| **Self-service IM pairing** | ❌ | ❌ | ✅ QR code, 30-second setup |
| **Org directory KB** | ❌ | ❌ | ✅ Seeded from org data, injected into every agent |
| Self-hosted, data in your VPC | ❌ | ❌ | ✅ Bedrock in your account |
| Open source | ❌ | ❌ | ✅ OpenClaw + AWS native |
| Cost for 27 users | $675/mo | $810/mo | ~$65/mo |

## Project Structure

```
enterprise/
├── README.md
├── deploy-multitenancy.sh          # One-click deployment
├── clawdbot-bedrock-agentcore-multitenancy.yaml  # CloudFormation
├── admin-console/
│   ├── src/pages/
│   │   ├── Dashboard.tsx           # Setup checklist + real-time stats
│   │   ├── AgentFactory/           # Agent list + Configuration tab
│   │   ├── SecurityCenter.tsx      # Runtime config + ECR/IAM/VPC browser
│   │   ├── IMChannels.tsx          # Per-channel employee management
│   │   ├── Knowledge/index.tsx     # KB management + Assignments tab
│   │   ├── Usage.tsx               # Billing + model pricing
│   │   ├── TwinChat.tsx            # Public Digital Twin page (no auth)
│   │   └── portal/
│   │       ├── Chat.tsx            # Employee chat + warmup indicator
│   │       └── Profile.tsx         # USER.md + memory view + Digital Twin toggle
│   └── server/
│       ├── main.py                 # 50+ API endpoints
│       ├── db.py                   # DynamoDB single-table + Digital Twin CRUD
│       └── seed_*.py               # Sample data scripts
├── agent-container/                # AgentCore Docker image
│   ├── server.py                   # Workspace assembly + twin/always-on detection
│   ├── workspace_assembler.py      # 3-layer SOUL merge + KB injection
│   └── permissions.py              # SSM permission profiles (base_id extraction)
├── exec-agent/                     # Executive tier Docker image
│   └── Dockerfile                  # All skills pre-installed, Sonnet 4.6
└── gateway/
    ├── bedrock_proxy_h2.js         # H2 Proxy (channel detection, pairing intercept)
    └── tenant_router.py            # 3-tier routing + always-on container support
```

## Operational Notes

### Always-on Agent Management (ECS Fargate)

Always-on shared agents run as **ECS Fargate tasks** — not Docker containers on EC2. Each task self-registers its private VPC IP in SSM on startup; the Tenant Router reads that SSM entry to route requests. No port mapping required.

Start/stop from **Agent Factory → Shared / Team Agents tab**, or manually:

```bash
# Read ECS config from CloudFormation outputs (one-time setup)
ECS_CLUSTER=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AlwaysOnEcsClusterName`].OutputValue' --output text)
ECS_TASK_DEF=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AlwaysOnTaskDefinitionArn`].OutputValue' --output text)
ECS_SUBNET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AlwaysOnSubnetId`].OutputValue' --output text)
ECS_SG=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AlwaysOnTaskSecurityGroupId`].OutputValue' --output text)

# Write to /etc/openclaw/env so the Admin Console can use them
aws ssm send-command --instance-ids $INSTANCE_ID --region $REGION \
  --document-name AWS-RunShellScript \
  --parameters "{\"commands\":[
    \"echo 'ECS_CLUSTER_NAME=${ECS_CLUSTER}' >> /etc/openclaw/env\",
    \"echo 'ECS_TASK_DEFINITION=${ECS_TASK_DEF}' >> /etc/openclaw/env\",
    \"echo 'ECS_SUBNET_ID=${ECS_SUBNET}' >> /etc/openclaw/env\",
    \"echo 'ECS_TASK_SG_ID=${ECS_SG}' >> /etc/openclaw/env\",
    \"systemctl restart openclaw-admin\"
  ]}"

# Manual ECS RunTask (if UI unavailable)
aws ecs run-task \
  --cluster $ECS_CLUSTER \
  --task-definition $ECS_TASK_DEF \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$ECS_SUBNET],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"always-on-agent\",\"environment\":[
    {\"name\":\"SHARED_AGENT_ID\",\"value\":\"agent-helpdesk\"},
    {\"name\":\"SESSION_ID\",\"value\":\"shared__agent-helpdesk\"},
    {\"name\":\"S3_BUCKET\",\"value\":\"$S3_BUCKET\"},
    {\"name\":\"STACK_NAME\",\"value\":\"$STACK_NAME\"},
    {\"name\":\"AWS_REGION\",\"value\":\"$REGION\"}
  ]}]}" \
  --region $REGION
```

The task's private IP is automatically registered in SSM as `/openclaw/{stack}/always-on/{agent_id}/endpoint` by `entrypoint.sh` once healthy (~30s). The Tenant Router picks it up within 60s (SSM cache TTL).

### Digital Twin Public URL

Set `PUBLIC_URL` in `/etc/openclaw/env` — the admin console systemd service reads this file automatically:
```bash
echo "PUBLIC_URL=https://your-domain.com" >> /etc/openclaw/env
sudo systemctl restart openclaw-admin
```

### Updating Agent Docker Image

After every build, update the AgentCore Runtime to resolve the new `:latest` digest:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id "$RUNTIME_ID" \
  --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${ECR_URI}\"}}" \
  --role-arn "$EXECUTION_ROLE_ARN" \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --environment-variables "{\"BEDROCK_MODEL_ID\":\"global.amazon.nova-2-lite-v1:0\", ...}" \
  --region $REGION
```

**Always pass `--environment-variables`** — AgentCore clears env vars if the field is omitted.

### Reminders and Scheduled Tasks

OpenClaw's reminder system writes a `HEARTBEAT.md` to the agent's workspace and sends the notification through the active channel at the scheduled time.

| Agent Type | Reminder Behavior |
|-----------|-----------------|
| **Always-on (Docker)** | Fully supported — container is persistent, heartbeat fires on schedule. Delivery channel is read from `CHANNELS.md` in the workspace (auto-injected at session start from IM pairings). |
| **Personal (AgentCore microVM)** | Heartbeat is set, `HEARTBEAT.md` synced to S3 immediately after the response. Fires on the **next session start** when the microVM loads the workspace. If no new message arrives before the scheduled time, the reminder is deferred to the next interaction. |

**For reliable reminders:** use an always-on agent, or connect via an IM channel (Discord/Telegram) where sessions are more continuous. Portal (webchat) users should configure a preferred IM channel so reminders can fall back to Discord/Telegram delivery.

`CHANNELS.md` is automatically written to each employee's workspace during session assembly (reverse-lookup of their SSM IM pairings). No manual configuration needed once the user has paired an IM channel.

### H2 Proxy and Tenant Router — systemd Services

```bash
sudo cp gateway/bedrock-proxy-h2.service /etc/systemd/system/
sudo cp gateway/tenant-router.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bedrock-proxy-h2 tenant-router
sudo systemctl start bedrock-proxy-h2 tenant-router
```

---

Built by [wjiad@aws](mailto:wjiad@amazon.com) · [aws-samples](https://github.com/aws-samples) · Contributions welcome
