"""
OpenClaw Enterprise — Demo Server (Mock API)

Serves the real production frontend (dist/) with mock API responses.
No AWS account, no DynamoDB, no S3 needed.

Usage:
  cd enterprise/demo
  python3 server.py
  # Open http://localhost:8099

The frontend is identical to production — same React app, same pages,
same animations. Only the data source is different (mock JSON vs DynamoDB).
"""

import json
import os
import sys
import time
import random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone, timedelta

PORT = int(os.environ.get("DEMO_PORT", 8099))
DIST_DIR = Path(__file__).parent / "dist"

# ============================================================
# Mock Data — mirrors real DynamoDB + S3 seed data
# ============================================================

DEPARTMENTS = [
    {"id":"dept-eng","name":"Engineering","parentId":"","headName":"Zhang San","headId":"emp-z3","employeeCount":8},
    {"id":"dept-frontend","name":"Frontend","parentId":"dept-eng","headName":"Li Si","headId":"emp-lisi","employeeCount":2},
    {"id":"dept-backend","name":"Backend","parentId":"dept-eng","headName":"Chen Wei","headId":"emp-chen","employeeCount":3},
    {"id":"dept-devops","name":"DevOps","parentId":"dept-eng","headName":"Sun Hao","headId":"emp-sun","employeeCount":2},
    {"id":"dept-qa","name":"QA","parentId":"dept-eng","headName":"Liu Yang","headId":"emp-liu","employeeCount":1},
    {"id":"dept-sales","name":"Sales","parentId":"","headName":"Mike Johnson","headId":"emp-mike","employeeCount":4},
    {"id":"dept-ae","name":"Account Executives","parentId":"dept-sales","headName":"Mike Johnson","headId":"emp-mike","employeeCount":2},
    {"id":"dept-csm","name":"Customer Success","parentId":"dept-sales","headName":"Emma Chen","headId":"emp-emma","employeeCount":2},
    {"id":"dept-product","name":"Product","parentId":"","headName":"Lin Xiaoyu","headId":"emp-lin","employeeCount":3},
    {"id":"dept-finance","name":"Finance & Accounting","parentId":"","headName":"Carol Zhang","headId":"emp-carol","employeeCount":2},
    {"id":"dept-hr","name":"HR & Admin","parentId":"","headName":"Jenny Wu","headId":"emp-jenny","employeeCount":2},
    {"id":"dept-legal","name":"Legal & Compliance","parentId":"","headName":"Rachel Kim","headId":"emp-rachel","employeeCount":1},
    {"id":"dept-exec","name":"Executive","parentId":"","headName":"CEO","headId":"emp-ceo","employeeCount":1},
]

_EMP_DATA = [
    ("emp-z3","Zhang San","EMP-001","pos-sa","Solutions Architect","dept-eng","Engineering","admin",44),
    ("emp-lisi","Li Si","EMP-002","pos-sa","Solutions Architect","dept-eng","Engineering","employee",35),
    ("emp-w5","Wang Wu","EMP-003","pos-sde","Software Engineer","dept-eng","Engineering","employee",38),
    ("emp-chen","Chen Wei","EMP-004","pos-sa","Solutions Architect","dept-eng","Engineering","employee",29),
    ("emp-sun","Sun Hao","EMP-005","pos-devops","DevOps Engineer","dept-eng","Engineering","employee",72),
    ("emp-liu","Liu Yang","EMP-006","pos-qa","QA Engineer","dept-eng","Engineering","employee",18),
    ("emp-zhao","Zhao Ming","EMP-007","pos-sde","Software Engineer","dept-eng","Engineering","employee",25),
    ("emp-zhou","Zhou Xiaoming","EMP-008","pos-sde","Software Engineer","dept-eng","Engineering","employee",21),
    ("emp-ma","Ma Tianyu","EMP-009","pos-devops","DevOps Engineer","dept-eng","Engineering","employee",15),
    ("emp-lin","Lin Xiaoyu","EMP-010","pos-pm","Product Manager","dept-product","Product","manager",31),
    ("emp-alex","Alex Rivera","EMP-011","pos-pm","Product Manager","dept-product","Product","employee",8),
    ("emp-wang2","Wang Fang","EMP-012","pos-pm","Product Manager","dept-product","Product","employee",12),
    ("emp-mike","Mike Johnson","EMP-013","pos-ae","Account Executive","dept-sales","Sales","manager",27),
    ("emp-tom","Tom Wilson","EMP-014","pos-ae","Account Executive","dept-sales","Sales","employee",19),
    ("emp-carol","Carol Zhang","EMP-015","pos-fa","Finance Analyst","dept-finance","Finance & Accounting","employee",22),
    ("emp-david","David Li","EMP-016","pos-fa","Finance Analyst","dept-finance","Finance & Accounting","employee",16),
    ("emp-emma","Emma Chen","EMP-017","pos-csm","Customer Success Manager","dept-sales","Sales","employee",19),
    ("emp-sarah","Sarah Lee","EMP-018","pos-csm","Customer Success Manager","dept-sales","Sales","employee",14),
    ("emp-jenny","Jenny Wu","EMP-019","pos-hr","HR Specialist","dept-hr","HR & Admin","employee",15),
    ("emp-rachel","Rachel Kim","EMP-020","pos-legal","Legal Counsel","dept-legal","Legal & Compliance","employee",11),
]

