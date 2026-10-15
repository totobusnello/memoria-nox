"""Read-only brief_log access and the production render bridge (spec §3, §4.1).

brief_log quirk: the refresh script requests the `main` brief with agent=nox, immediately before the
`nox` brief, so both are logged as agent='nox'. Within a refresh cycle the earlier brief_id (lower row
id) is main's and the later is nox's.
"""
import json
import os
import random
import subprocess
from datetime import datetime, timezone

NOX_MEM_DIR = os.environ.get("NOX_MEM_DIR", "/root/.openclaw/workspace/tools/nox-mem")
DB_PATH = os.environ.get("NOX_MEM_DB", f"{NOX_MEM_DIR}/nox-mem.db")
BRIDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "render_brief.mjs")
AUTO_HEADER = (
    "<!-- AUTO-GERADO por nox-mem-brief-refresh.sh (cron */15) — NÃO EDITAR.\n"
    "     Session Priming Loop F3 — brief por salience do nox-mem.\n"
    "     Detalhe de qualquer item: nox_mem_search por id/título. -->\n\n"
)
PAIR_SECONDS = 60


def connect():
    import sqlite3
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def db_agent(agent):
    return "nox" if agent == "main" else agent


def iso_to_db(ts):
    return ts[:19].replace("T", " ")


def db_to_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _secs(s):
    return db_to_ms(s) // 1000


def _briefs(con, agent, where, args, limit):
    return con.execute(
        "SELECT brief_id, MIN(id) AS r, MIN(served_at) AS s FROM brief_log "
        f"WHERE agent = ? AND brief_id IS NOT NULL AND {where} GROUP BY brief_id ORDER BY r DESC LIMIT ?",
        (db_agent(agent), *args, limit)).fetchall()


def _pick(agent, rows):
    """rows: newest first. For main/nox, split a same-cycle pair by row order."""
    if not rows:
        return None
    if agent in ("main", "nox") and len(rows) >= 2 and _secs(rows[0][2]) - _secs(rows[1][2]) <= PAIR_SECONDS:
        later, earlier = rows[0], rows[1]
        chosen = earlier if agent == "main" else later
    else:
        chosen = rows[0]
    return {"brief_id": chosen[0], "served_at": chosen[2]}


def brief_at(con, agent, t):
    return _pick(agent, _briefs(con, agent, "served_at < ?", (t,), 2))


def brief_by_generated_at(con, agent, gen_iso):
    s = _secs(iso_to_db(gen_iso))
    lo = datetime.fromtimestamp(s - 2, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    hi = datetime.fromtimestamp(s + 2, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = con.execute(
        "SELECT brief_id, MIN(id) AS r, MIN(served_at) AS s FROM brief_log WHERE agent = ? AND brief_id IS NOT NULL "
        "GROUP BY brief_id HAVING MIN(served_at) BETWEEN ? AND ? ORDER BY r", (db_agent(agent), lo, hi)).fetchall()
    if not rows:
        return None
    if agent in ("main", "nox") and len(rows) >= 2:
        return rows[0][0] if agent == "main" else rows[1][0]
    return rows[0][0]


def brief_items(con, brief_id):
    return [r[0] for r in con.execute("SELECT chunk_id FROM brief_log WHERE brief_id = ? ORDER BY id", (brief_id,))]


def candidate_briefs(con, owner, t, seed, per_agent=20):
    """§3 step 1: other agents in seeded order; for each, brief_ids within ±3 days of t, nearest first."""
    agents = sorted(r[0] for r in con.execute(
        "SELECT DISTINCT agent FROM brief_log WHERE agent IS NOT NULL AND agent != ?", (db_agent(owner),)))
    random.Random(seed).shuffle(agents)
    out = []
    for a in agents:
        rows = con.execute(
            "SELECT brief_id, MIN(served_at) AS s FROM brief_log WHERE agent = ? AND brief_id IS NOT NULL "
            "GROUP BY brief_id HAVING ABS(julianday(MIN(served_at)) - julianday(?)) <= 3 "
            "ORDER BY ABS(julianday(MIN(served_at)) - julianday(?)), MIN(id) LIMIT ?",
            (a, t, t, per_agent)).fetchall()
        out += [r[0] for r in rows]
    return out


def chunk_meta(con, ids):
    out = {}
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        q = f"SELECT id, created_at FROM chunks WHERE id IN ({','.join('?' * len(part))})"
        for cid, created in con.execute(q, part):
            out[cid] = {"id": cid, "created_at": created}
    return out


def brief_block(render_text):
    return AUTO_HEADER + render_text


class Bridge:
    """Long-lived `node render_brief.mjs` process; one JSON request per line."""

    def __init__(self):
        env = {**os.environ, "NOX_MEM_DIR": NOX_MEM_DIR, "NOX_MEM_DB": DB_PATH}
        self.p = subprocess.Popen(["node", BRIDGE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, env=env, bufsize=1)

    def render(self, chunk_ids, now_ms, agent, scope="global"):
        self.p.stdin.write(json.dumps({"chunk_ids": list(chunk_ids), "now_ms": now_ms,
                                       "agent": agent, "scope": scope}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("render bridge exited")
        return json.loads(line)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)
