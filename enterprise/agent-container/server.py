"""
Agent Container HTTP server for Amazon Bedrock AgentCore.

Wraps `openclaw agent --session-id <tenant_id> --message <text> --json`
as a subprocess for each /invocations request.

Plan A: inject allowed tools into system prompt via SOUL.md prepend.
Plan E: audit response for blocked tool usage.
"""
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permissions import read_permission_profile
from observability import log_agent_invocation, log_permission_denied
from safety import validate_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Path to openclaw binary (nvm install on EC2, system install in container)
_OPENCLAW_CANDIDATES = [
    "/home/ubuntu/.nvm/versions/node/v22.22.1/bin/openclaw",
    "/usr/local/bin/openclaw",
    "/usr/bin/openclaw",
]

_TOOL_PATTERN = re.compile(
    r'\b(shell|browser|file_write|code_execution|install_skill|load_extension|eval)\b',
    re.IGNORECASE,
)


def _find_openclaw() -> str:
    for p in _OPENCLAW_CANDIDATES:
        if os.path.isfile(p):
            return p
    # fallback: hope it's on PATH
    return "openclaw"


OPENCLAW_BIN = _find_openclaw()
logger.info("openclaw binary: %s", OPENCLAW_BIN)

# Track which tenants have had their workspace assembled
_assembled_tenants: set = set()
_assembly_lock = threading.Lock()

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", "/root/.openclaw/workspace")
S3_BUCKET = os.environ.get("S3_BUCKET", "openclaw-tenants-000000000000")
STACK_NAME = os.environ.get("STACK_NAME", "dev")
AWS_REGION_RUNTIME = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "openclaw-enterprise")
DYNAMODB_REGION = os.environ.get("DYNAMODB_REGION", "us-east-2")


