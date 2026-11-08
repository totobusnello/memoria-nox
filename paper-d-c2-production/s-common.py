"""C2 shadow study: what the registered scripts share (SHADOW-PREREGISTRATION.md). Not run on its own.

Loaded by path (importlib), so every script runs under `python3 -I` from any directory, including
the tree `git archive` extracts from the tag. Standard library only. Paper D's own module
(d-common.py) is loaded as a separate instance and pointed at this study's tag and commitment
names, so the public-history checks are Paper D's code, not a copy.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
D = "paper-d-c2-production"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ registered constants
TAG = "paper-d-shadow-prereg-v1.0"
# SHADOW-PROTOCOL.md §2: sha256 of Paper 3's DISTILL_SYSTEM_V3, the only C2 prompt the shadow runs
C2_PROMPT_SHA256 = "325342a36e742f1e844b7c3792dae3eb47a76879c501678b576cd6df2cc8089d"
MIN_BLOCK_CHARS = 500                   # §2 eligible block
START = "2026-11-08"                    # §2: records dated from this UTC date
EARLIEST_FREEZE = "2026-12-01"          # §2: not before
LATEST_FREEZE = "2027-01-10"            # §2: if this date comes first, freeze what exists
EXCLUDED_FILE = "c2-shadow-2026-11-07.jsonl"   # §2 and §9
EXCLUDED_SESSIONS, EXCLUDED_BLOCKS = 3, 4      # §2: "(3 sessions, 4 blocks)"
MIN_BLOCKS, MIN_SESSIONS = 300, 100     # §2 stopping rule
N_DRAW = 400                            # §3, per set
CAP_USD = 5.0                           # §4
N_HUMAN = 60                            # §5.3 (Paper D's §5.4)
B_BOOT = 10_000                         # §5.2
KAPPA_MIN = 0.40                        # §5.3
GATES = {"ceiling": 0.70, "positive": 0.10}    # §5.1
IMPORTANCE_MIN = 0.5                    # §5.1 record integrity
PAD = 1_500                             # §4 arm A: citations plus 1,500 characters each side
ARMS = ("A", "C0", "C2", "C2-cut")      # §4
SETS = ("primary", "secondary")
# The writer (glm-5.3 through paper-a-eval-ptbr/holdout-generate.py) returns no token usage, so
# its calls are counted, not priced (§4 "the writer's calls are counted"). None = unpriced.
WRITER_USD_PER_CALL = None
# Commitments, in the order of §6. The names carry SHADOW- so they never collide with Paper D's
# own FREEZE/QUESTIONS/HUMAN commitments, which live in the same directory.
COMMITS = ("SHADOW-FREEZE", "SHADOW-QUESTIONS", "SHADOW-RESULTS", "SHADOW-HUMAN")
FILE_RX = re.compile(r"^c2-shadow-(\d{4}-\d{2}-\d{2})\.jsonl$")
DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Paper D's module, a separate instance pointed at this study's tag and commitment names.
DC = load("dcommon_shadow", HERE / "d-common.py")
DC.TAG = TAG
DC.COMMITS = COMMITS
sha_bytes, sha_file, sha_json = DC.sha_bytes, DC.sha_file, DC.sha_json
private, inside_repo, git, commit_of = DC.private, DC.inside_repo, DC.git, DC.commit_of
serve = DC.serve


def seed_from_commit(commit):
    """§3: the seed is the first eight hex digits of the tag commit, read as an integer."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        raise SystemExit(f"refusing: {commit!r} is not a full commit id")
    return int(commit[:8], 16)


def utc_today():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


# ------------------------------------------------------------------ the record
# The record as distill-shadow.ts writes it (SHADOW-PROTOCOL.md §3; field names checked against the
# host module, record version v: 1, on 2026-11-07). Every read of a record goes through the
# functions below, so a rename is one edit here.
#   v, ts, session_key, agent, block_index, n_blocks, message_count, session_mtime
#   block            the block text as sent to production's model
#   block_sha256     sha256 of the block text (UTF-8), hex
#   c0_units: [{text, category, importance}, ...]           production's C0 units, before dedup
#   c2: {ok, units, model, model_version, prompt_sha256, usage: {promptTokenCount,
#        candidatesTokenCount, ...}, error}
REASONS = ("malformed", "excluded_session", "c2_failed", "prompt_hash", "block_hash", "short_block")


def r_session(r):
    return r["session_key"]


def r_agent(r):
    return r.get("agent")


def r_block(r):
    return r["block"]


def r_c0_units(r):
    return r["c0_units"]


def r_c2(r):
    return r["c2"]


def r_c2_units(r):
    return r["c2"].get("units") or []


def r_c2_tokens(r):
    u = r["c2"].get("usage") or {}
    return int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0) + \
        int(u.get("thoughtsTokenCount") or 0)