EMPLOYEES = []
for eid, name, eno, pid, pname, did, dname, role, msgs in _EMP_DATA:
    aid = f"agent-{pid.replace('pos-','')}-{eid.replace('emp-','')}"
    ch = {"pos-sa":["telegram","slack"],"pos-sde":["telegram"],"pos-devops":["slack"],"pos-qa":["slack"],"pos-pm":["slack"],"pos-ae":["slack","whatsapp"],"pos-fa":["portal"],"pos-hr":["slack"],"pos-csm":["slack"],"pos-legal":["portal"]}.get(pid,["slack"])
    EMPLOYEES.append({"id":eid,"name":name,"employeeNo":eno,"positionId":pid,"positionName":pname,"departmentId":did,"departmentName":dname,"role":role,"agentId":aid,"agentStatus":"active","channels":ch,"messagesThisWeek":msgs})

AGENTS = [{"id":e["agentId"],"name":f"{e['positionName']} Agent - {e['name']}","employeeId":e["id"],"employeeName":e["name"],"positionId":e["positionId"],"positionName":e["positionName"],"status":"active","soulVersions":{"global":3,"position":1,"personal":0},"skills":["web-search","jina-reader","deep-research","s3-files"],"channels":e["channels"],"qualityScore":round(3.5+random.random()*1.5,1),"createdAt":"2026-03-15T00:00:00Z","updatedAt":"2026-03-20T00:00:00Z"} for e in EMPLOYEES]
AGENTS.append({"id":"agent-helpdesk","name":"IT Help Desk (Shared)","employeeId":"","employeeName":"","positionId":"pos-devops","positionName":"DevOps","status":"active","soulVersions":{"global":3,"position":1,"personal":0},"skills":["web-search","shell"],"channels":["slack","portal"],"qualityScore":3.8,"createdAt":"2026-03-10T00:00:00Z","updatedAt":"2026-03-20T00:00:00Z","autoBindAll":True})
AGENTS.append({"id":"agent-onboarding","name":"Onboarding Bot (Shared)","employeeId":"","employeeName":"","positionId":"pos-hr","positionName":"HR","status":"active","soulVersions":{"global":3,"position":1,"personal":0},"skills":["web-search"],"channels":["slack","portal"],"qualityScore":4.1,"createdAt":"2026-03-10T00:00:00Z","updatedAt":"2026-03-20T00:00:00Z","autoBindAll":True})

POSITIONS = [
    {"id":"pos-sa","name":"Solutions Architect","departmentId":"dept-eng","departmentName":"Engineering","defaultChannel":"telegram","employeeCount":3},
    {"id":"pos-sde","name":"Software Engineer","departmentId":"dept-eng","departmentName":"Engineering","defaultChannel":"telegram","employeeCount":3},
    {"id":"pos-devops","name":"DevOps Engineer","departmentId":"dept-eng","departmentName":"Engineering","defaultChannel":"slack","employeeCount":2},
    {"id":"pos-qa","name":"QA Engineer","departmentId":"dept-eng","departmentName":"Engineering","defaultChannel":"slack","employeeCount":1},
    {"id":"pos-ae","name":"Account Executive","departmentId":"dept-sales","departmentName":"Sales","defaultChannel":"whatsapp","employeeCount":2},
    {"id":"pos-pm","name":"Product Manager","departmentId":"dept-product","departmentName":"Product","defaultChannel":"slack","employeeCount":3},
    {"id":"pos-fa","name":"Finance Analyst","departmentId":"dept-finance","departmentName":"Finance & Accounting","defaultChannel":"portal","employeeCount":2},
    {"id":"pos-hr","name":"HR Specialist","departmentId":"dept-hr","departmentName":"HR & Admin","defaultChannel":"slack","employeeCount":1},
    {"id":"pos-csm","name":"Customer Success Manager","departmentId":"dept-sales","departmentName":"Sales","defaultChannel":"slack","employeeCount":2},
    {"id":"pos-legal","name":"Legal Counsel","departmentId":"dept-legal","departmentName":"Legal & Compliance","defaultChannel":"portal","employeeCount":1},
]

BINDINGS = [{"id":f"bind-{i+1:03d}","employeeId":e["id"],"employeeName":e["name"],"agentId":e["agentId"],"agentName":f"{e['positionName']} Agent - {e['name']}","mode":"1:1","channel":e["channels"][0],"status":"active","source":"auto-provision","createdAt":"2026-03-15T00:00:00Z"} for i,e in enumerate(EMPLOYEES)]

