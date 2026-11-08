#!/usr/bin/env python3
"""C2 shadow study, step 3 (SHADOW-PREREGISTRATION.md §2 and §6): freeze the eligible records.

  python3 -I s-freeze.py select --src <shadow directory> --out <dir>
  python3 -I s-freeze.py commit --private <dir> --repo <clone>
  (smoke: select ... --smoke --today YYYY-MM-DD ; commit ... --smoke --seed N)

`select`, where the shadow files are: recomputes the stopping rule of §2 from the files (the same
code as s-count.py), refuses unless the freeze is due, and copies the eligible records dated from
2026-11-08 to the freeze date, byte for byte and one file per date, into <out>/records/. Writes
<out>/freeze.json (counts, the date range, the stopping rule, the sha256 of every source file read,
never text) and <out>/manifest.json (sha256 of every file written). <out> must not exist and must
not be inside a git repository; it is made with mode 700 and its files 600. Prints counts only.

The author then copies <out> to <private>/freeze under ~/Backups/ (§2); this script does not move
material between machines.

`commit`, on the author's machine: refuses unless <private> is under ~/Backups/ (not in smoke),
the manifest matches every frozen file, every frozen record is eligible and inside the date range,
and the tag is on the public history with no commitment of this study in it. Writes
<private>/SHADOW-FREEZE-COMMITMENT.json: counts, the date range, the seed and its source (§3), the
sha256 of every source file and every frozen file. Copy it into this directory, commit and push it
before s-generate.py runs.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


# ------------------------------------------------------------------ select
def select(a):
    if a.today and not a.smoke:
        sys.exit("refusing: --today is for smoke runs; the freeze uses today's UTC date")
    today = a.today or C.utc_today()
    out = C.private(a.out)
    if out.exists():
        sys.exit(f"refusing: {out} exists; a freeze is made once")
    src = pathlib.Path(a.src)
    excluded = C.excluded_keys(src)
    try:
        per, kept, other = C.scan(src, today, excluded)
    except Exception as e:
        sys.exit(f"s-freeze select failed: {type(e).__name__}")
    stop = C.stopping(per, today)
    if not stop["due"]:
        sys.exit(f"refusing: the freeze is not due (threshold met: {stop['threshold_met']}, "
                 f"freeze date: {stop['freeze_date']}, today {today})")
    end = stop["freeze_date"]
    per = C.cumulate(per, end)
    old = os.umask(0o077)
    try:
        (out / "records").mkdir(parents=True)
        sessions = set()
        for date, rows in sorted(kept.items()):
            if date > end or not rows:
                continue
            body = b"".join(raw + b"\n" for _, raw, _ in rows)
            (out / "records" / f"c2-shadow-{date}.jsonl").write_bytes(body)
            sessions |= {C.r_session(o) for _, _, o in rows}
        sources = {p.name: C.sha_file(p) for d, p in C.shadow_files(src) if C.START <= d <= end}
        freeze = {"smoke": bool(a.smoke), "select_date": today, "window": [C.START, end],
                  "stopping": stop, "per_date": per,
                  "totals": {"records": sum(c["records"] for c in per.values()),
                             "c2_failures": sum(c["c2_failures"] for c in per.values()),
                             "eligible_blocks": sum(c["eligible_blocks"] for c in per.values()),
                             "eligible_sessions": len(sessions),
                             "excluded": {k: sum(c["excluded"][k] for c in per.values()) for k in C.REASONS}},
                  "other_files": other,
                  "excluded_file": {"name": C.EXCLUDED_FILE, "sha256": C.sha_file(src / C.EXCLUDED_FILE),
                                    "sessions": C.EXCLUDED_SESSIONS, "blocks": C.EXCLUDED_BLOCKS},
                  "source_files_sha256": sources,
                  "registered": {"c2_prompt_sha256": C.C2_PROMPT_SHA256, "min_block_chars": C.MIN_BLOCK_CHARS},
                  "script_sha256": {f: C.sha_file(HERE / f) for f in ("s-freeze.py", "s-common.py", "d-common.py")}}
        (out / "freeze.json").write_text(json.dumps(freeze, indent=1, sort_keys=True), encoding="utf-8")
        files = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
        (out / "manifest.json").write_text(json.dumps({f: C.sha_file(out / f) for f in files}, indent=1),
                                           encoding="utf-8")
    finally:
        os.umask(old)
    C.lock_down(out)
    t = freeze["totals"]
    print(f"window {C.START}..{end}{' (SHORTFALL)' if stop['shortfall'] else ''} · records {t['records']} · "
          f"eligible blocks {t['eligible_blocks']} from {t['eligible_sessions']} sessions · "
          f"excluded {t['excluded']}")
    print(f"next: copy {out} to <private>/freeze under ~/Backups/, then s-freeze.py commit")


# ------------------------------------------------------------------ commit
def under_backups(P):
    base = pathlib.Path(os.path.expanduser("~/Backups")).resolve()
    return base in pathlib.Path(P).resolve().parents


def commit(a):
    P = C.private(a.private)
    if not a.smoke and not under_backups(P):
        sys.exit("refusing: the private directory is not under ~/Backups/ (§2)")
    F = P / "freeze"
    man = C.check_manifest(F)
    fz = json.loads((F / "freeze.json").read_text(encoding="utf-8"))
    if fz["smoke"] is not bool(a.smoke):
        sys.exit(f"refusing: the freeze says smoke={fz['smoke']}")
    lo, hi = fz["window"]
    if lo != C.START or not fz["stopping"]["due"] or hi != fz["stopping"]["freeze_date"]:
        sys.exit("refusing: the freeze window is not the stopping rule's")
    # every frozen record is eligible, inside the window, and the counts are the files'
    sessions, n = set(), 0
    for bid, date, o in C.frozen_records(F):
        ok, why = C.eligible(o, set())
        if not ok or not (lo <= date <= hi):
            sys.exit(f"refusing: frozen record {bid} is not eligible ({why or 'outside the window'})")
        n += 1
        sessions.add(C.r_session(o))
    if (n, len(sessions)) != (fz["totals"]["eligible_blocks"], fz["totals"]["eligible_sessions"]):
        sys.exit("refusing: the frozen records are not the counts freeze.json reports")
    if a.smoke:
        if a.seed is None:
            sys.exit("refusing: a smoke commitment needs --seed")
        tag_commit, seed = None, a.seed
    else:
        if a.seed is not None:
            sys.exit("refusing: the registered seed comes from the tag commit (§3)")
        C.DC.ordered(a.repo, [])            # the tag exists and carries no commitment of this study
        C.same_as_tag(a.repo)
        tag_commit = C.commit_of(a.repo, C.TAG)
        seed = C.tag_seed(a.repo)          # §10: the registered seed, not this tag commit's digits
    out = {"smoke": bool(a.smoke), "tag": C.TAG, "tag_commit": tag_commit, "seed": seed,
           "seed_source": "smoke --seed" if a.smoke else "registered (§3, §10): int('6ac8272d', 16), the original v1.0 tag commit",
           "secondary_seed": seed + 1, "window": fz["window"], "select_date": fz["select_date"],
           "stopping": fz["stopping"], "totals": fz["totals"], "per_date": fz["per_date"],
           "other_files": fz["other_files"], "excluded_file": fz["excluded_file"],
           "registered": fz["registered"], "source_files_sha256": fz["source_files_sha256"],
           "frozen_files_sha256": {f: h for f, h in man.items() if f.startswith("records/")},
           "freeze_json_sha256": man["freeze.json"], "manifest_sha256": C.sha_file(F / "manifest.json"),
           "script_sha256": {f: C.sha_file(HERE / f) for f in ("s-freeze.py", "s-common.py", "d-common.py")}}
    C.write_private(P / "SHADOW-FREEZE-COMMITMENT.json", json.dumps(out, indent=1) + "\n")
    C.lock_down(P)
    print(f"window {fz['window'][0]}..{fz['window'][1]} · eligible blocks {n} from {len(sessions)} sessions"
          f"{' · SHORTFALL' if fz['stopping']['shortfall'] else ''} · seed {seed}")
    print(f"next: cp {P / 'SHADOW-FREEZE-COMMITMENT.json'} {C.D}/ ; commit; push; then s-generate.py")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("select", "commit"))
    ap.add_argument("--src")
    ap.add_argument("--out")
    ap.add_argument("--private")
    ap.add_argument("--repo", default=str(C.ROOT))
    ap.add_argument("--today")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.mode == "select":
        if not (a.src and a.out):
            sys.exit("select needs --src and --out")
        select(a)
    else:
        if not a.private:
            sys.exit("commit needs --private")
        commit(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
