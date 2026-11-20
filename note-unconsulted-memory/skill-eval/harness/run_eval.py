#!/usr/bin/env python3
"""Runner for the skill evaluation (PROTOCOL.md sections 2, 3 and 6).

One run = one fresh `claude -p` session on one task in one arm:
  S0  MCP, no skill            S1  MCP + skill
  P+  MCP, prompt says "check memory first"   N  no MCP

Each run gets its own copy of the frozen eval DB, so a write in one run never reaches the next,
and its own NOX_AGENT_NAME, so search_telemetry attributes every row. The agent can reach the
corpus only through the MCP: --permission-mode dontAsk with only the nox-mem tools and Skill
allowed denies Bash, reads outside the empty cwd and the web (the corpus is public on GitHub).

Usage:
  run_eval.py --bank tasks.jsonl --arms S0,S1 --replicas 3 --label smoke [--tasks id1,id2] [--dry-run]
Output: <eval>/runs/<label>/<run_id>.stream.jsonl and one line per run in <eval>/runs/<label>/results.jsonl
"""
import argparse, json, os, random, shutil, sqlite3, subprocess, sys, time, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent.parent / "skills" / "nox-mem-memory" / "SKILL.md"
P_PLUS_PREFIX = "Before answering, check the nox-mem memory for anything relevant to this.\n\n"
MEMORY_TOOLS = {"nox_mem_search", "nox_mem_get", "nox_mem_decision_get", "nox_mem_decision_list", "nox_mem_reflect"}
WRITE_TOOLS = {"nox_mem_decision_set", "nox_mem_ingest", "nox_mem_crystallize"}
ARMS = {"S0", "S1", "P+", "N", "T"}  # T: no skill; MCP build with server instructions (--noxmem-t)


def mcp_wrapper(work: Path, noxmem: Path, keyfile: Path) -> Path:
    w = work / "mcp-server.sh"
    w.write_text(
        "#!/bin/bash\n"
        "# args: <db path> <agent name>. The key is read here so it never sits in mcp.json.\n"
        'export NOX_DB_PATH="$1" NOX_AGENT_NAME="$2"\n'
        f'export GEMINI_API_KEY="$(cat {keyfile})"\n'
        'cd "$(dirname "$1")"\n'
        f'exec node {noxmem}/dist/mcp-server.js\n'
    )
    w.chmod(0o700)
    return w


def db_counts(db: Path) -> dict:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = {"chunks": c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]}
    for t in ("decisions", "search_telemetry"):
        try:
            out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.Error:
            out[t] = None
    try:
        out["telemetry_by_agent"] = dict(c.execute(
            "SELECT requesting_agent, COUNT(*) FROM search_telemetry GROUP BY 1").fetchall())
    except sqlite3.Error:
        out["telemetry_by_agent"] = None
    c.close()
    return out