SKILLS = [
    {"id":"sk-web-search","name":"web-search","version":"1.0.0","description":"Search the web using multiple search engines.","author":"OpenClaw Core","layer":1,"category":"information","scope":"global","status":"installed","requires":{"env":[],"tools":[]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]}},
    {"id":"sk-jina-reader","name":"jina-reader","version":"2.1.0","description":"Extract clean text from any URL.","author":"OpenClaw Core","layer":1,"category":"information","scope":"global","status":"installed","requires":{"env":[],"tools":["web_fetch"]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]}},
    {"id":"sk-deep-research","name":"deep-research","version":"1.3.0","description":"Multi-step research with sub-agent orchestration.","author":"OpenClaw Core","layer":1,"category":"information","scope":"global","status":"installed","requires":{"env":[],"tools":[]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]}},
    {"id":"sk-s3-files","name":"s3-files","version":"1.0.0","description":"Upload and share files via S3 with pre-signed URLs.","author":"aws-samples","layer":1,"category":"storage","scope":"global","status":"installed","requires":{"env":[],"tools":[]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]}},
    {"id":"sk-summarize","name":"summarize","version":"1.0.0","description":"Summarize long documents and web pages.","author":"OpenClaw Core","layer":1,"category":"information","scope":"global","status":"installed","requires":{"env":[],"tools":[]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]}},
    {"id":"sk-transcript","name":"transcript","version":"1.0.0","description":"Transcribe audio and video files.","author":"OpenClaw Core","layer":1,"category":"media","scope":"global","status":"installed","requires":{"env":["AWS_REGION"],"tools":[]},"permissions":{"allowedRoles":["*"],"blockedRoles":[]},"awsService":"transcribe"},
    {"id":"sk-github-pr","name":"github-pr","version":"1.2.0","description":"Create and manage GitHub pull requests.","author":"Community","layer":2,"category":"development","scope":"department","status":"installed","requires":{"env":["GITHUB_TOKEN"],"tools":["shell"]},"permissions":{"allowedRoles":["pos-sde","pos-devops","pos-sa"],"blockedRoles":["pos-fa","pos-hr","pos-legal"]}},
    {"id":"sk-shell","name":"shell","version":"1.0.0","description":"Execute shell commands in Docker sandbox.","author":"OpenClaw Core","layer":1,"category":"system","scope":"department","status":"installed","requires":{"env":[],"tools":["shell"]},"permissions":{"allowedRoles":["pos-sde","pos-devops","pos-sa","pos-qa"],"blockedRoles":["pos-fa","pos-hr","pos-legal","pos-ae","pos-csm"]}},
    {"id":"sk-excel-gen","name":"excel-gen","version":"1.0.0","description":"Generate Excel spreadsheets from data.","author":"Enterprise","layer":2,"category":"productivity","scope":"department","status":"installed","requires":{"env":[],"tools":["file_write"]},"permissions":{"allowedRoles":["pos-fa","pos-ae","pos-pm","pos-csm"],"blockedRoles":["pos-sde","pos-devops"]}},
    {"id":"sk-crm-query","name":"crm-query","version":"1.0.0","description":"Query CRM data for customer insights.","author":"Enterprise","layer":2,"category":"sales","scope":"department","status":"installed","requires":{"env":["CRM_API_KEY"],"tools":[]},"permissions":{"allowedRoles":["pos-ae","pos-csm"],"blockedRoles":[]}},
    {"id":"sk-email-send","name":"email-send","version":"1.0.0","description":"Compose and send emails via SES.","author":"Enterprise","layer":2,"category":"communication","scope":"department","status":"installed","requires":{"env":["AWS_REGION"],"tools":[]},"permissions":{"allowedRoles":["pos-ae","pos-csm","pos-hr"],"blockedRoles":["pos-sde"]},"awsService":"ses","approvalRequired":True},
    {"id":"sk-calendar-check","name":"calendar-check","version":"1.0.0","description":"Check calendar availability.","author":"Enterprise","layer":2,"category":"productivity","scope":"global","status":"installed","requires":{"env":["CALENDAR_API_KEY"],"tools":[]},"permissions":{"allowedRoles":["pos-pm","pos-ae","pos-hr"],"blockedRoles":[]}},
    {"id":"sk-sap-connector","name":"sap-connector","version":"1.0.0","description":"Query SAP ERP for financial data.","author":"Enterprise","layer":2,"category":"finance","scope":"department","status":"installed","requires":{"env":["SAP_API_KEY"],"tools":[]},"permissions":{"allowedRoles":["pos-fa"],"blockedRoles":[]}},
    {"id":"sk-notion-sync","name":"notion-sync","version":"1.0.0","description":"Sync content with Notion workspace.","author":"Community","layer":2,"category":"productivity","scope":"department","status":"installed","requires":{"env":["NOTION_TOKEN"],"tools":[]},"permissions":{"allowedRoles":["pos-pm"],"blockedRoles":[]}},
]

def _usage_trend():
    base = datetime(2026,3,16)
    return [{"date":(base+timedelta(days=i)).strftime("%Y-%m-%d"),"openclawCost":round(6+random.random()*6,2),"chatgptEquivalent":round(70+random.random()*10,2),"totalRequests":110+int(random.random()*90)} for i in range(7)]

def _usage_by_dept():
    return [
        {"department":"Engineering","inputTokens":520000,"outputTokens":104000,"requests":520,"cost":31.20,"agents":8},
        {"department":"Sales","inputTokens":210000,"outputTokens":42000,"requests":210,"cost":12.60,"agents":4},
        {"department":"Product","inputTokens":155000,"outputTokens":31000,"requests":155,"cost":9.30,"agents":3},
        {"department":"Finance & Accounting","inputTokens":110000,"outputTokens":22000,"requests":110,"cost":6.60,"agents":2},
        {"department":"HR & Admin","inputTokens":55000,"outputTokens":11000,"requests":55,"cost":3.30,"agents":2},
        {"department":"Legal & Compliance","inputTokens":35000,"outputTokens":7000,"requests":35,"cost":2.10,"agents":1},
    ]

def _usage_by_agent():
    return [{"agentId":a["id"],"agentName":a["name"],"employeeName":a.get("employeeName",""),"positionName":a.get("positionName",""),"inputTokens":int(random.random()*50000),"outputTokens":int(random.random()*10000),"requests":int(random.random()*50),"cost":round(random.random()*5,2)} for a in AGENTS[:10]]

