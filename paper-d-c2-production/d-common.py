"""Paper D: what the registered scripts share (PREREGISTRATION.md). Not run on its own.

Loaded by path (importlib), so every script runs under `python3 -I` from any directory, including
the tree `git archive` extracts from the tag. Standard library only.
"""
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TAG = "paper-d-prereg-v1.0"
SEED = 20261106
START = "2026-08-15"
MIN_CHARS = 3000
N_SESSIONS, N_MAX, BLOCK, TARGET_PRIMARY = 80, 120, 10, 232
WINDOW, PAD = 20_000, 1_500
D = "paper-d-c2-production"
COMMITS = ("FREEZE", "QUESTIONS", "HUMAN")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def sha_json(o):
    return sha_bytes(json.dumps(o, sort_keys=True, ensure_ascii=False).encode())


def inside_repo(p):
    p = pathlib.Path(p).resolve()
    d = p if p.is_dir() else p.parent
    while not d.exists():
        d = d.parent
    return subprocess.run(["git", "-C", str(d), "rev-parse"], capture_output=True).returncode == 0


def private(p):
    if inside_repo(p):
        raise SystemExit(f"refusing: {p} is inside a git repository; it holds private material")
    return pathlib.Path(p)


# ------------------------------------------------------------------ sessions
def norm_ts(ts):
    """ISO timestamp of a transcript event -> 'YYYY-MM-DD HH:MM:SS' (UTC), the format of
    session_distill_log.processed_at, as in audits/2026-10-27-see-once-probe.py. '' if none."""
    return ts.replace("T", " ")[:19] if isinstance(ts, str) and len(ts) >= 19 else ""


