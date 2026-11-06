#!/usr/bin/env python3
"""Paper D, step 2 (PREREGISTRATION.md §2, §3 and §6): freeze the material and draw the sessions.

  python3 -I d-freeze.py run --host <ssh destination> --private <dir> --exclude-from <smoke select.json>

`run`, on the author's machine, on the tag's UTC date: extracts this directory and lme-run.py from
the tag (`git archive`), copies them to a fresh directory under /var/tmp on the serving host, runs
`host` there, copies the output to <private>/freeze/, deletes the host directory, and runs
`commit`, which writes <private>/FREEZE-COMMITMENT.json. Copy that file into this directory,
commit and push it before d-generate.py runs. The host address is an argument, never a file.

`host`, on the serving host, read-only on production: lists the archive, decompresses the freeze
day's daily-main snapshot next to its output (outside /tmp, deleted at the end), computes the
frame (eligible sessions the distiller logged in the snapshot), shuffles it once with seed
20261106, copies the first 120 sessions of the order (80 drawn plus the 40 the extension may
add), and reads from the snapshot, for those 120, the units production stored, processed_at (the
maximum across agents) and chunks_extracted. Writes a manifest of sha256 per file. Prints counts.

`commit` checks the manifest and that the deployed DISTILL_SYSTEM is C0's text in lme-run.py, and
writes the public commitment: counts, exclusions, seed, and the sha256 of the listing, the order,
the manifest, the production units, the snapshot and the deployed source.

--smoke (with --seed other than 20261106) archives HEAD instead of the tag and skips the date
check; its commitment says smoke and no registered step accepts it.
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dcommon", HERE / "d-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

ARCHIVE = "/var/lib/nox-mem/action-archive"
SNAPDIR = "/var/backups/nox-mem/daily-main"
NOXMEM = "/root/.openclaw/workspace/tools/nox-mem"
SPENT = "/root/medicoes/2026-10-26-memory-tax/replay-set.json"
UNIT_PREFIX = re.compile(r"^\[[^\]|]*\|[^\]]*\]\s*")
LITERAL = re.compile(r"const DISTILL_SYSTEM = `(.*?)`;", re.S)


def band(chars):
    return "<50k" if chars < 50_000 else "50k-200k" if chars < 200_000 else ">=200k"


# ------------------------------------------------------------------ host
def host(a):
    S = C.load("dsel", HERE / "d-select.py")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True)
    (out / "sessions").mkdir()
    seed = a.seed if a.smoke else C.SEED
    if not a.smoke and a.seed not in (None, C.SEED):
        sys.exit("refusing: the registered seed is 20261106")
    snap = a.snapshot or ""
    if a.snapshot_date:
        hits = sorted(glob.glob(os.path.join(a.snapdir, f"daily-main-main-{a.snapshot_date}*.db.gz")))
        if len(hits) != 1:
            sys.exit(f"expected one snapshot of {a.snapshot_date}, found {len(hits)}")
        snap = hits[0]
    if not os.path.isfile(snap):
        sys.exit(f"no snapshot at {snap!r}")        # sqlite3 would create an empty database
    work = pathlib.Path(a.work or out.parent)
    db = work / "snapshot.db"
    try:
        with gzip.open(snap, "rb") as src, open(db, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        log = collections.defaultdict(list)
        for sk, ag, pa, ce, mc in con.execute(
                "SELECT session_key, agent, processed_at, chunks_extracted, message_count "
                "FROM session_distill_log"):
            m = S.UUID.search(sk or "")
            if m:
                log[m.group(1)].append((pa or "", ce or 0, mc or 0))
        # the archive, listed and hashed: every file, the largest copy of each session kept
        listing, best = [], {}
        for p in sorted(glob.glob(os.path.join(a.archive, "*", "*.jsonl"))):
            sz = os.path.getsize(p)
            listing.append(f"{os.path.relpath(p, a.archive)}\t{sz}\n")
            m = S.UUID.search(os.path.basename(p))
            if m and (m.group(1) not in best or sz > best[m.group(1)][1]):
                best[m.group(1)] = (p, sz)
        (out / "listing.tsv").write_text("".join(listing), encoding="utf-8")
        spent = {s["uuid"] for s in json.load(open(a.spent))["sessions"]}
        excl = set(open(a.exclude).read().split())
        c, bands, meta = collections.Counter(), collections.Counter(), {}
        c["archive_sessions"] = len(best)
        for u, (p, _) in sorted(best.items()):
            if u in spent:
                c["excluded_spent"] += 1
                continue
            if u in excl:
                c["excluded_listed"] += 1
                continue
            chars, last = S.scan(p)
            if not (C.START <= last <= a.end and chars >= C.MIN_CHARS):
                continue
            c["eligible"] += 1
            if u not in log:
                c["eligible_never_logged"] += 1
                continue
            meta[u] = {"path": os.path.relpath(p, a.archive), "last_event": last, "prose_chars": chars}
            bands[band(chars)] += 1
        c["frame"] = len(meta)
        order = C.draw(list(meta), seed)
        take = order[:C.N_MAX]
        present = collections.defaultdict(list)
        for cid, sf, text, md, imp, sd in con.execute(
                "SELECT id, source_file, chunk_text, metadata, importance, source_date FROM chunks "
                "WHERE source_file LIKE 'sessions/%'"):
            m = S.UUID.search(sf or "")
            if m:
                present[m.group(1)].append((cid, text, md, imp, sd))
        c["frame_zero_units"] = sum(1 for u in meta if not present.get(u))
        prod = {}
        for u in take:
            units = []
            for cid, text, md, imp, sd in sorted(present.get(u, [])):
                try:
                    cat = json.loads(md or "{}").get("category")
                except Exception:
                    cat = None
                units.append({"id": cid, "text": UNIT_PREFIX.sub("", text or ""), "category": cat,
                              "importance": imp, "source_date": sd})
            prod[u] = {"processed_at": max(x[0] for x in log[u]),
                       "chunks_extracted": sum(x[1] for x in log[u]),
                       "message_count": max(x[2] for x in log[u]), "units": units}
            shutil.copyfile(os.path.join(a.archive, meta[u]["path"]), out / "sessions" / f"{u}.jsonl")
        con.close()
    finally:
        if db.exists():
            db.unlink()
    ts_src = pathlib.Path(a.distill_ts).read_text(encoding="utf-8")
    lit = LITERAL.search(ts_src)
    write = lambda name, obj: (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                                                     encoding="utf-8")
    write("frame.json", {"smoke": a.smoke, "seed": seed, "window": [C.START, a.end],
                         "counts": dict(c), "bands": dict(bands),
                         "order": [dict(uuid=u, **meta[u]) for u in order]})
    write("production.json", prod)
    write("deployed.json", {"session_distill_ts_sha256": C.sha_file(a.distill_ts),
                            "session_distill_js_sha256": C.sha_file(a.distill_js)
                            if os.path.isfile(a.distill_js) else None,
                            "distill_system": lit.group(1) if lit else None})
    write("snapshot.json", {"name": os.path.basename(snap), "sha256": C.sha_file(snap)})
    write("exclude.json", sorted(excl))
    files = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    write("manifest.json", {f: C.sha_file(out / f) for f in files})
    print(json.dumps({"counts": dict(c), "bands": dict(bands), "copied": len(take)}))


# ------------------------------------------------------------------ commit
def commit(a):
    P = C.private(a.private)
    F = P / "freeze"
    man = json.loads((F / "manifest.json").read_text(encoding="utf-8"))
    on_disk = sorted(str(p.relative_to(F)) for p in F.rglob("*") if p.is_file() and p.name != "manifest.json")
    if on_disk != sorted(man):
        sys.exit("refusing: the files on disk are not the manifest's")
    for f, h in man.items():
        if C.sha_file(F / f) != h:
            sys.exit(f"refusing: {f} does not match the manifest")
    frame = json.loads((F / "frame.json").read_text(encoding="utf-8"))
    if frame["smoke"] is not bool(a.smoke):
        sys.exit(f"refusing: the freeze says smoke={frame['smoke']}")
    dep = json.loads((F / "deployed.json").read_text(encoding="utf-8"))
    L = C.load("lme", C.ROOT / "paper3-construction/lme-run.py")
    same = dep["distill_system"] == L.DISTILL_SYSTEM
    order = [o["uuid"] for o in frame["order"]]
    out = {"smoke": bool(a.smoke), "tag": C.TAG, "freeze_date": a.freeze_date,
           "window": frame["window"], "seed": frame["seed"], "min_chars": C.MIN_CHARS,
           "counts": frame["counts"], "bands": frame["bands"], "copied": sum(1 for f in man if f.startswith("sessions/")),
           "listing_sha256": man["listing.tsv"], "order_sha256": C.sha_json(order),
           "frame_sha256": man["frame.json"], "manifest_sha256": C.sha_file(F / "manifest.json"),
           "production_sha256": man["production.json"], "exclude_sha256": man["exclude.json"],
           "snapshot": json.loads((F / "snapshot.json").read_text(encoding="utf-8")),
           "deployed": {"session_distill_ts_sha256": dep["session_distill_ts_sha256"],
                        "session_distill_js_sha256": dep["session_distill_js_sha256"],
                        "distill_system_equals_c0": same,
                        "distill_system_found": dep["distill_system"] is not None}}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"frame {frame['counts'].get('frame')} · copied {out['copied']} · deployed C0 "
          f"{'equal' if same else 'DIFFERS: report it (§2)'} · wrote {a.out}")


# ------------------------------------------------------------------ run
def sh(*args, **kw):
    r = subprocess.run(list(args), capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"{args[0]} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout.strip()


def tag_date(repo):
    s = sh("git", "-C", str(repo), "for-each-ref", "--format=%(taggerdate:iso-strict)",
           f"refs/tags/{C.TAG}")
    if not s:
        sys.exit(f"{C.TAG} is missing or not an annotated tag")
    return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc).date()


def run(a):
    P = C.private(a.private)
    P.mkdir(parents=True, exist_ok=True)
    if (P / "freeze").exists():
        sys.exit(f"refusing: {P / 'freeze'} exists; a freeze is made once")
    repo = C.ROOT
    if a.smoke:
        if a.seed in (None, C.SEED):
            sys.exit("refusing: a smoke freeze needs --seed other than the registered one")
        ref, day = "HEAD", dt.datetime.now(dt.timezone.utc).date()
    else:
        if a.seed not in (None, C.SEED):
            sys.exit("refusing: the registered seed is 20261106")
        sh("git", "-C", str(repo), "fetch", "-q", "--tags", "origin", "main")
        ref, day = C.TAG, tag_date(repo)
        if day != dt.datetime.now(dt.timezone.utc).date():
            sys.exit(f"refusing: the freeze runs on the tag's UTC date ({day}), not today")
    end = (day - dt.timedelta(days=7)).isoformat()
    sel = json.load(open(a.exclude_from))
    excl = "\n".join(sorted(c["uuid"] for c in sel["chosen"])) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        arc = subprocess.run(["git", "-C", str(repo), "archive", ref, C.D, "paper3-construction/lme-run.py"],
                             capture_output=True)
        if arc.returncode:
            sys.exit("git archive failed")
        subprocess.run(["tar", "-x", "-C", tmp], input=arc.stdout, check=True)
        code = pathlib.Path(tmp) / C.D
        (code / "exclude.txt").write_text(excl)
        rem = sh("ssh", "-o", "BatchMode=yes", a.host, "mktemp -d /var/tmp/paper-d-freeze.XXXXXX")
        if not rem.startswith("/var/tmp/paper-d-freeze."):
            sys.exit(f"unexpected remote directory {rem!r}")
        try:
            sh("ssh", "-o", "BatchMode=yes", a.host, f"mkdir {rem}/code")
            sh("scp", "-q", *(str(code / f) for f in ("d-freeze.py", "d-common.py", "d-select.py",
                                                       "exclude.txt")), f"{a.host}:{rem}/code/")
            cmd = (f"python3 -I {rem}/code/d-freeze.py host --out {rem}/out --end {end} "
                   f"--snapshot-date {day.strftime('%Y%m%d')} --exclude {rem}/code/exclude.txt")
            if a.smoke:
                cmd += f" --smoke --seed {a.seed}"
            if a.host_extra:                    # tests only: point the host at synthetic paths
                if not a.smoke:
                    sys.exit("refusing: --host-extra is for smoke runs")
                cmd += " " + a.host_extra
            print(sh("ssh", "-o", "BatchMode=yes", a.host, cmd))
            sh("scp", "-q", "-r", f"{a.host}:{rem}/out", str(P / "freeze"))
        finally:
            subprocess.run(["ssh", "-o", "BatchMode=yes", a.host, f"rm -rf {rem}"], capture_output=True)
        os.chmod(P, 0o700)
        r = subprocess.run([sys.executable, "-I", str(code / "d-freeze.py"), "commit", "--private", str(P),
                            "--out", str(P / "FREEZE-COMMITMENT.json"), "--freeze-date", day.isoformat()]
                           + (["--smoke"] if a.smoke else []))
        if r.returncode:
            sys.exit(r.returncode)
    print(f"next: cp {P / 'FREEZE-COMMITMENT.json'} {C.D}/ ; commit; push; then d-generate.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "host", "commit"))
    ap.add_argument("--host")
    ap.add_argument("--private")
    ap.add_argument("--exclude-from")
    ap.add_argument("--out")
    ap.add_argument("--end")
    ap.add_argument("--freeze-date")
    ap.add_argument("--archive", default=ARCHIVE)
    ap.add_argument("--snapshot")
    ap.add_argument("--snapshot-date")
    ap.add_argument("--snapdir", default=SNAPDIR)
    ap.add_argument("--host-extra")
    ap.add_argument("--work")
    ap.add_argument("--spent", default=SPENT)
    ap.add_argument("--exclude")
    ap.add_argument("--distill-ts", default=f"{NOXMEM}/src/session-distill.ts")
    ap.add_argument("--distill-js", default=f"{NOXMEM}/dist/session-distill.js")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    {"run": run, "host": host, "commit": commit}[a.mode](a)