SESSIONS = [
    {"id":"sess-001","agentId":"agent-sa-z3","agentName":"SA Agent - Zhang San","employeeId":"emp-z3","employeeName":"Zhang San","channel":"telegram","turns":12,"tokensUsed":24500,"status":"active","lastActive":"2026-03-22T10:30:00Z","lastMessage":"Analyzing microservice architecture..."},
    {"id":"sess-002","agentId":"agent-sde-w5","agentName":"SDE Agent - Wang Wu","employeeId":"emp-w5","employeeName":"Wang Wu","channel":"telegram","turns":8,"tokensUsed":16200,"status":"active","lastActive":"2026-03-22T10:25:00Z","lastMessage":"Running git diff on feature branch..."},
    {"id":"sess-003","agentId":"agent-fa-carol","agentName":"Finance Agent - Carol Zhang","employeeId":"emp-carol","employeeName":"Carol Zhang","channel":"portal","turns":5,"tokensUsed":10100,"status":"active","lastActive":"2026-03-22T10:20:00Z","lastMessage":"Generating Q1 EBITDA report..."},
    {"id":"sess-004","agentId":"agent-ae-mike","agentName":"AE Agent - Mike Johnson","employeeId":"emp-mike","employeeName":"Mike Johnson","channel":"slack","turns":3,"tokensUsed":6100,"status":"active","lastActive":"2026-03-22T10:15:00Z","lastMessage":"Querying CRM for pipeline data..."},
    {"id":"sess-005","agentId":"agent-helpdesk","agentName":"IT Help Desk","employeeId":"emp-zhou","employeeName":"Zhou Xiaoming","channel":"slack","turns":2,"tokensUsed":4100,"status":"active","lastActive":"2026-03-22T10:10:00Z","lastMessage":"Resetting VPN credentials..."},
    {"id":"sess-006","agentId":"agent-devops-sun","agentName":"DevOps Agent - Sun Hao","employeeId":"emp-sun","employeeName":"Sun Hao","channel":"slack","turns":15,"tokensUsed":30500,"status":"active","lastActive":"2026-03-22T09:45:00Z","lastMessage":"Checking CloudWatch alarms..."},
    {"id":"sess-007","agentId":"agent-pm-lin","agentName":"PM Agent - Lin Xiaoyu","employeeId":"emp-lin","employeeName":"Lin Xiaoyu","channel":"slack","turns":6,"tokensUsed":12200,"status":"idle","lastActive":"2026-03-22T09:00:00Z","lastMessage":"Updating sprint backlog..."},
    {"id":"sess-008","agentId":"agent-csm-emma","agentName":"CSM Agent - Emma Chen","employeeId":"emp-emma","employeeName":"Emma Chen","channel":"slack","turns":4,"tokensUsed":8100,"status":"idle","lastActive":"2026-03-22T08:30:00Z","lastMessage":"Preparing customer QBR deck..."},
]

AUDIT_ENTRIES = [
    {"id":"aud-001","timestamp":"2026-03-22T10:30:00Z","eventType":"agent_invocation","actorId":"emp-z3","actorName":"Zhang San","targetType":"agent","targetId":"agent-sa-z3","detail":"Portal chat: Analyze microservice architecture for Project Phoenix","status":"success"},
    {"id":"aud-002","timestamp":"2026-03-22T10:25:00Z","eventType":"agent_invocation","actorId":"emp-w5","actorName":"Wang Wu","targetType":"agent","targetId":"agent-sde-w5","detail":"Telegram: Run git diff on feature/payment-api branch","status":"success"},
    {"id":"aud-003","timestamp":"2026-03-22T10:20:00Z","eventType":"permission_denied","actorId":"emp-zhou","actorName":"Zhou Xiaoming","targetType":"tool","targetId":"shell","detail":"Intern attempted shell access — blocked by Plan A","status":"blocked"},
    {"id":"aud-004","timestamp":"2026-03-22T10:15:00Z","eventType":"config_change","actorId":"system","actorName":"Auto-Provision","targetType":"binding","targetId":"agent-sde-zhou","detail":"Auto-provisioned SDE Agent for Zhou Xiaoming","status":"success"},
    {"id":"aud-005","timestamp":"2026-03-22T09:45:00Z","eventType":"agent_invocation","actorId":"emp-carol","actorName":"Carol Zhang","targetType":"agent","targetId":"agent-fa-carol","detail":"Portal chat: Generate Q1 EBITDA report for Engineering","status":"success"},
    {"id":"aud-006","timestamp":"2026-03-22T09:30:00Z","eventType":"permission_denied","actorId":"emp-carol","actorName":"Carol Zhang","targetType":"tool","targetId":"shell","detail":"Finance role attempted shell — blocked by Position SOUL","status":"blocked"},
    {"id":"aud-007","timestamp":"2026-03-22T09:00:00Z","eventType":"config_change","actorId":"emp-z3","actorName":"Zhang San","targetType":"soul","targetId":"pos-sa","detail":"Updated SA Position SOUL template v1→v2","status":"success"},
    {"id":"aud-008","timestamp":"2026-03-22T08:30:00Z","eventType":"approval","actorId":"emp-z3","actorName":"Zhang San","targetType":"approval","targetId":"apr-003","detail":"Approved shell access for Wang Wu (SDE)","status":"success"},
]

