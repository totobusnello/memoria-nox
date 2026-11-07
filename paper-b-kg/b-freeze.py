#!/usr/bin/env python3
"""Paper B, step 1 (PREREGISTRATION.md §3, §7.1): the draw and the freeze.

  python3 -I b-freeze.py --snapshot <file.db.gz> --db <snapshot.db> --private <dir>

Refuses unless the tag `paper-b-prereg-v1.0` is on the public main branch and carries no
commitment, and unless the gz's sha256 is the snapshot §2 names (`--db` must be its gunzip; the
population count is checked against the census). The seed is the first eight hex digits of the
tag commit. Draws n = 300 uniformly over the relations with live evidence, ordered by id, and 30
of them (seed + 3) for the mismatched-evidence control, each paired with a live chunk from a
different document.

Writes <dir>/freeze.json (private: triples, chunk text, mode 600) and FREEZE-COMMITMENT.json next
to this script (counts, seed and hashes only). Commit and push the commitment, alone, before
b-judge.py.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bcommon", HERE / "b-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
CENSUS = C.load("bcensus", HERE / "b-census.py")


def freeze(con, seed):
    """The frozen material for a given seed: no git, no I/O beyond the read-only connection."""
    pop = C.population(con)
    if len(pop) != C.POPULATION:
        raise SystemExit(f"population {len(pop)} is not the census's {C.POPULATION}")
    ids = C.draw(pop, seed)
    rows = [C.row(con, i, CENSUS.bucket) for i in ids]
    mm = []
    for rid in C.mismatch_ids(ids, seed):
        own = next(r for r in rows if r["relation_id"] == rid)
        oc = C.other_chunk(con, rid, own["source_file"], seed)
        mm.append({"relation_id": rid, "chunk_id": oc["chunk_id"], "source_file": oc["source_file"],
                   "bucket": CENSUS.bucket(oc["source_file"]), "chunk_text": oc["chunk_text"] or ""})
    return {"seed": seed, "population": len(pop), "sample": rows, "mismatch": mm}


def commitment(fz, tag, tag_commit, body):
    return {
        "step": "FREEZE", "tag": tag, "tag_commit": tag_commit, "seed": fz["seed"],
        "snapshot_name": C.SNAPSHOT_NAME, "snapshot_sha256": C.SNAPSHOT_SHA256,
        "population": fz["population"], "n_sample": len(fz["sample"]),
        "n_mismatch": len(fz["mismatch"]),
        "sample_ids_sha256": C.sha_json([r["relation_id"] for r in fz["sample"]]),
        "mismatch_pairs_sha256": C.sha_json([[m["relation_id"], m["chunk_id"]] for m in fz["mismatch"]]),
        "sample_by_bucket": dict(collections.Counter(r["bucket"] for r in fz["sample"]).most_common()),
        "sample_by_reason": dict(collections.Counter(str(r["relation_reason"])
                                                     for r in fz["sample"]).most_common()),
        "sample_with_marker": dict(collections.Counter(str(C.marker(r["chunk_text"][:C.CHUNK_CHARS]))
                                                       for r in fz["sample"]).most_common()),
        "freeze_json_sha256": C.sha_bytes(body.encode("utf-8")),
        "script_sha256": {p: C.sha_file(HERE / p) for p in ("b-common.py", "b-freeze.py", "b-census.py")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--private", required=True)
    a = ap.parse_args()
    P = C.private(a.private)
    out = P / "freeze.json"
    if out.exists():
        sys.exit(f"refusing: {out} exists; the freeze runs once")
    if pathlib.Path(a.snapshot).name != C.SNAPSHOT_NAME:
        sys.exit("refusing: the snapshot file is not the one §2 names")
    got = C.sha_file(a.snapshot)
    if got != C.SNAPSHOT_SHA256:
        sys.exit(f"refusing: snapshot sha256 {got[:12]} is not the registered one")
    t = C.tag_commit(C.ROOT)
    fz = freeze(C.ro(a.db), C.seed_of(t))
    body = json.dumps(fz, ensure_ascii=False, indent=1)
    C.write_private(out, body)
    C.write_public(HERE / "FREEZE-COMMITMENT.json", commitment(fz, C.TAG, t, body))
    print(f"seed {fz['seed']} · sample {len(fz['sample'])} · mismatch {len(fz['mismatch'])} "
          f"· freeze.json sha256 {C.sha_bytes(body.encode('utf-8'))[:12]}")
    print("next: commit FREEZE-COMMITMENT.json alone, merge to main, then b-judge.py --freeze-ref <commit>")


if __name__ == "__main__":
    main()