def _append_conversation_turn(tenant_id: str, user_message: str, assistant_reply: str, model: str, duration_ms: int):
    """Append a user+assistant turn to DynamoDB CONV# AND local daily memory file.

    The DynamoDB write enables Session Detail view in the Admin Console.
    The local memory file write ensures memory persists even for short sessions
    that never trigger OpenClaw Gateway's compaction threshold — the watchdog
    syncs workspace/memory/{date}.md to S3 within 60s, so the next session
    always has context regardless of session length.
    """
    from datetime import datetime, timezone
    ts_dt = datetime.now(timezone.utc)
    ts = ts_dt.isoformat()

    # 1. Write to DynamoDB for Session Detail view
    try:
        import boto3 as _b3_conv
        ddb = _b3_conv.resource("dynamodb", region_name=DYNAMODB_REGION)
        table = ddb.Table(DYNAMODB_TABLE)
        org_pk = "ORG#acme"
        session_sk = f"SESSION#{tenant_id[:40]}"

        try:
            resp = table.get_item(Key={"PK": org_pk, "SK": session_sk})
            turns = int(resp.get("Item", {}).get("turns", 0))
        except Exception:
            turns = 0

        seq_base = (turns - 1) * 2
        table.put_item(Item={
            "PK": org_pk, "SK": f"CONV#{tenant_id[:40]}#{seq_base:04d}",
            "sessionId": tenant_id[:40], "seq": seq_base, "role": "user",
            "content": user_message[:2000], "ts": ts,
        })
        table.put_item(Item={
            "PK": org_pk, "SK": f"CONV#{tenant_id[:40]}#{seq_base + 1:04d}",
            "sessionId": tenant_id[:40], "seq": seq_base + 1, "role": "assistant",
            "content": assistant_reply[:4000], "ts": ts,
            "model": model, "durationMs": duration_ms,
        })
    except Exception as e:
        logger.warning("CONV# write failed (non-fatal): %s", e)

    # 2. Append to daily memory file — ensures memory persists for short sessions
    # that never trigger Gateway compaction. OpenClaw reads memory/*.md at session
    # start, so this guarantees continuity even for 1-message microVM sessions.
    try:
        workspace = os.environ.get("OPENCLAW_WORKSPACE", "/root/.openclaw/workspace")
        memory_dir = os.path.join(workspace, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        date_str = ts_dt.strftime("%Y-%m-%d")
        time_str = ts_dt.strftime("%H:%M UTC")
        daily_file = os.path.join(memory_dir, f"{date_str}.md")

        entry = (
            f"\n## {time_str}\n"
            f"**User:** {user_message[:300]}\n"
            f"**Agent:** {assistant_reply[:300]}\n"
        )
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info("Memory checkpoint written: %s", daily_file)
    except Exception as e:
        logger.warning("Daily memory write failed (non-fatal): %s", e)


def _write_usage_to_dynamodb(tenant_id: str, base_id: str, usage: dict, model: str, duration_ms: int, message: str = ""):
    """Fire-and-forget: write usage metrics, session, and audit entry to DynamoDB.
    Runs in a background thread to avoid blocking the response."""
    try:
        import boto3 as _b3
        from datetime import datetime, timezone
        from decimal import Decimal

        ddb = _b3.resource("dynamodb", region_name=DYNAMODB_REGION)
        table = ddb.Table(DYNAMODB_TABLE)
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        org_pk = "ORG#acme"

        input_tokens = int(usage.get("input", 0))
        output_tokens = int(usage.get("output", 0))
        total_tokens = int(usage.get("total", input_tokens + output_tokens))

        # Estimate cost based on model (Nova 2 Lite: $0.30/$2.50 per 1M tokens)
        cost = Decimal(str(round(input_tokens * 0.30 / 1_000_000 + output_tokens * 2.50 / 1_000_000, 6)))

        # 1. Atomic increment USAGE#{base_id}#{date}
        table.update_item(
            Key={"PK": org_pk, "SK": f"USAGE#{base_id}#{today}"},
            UpdateExpression="SET #d = :date, agentId = :aid, model = :model, GSI1PK = :gsi1pk, GSI1SK = :gsi1sk ADD inputTokens :inp, outputTokens :out, requests :one, cost :cost",
            ExpressionAttributeNames={"#d": "date"},
            ExpressionAttributeValues={
                ":date": today,
                ":aid": base_id,
                ":model": model,
                ":inp": input_tokens,
                ":out": output_tokens,
                ":one": 1,
                ":cost": cost,
                ":gsi1pk": "TYPE#usage",
                ":gsi1sk": f"USAGE#{today}#{base_id}",
            },
        )

        # 2. Update or create SESSION#{tenant_id} — increment turns, update lastMessage
        # 'id' is set explicitly so the admin console can find sessions by ID without parsing the SK
        session_id = tenant_id[:40]
        table.update_item(
            Key={"PK": org_pk, "SK": f"SESSION#{session_id}"},
            UpdateExpression="SET id = :id, agentId = :aid, employeeId = :eid, #s = :status, lastActive = :now, GSI1PK = :gsi1pk, GSI1SK = :gsi1sk ADD turns :one, tokensUsed :tokens",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":id": session_id,
                ":aid": base_id,
                ":eid": base_id,
                ":status": "active",
                ":now": now.isoformat(),
                ":one": 1,
                ":tokens": total_tokens,
                ":gsi1pk": "TYPE#session",
                ":gsi1sk": f"SESSION#{session_id}",
            },
        )

        logger.info("DynamoDB usage written: %s tokens=%d cost=%s", base_id, total_tokens, cost)

        # 3. Write audit entry — makes ALL channels (Discord, Telegram, Portal) visible
        #    in the Admin Console Audit Center, not just Portal chat.
        #    Try to resolve the employee display name from DynamoDB EMP# record.
        actor_name = base_id
        try:
            emp_resp = table.get_item(Key={"PK": "ORG#acme", "SK": f"EMP#{base_id}"})
            emp_item = emp_resp.get("Item", {})
            if emp_item.get("name"):
                actor_name = emp_item["name"]
        except Exception:
            pass

        # Detect channel from tenant_id prefix (wa__, tg__, dc__, sl__, port__, etc.)
        channel = "unknown"
        t_parts = tenant_id.split("__")
        if t_parts:
            ch_map = {"wa": "WhatsApp", "tg": "Telegram", "dc": "Discord",
                      "sl": "Slack", "ms": "Teams", "im": "iMessage",
                      "gc": "Google Chat", "web": "Web", "port": "Portal"}
            channel = ch_map.get(t_parts[0], t_parts[0].upper())

        detail_msg = message[:100] if message else "(no message)"
        audit_id = f"aud-{int(now.timestamp() * 1000)}"  # ms precision avoids overwrite
        table.put_item(Item={
            "PK": "ORG#acme",
            "SK": f"AUDIT#{audit_id}",
            "GSI1PK": "TYPE#audit",
            "GSI1SK": f"AUDIT#{audit_id}",
            "id": audit_id,
            "timestamp": now.isoformat(),
            "eventType": "agent_invocation",
            "actorId": base_id,
            "actorName": actor_name,
            "targetType": "agent",
            "targetId": base_id,
            "channel": channel,
            "detail": f"{channel} chat: {detail_msg}",
            "status": "success",
            "durationMs": duration_ms,
            "model": model,
        })
        logger.info("Audit entry written: %s channel=%s", audit_id, channel)

    except Exception as e:
        logger.warning("DynamoDB usage write failed (non-fatal): %s", e)