APPROVALS = [
    {"id":"apr-001","tenant":"Zhou Xiaoming","tenantId":"emp-zhou","tool":"shell","reason":"Need to run diagnostic commands for onboarding task","risk":"medium","timestamp":"2026-03-22T08:00:00Z","status":"pending"},
    {"id":"apr-002","tenant":"Ma Tianyu","tenantId":"emp-ma","tool":"code_execution","reason":"Testing Python script for infrastructure automation","risk":"low","timestamp":"2026-03-22T07:30:00Z","status":"pending"},
    {"id":"apr-003","tenant":"Wang Wu","tenantId":"emp-w5","tool":"github-pr","reason":"Need to create PR for payment API feature","risk":"low","timestamp":"2026-03-21T14:00:00Z","status":"approved","reviewer":"Zhang San","resolvedAt":"2026-03-21T15:00:00Z"},
    {"id":"apr-004","tenant":"Carol Zhang","tenantId":"emp-carol","tool":"shell","reason":"Want to check server logs for discrepancy","risk":"high","timestamp":"2026-03-20T10:00:00Z","status":"denied","reviewer":"Zhang San","resolvedAt":"2026-03-20T11:00:00Z"},
]

AUDIT_INSIGHTS = {"insights":[
    {"id":"ins-001","severity":"high","category":"access_pattern","title":"Repeated shell access attempts from Intern role","description":"3 blocked shell access attempts from intern-role employees in 24h.","recommendation":"Consider sandboxed shell skill for Intern position.","affectedUsers":["Zhou Xiaoming","Ma Tianyu"],"detectedAt":"2026-03-22T10:35:00Z","source":"audit_log_scan"},
    {"id":"ins-002","severity":"medium","category":"data_exposure","title":"Finance Agent sharing cost data via public Slack channel","description":"Q2 budget variance shared in #general instead of #finance-private.","recommendation":"Add channel restriction rule for financial data.","affectedUsers":["Carol Zhang"],"detectedAt":"2026-03-22T10:25:00Z","source":"memory_scan"},
    {"id":"ins-003","severity":"high","category":"compliance","title":"SOUL template drift — 3 SA agents on old version","description":"Position SOUL updated 2 days ago but 3 agents not reassembled.","recommendation":"Trigger workspace reassembly for affected agents.","affectedUsers":["Zhang San","Li Si","Chen Wei"],"detectedAt":"2026-03-22T07:00:00Z","source":"version_drift_check"},
    {"id":"ins-004","severity":"medium","category":"memory_risk","title":"PII detected in 2 employee memory files","description":"Phone numbers found in MEMORY.md files.","recommendation":"Enable automatic PII redaction for memory writes.","affectedUsers":["Mike Johnson","Emma Chen"],"detectedAt":"2026-03-22T08:30:00Z","source":"memory_scan"},
    {"id":"ins-005","severity":"low","category":"behavior_anomaly","title":"Unusual after-hours usage from DevOps Agent","description":"72 messages this week, 40% between 11PM-3AM.","recommendation":"Review session logs, add after-hours alerts.","affectedUsers":["Sun Hao"],"detectedAt":"2026-03-22T09:00:00Z","source":"usage_pattern_analysis"},
],"summary":{"totalInsights":5,"high":2,"medium":2,"low":1,"lastScanAt":"2026-03-22T10:35:00Z","scanSources":["audit_log","memory_files","usage_patterns","version_drift"]}}

MODEL_CONFIG = {"default":{"modelId":"global.amazon.nova-2-lite-v1:0","modelName":"Nova 2 Lite","inputRate":0.30,"outputRate":2.50},"fallback":{"modelId":"us.amazon.nova-pro-v1:0","modelName":"Nova Pro","inputRate":0.80,"outputRate":3.20},"positionOverrides":{"pos-sa":{"modelId":"global.anthropic.claude-sonnet-4-5-20250929-v1:0","modelName":"Claude Sonnet 4.5","inputRate":3.0,"outputRate":15.0,"reason":"SA needs advanced reasoning"}},"availableModels":[{"modelId":"global.amazon.nova-2-lite-v1:0","modelName":"Nova 2 Lite","inputRate":0.30,"outputRate":2.50,"enabled":True},{"modelId":"us.amazon.nova-pro-v1:0","modelName":"Nova Pro","inputRate":0.80,"outputRate":3.20,"enabled":True},{"modelId":"global.anthropic.claude-sonnet-4-5-20250929-v1:0","modelName":"Claude Sonnet 4.5","inputRate":3.0,"outputRate":15.0,"enabled":True},{"modelId":"moonshotai.kimi-k2.5","modelName":"Kimi K2.5","inputRate":0.60,"outputRate":3.0,"enabled":False}]}

SECURITY_CONFIG = {"alwaysBlocked":["install_skill","load_extension","eval"],"piiDetection":{"enabled":True,"mode":"warn"},"dataSovereignty":{"enabled":True,"region":"us-east-2"},"conversationRetention":{"days":180},"dockerSandbox":True,"fastPathRouting":True,"verboseAudit":False}

ROUTING_RULES = [
    {"id":"rule-001","priority":1,"name":"Help Desk Keyword","condition":{"messagePrefix":"/help"},"action":"route_to_shared_agent","agentId":"agent-helpdesk","description":"Messages starting with /help go to IT Help Desk"},
    {"id":"rule-002","priority":2,"name":"Onboarding Keyword","condition":{"messagePrefix":"/onboard"},"action":"route_to_shared_agent","agentId":"agent-onboarding","description":"Messages starting with /onboard go to Onboarding Bot"},
    {"id":"rule-003","priority":10,"name":"Default Personal Agent","condition":{},"action":"route_to_personal_agent","description":"All other messages go to employee's personal 1:1 agent"},
]

