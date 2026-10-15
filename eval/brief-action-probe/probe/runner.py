"""`claude -p` execution for the probe (spec §4). Every tool call is denied by the PreToolUse hook in
PROBE_CONFIG_DIR; this module only parses the first assistant message and checks the hook saw it."""
import json
import os
import subprocess
import time

PROBE_CONFIG_DIR = "/root/.claude-7b-probe"
MCP_CONFIG = f"{PROBE_CONFIG_DIR}/mcp-config.json"
PROD_ARGS = ["-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "user",
             "--allowedTools", "mcp__openclaw__*",
             "--disallowedTools", "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor"]
RATE_MARKERS = ("usage limit", "rate_limit", "rate limit", " 429")
# Same account as the agents (Toto, 2026-10-14): a probe run never retries through a limit; it stops.
AGENTS_CREDENTIALS = "/root/.claude-nuvini-team/.credentials.json"


class RateLimited(RuntimeError):
    """The subscription limit was hit; the phase stops so the agents keep their quota."""


def oauth_token():
    """Long-lived access token of the agents' login, passed by env so the probe never refreshes or
    rewrites the agents' credentials."""
    with open(AGENTS_CREDENTIALS) as f:
        return json.load(f)["claudeAiOauth"]["accessToken"]


def probe_env(base, hook_log, token):
    env = {k: v for k, v in base.items() if not k.startswith("ANTHROPIC_")}
    env.update(CLAUDE_CONFIG_DIR=PROBE_CONFIG_DIR, PROBE_HOOK_LOG=hook_log, CLAUDE_CODE_OAUTH_TOKEN=token)
    return env


def build_cmd(arm_file, model="claude-sonnet-5"):
    return ["claude", *PROD_ARGS, "--model", model, "--append-system-prompt-file", arm_file,
            "--mcp-config", MCP_CONFIG, "--strict-mcp-config", "--max-turns", "1"]


def parse_first_message(stdout):
    first, text, calls, seen = None, [], [], set()
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        msg = ev.get("message") or {}
        mid = msg.get("id")
        if first is None:
            first = mid
        if mid != first:
            break
        for b in msg.get("content") or []:
            key = (b.get("type"), b.get("id") or b.get("text"))
            if key in seen:
                continue
            seen.add(key)
            if b.get("type") == "text":
                text.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                calls.append({"name": b.get("name"), "input": b.get("input")})
    if first is None:
        return None
    return {"message_id": first, "text": "\n".join(text), "tool_calls": calls}


def is_rate_limited(stdout, stderr):
    blob = (stdout[-4000:] + stderr[-4000:]).lower()
    return any(m in blob for m in RATE_MARKERS)


def hook_mismatch(message, hook_names):
    return [c["name"] for c in message.get("tool_calls", [])] != list(hook_names)


def _read_hook(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l)["tool_name"] for l in f if l.strip()]


def run_arm(arm_file, input_text, cwd, run_dir, timeout=900, token=None):
    os.makedirs(run_dir, exist_ok=True)
    hook_log = os.path.join(run_dir, "hook.jsonl")
    if os.path.exists(hook_log):
        os.remove(hook_log)
    env = probe_env(os.environ, hook_log, token or oauth_token())
    try:
        p = subprocess.run(build_cmd(arm_file), input=input_text, capture_output=True, text=True,
                           cwd=cwd, env=env, timeout=timeout)
        out, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or ""), (e.stderr or "") + "\nTIMEOUT", -1
        out = out.decode() if isinstance(out, bytes) else out
        err = err.decode() if isinstance(err, bytes) else err
    with open(os.path.join(run_dir, "stdout.jsonl"), "w") as f:
        f.write(out)
    with open(os.path.join(run_dir, "stderr.txt"), "w") as f:
        f.write(err)
    msg = parse_first_message(out)
    hooks = _read_hook(hook_log)
    mismatch = msg is not None and hook_mismatch(msg, hooks)
    return {"ok": msg is not None and not mismatch, "returncode": rc, "message": msg, "hook_calls": hooks,
            "hook_mismatch": mismatch, "rate_limited": msg is None and is_rate_limited(out, err)}


def run_unit(unit_id, arm_files, input_text, cwd, run_root, reps, rng, token=None):
    """All runs of a unit back-to-back in random order (§4); one retry per failed run."""
    plan = [(arm, r) for arm in sorted(arm_files) for r in range(1, reps + 1)]
    rng.shuffle(plan)
    results = []
    for arm, r in plan:
        run_dir = os.path.join(run_root, unit_id, f"{arm}-r{r}")
        attempt, res = 0, None
        while True:
            res = run_arm(arm_files[arm], input_text, cwd, run_dir, token=token)
            if res["rate_limited"]:
                raise RateLimited(f"{unit_id} {arm}-r{r}")
            if res["ok"] or attempt == 1:
                break
            attempt += 1
        results.append({"unit_id": unit_id, "arm": arm, "rep": r, "attempts": attempt + 1,
                        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res})
    return results
