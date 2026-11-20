#!/usr/bin/env python3
"""Paper A, H-A2R (PREREGISTRATION-H-A2R.md): the retrospective test of reference persistence.

  python3 -I h-a2r.py --db <copy of each registered database> [--db ...] \
      --end-gz <daily-main-main-20261118030003-…db.gz> --workdir <private directory outside any repo>

Every --db is identified by its sha256 against REGISTERED; the start (2026-05-04) is required, the
checkpoints are optional, and an unregistered file is refused. The end is the registered .gz of
2026-11-18, decompressed into --workdir. Databases are opened read-only and immutable.

1. Lineage, printed first: per database, the columns of `chunks`, PRAGMA quick_check, row count,
   active count and MAX(id). Start or end failing (no chunks(id, source_file, chunk_text), or
   quick_check not ok) stops the run; a failing checkpoint is dropped and reported.
2. Draw, on the start only: SEED, strata of strata.py, quotas 5 x quotas.json. Within a stratum the
   eligible source files are sorted and shuffled; passes over that order take, per file, one
   untried eligible chunk uniformly at random until the quota is met. A chunk is eligible if
   active and at least strata.MIN_CHARS long. Its evidence span is K consecutive whitespace tokens
   of the normalised text at a random start, 30 to 300 characters, occurring exactly once in the
   file's active chunks; up to MAX_TRIES starts, else the chunk is rejected and the next draw
   follows. The references (ids, paths, spans) are written to --workdir only; their sha256 is
   printed. No chunk text, path or span is printed.
3. Reading on the end, then descriptive counts on every database in date order.

A database without the column superseded_by has every chunk active.

--smoke: synthetic databases only. Skips the tag check and the registered hashes, and refuses any
input whose sha256 is registered, so it cannot be pointed at the real data.

Keyless, read-only.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import shutil
import sqlite3
import subprocess
import sys

TAG = "paper-a-h-a2r-prereg-v1.0"
SEED = 20261120
K = 12
SPAN_MIN, SPAN_MAX = 30, 300
MAX_TRIES = 20
QUOTA_FACTOR = 5
START = "2026-05-04"
END = "2026-11-18"
REGISTERED = {
    "03cd8f55afd3a57b4ff71e7427bce40401796132a1b1d1e54cf8c6345f136e93": "2026-05-04",
    "6247e6889feb2e423fbf32a89a68882b1cefe9b4117649e276a726aa6071164b": "2026-08-23",
    "b277bc96d0223a2360ac54ad81f451bf7dea9a05687fceacc6feef194634b47d": "2026-09-08",
    "d1cd2b57bdf7a1a1d0163b7e37ccf839f2492e7dcfd613e094c3979a6399aa07": "2026-10-11",
    "4ab1a94f7245c272177e184e0b465eeb795ab90813c91fb9afc1b6cf273a58ad": "2026-11-04",
}
END_GZ_SHA = "abbf0274bdaae1a05e175d5afa4e72649cc27b0354a455e29b15a3073fa1a16d"
here = pathlib.Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ws(t):
    return re.sub(r"\s+", " ", t).strip()


def load_strata():
    spec = importlib.util.spec_from_file_location("strata", here / "strata.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check_tag():
    repo = str(here.parent)
    subprocess.run(["git", "-C", repo, "fetch", "-q", "--tags", "origin"], check=True)
    for f in ("h-a2r.py", "strata.py", "quotas.json"):
        t = subprocess.run(["git", "-C", repo, "show", f"refs/tags/{TAG}:paper-a-eval-ptbr/{f}"],
                           capture_output=True)
        if t.returncode != 0:
            sys.exit(f"refusing: tag {TAG} not found on origin")
        if t.stdout != (here / f).read_bytes():
            sys.exit(f"refusing: {f} differs from the tag {TAG}")


class DB:
    def __init__(self, path, label):
        self.label = label
        self.con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
        cols = [r[1] for r in self.con.execute("PRAGMA table_info(chunks)")]
        self.cols = cols
        self.ok = {"id", "source_file", "chunk_text"} <= set(cols)
        self.qc = self.con.execute("PRAGMA quick_check").fetchone()[0] if self.ok else "no chunks table"
        self.ok = self.ok and self.qc == "ok"
        self.where = " WHERE superseded_by IS NULL" if "superseded_by" in cols else ""

    def lineage(self):
        if not self.ok:
            return f"{self.label}: FAILS lineage (columns {len(self.cols)}, quick_check {self.qc})"
        n = self.con.execute("SELECT COUNT(*), MAX(id) FROM chunks").fetchone()
        a = self.con.execute(f"SELECT COUNT(*) FROM chunks{self.where}").fetchone()[0]
        return (f"{self.label}: chunks {n[0]}, active {a}, max id {n[1]}, "
                f"superseded_by {'present' if self.where else 'absent (all active)'}, quick_check ok")

    def active(self):
        return self.con.execute(f"SELECT id, source_file, chunk_text FROM chunks{self.where}")

    def index(self):
        """id -> normalised text, path -> [normalised texts], one string of every active text."""
        by_id, by_path = {}, {}
        for cid, sf, t in self.active():
            w = ws(t or "")
            by_id[cid] = (sf, w)
            by_path.setdefault(sf, []).append(w)
        return by_id, by_path, "\x00".join(w for _, w in by_id.values())


def draw(start, st, quota, rng):
    by_id, by_path, _ = start.index()
    elig = {}
    for cid, (sf, w) in sorted(by_id.items()):
        s = st.stratum(sf)
        if s and len(w) >= st.MIN_CHARS:
            elig.setdefault(s, {}).setdefault(sf, []).append(cid)
    refs, stats = [], {}
    for s in sorted(quota):
        files = sorted(elig.get(s, {}))
        rng.shuffle(files)
        tried = {f: set() for f in files}
        got = rejected = passes = 0
        while got < quota[s]:
            passes += 1
            progressed = False
            for f in files:
                if got >= quota[s]:
                    break
                left = [c for c in elig[s][f] if c not in tried[f]]
                if not left:
                    continue
                progressed = True
                cid = rng.choice(left)
                tried[f].add(cid)
                toks = by_id[cid][1].split(" ")
                span = None
                for _ in range(MAX_TRIES if len(toks) >= K else 0):
                    i = rng.randrange(len(toks) - K + 1)
                    cand = " ".join(toks[i:i + K])
                    if SPAN_MIN <= len(cand) <= SPAN_MAX and sum(t.count(cand) for t in by_path[f]) == 1:
                        span = cand
                        break
                if span is None:
                    rejected += 1
                    continue
                refs.append({"stratum": s, "chunk_id": cid, "source_file": f, "span": span,
                             "start_text_sha": hashlib.sha256(by_id[cid][1].encode()).hexdigest()})
                got += 1
            if not progressed:
                break
        stats[s] = {"quota": quota[s], "drawn": got, "rejected": rejected, "passes": passes,
                    "eligible_files": len(files)}
    return refs, stats


def evaluate(db, refs):
    by_id, by_path, blob = db.index()
    out = []
    for r in refs:
        cur = by_id.get(r["chunk_id"])
        by_id_ok = cur is not None and r["span"] in cur[1]
        exposed = cur is None or hashlib.sha256(cur[1].encode()).hexdigest() != r["start_text_sha"]
        hits = sum(r["span"] in t for t in by_path.get(r["source_file"], []))
        out.append({"by_id": by_id_ok, "exposed": exposed, "anchor": hits > 0, "ambiguous": hits > 1,
                    "present": r["span"] in blob})
    return out


def tally(ev, idx=None):
    sel = [e for i, e in enumerate(ev) if idx is None or i in idx]
    return {k: sum(e[k] for e in sel) for k in ("by_id", "anchor", "ambiguous", "exposed", "present")}, len(sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", action="append", required=True)
    ap.add_argument("--end-gz", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        check_tag()
    if subprocess.run(["git", "-C", a.workdir, "rev-parse"], capture_output=True).returncode == 0:
        sys.exit("refusing: --workdir is inside a git repository")
    dbs = {}
    for p in a.db:
        h = sha(p)
        if a.smoke:
            if h in REGISTERED:
                sys.exit("refusing: --smoke given a registered database")
            label = pathlib.Path(p).stem          # smoke files are named by date
        elif h not in REGISTERED:
            sys.exit(f"refusing: {pathlib.Path(p).name} is not a registered database")
        else:
            label = REGISTERED[h]
        print(f"input {label}: sha256 {h}")
        dbs[label] = DB(p, label)
    gz = sha(a.end_gz)
    if a.smoke and gz == END_GZ_SHA:
        sys.exit("refusing: --smoke given the registered end snapshot")
    if not a.smoke and gz != END_GZ_SHA:
        sys.exit("refusing: --end-gz is not the registered snapshot of 2026-11-18")
    print(f"input {END} (.gz): sha256 {gz}")
    end_path = pathlib.Path(a.workdir) / "h-a2r-end.db"
    with gzip.open(a.end_gz, "rb") as src, open(end_path, "wb") as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    dbs[END] = DB(str(end_path), END)
    if START not in dbs:
        sys.exit(f"refusing: the start database ({START}) was not given")

    print("\n== lineage")
    for label in sorted(dbs):
        print(dbs[label].lineage())
    for label in (START, END):
        if not dbs[label].ok:
            print(f"H-A2R: not run ({label} fails the lineage check)")
            return 0
    order = [l for l in sorted(dbs) if dbs[l].ok]

    st = load_strata()
    base = json.loads((here / "quotas.json").read_text())["quota"]
    quota = {s: QUOTA_FACTOR * q for s, q in base.items()}
    refs, stats = draw(dbs[START], st, quota, random.Random(SEED))
    blob = "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in refs).encode()
    (pathlib.Path(a.workdir) / "h-a2r-refs.jsonl").write_bytes(blob)
    print(f"\n== draw (seed {SEED}, K {K})")
    for s in sorted(stats):
        print(f"stratum {s}: {json.dumps(stats[s], sort_keys=True)}")
    print(f"references {len(refs)}; private file h-a2r-refs.jsonl sha256 {hashlib.sha256(blob).hexdigest()}")

    ev = {l: evaluate(dbs[l], refs) for l in order if l != START}
    end = ev[END]
    n = len(refs)
    P = {i for i, e in enumerate(end) if e["present"]}
    tp, np_ = tally(end, P)
    ta, _ = tally(end)

    print("\n== reading (integer comparisons)")
    print(f"primary population: references whose span is still in an active chunk of the end = {np_}/{n}")
    print(f"primary: exposed {tp['exposed']}/{np_} · by id {tp['by_id']}/{np_} · by anchor "
          f"{tp['anchor']}/{np_} (ambiguous {tp['ambiguous']})")
    if np_ < 120 or 10 * tp["exposed"] < np_:
        print("H-A2R primary: not tested (population under 120 or exposure under 10%)")
    else:
        holds = 20 * tp["anchor"] >= 19 * np_ and 10 * (tp["anchor"] - tp["by_id"]) >= np_
        print(f"H-A2R primary: anchor >= 95% and anchor - id >= 10 points -> "
              f"{'holds' if holds else 'does not hold'}")
    print(f"secondary (H-A2 form, all {n}): exposed {ta['exposed']} · by id {ta['by_id']} · by anchor "
          f"{ta['anchor']} (ambiguous {ta['ambiguous']}) · span present anywhere {ta['present']}")
    if 10 * ta["exposed"] < n:
        print("H-A2R secondary: not tested (exposure under 10%)")
    else:
        holds = 20 * ta["anchor"] >= 19 * n and 10 * (ta["anchor"] - ta["by_id"]) >= n
        print(f"H-A2R secondary: anchor >= 95% and anchor - id >= 10 points -> "
              f"{'holds' if holds else 'does not hold'}")

    print("\n== descriptive, no threshold")
    for l in order:
        if l == START:
            continue
        t, _ = tally(ev[l])
        print(f"{l}: by id {t['by_id']} · by anchor {t['anchor']} · present anywhere {t['present']} · "
              f"exposed {t['exposed']} (of {n})")
    for arm in ("by_id", "anchor"):
        first = {}
        for i in range(n):
            lost = next((l for l in order if l != START and not ev[l][i][arm]), None)
            first[lost or "never"] = first.get(lost or "never", 0) + 1
        print(f"first database where {arm} no longer reaches the span: "
              f"{json.dumps(dict(sorted(first.items())))}")
    for s in sorted(quota):
        idx = {i for i, r in enumerate(refs) if r["stratum"] == s}
        t, m = tally(end, idx)
        print(f"end, stratum {s}: n {m} · present {t['present']} · by id {t['by_id']} · by anchor {t['anchor']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
