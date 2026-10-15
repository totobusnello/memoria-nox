"""Git-archived served briefs (spec v3.2 §3, §4.1).

`brief_log` cannot rebuild any brief of the window (ids rotated by daily re-ingest before the
2026-10-14 write-path fix), so B1 is the served `MEMORY.md` text itself, as committed to the workspace
git, and BS is built from other agents' snapshots served before t.
"""
import random
import re
from datetime import datetime, timedelta

from probe.briefs import AUTO_HEADER

HDR = re.compile(r"^# nox-mem brief — scope=(\S+)(?: agent=(\S+))? — (\S+) — (\d+) items$")
CHK = re.compile(r"\s*\(chk (\d+)\)$")
PREFIX = re.compile(r"^\[[^\]]*\]\s*")
FILES = {"main": "brief/MEMORY.md",
         **{a: f"agents/{a}/brief/MEMORY.md" for a in ("nox", "atlas", "boris", "cipher", "forge", "lex")}}
FMT = "%Y-%m-%d %H:%M:%S"


def parse_snapshot(text):
    lines = text.split("\n")
    hi = next((i for i, l in enumerate(lines) if HDR.match(l)), None)
    if hi is None:
        return None
    scope, agent, gen, _ = HDR.match(lines[hi]).groups()
    items = []
    for l in lines[hi + 1:]:
        m = CHK.search(l)
        if l.startswith("[") and m:
            items.append({"id": int(m.group(1)), "line": l, "text": PREFIX.sub("", CHK.sub("", l)).strip()})
    return {"scope": scope, "agent_label": agent, "generated_iso": gen,
            "generated_at": gen[:19].replace("T", " "), "text": text, "items": items}


def build_index(entries):
    """entries: iterable of (persona, file text). Returns persona -> snapshots sorted by generated_at."""
    idx = {}
    for persona, text in entries:
        s = parse_snapshot(text)
        if s is None:
            continue
        bucket = idx.setdefault(persona, {})
        bucket.setdefault(s["generated_iso"], dict(s, persona=persona))
    return {p: sorted(b.values(), key=lambda s: s["generated_iso"]) for p, b in idx.items()}


def snapshot_at(idx, persona, t):
    best = None
    for s in idx.get(persona, []):
        if s["generated_at"] <= t:
            best = s
    return best


def excluded(owner):
    return {"main", "nox"} if owner in ("main", "nox") else {owner}


def candidate_items(idx, owner, t, seed, days=3):
    """§3 steps 1–2 (before the overlap filter): other personas in seeded order; for each, snapshots
    served in [t − days, t], nearest first; item lines in served order."""
    lo = (datetime.strptime(t, FMT) - timedelta(days=days)).strftime(FMT)
    personas = sorted(p for p in idx if p not in excluded(owner))
    random.Random(seed).shuffle(personas)
    out = []
    for p in personas:
        snaps = [s for s in idx[p] if lo <= s["generated_at"] <= t]
        for s in sorted(snaps, key=lambda s: s["generated_iso"], reverse=True):
            out += [dict(i, created_at=s["generated_at"]) for i in s["items"]]
    return out


def block(agent_label, scope, generated_iso, lines):
    head = f"# nox-mem brief — scope={scope}{f' agent={agent_label}' if agent_label else ''} — {generated_iso} — {len(lines)} items"
    return AUTO_HEADER + head + "\n" + "\n".join(lines) + "\n"


def turnover(a, b):
    """Share of b's item ids not present in a."""
    ia, ib = {i["id"] for i in a["items"]}, [i["id"] for i in b["items"]]
    return sum(1 for i in ib if i not in ia) / len(ib) if ib else 0.0