def turns(path, S):
    """[{role, content, ts}] with the envelope cuts of d-select.py (replay-build rule)."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            s = S.turn_text(o)
            if s:
                role, _, content = s.partition(": ")
                out.append({"role": role, "content": content, "ts": norm_ts(o.get("timestamp"))})
    return out


def layout(ts):
    """The session's cleaned prose and each turn's [start, end) inside it."""
    parts, spans, pos = [], [], 0
    for t in ts:
        seg = f"{t['role']}: {t['content']}"
        if parts:
            pos += 2
        spans.append((pos, pos + len(seg)))
        parts.append(seg)
        pos += len(seg)
    return "\n\n".join(parts), spans


def windows(full):
    """{offset: text}: 20,000 chars from the start and from the middle (half the length minus
    10,000); each kept only if >= 3,000 chars, the middle one only if it does not overlap the
    first (PREREGISTRATION.md §3)."""
    out = {}
    if len(full[:WINDOW]) >= MIN_CHARS:
        out[0] = full[:WINDOW]
    mid = len(full) // 2 - WINDOW // 2
    if mid >= WINDOW and len(full[mid:mid + WINDOW]) >= MIN_CHARS:
        out[mid] = full[mid:mid + WINDOW]
    return out


def cut_regions(ts, spans, regions):
    """The session with every character inside `regions` (absolute [lo, hi) in the prose) removed.
    A turn keeps its role; a turn left empty is dropped (C2-cut, PREREGISTRATION.md §4)."""
    out = []
    for t, (s, e) in zip(ts, spans):
        seg = f"{t['role']}: {t['content']}"
        keep = [c for i, c in enumerate(seg, s) if not any(lo <= i < hi for lo, hi in regions)]
        txt = "".join(keep)
        pre = f"{t['role']}: "
        txt = txt[len(pre):] if txt.startswith(pre) else txt
        if txt.strip():
            out.append(dict(t, content=txt.strip()))
    return out


def visible_prefix(ts, processed_at):
    """The turns the production distiller could have seen: the prefix up to (not including) the
    first dated turn after processed_at. Undated turns inside the prefix are kept."""
    for i, t in enumerate(ts):
        if t["ts"] and t["ts"] > processed_at:
            return ts[:i]
    return list(ts)


DIGITS = re.compile(r"\d+")


def cf_run(ref, citations):
    """The first maximal digit run of the reference answer that also occurs, as a whole token, in
    one of its citations; None if there is none (counterfactual eligibility, §5.3)."""
    for m in DIGITS.finditer(ref):
        rx = re.compile(r"(?<!\d)" + re.escape(m.group(0)) + r"(?!\d)")
        if any(rx.search(c) for c in citations):
            return m.group(0)
    return None


def cf_alter(run):
    return run[:-1] + str((int(run[-1]) + 5) % 10)


def cf_rewrite(ts, run):
    rx = re.compile(r"(?<!\d)" + re.escape(run) + r"(?!\d)")
    alt = cf_alter(run)
    return [dict(t, content=rx.sub(alt, t["content"])) for t in ts]


def has_token(text, run):
    return re.search(r"(?<!\d)" + re.escape(run) + r"(?!\d)", text or "") is not None


def serve(units, date):
    """All units, importance descending, ties by block then position (§4). `units` is a list of
    blocks, each a list of {text, category, importance}."""
    items = [(-(u.get("importance") or 0), b, p, u)
             for b, us in enumerate(units) for p, u in enumerate(us)]
    items.sort(key=lambda x: x[:3])
    return "\n".join(f"[{date}] [{u.get('category')}] {u.get('text')}" for *_, u in items) or "(vazio)"


def draw(frame, seed=SEED):
    order = sorted(frame)
    random.Random(seed).shuffle(order)
    return order


# ------------------------------------------------------------------ the public history
def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r


def commit_of(repo, ref):
    return git(repo, "rev-parse", f"{ref}^{{commit}}").stdout.strip()


def written_once(repo, name, ref):
    """The only commit on origin/main that ever touched <name>-COMMITMENT.json is `ref`."""
    hist = git(repo, "log", "--full-history", "--format=%H", "origin/main", "--",
               f"{D}/{name}-COMMITMENT.json").stdout.split()
    if hist != [commit_of(repo, ref)]:
        raise SystemExit(f"{name}-COMMITMENT.json on origin/main was not written once, by {ref}")


def exists_at(repo, ref, name):
    return git(repo, "cat-file", "-e", f"{ref}:{D}/{name}-COMMITMENT.json", check=False).returncode == 0


def ordered(repo, refs):
    """refs = [(name, commit), ...] in the registered order, after the tag. Each commitment is a
    different commit, descends from the previous one, is on origin/main, is written once, and did
    not exist at the previous step. Returns the parsed commitments."""
    git(repo, "fetch", "-q", "--tags", "origin", "main")
    if git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{TAG}", check=False).returncode:
        raise SystemExit(f"tag {TAG} not found")
    prev_name, prev = "tag", commit_of(repo, TAG)
    for n in COMMITS:
        if exists_at(repo, TAG, n):
            raise SystemExit(f"the tag already carries a {n}-COMMITMENT.json")
    out = {}
    for name, ref in refs:
        c = commit_of(repo, ref)
        if c == prev:
            raise SystemExit(f"the {name} commitment is the {prev_name}'s own commit")
        if git(repo, "merge-base", "--is-ancestor", prev, c, check=False).returncode:
            raise SystemExit(f"{ref} does not descend from the {prev_name} ({prev[:12]})")
        if git(repo, "merge-base", "--is-ancestor", c, "origin/main", check=False).returncode:
            raise SystemExit(f"{ref} is not on origin/main")
        if exists_at(repo, prev, name):
            raise SystemExit(f"{name}-COMMITMENT.json already exists at the {prev_name}")
        written_once(repo, name, c)
        out[name] = json.loads(git(repo, "show", f"{c}:{D}/{name}-COMMITMENT.json").stdout)
        out[name]["_commit"] = c
        prev_name, prev = name, c
    return out


def tag_file_sha(repo, path):
    r = subprocess.run(["git", "-C", str(repo), "show", f"{TAG}:{path}"], capture_output=True)
    if r.returncode:
        raise SystemExit(f"{path} is not in the tag")
    return sha_bytes(r.stdout)