def well_formed(r):
    try:
        return (isinstance(r, dict) and isinstance(r.get("session_key"), str) and r["session_key"] != ""
                and isinstance(r.get("block"), str) and isinstance(r.get("block_sha256"), str)
                and isinstance(r.get("c0_units"), list)
                and isinstance(r.get("c2"), dict)
                and isinstance(r["c2"].get("units", []), (list, type(None))))
    except Exception:
        return False


def c2_ok(r):
    c2 = r["c2"]
    return c2.get("ok") is True and not c2.get("error")


def eligible(record, excluded_keys):
    """§2, the eligible-block rule: the C2 call succeeded (c2.ok, no error), the C2 prompt sha256 is
    the registered one, the block text hashes to its block_sha256, the block has at least 500
    characters; and (§2 "excluded by date") the session key is not one of the three excluded
    sessions. Pure: reads only its arguments. Returns (True, None) or (False, reason); reasons are
    tested in the order of REASONS and the first one that applies is returned."""
    if not well_formed(record):
        return False, "malformed"
    if r_session(record) in excluded_keys:
        return False, "excluded_session"
    if not c2_ok(record):
        return False, "c2_failed"
    if r_c2(record).get("prompt_sha256") != C2_PROMPT_SHA256:
        return False, "prompt_hash"
    if sha_bytes(r_block(record).encode("utf-8")) != record["block_sha256"]:
        return False, "block_hash"
    if len(r_block(record)) < MIN_BLOCK_CHARS:
        return False, "short_block"
    return True, None


# ------------------------------------------------------------------ the shadow directory
def shadow_files(src):
    """[(date, path)] of every c2-shadow-<date>.jsonl in src, by date. Other names are ignored."""
    out = []
    for p in sorted(pathlib.Path(src).iterdir()):
        m = FILE_RX.match(p.name)
        if m and p.is_file():
            out.append((m.group(1), p))
    return out


def read_lines(path):
    """[(line number, raw bytes without the newline, parsed object or None)]; blank lines skipped."""
    out = []
    with open(path, "rb") as f:
        for i, raw in enumerate(f, 1):
            raw = raw.rstrip(b"\n")
            if not raw.strip():
                continue
            try:
                o = json.loads(raw.decode("utf-8"))
            except Exception:
                o = None
            out.append((i, raw, o))
    return out


def excluded_keys(src):
    """The session keys of the excluded file (§2). Never printed. Refuses if the file is missing or
    does not hold the 3 sessions and 4 blocks the pre-registration names."""
    p = pathlib.Path(src) / EXCLUDED_FILE
    if not p.is_file():
        raise SystemExit(f"refusing: {EXCLUDED_FILE} is not in the shadow directory; the exclusion "
                         "of its sessions cannot be applied")
    keys, n = set(), 0
    for _, _, o in read_lines(p):
        n += 1
        if isinstance(o, dict) and isinstance(o.get("session_key"), str):
            keys.add(o["session_key"])
    if (len(keys), n) != (EXCLUDED_SESSIONS, EXCLUDED_BLOCKS):
        raise SystemExit(f"refusing: {EXCLUDED_FILE} holds {len(keys)} sessions and {n} blocks, "
                         f"not the registered {EXCLUDED_SESSIONS} and {EXCLUDED_BLOCKS}")
    return keys


def scan(src, upto, excluded):
    """Read every shadow file dated START..min(upto, LATEST_FREEZE). Returns (per_date, kept, other):
    per_date[date] = counts, with cumulative eligible blocks and sessions; kept[date] = [(line,
    raw bytes, record)] of the eligible records; other = counts of the files outside the window.
    Nothing but counts leaves this function's per_date and other."""
    last = min(upto, LATEST_FREEZE)
    per, kept, other = {}, {}, {"files_before_start": 0, "files_after_window": 0}
    seen = set()
    cum = 0
    for date, path in shadow_files(src):
        if date < START:
            other["files_before_start"] += 1
            continue
        if date > last:
            other["files_after_window"] += 1
            continue
        c = {"records": 0, "c2_failures": 0, "eligible_blocks": 0, "eligible_sessions": 0,
             "excluded": {k: 0 for k in REASONS}}
        day_sessions, rows = set(), []
        for line, raw, o in read_lines(path):
            c["records"] += 1
            try:
                if well_formed(o) and not c2_ok(o):
                    c["c2_failures"] += 1
                ok, why = eligible(o, excluded)
            except Exception:
                ok, why = False, "malformed"
            if not ok:
                c["excluded"][why] += 1
                continue
            c["eligible_blocks"] += 1
            day_sessions.add(r_session(o))
            rows.append((line, raw, o))
        seen |= day_sessions
        cum += c["eligible_blocks"]
        c["eligible_sessions"] = len(day_sessions)
        c["cum_eligible_blocks"], c["cum_eligible_sessions"] = cum, len(seen)
        per[date] = c
        kept[date] = rows
    return per, kept, other


