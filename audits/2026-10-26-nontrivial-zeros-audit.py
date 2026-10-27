"""Close the probe: are the 45 auditable, and what do they actually contain?

message_count is written BEFORE the noise filter (session-distill.ts:384 vs
478), so a session of 393 messages yielding zero can be 393 heartbeats and
correct by design. The archive settles it: where the raw transcript survived,
the real messages can be counted and read. Where it did not, the zero is not
auditable and must be reported as such rather than as loss.
"""
import collections
import glob
import json
import os
import re
import sqlite3

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
ARCHIVE = "/var/lib/nox-mem/action-archive"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

con = sqlite3.connect(DB, uri=True)
per_uuid = collections.defaultdict(list)
for sk, ag, ce, mc in con.execute(
        "SELECT session_key, agent, chunks_extracted, message_count FROM session_distill_log"):
    m = UUID.search(sk)
    if m:
        per_uuid[m.group(1)].append((ag, ce, mc))
best = {u: max(c for _, c, _ in v) for u, v in per_uuid.items()}
maxmsg = {u: max(m for _, _, m in v) for u, v in per_uuid.items()}
nontrivial = sorted((u for u in best if best[u] == 0 and maxmsg[u] >= 3),
                    key=lambda u: -maxmsg[u])

raw = {}
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        raw[m.group(1)] = p

print("=== the 45, against the archive ===")
have = [u for u in nontrivial if u in raw]
print(f"nontrivial zeros: {len(nontrivial)} | raw transcript still exists: {len(have)}"
      f" | raw gone (not auditable): {len(nontrivial) - len(have)}")

ROLE_NOISE = re.compile(
    r"heartbeat|^\s*ok\s*$|^\s*$|system-reminder|<command-name>|caveat: the messages below",
    re.I)
print(f"\n{'uuid':10s} {'agents':26s} {'msg_log':>7s} {'lines':>6s} {'user':>5s} "
      f"{'asst':>5s} {'chars':>9s} {'KB':>7s}")
rows = []
for u in have[:14]:
    n_lines = n_user = n_asst = n_chars = 0
    with open(raw[u], encoding="utf-8", errors="replace") as f:
        for line in f:
            n_lines += 1
            try:
                o = json.loads(line)
            except Exception:
                continue
            msg = o.get("message") or {}
            role = msg.get("role") or o.get("type") or ""
            c = msg.get("content")
            txt = c if isinstance(c, str) else " ".join(
                b.get("text", "") for b in c if isinstance(b, dict)) if isinstance(c, list) else ""
            n_chars += len(txt)
            if role == "user":
                n_user += 1
            elif role == "assistant":
                n_asst += 1
    ags = ",".join(sorted({a for a, _, _ in per_uuid[u]}))
    rows.append((u, ags, maxmsg[u], n_lines, n_user, n_asst, n_chars, os.path.getsize(raw[u])))
    print(f"{u[:8]:10s} {ags[:26]:26s} {maxmsg[u]:7d} {n_lines:6d} {n_user:5d} "
          f"{n_asst:5d} {n_chars:9d} {os.path.getsize(raw[u])/1024:7.0f}")

print("\n=== by directory: the two rows cut off earlier ===")
by_dir = collections.defaultdict(dict)
for u, p in raw.items():
    by_dir[os.path.basename(os.path.dirname(p))][u] = os.path.getsize(p)
for d in ("-root--openclaw-workspace", "-root--openclaw-workspace-agents-forge"):
    us = by_dir[d]
    print(f"{d:48s} files={len(us):4d} never_logged="
          f"{sum(1 for u in us if u not in per_uuid):4d} logged_zero="
          f"{sum(1 for u in us if u in best and best[u] == 0):4d} produced="
          f"{sum(1 for u in us if u in best and best[u] > 0):4d}")

print("\n=== the 991 logged-and-empty: how many are non-trivial AND auditable? ===")
in_reach = {u for d, us in by_dir.items() for u in us
            if any(x in per_uuid for x in us)}
z991 = [u for u in raw if u in best and best[u] == 0 and u in in_reach]
print("logged_zero with raw present:", len(z991),
      "| of those non-trivial (>=3 msgs):", sum(1 for u in z991 if maxmsg[u] >= 3))