def parse_stream(path: Path) -> dict:
    s = {"model": None, "skills_listed": None, "mcp_status": None, "tool_calls": [],
         "skill_loaded": False, "result": None, "is_error": None, "cost_usd": None,
         "usage": None, "num_turns": None, "duration_ms": None, "permission_denials": None}
    for line in path.read_text().splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("type") == "system" and m.get("subtype") == "init":
            s["model"] = m.get("model")
            s["skills_listed"] = "nox-mem-memory" in (m.get("skills") or [])
            s["mcp_status"] = {x.get("name"): x.get("status") for x in m.get("mcp_servers") or []}
        elif m.get("type") == "assistant":
            for b in (m.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use":
                    name = b.get("name", "")
                    short = name.split("__")[-1]
                    s["tool_calls"].append({"name": short, "input": b.get("input")})
                    if name == "Skill" and "nox-mem-memory" in json.dumps(b.get("input")):
                        s["skill_loaded"] = True
        elif m.get("type") == "result":
            s.update(result=m.get("result"), is_error=m.get("is_error"), cost_usd=m.get("total_cost_usd"),
                     usage=m.get("usage"), num_turns=m.get("num_turns"), duration_ms=m.get("duration_ms"),
                     permission_denials=m.get("permission_denials"))
    names = [t["name"] for t in s["tool_calls"]]
    s["memory_calls"] = sum(n in MEMORY_TOOLS for n in names)
    s["search_calls"] = names.count("nox_mem_search")
    s["write_calls"] = sum(n in WRITE_TOOLS for n in names)
    return s


def one_run(task: dict, arm: str, rep: int, a, work_root: Path, out: Path, frozen: Path) -> dict:
    run_id = f"{arm.replace('+', 'p')}-{task['id']}-r{rep}-{uuid.uuid4().hex[:6]}"
    agent = f"skilleval-{run_id}".lower()[:40]
    work = work_root / run_id
    cwd = work / "cwd"
    cwd.mkdir(parents=True)
    if arm == "S1":
        (cwd / ".claude" / "skills" / "nox-mem-memory").mkdir(parents=True)
        shutil.copy(SKILL, cwd / ".claude" / "skills" / "nox-mem-memory" / "SKILL.md")
    db = work / "eval.db"
    shutil.copy(frozen, db)
    db.chmod(0o644)
    before = db_counts(db)
    servers = {}
    if arm != "N":
        w = mcp_wrapper(work, Path(a.noxmem_t if arm == "T" else a.noxmem), Path(a.keyfile))
        servers["nox-mem"] = {"type": "stdio", "command": "/bin/bash", "args": [str(w), str(db), agent]}
    mcp = work / "mcp.json"
    mcp.write_text(json.dumps({"mcpServers": servers}))
    prompt = (P_PLUS_PREFIX if arm == "P+" else "") + task["prompt"]
    claude = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
    env = {"HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""), "LANG": "en_US.UTF-8",
           "PATH": f"{Path(claude).resolve().parent}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    allowed = ["Skill"] + (["mcp__nox-mem"] if arm != "N" else [])
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(mcp),
           "--no-session-persistence", "--model", a.model,
           # the user's `language` setting leaks past --setting-sources project; pin it
           "--settings", json.dumps({"language": "english"}), "--permission-mode", "dontAsk",
           "--max-budget-usd", str(a.max_budget), "--allowedTools", *allowed]
    stream = out / f"{run_id}.stream.jsonl"
    t0 = time.time()
    with open(stream, "w") as f, open(work / "stderr.txt", "w") as e:
        try:
            rc = subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=f, stderr=e,
                                timeout=a.timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    after = db_counts(db)
    rec = {"run_id": run_id, "task": task["id"], "set": task.get("set"), "arm": arm, "rep": rep,
           "agent": agent, "rc": rc, "wall_s": round(time.time() - t0, 1),
           "db_before": before, "db_after": after, **parse_stream(stream)}
    tel = (after.get("telemetry_by_agent") or {}).get(f"mcp:{agent}", 0)
    rec["telemetry_rows"] = tel
    rec["instrument_agree"] = (tel >= rec["search_calls"]) if arm != "N" else (rec["memory_calls"] == 0)
    rec["stderr_tail"] = (work / "stderr.txt").read_text()[-400:]
    if not a.keep_work:
        shutil.rmtree(work)
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bank", required=True)
    p.add_argument("--arms", default="S0,S1")
    p.add_argument("--replicas", type=int, default=1)
    p.add_argument("--tasks", default="")
    p.add_argument("--label", required=True)
    p.add_argument("--eval-dir", default=str(Path.home() / "nox-skill-eval"))
    p.add_argument("--db", default="")
    p.add_argument("--noxmem", default=str(Path.home() / "Claude/Projetos/nox-supermem/nox-mem"))
    p.add_argument("--noxmem-t", default="", help="nox-mem build used by arm T")
    p.add_argument("--keyfile", default=str(Path.home() / ".config/secrets/GEMINI_API_KEY"))
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--max-budget", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--seed", type=int, default=20261106)
    p.add_argument("--keep-work", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    assert set(arms) <= ARMS, f"unknown arm in {arms}"
    assert "T" not in arms or a.noxmem_t, "arm T needs --noxmem-t"
    tasks = [json.loads(l) for l in open(a.bank) if l.strip()]
    if a.tasks:
        keep = set(a.tasks.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    ev = Path(a.eval_dir)
    frozen = Path(a.db) if a.db else sorted((ev / "db").glob("eval-*.db"))[-1]
    plan = [(t, arm, r) for t in tasks for arm in arms for r in range(1, a.replicas + 1)]
    random.Random(a.seed).shuffle(plan)  # interleave arms so drift over time hits both equally
    print(f"{len(plan)} runs, db {frozen.name}, model {a.model}", file=sys.stderr)
    if a.dry_run:
        for t, arm, r in plan:
            print(arm, t["id"], r)
        return
    out = ev / "runs" / a.label
    out.mkdir(parents=True, exist_ok=True)
    work_root = ev / "work" / a.label
    work_root.mkdir(parents=True, exist_ok=True)
    with open(out / "results.jsonl", "a") as res:
        for i, (t, arm, r) in enumerate(plan, 1):
            rec = one_run(t, arm, r, a, work_root, out, frozen)
            res.write(json.dumps(rec) + "\n")
            res.flush()
            print(f"[{i}/{len(plan)}] {rec['run_id']} rc={rec['rc']} mem={rec['memory_calls']} "
                  f"skill={rec['skill_loaded']} cost={rec['cost_usd']} {rec['wall_s']}s", file=sys.stderr)


if __name__ == "__main__":
    main()