KNOWLEDGE_BASES = [
    {"id":"kb-policies","name":"Company Policies","scope":"global","scopeName":"All Employees","docCount":3,"sizeMB":0.02,"sizeBytes":24000,"status":"indexed","lastUpdated":"2026-03-20T00:00:00Z","accessibleBy":"All employees","s3Prefix":"_shared/knowledge/company-policies/","files":[{"name":"code-of-conduct.md","size":8000,"key":"_shared/knowledge/company-policies/code-of-conduct.md"},{"name":"data-handling-policy.md","size":9000,"key":"_shared/knowledge/company-policies/data-handling-policy.md"},{"name":"remote-work-policy.md","size":7000,"key":"_shared/knowledge/company-policies/remote-work-policy.md"}]},
    {"id":"kb-arch","name":"Architecture Standards","scope":"department","scopeName":"Engineering","docCount":2,"sizeMB":0.02,"sizeBytes":18000,"status":"indexed","lastUpdated":"2026-03-19T00:00:00Z","accessibleBy":"Engineering dept","s3Prefix":"_shared/knowledge/arch-standards/","files":[{"name":"microservice-guidelines.md","size":10000,"key":"_shared/knowledge/arch-standards/microservice-guidelines.md"},{"name":"api-design-standards.md","size":8000,"key":"_shared/knowledge/arch-standards/api-design-standards.md"}]},
    {"id":"kb-runbooks","name":"Runbooks","scope":"department","scopeName":"Engineering","docCount":1,"sizeMB":0.01,"sizeBytes":8000,"status":"indexed","lastUpdated":"2026-03-18T00:00:00Z","accessibleBy":"Engineering dept","s3Prefix":"_shared/knowledge/runbooks/","files":[{"name":"incident-response.md","size":8000,"key":"_shared/knowledge/runbooks/incident-response.md"}]},
    {"id":"kb-cases","name":"Case Studies","scope":"department","scopeName":"Sales","docCount":2,"sizeMB":0.01,"sizeBytes":15000,"status":"indexed","lastUpdated":"2026-03-17T00:00:00Z","accessibleBy":"Sales + SA positions","s3Prefix":"_shared/knowledge/case-studies/","files":[]},
    {"id":"kb-finance","name":"Financial Reports","scope":"department","scopeName":"Finance","docCount":1,"sizeMB":0.01,"sizeBytes":6000,"status":"indexed","lastUpdated":"2026-03-16T00:00:00Z","accessibleBy":"Finance + C-level","s3Prefix":"_shared/knowledge/financial-reports/","files":[]},
]

# ============================================================
# Mock JWT — auto-login as Zhang San (admin)
# ============================================================
import base64, hashlib, hmac

DEMO_JWT_SECRET = "demo-secret-not-for-production"
DEMO_USERS = {e["id"]: e for e in EMPLOYEES}