def _ensure_workspace_assembled(tenant_id: str) -> None:
    """Assemble workspace on first invocation for a tenant.
    Runs workspace_assembler.py to merge Global + Position + Personal SOUL.
    Thread-safe: only runs once per tenant per microVM lifecycle."""
    if tenant_id in _assembled_tenants or tenant_id == "unknown":
        return

    with _assembly_lock:
        if tenant_id in _assembled_tenants:
            return  # double-check after acquiring lock

        logger.info("First invocation for tenant %s — assembling workspace", tenant_id)

        # Extract base employee ID for S3 paths
        # Tenant ID formats:
        #   port__emp-carol__bbee1f93  → base = emp-carol (Portal, 3 parts)
        #   tg__emp-w5__a1b2c3d4      → base = emp-w5 (Telegram, 3 parts)
        #   unknown__1484960930608578580 → base = 1484960930608578580 (Discord via H2 Proxy, 2 parts)
        #   actions__a                 → base = a (H2 Proxy fallback, 2 parts)
        #   emp-carol                  → base = emp-carol (direct)
        base_id = tenant_id
        parts = tenant_id.split("__")
        if len(parts) >= 3:
            # channel__user_id__hash → take user_id (middle)
            base_id = parts[1]
        elif len(parts) == 2:
            # channel__user_id → take user_id (second part, the actual identifier)
            base_id = parts[1]

        # Check SSM user-mapping for IM channel user IDs
        # e.g., discord__1460888812426363004 → emp-carol
        if not base_id.startswith("emp-"):
            try:
                import boto3 as _b3_mapping
                ssm = _b3_mapping.client("ssm", region_name=AWS_REGION_RUNTIME)
                # Try multiple mapping key formats
                mapping_keys = [
                    f"{parts[0]}__{base_id}" if len(parts) >= 2 else base_id,  # channel__userId
                    base_id,  # just userId
                    tenant_id,  # full tenant_id
                ]
                for mapping_key in mapping_keys:
                    try:
                        resp = ssm.get_parameter(Name=f"/openclaw/{STACK_NAME}/user-mapping/{mapping_key}")
                        resolved = resp["Parameter"]["Value"]
                        logger.info("SSM user-mapping resolved: %s → %s", mapping_key, resolved)
                        base_id = resolved
                        break
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("SSM user-mapping lookup failed: %s", e)

        # 0. Load shared OpenClaw credentials (discord allowFrom list) into microVM
        #    This is how the microVM knows which Discord users are approved.
        #    The EC2 updates this file on every pairing approval and uploads to S3.
        creds_dir = "/root/.openclaw/credentials"
        os.makedirs(creds_dir, exist_ok=True)
        try:
            subprocess.run(
                ["aws", "s3", "cp",
                 f"s3://{S3_BUCKET}/_shared/openclaw-creds/discord-default-allowFrom.json",
                 f"{creds_dir}/discord-default-allowFrom.json", "--quiet"],
                capture_output=True, text=True, timeout=10
            )
            logger.info("Discord allowFrom credentials loaded into microVM")
        except Exception as e:
            logger.warning("Could not load discord credentials (non-fatal): %s", e)

        # 1. Sync tenant's personal workspace from S3 using BASE ID
        # IMPORTANT: Use 'cp --recursive' instead of 'sync' to force S3 → local overwrite.
        # The entrypoint.sh initial sync uses tenant=unknown, creating empty workspace files.
        # 'aws s3 sync' won't overwrite these because the local files are newer.
        # 'aws s3 cp --recursive' always downloads from S3, ensuring seed data (MEMORY.md,
        # USER.md, memory/*.md) is correctly loaded.
        s3_base = f"s3://{S3_BUCKET}/{base_id}"
        try:
            subprocess.run(
                ["aws", "s3", "cp", f"{s3_base}/workspace/", f"{WORKSPACE}/",
                 "--recursive", "--quiet"],
                capture_output=True, text=True, timeout=30
            )
            logger.info("S3 workspace copied for tenant %s (base: %s)", tenant_id, base_id)
        except Exception as e:
            logger.warning("S3 cp failed for %s: %s", tenant_id, e)

        # 2. Run workspace_assembler.py to merge three-layer SOUL
        assembler = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace_assembler.py")
        if os.path.isfile(assembler):
            try:
                result = subprocess.run(
                    [sys.executable, assembler,
                     "--tenant", tenant_id,
                     "--workspace", WORKSPACE,
                     "--bucket", S3_BUCKET,
                     "--stack", STACK_NAME,
                     "--region", AWS_REGION_RUNTIME],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    logger.info("Workspace assembled for %s: %s", tenant_id, result.stdout.strip().split('\n')[-1])
                else:
                    logger.warning("Workspace assembly failed for %s: %s", tenant_id, result.stderr[:200])
            except Exception as e:
                logger.warning("Workspace assembly error for %s: %s", tenant_id, e)
        else:
            logger.warning("workspace_assembler.py not found at %s", assembler)

        # 3. Plan A: Prepend permission constraints to merged SOUL.md
        # Skip for exec profile — SOUL.md already declares full tool access,
        # and injecting restrictions would conflict with the executive tier design.
        soul_path = os.path.join(WORKSPACE, "SOUL.md")
        if os.path.isfile(soul_path):
            try:
                profile = read_permission_profile(tenant_id)
                is_exec = profile.get("role") == "exec" or profile.get("profile") == "exec"
                if not is_exec:
                    constraint = _build_system_prompt(tenant_id)
                    if constraint:
                        with open(soul_path, "r") as f:
                            existing = f.read()
                        if "Allowed tools for this session" not in existing:
                            with open(soul_path, "w") as f:
                                f.write(f"<!-- PLAN A: PERMISSION ENFORCEMENT -->\n{constraint}\n\n---\n\n{existing}")
                            logger.info("Plan A constraints injected into SOUL.md for %s", tenant_id)
                else:
                    logger.info("Plan A skipped for exec profile tenant %s", tenant_id)
            except Exception as e:
                logger.warning("Plan A injection failed for %s: %s", tenant_id, e)

        # 4. Re-source skill env vars (in case skills were loaded)
        skill_env = "/tmp/skill_env.sh"
        if os.path.isfile(skill_env):
            try:
                with open(skill_env) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export ") and "=" in line:
                            kv = line[7:]
                            key, _, val = kv.partition("=")
                            os.environ[key] = val.strip("'\"")
            except IOError:
                pass

        # Write tenant_id so watchdog sync knows where to write back
        try:
            with open("/tmp/tenant_id", "w") as f:
                f.write(tenant_id)
            with open("/tmp/base_tenant_id", "w") as f:
                f.write(base_id)
            logger.info("Base tenant ID written: %s", base_id)
        except IOError:
            pass

        # 5. Dynamic model config: read from DynamoDB and update openclaw.json
        # This allows Admin Console to change the model without redeploying the Runtime
        try:
            import boto3 as _b3_model
            ddb = _b3_model.resource("dynamodb", region_name=DYNAMODB_REGION)
            table = ddb.Table(DYNAMODB_TABLE)
            config_resp = table.get_item(Key={"PK": "ORG#acme", "SK": "CONFIG#model"})
            if "Item" in config_resp:
                model_config = config_resp["Item"]
                # Check for position-specific override first
                pos_id = ""
                try:
                    ssm_client = _b3_model.client("ssm", region_name=AWS_REGION_RUNTIME)
                    pos_resp = ssm_client.get_parameter(
                        Name=f"/openclaw/{STACK_NAME}/tenants/{base_id}/position")
                    pos_id = pos_resp["Parameter"]["Value"]
                except Exception:
                    pass

                overrides = model_config.get("positionOverrides", {})
                if pos_id and pos_id in overrides:
                    new_model_id = overrides[pos_id].get("modelId", "")
                    if new_model_id:
                        logger.info("Position model override: %s → %s", pos_id, new_model_id)
                else:
                    new_model_id = model_config.get("default", {}).get("modelId", "")

                if new_model_id:
                    # Update openclaw.json with the new model ID
                    oc_config_path = os.path.expanduser("~/.openclaw/openclaw.json")
                    if os.path.isfile(oc_config_path):
                        with open(oc_config_path) as f:
                            oc_config = json.load(f)
                        # Update model references
                        old_model = os.environ.get("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")
                        oc_json_str = json.dumps(oc_config)
                        oc_json_str = oc_json_str.replace(old_model, new_model_id)
                        with open(oc_config_path, "w") as f:
                            f.write(oc_json_str)
                        os.environ["BEDROCK_MODEL_ID"] = new_model_id
                        logger.info("Model updated to %s (from DynamoDB CONFIG#model)", new_model_id)
        except Exception as e:
            logger.warning("Dynamic model config failed (non-fatal): %s", e)

        _assembled_tenants.add(tenant_id)
        logger.info("Workspace ready for tenant %s", tenant_id)



def _build_system_prompt(tenant_id: str) -> str:
    """Plan A: build constraint text to prepend to SOUL.md."""
    try:
        profile = read_permission_profile(tenant_id)
        allowed = profile.get("tools", ["web_search"])
        blocked = [t for t in ["shell", "browser", "file", "file_write", "code_execution",
                                "install_skill", "load_extension", "eval"]
                   if t not in allowed]
    except Exception:
        allowed = ["web_search"]
        blocked = ["shell", "browser", "file", "file_write", "code_execution",
                   "install_skill", "load_extension", "eval"]

    lines = [f"Allowed tools for this session: {', '.join(allowed)}."]
    if blocked:
        lines.append(
            f"You MUST NOT use these tools: {', '.join(blocked)}. "
            "If the user requests an action requiring a blocked tool, "
            "explain that you don't have permission."
        )
    return " ".join(lines)


def _audit_response(tenant_id: str, response_text: str, allowed_tools: list) -> None:
    """Plan E: scan response for blocked tool usage."""
    matches = _TOOL_PATTERN.findall(response_text)
    if not matches:
        return
    for tool in set(t.lower() for t in matches):
        if tool not in allowed_tools:
            log_permission_denied(
                tenant_id=tenant_id,
                tool_name=tool,
                cedar_decision="RESPONSE_AUDIT",
                request_id=None,
            )
            logger.warning("AUDIT: blocked tool '%s' in response tenant_id=%s", tool, tenant_id)


def invoke_openclaw(tenant_id: str, message: str, timeout: int = 300, max_retries: int = 2) -> dict:
    """
    Run openclaw agent CLI with automatic retry on transient failures.
    Retries on: empty output, JSON parse errors, timeouts.
    Does NOT retry on successful responses (even if the content is an error message).
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _invoke_openclaw_once(tenant_id, message, timeout)
        except RuntimeError as e:
            last_error = e
            if attempt < max_retries:
                wait = (attempt + 1) * 2  # 2s, 4s linear backoff
                logger.warning(
                    "openclaw retry %d/%d after %ds: %s",
                    attempt + 1, max_retries, wait, e,
                )
                time.sleep(wait)
    raise last_error


def _invoke_openclaw_once(tenant_id: str, message: str, timeout: int = 300) -> dict:
    """
    Run: openclaw agent --session-id <tenant_id> --message <message> --json
    Returns parsed JSON result dict.
    Runs as 'ubuntu' user if we're root (EC2 host) so openclaw config is accessible.
    """
    env = os.environ.copy()

    # Inject skill API keys from /tmp/skill_env.sh (written by skill_loader.py)
    skill_env_file = "/tmp/skill_env.sh"
    if os.path.isfile(skill_env_file):
        try:
            with open(skill_env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export ") and "=" in line:
                        kv = line[7:]  # strip "export "
                        key, _, val = kv.partition("=")
                        # Strip surrounding quotes
                        val = val.strip("'\"")
                        env[key] = val
        except IOError:
            pass

    # Ensure node is on PATH for nvm installs
    nvm_bin = "/home/ubuntu/.nvm/versions/node/v22.22.1/bin"
    if os.path.isdir(nvm_bin):
        env["PATH"] = nvm_bin + ":" + env.get("PATH", "")
        env["HOME"] = "/home/ubuntu"

    openclaw_cmd = [
        OPENCLAW_BIN,
        "agent",
        "--session-id", tenant_id,
        "--message", message,
        "--json",
        "--timeout", str(timeout),
    ]

    # If running as root (EC2 host), sudo to ubuntu so openclaw config is accessible
    # Use 'sudo -u ubuntu env KEY=VAL ...' and do NOT pass env= to subprocess
    # (subprocess env= would override the sudo env vars)
    run_env = None  # None = inherit current process env (used in container as ubuntu)
    if os.geteuid() == 0 and os.path.isdir("/home/ubuntu"):
        path_val = env.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        aws_region = env.get("AWS_REGION", "us-east-1")
        cmd = [
            "sudo", "-u", "ubuntu",
            "env",
            f"PATH={path_val}",
            "HOME=/home/ubuntu",
            f"AWS_REGION={aws_region}",
            f"AWS_DEFAULT_REGION={aws_region}",
        ] + openclaw_cmd
        run_env = None  # let sudo handle the environment
    else:
        cmd = openclaw_cmd
        run_env = env  # pass env in container (running as ubuntu already)

    logger.info("Invoking openclaw tenant_id=%s cmd=%s", tenant_id, " ".join(cmd[:5]))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,
            env=run_env,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"openclaw timed out after {timeout}s")

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stderr:
        # openclaw logs info/warnings to stderr — log at WARNING for visibility
        for line in stderr.splitlines():
            logger.warning("[openclaw stderr] %s", line)

    # OpenClaw may write JSON response to stderr when Gateway fallback occurs
    # ("Gateway agent failed; falling back to embedded" → JSON goes to stderr)
    if not stdout and stderr:
        json_start_stderr = stderr.find('{')
        if json_start_stderr != -1:
            logger.info("JSON found in stderr (Gateway fallback mode), using stderr as output")
            stdout = stderr[json_start_stderr:]

    if not stdout:
        raise RuntimeError(f"openclaw returned empty output (exit={result.returncode})")

    # Find the first JSON object in stdout (may have log lines before it)
    json_start = stdout.find('{')
    if json_start == -1:
        raise RuntimeError(f"No JSON in openclaw output: {stdout[:200]}")

    # Use JSONDecoder to parse only the first complete JSON object
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(stdout, json_start)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse openclaw JSON: {e} — output: {stdout[:200]}")

    return data


class AgentCoreHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # noqa: A002
        logger.info(format, *args)

    def do_GET(self):
        if self.path == "/ping":
            self._respond(200, {"status": "Healthy", "time_of_last_update": int(time.time())})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/invocations":
            self._respond(404, {"error": "not found"})
            return

        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid json"})
            return

        # Extract tenant_id from headers or payload
        _file_tenant = ""
        try:
            with open("/tmp/tenant_id") as f:
                _file_tenant = f.read().strip()
        except Exception:
            pass

        tenant_id = (
            self.headers.get("X-Amzn-Bedrock-AgentCore-Runtime-Session-Id")
            or self.headers.get("x-amzn-bedrock-agentcore-runtime-session-id")
            or payload.get("runtimeSessionId")
            or payload.get("sessionId")
            or payload.get("tenant_id")
            or _file_tenant
            or "unknown"
        )

        message = validate_message(
            payload.get("prompt") or payload.get("message") or str(payload)
        )

        logger.info("Invocation tenant_id=%s message_len=%d", tenant_id, len(message))
        self._handle_invocation(tenant_id, message, payload)

    def _handle_invocation(self, tenant_id: str, message: str, payload: dict):
        # Ensure workspace is assembled for this tenant (first invocation only)
        _ensure_workspace_assembled(tenant_id)

        start_ms = int(time.time() * 1000)
        try:
            timeout = int(payload.get("timeout", 300))
            data = invoke_openclaw(tenant_id, message, timeout=timeout)
            duration_ms = int(time.time() * 1000) - start_ms

            # Extract text from openclaw JSON response.
            # Embedded mode:  {"payloads": [...], "meta": {...}}
            # Gateway mode:   {"runId": "...", "result": {"payloads": [...], "meta": {...}}}
            result_block = data.get("result", data)  # unwrap Gateway's "result" wrapper
            payloads = result_block.get("payloads", [])
            response_text = " ".join(
                p.get("text", "") for p in payloads if p.get("text")
            ).strip()

            if not response_text:
                response_text = result_block.get("text", data.get("text", ""))
            if not response_text:
                logger.warning("Empty response_text from openclaw, raw data keys: %s", list(data.keys()))
                response_text = "(no response)"

            # Plan E audit
            try:
                profile = read_permission_profile(tenant_id)
                allowed = profile.get("tools", ["web_search"])
            except Exception:
                allowed = ["web_search"]
            _audit_response(tenant_id, response_text, allowed)

            # Extract model usage for observability
            meta = result_block.get("meta", data.get("meta", {}))
            agent_meta = meta.get("agentMeta", {})
            model = agent_meta.get("model", "unknown")
            usage = agent_meta.get("usage", {})

            log_agent_invocation(
                tenant_id=tenant_id,
                tools_used=[],
                duration_ms=duration_ms,
                status="success",
            )
            logger.info(
                "Response tenant_id=%s duration_ms=%d model=%s tokens=%s text_len=%d",
                tenant_id, duration_ms, model, usage.get("total", "?"), len(response_text),
            )

            # Fire-and-forget: write usage to DynamoDB in background thread
            base_id = tenant_id
            parts = tenant_id.split("__")
            if len(parts) >= 3:
                base_id = parts[1]
            elif len(parts) == 2:
                base_id = parts[1]
            # Use resolved base_id from workspace assembly if available
            try:
                with open("/tmp/base_tenant_id") as f:
                    resolved = f.read().strip()
                    if resolved and resolved != "unknown":
                        base_id = resolved
            except Exception:
                pass

            threading.Thread(
                target=_write_usage_to_dynamodb,
                args=(tenant_id, base_id, usage, model, duration_ms, message),
                daemon=True,
            ).start()

            # Fire-and-forget: write conversation turn to DynamoDB for Session Detail view
            threading.Thread(
                target=_append_conversation_turn,
                args=(tenant_id, message, response_text, model, duration_ms),
                daemon=True,
            ).start()

            self._respond(200, {
                "response": response_text,
                "status": "success",
                "model": model,
                "usage": usage,
            })

        except Exception as e:
            duration_ms = int(time.time() * 1000) - start_ms
            log_agent_invocation(tenant_id=tenant_id, tools_used=[], duration_ms=duration_ms, status="error")
            logger.error("Invocation failed tenant_id=%s error=%s", tenant_id, e)
            self._respond(500, {"error": str(e)})

    def _respond(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), AgentCoreHandler)
    logger.info("HTTP server listening on port %d", port)
    logger.info("openclaw binary: %s", OPENCLAW_BIN)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