def stopping(per, today):
    """§2: the freeze date is the first UTC date on which the cumulative eligible records reach 300
    blocks from at least 100 sessions, and not before 2026-12-01; if 2027-01-10 comes first, it is
    2027-01-10 with a shortfall. `due` says the freeze date has arrived (today >= freeze date)."""
    reach = next((d for d in sorted(per) if per[d]["cum_eligible_blocks"] >= MIN_BLOCKS
                  and per[d]["cum_eligible_sessions"] >= MIN_SESSIONS), None)
    if reach is not None:
        end, shortfall = max(reach, EARLIEST_FREEZE), False
    elif today >= LATEST_FREEZE:
        end, shortfall = LATEST_FREEZE, True
    else:
        end, shortfall = None, False
    return {"reach_date": reach, "threshold_met": reach is not None, "freeze_date": end,
            "due": end is not None and today >= end, "shortfall": shortfall,
            "min_blocks": MIN_BLOCKS, "min_sessions": MIN_SESSIONS,
            "earliest": EARLIEST_FREEZE, "latest": LATEST_FREEZE}


def cumulate(per, end):
    """per_date restricted to dates <= end; the cumulative fields are unchanged (they start at START)."""
    return {d: c for d, c in per.items() if d <= end}


# ------------------------------------------------------------------ private material
def lock_down(p):
    """Mode 700 on every directory and 600 on every file under p (and p itself)."""
    p = pathlib.Path(p)
    if p.is_dir():
        os.chmod(p, 0o700)
        for q in p.rglob("*"):
            os.chmod(q, 0o700 if q.is_dir() else 0o600)
    elif p.exists():
        os.chmod(p, 0o600)


def write_private(path, text):
    path = pathlib.Path(path)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def frozen_records(F):
    """[(block id, date, record)] of the frozen eligible records in <F>/records, by date and line."""
    out = []
    for date, path in shadow_files(pathlib.Path(F) / "records"):
        for line, _, o in read_lines(path):
            out.append((f"{date}:{line}", date, o))
    return out


def check_manifest(F, want_sha=None):
    F = pathlib.Path(F)
    if want_sha is not None and sha_file(F / "manifest.json") != want_sha:
        raise SystemExit("refusing: the manifest is not the committed one")
    man = json.loads((F / "manifest.json").read_text(encoding="utf-8"))
    on_disk = sorted(str(p.relative_to(F)) for p in F.rglob("*") if p.is_file() and p.name != "manifest.json")
    if on_disk != sorted(man):
        raise SystemExit("refusing: the files on disk are not the manifest's")
    for f, h in man.items():
        if sha_file(F / f) != h:
            raise SystemExit(f"refusing: {f} does not match the manifest")
    return man


# ------------------------------------------------------------------ the public history
SCRIPTS = ("s-common.py", "s-count.py", "s-freeze.py", "s-generate.py", "s-run.py", "s-human.py",
           "s-read.py", "d-common.py", "d-generate.py", "d-smoke.py", "d-select.py", "d-human.py",
           "d-read.py")
DEPS = ("paper3-construction/lme-run.py", "paper-a-eval-ptbr/holdout-generate.py")


def same_as_tag(repo):
    """The code that runs is the tag's: every script of this study, the Paper D modules it loads
    and Paper 3's and Paper A's callers are byte-equal to their copies at the tag."""
    for rel in [f"{D}/{s}" for s in SCRIPTS] + list(DEPS):
        here = ROOT / rel
        r = subprocess.run(["git", "-C", str(repo), "show", f"{TAG}:{rel}"], capture_output=True)
        if r.returncode or not here.is_file() or sha_file(here) != sha_bytes(r.stdout):
            raise SystemExit(f"refusing: {rel} is not the tag's; run the code of {TAG}")


def tag_seed(repo):
    return seed_from_commit(commit_of(repo, TAG))


def chain(repo, P, refs, smoke):
    """refs = [(name, ref), ...] in the registered order. Every named commitment must exist in P;
    unless smoke, the public history must be in order after the tag (d-common.ordered: each a
    different commit, descending from the previous, on origin/main, written once) and each
    published file byte-equal to the private one. Returns {name: (bytes, parsed)}."""
    P = pathlib.Path(P)
    loc = {}
    for n, _ in refs:
        f = P / f"{n}-COMMITMENT.json"
        if not f.is_file():
            raise SystemExit(f"refusing: the {n} commitment is missing from the private directory")
        loc[n] = f.read_bytes()
    if not smoke:
        if any(not r for _, r in refs):
            raise SystemExit("refusing: every earlier commitment needs its commit (--refs)")
        got = DC.ordered(repo, refs)
        for n, _ in refs:
            pub = git(repo, "show", f"{got[n]['_commit']}:{D}/{n}-COMMITMENT.json").stdout
            if pub.encode() != loc[n]:
                raise SystemExit(f"refusing: the published {n} commitment is not the private copy")
    out = {}
    for n, b in loc.items():
        o = json.loads(b)
        if o.get("smoke") is not bool(smoke):
            raise SystemExit(f"refusing: the {n} commitment says smoke={o.get('smoke')}")
        out[n] = (b, o)
    return out