def _make_token(emp):
    header = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    payload_data = {"sub":emp["id"],"name":emp["name"],"role":emp["role"],"departmentId":emp["departmentId"],"positionId":emp["positionId"],"exp":int(time.time())+86400}
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(hmac.new(DEMO_JWT_SECRET.encode(),f"{header}.{payload}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"

# ============================================================
# API Route Matching
# ============================================================

def _now():
    return datetime.now(timezone.utc).isoformat()

def handle_api(method, path, body=None):
    """Match API path and return (status_code, response_dict)."""
    p = path.replace("/api/v1/","")

    # Auth
    if p == "auth/login" and method == "POST":
        eid = (body or {}).get("employeeId","")
        emp = next((e for e in EMPLOYEES if e["id"]==eid or e.get("employeeNo")==eid), None)
        if not emp: return 401, {"detail":"Employee not found"}
        # Demo mode: accept any password
        return 200, {"token":_make_token(emp),"employee":{"id":emp["id"],"name":emp["name"],"role":emp["role"],"departmentId":emp["departmentId"],"departmentName":emp["departmentName"],"positionId":emp["positionId"],"positionName":emp["positionName"]}}
    if p == "auth/me":
        return 200, {"id":"emp-z3","name":"Zhang San","role":"admin","departmentId":"dept-eng","departmentName":"Engineering","positionId":"pos-sa","positionName":"Solutions Architect"}

    # Org
    if p == "org/departments": return 200, DEPARTMENTS
    if p == "org/positions": return 200, POSITIONS
    if p == "org/employees": return 200, EMPLOYEES
    if p == "org/employees/activity": return 200, [{"employeeId":e["id"],"messagesThisWeek":e["messagesThisWeek"],"channelStatus":{c:"connected" for c in e["channels"]}} for e in EMPLOYEES]

    # Agents
    if p == "agents": return 200, AGENTS
    if p.startswith("agents/") and "/soul" not in p and "/memory" not in p:
        aid = p.split("/")[1]
        a = next((x for x in AGENTS if x["id"]==aid), None)
        return (200, a) if a else (404, {"detail":"Not found"})
    if "/soul" in p and "full" not in p:
        return 200, [
            {"layer":"global","content":"# Global SOUL (IT Locked)\n\n**CRITICAL IDENTITY OVERRIDE: You are a digital employee of ACME Corp.**\n\n## Security Red Lines\n- NEVER share customer PII\n- NEVER execute destructive commands\n- NEVER expose internal credentials","locked":True,"version":3,"updatedAt":"2026-03-15T00:00:00Z"},
            {"layer":"position","content":"# Finance Analyst\n\nYou are a Finance Analyst at ACME Corp.\n\n## Tool Permissions\nAllowed: web_search, excel-gen, s3-files, sap-connector\nBlocked: shell, code_execution, github-pr","locked":False,"version":1,"updatedAt":"2026-03-18T00:00:00Z"},
            {"layer":"personal","content":"# Carol's Preferences\n\n- Prefer EBITDA analysis over net income\n- Always include YoY comparison\n- Format: $X,XXX.XX (USD)","locked":False,"version":0,"updatedAt":"2026-03-19T00:00:00Z"},
        ]

    # Bindings
    if p == "bindings": return 200, BINDINGS
    if p == "routing/rules": return 200, ROUTING_RULES

    # Skills
    if p == "skills": return 200, SKILLS
    if p == "skills/keys/all": return 200, [{"id":"key-1","skillName":"github-pr","envVar":"GITHUB_TOKEN","ssmPath":"/openclaw/demo/skill-keys/github-pr/GITHUB_TOKEN","status":"not-configured","awsService":"","note":"Needs configuration"},{"id":"key-2","skillName":"crm-query","envVar":"CRM_API_KEY","ssmPath":"/openclaw/demo/skill-keys/crm-query/CRM_API_KEY","status":"not-configured","awsService":"","note":"Needs configuration"},{"id":"key-3","skillName":"email-send","envVar":"AWS_REGION","ssmPath":"","status":"iam-role","awsService":"ses","note":"Provided by IAM role (ses)"}]

    # Knowledge
    if p == "knowledge": return 200, KNOWLEDGE_BASES
    if p == "knowledge/search": return 200, []

    # Monitor
    if p == "monitor/sessions": return 200, SESSIONS
    if p.startswith("monitor/sessions/"):
        sid = p.split("/")[2]
        s = next((x for x in SESSIONS if x["id"]==sid), None)
        if not s: return 404, {"detail":"Not found"}
        return 200, {"session":s,"conversation":[{"role":"user","content":"Hello","ts":_now()},{"role":"assistant","content":"Hi! I'm your AI assistant. How can I help?","ts":_now()}],"quality":{"satisfaction":4.2,"toolSuccess":95,"responseTime":2.8,"compliance":98,"completionRate":92,"overallScore":4.1},"planE":[{"turn":1,"result":"pass","detail":"No sensitive data detected"}]}
    if p == "monitor/health":
        agent_health = [{"agentId":a["id"],"agentName":a["name"],"employeeName":a.get("employeeName",""),"positionName":a.get("positionName",""),"status":a["status"],"qualityScore":a["qualityScore"],"channels":a["channels"],"skillCount":len(a["skills"]),"requestsToday":int(random.random()*20),"costToday":round(random.random()*3,2),"avgResponseSec":round(2+random.random()*3,1),"toolSuccessRate":85+int(random.random()*15),"soulVersion":"v3.1.0","lastActive":_now(),"uptime":"14d 6h"} for a in AGENTS[:10]]
        return 200, {"agents":agent_health,"system":{"totalAgents":22,"activeAgents":18,"avgQuality":4.1,"totalRequestsToday":168,"totalCostToday":9.70,"p95ResponseSec":4.2,"overallToolSuccess":96,"gatewayStatus":"healthy","agentCoreStatus":"healthy","bedrockLatencyMs":245}}
    if p == "monitor/alerts":
        now = _now()
        return 200, [{"id":"alert-01","type":"Agent crash loop","condition":"3 restarts in 5min","action":"Notify IT","status":"ok","lastChecked":now,"detail":"No crash loops"},{"id":"alert-05","type":"Budget overrun","condition":"Dept budget > 80%","action":"Notify dept admin","status":"warning","lastChecked":now,"detail":"1 department near limit"},{"id":"alert-08","type":"Unbound employees","condition":"Employee without agent","action":"Notify IT","status":"ok","lastChecked":now,"detail":"All employees bound"}]

    # Audit
    if p == "audit/entries" or p.startswith("audit/entries?"): return 200, AUDIT_ENTRIES
    if p == "audit/insights": return 200, AUDIT_INSIGHTS

    # Usage
    if p == "usage/summary": return 200, {"totalInputTokens":1085000,"totalOutputTokens":217000,"totalCost":62.70,"totalRequests":1085,"tenantCount":20,"chatgptEquivalent":500.0}
    if p == "usage/trend": return 200, _usage_trend()
    if p == "usage/by-department": return 200, _usage_by_dept()
    if p == "usage/by-agent": return 200, _usage_by_agent()
    if p == "usage/budgets": return 200, [{"department":"Engineering","budget":50,"used":31.20,"projected":44.6,"status":"ok"},{"department":"Sales","budget":25,"used":12.60,"projected":18.0,"status":"ok"},{"department":"Product","budget":20,"used":9.30,"projected":13.3,"status":"ok"},{"department":"Finance & Accounting","budget":15,"used":6.60,"projected":9.4,"status":"ok"},{"department":"HR & Admin","budget":10,"used":3.30,"projected":4.7,"status":"ok"},{"department":"Legal & Compliance","budget":10,"used":2.10,"projected":3.0,"status":"ok"}]
    if p.startswith("usage/agent/"): return 200, [{"date":f"2026-03-{16+i}","inputTokens":int(random.random()*8000),"outputTokens":int(random.random()*2000),"requests":int(random.random()*15),"cost":round(random.random()*2,2)} for i in range(7)]

    # Approvals
    if p == "approvals": return 200, {"pending":[a for a in APPROVALS if a["status"]=="pending"],"resolved":[a for a in APPROVALS if a["status"]!="pending"]}
    if p.startswith("approvals/") and "/approve" in p: return 200, {"status":"approved"}
    if p.startswith("approvals/") and "/deny" in p: return 200, {"status":"denied"}

    # Settings
    if p == "settings/model": return 200, MODEL_CONFIG
    if p == "settings/security": return 200, SECURITY_CONFIG
    if p == "settings/services": return 200, {"gateway":{"status":"healthy","port":18789,"uptime":"14d 6h","requestsToday":168},"auth_agent":{"status":"healthy","uptime":"14d 6h","approvalsProcessed":12},"bedrock":{"status":"healthy","region":"us-east-1","latencyMs":245,"vpcEndpoint":True},"dynamodb":{"status":"healthy","table":"openclaw-enterprise","itemCount":450},"s3":{"status":"healthy","bucket":"openclaw-tenants-demo"}}

    # Dashboard
    if p == "dashboard": return 200, {"departments":7,"positions":10,"employees":20,"agents":22,"activeAgents":18,"bindings":20,"sessions":8,"totalTurns":55,"unboundEmployees":0}

    # Playground
    if p == "playground/profiles": return 200, {"wa__intern_sarah":{"role":"intern","tools":["web_search"],"planA":"DENY shell.","planE":"Block credentials."},"tg__engineer_alex":{"role":"engineer","tools":["web_search","shell","browser","file","file_write","code_execution"],"planA":"ALLOW all dev tools.","planE":"Block /etc/shadow."}}
    if p == "playground/send" and method == "POST": return 200, {"response":"[Demo Mode] I received your message. In production, this routes through Tenant Router → AgentCore → OpenClaw → Bedrock.","tenant_id":(body or {}).get("tenant_id","demo"),"profile":{},"plan_a":"Demo","plan_e":"✅ PASS"}

    # Portal
    if p == "portal/chat" and method == "POST": return 200, {"response":"[Demo Mode] I'm your AI assistant at ACME Corp. In production, this message would be processed by a real Bedrock model inside a Firecracker microVM with your personalized SOUL identity.","agentId":"agent-fa-carol","agentName":"Finance Agent - Carol Zhang","source":"demo"}
    if p == "portal/profile": return 200, {"employee":EMPLOYEES[14],"agent":AGENTS[14],"userMd":"# Carol's Preferences\n\n- Prefer EBITDA over net income\n- YoY comparison always\n- USD format: $X,XXX.XX","memoryMdSize":2400,"dailyMemoryCount":5}
    if p == "portal/usage": return 200, {"totalInputTokens":44300,"totalOutputTokens":8860,"totalRequests":22,"totalCost":0.24,"dailyUsage":[{"date":f"2026-03-{16+i}","requests":2+int(random.random()*5),"cost":round(0.02+random.random()*0.05,3)} for i in range(7)]}
    if p == "portal/skills": return 200, {"available":[s for s in SKILLS if s["permissions"]["allowedRoles"]==["*"] or "pos-fa" in s["permissions"].get("allowedRoles",[])],"restricted":[s for s in SKILLS if "pos-fa" in s["permissions"].get("blockedRoles",[])]}
    if p == "portal/requests": return 200, {"pending":[],"resolved":[APPROVALS[3]]}

    # Workspace
    if p.startswith("workspace/tree"): return 200, {"global":[{"name":"SOUL.md","key":"_shared/soul/global/SOUL.md","size":1200},{"name":"AGENTS.md","key":"_shared/soul/global/AGENTS.md","size":800},{"name":"TOOLS.md","key":"_shared/soul/global/TOOLS.md","size":600}],"position":[{"name":"SOUL.md","key":"_shared/soul/positions/pos-fa/SOUL.md","size":900}],"personal":[{"name":"USER.md","key":"emp-carol/workspace/USER.md","size":300},{"name":"MEMORY.md","key":"emp-carol/workspace/MEMORY.md","size":2400}]}
    if p.startswith("workspace/file"): return 200, {"key":"demo","content":"# Demo file content\n\nThis is a mock workspace file.","size":50}

    return 404, {"detail":f"Not found: {p}"}


# ============================================================
# HTTP Server — serves dist/ + mock API
# ============================================================

class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            path = self.path.split("?")[0]
            status, data = handle_api("GET", path)
            self._json_response(status, data)
        elif self.path.startswith("/assets/") or self.path == "/favicon.ico":
            super().do_GET()
        else:
            # SPA fallback — serve index.html for all non-asset routes
            self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            status, data = handle_api("POST", self.path, body)
            self._json_response(status, data)
        else:
            self._json_response(404, {"detail": "Not found"})

    def do_PUT(self):
        if self.path.startswith("/api/"):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            status, data = handle_api("PUT", self.path, body)
            self._json_response(status, data)
        else:
            self._json_response(404, {"detail": "Not found"})

    def _json_response(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format, *args):
        if "/api/" in (args[0] if args else ""):
            sys.stderr.write(f"[demo] {args[0]}\n")


if __name__ == "__main__":
    if not DIST_DIR.exists():
        print(f"ERROR: {DIST_DIR} not found.")
        print(f"Build the frontend first:")
        print(f"  cd enterprise/admin-console && npm install && npm run build")
        print(f"  cp -r enterprise/admin-console/dist enterprise/demo/dist")
        sys.exit(1)

    server = HTTPServer(("0.0.0.0", PORT), DemoHandler)
    print(f"🦞 OpenClaw Enterprise Demo Server")
    print(f"   http://localhost:{PORT}")
    print(f"   Serving: {DIST_DIR}")
    print(f"   Mode: Mock API (no AWS needed)")
    print(f"   Login: any employee ID (e.g. emp-z3, emp-carol)")
    print(f"   Password: any value (demo mode)")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
