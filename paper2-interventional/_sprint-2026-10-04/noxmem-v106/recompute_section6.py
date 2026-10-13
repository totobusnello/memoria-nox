#!/usr/bin/env python3
"""Recompute every Section 6 value that per-query outputs support, under the legacy
scorer (report v1.0.5: each occurrence of a relevant id credited) and under the fixed
scorer (report v1.0.6: each retrieved id credited once, at its first rank, no re-padding),
and check each against the values printed in the version that used it.

Read-only on every input. Writes only under this directory (nothing with --check):

    out/section6-old-vs-new.json       the 135 checks, v1.0.5 vs v1.0.6, + changed rows
    out/duplicate-census.json          per output file: queries repeating an id in the top 10
    aggregates/<run>/_aggregate.{json,md}   regenerated with the fixed scorer

The legacy zip is extracted to a temporary directory that is removed on exit.

Inputs and how each is pinned
-----------------------------
  local originals  eval/q4-comparison/output/rc4{,-ablation}/*.json   sha256 == MANIFESTO-LASTRO.json
                   eval/q4-comparison/output/{nox_mem,mem0,zep}.json,
                   eval/q4-comparison/output-2026-09-10/*.json         sha256 == payload PROVENANCE.json
  v1.0.6 payload   noxmem-evidence/payload/**                          sha256 == payload SHA256SUMS
  v1.0.5 record    noxmem-v106/legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip
                   (the dataset as built before the scorer fix; its scripts/aggregate.py is the
                   legacy scorer and its verify_dataset.py carries the v1.0.5 printed values)
                                                                      sha256 == the zip's SHA256SUMS
  fixed scorer     eval/q4-comparison/aggregate.py (== payload/scripts/aggregate.py, checked)

Why the legacy zip lives in legacy-input/: the zip at noxmem-evidence/ was regenerated with
the fixed scorer on 2026-10-04. Reading the "legacy" scorer from it compared v1.0.6 with
itself, reported zero changes and labelled the result v1.0.5 (finding Codex 1, 2026-10-04).

Legs; any failure exits 1 (and, without --check, the report records the failures):
  (A) v1.0.5: the legacy scorer differs from the fixed one (bytes); the legacy record's
      stored per-query metrics equal the legacy scorer; all 135 checks of the legacy
      verifier equal the v1.0.5 printed values; rebuilding the run-time aggregates of the
      local originals with the legacy scorer is byte-identical to the pinned files;
  (B) v1.0.6: the payload's stored per-query metrics equal the fixed scorer, none exceeds 1;
      all 135 checks of the payload verifier equal the v1.0.6 printed values; the fixed
      rebuild of the rc4 and ablation aggregates equals the payload's shipped files;
  (C) cross: both verifiers hold the same 135 check ids; the retrieved ids and gold ids of
      every query are identical in the two records (only stored metrics may differ); the
      printed values differ between v1.0.5 and v1.0.6 on exactly EXPECTED_CHANGED, and the
      two scorers give different printed values on exactly that set.

    python3 paper2-interventional/_sprint-2026-10-04/noxmem-v106/recompute_section6.py [--check]
"""
from __future__ import annotations

import argparse
import ast
import copy
import glob
import hashlib
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
Q4 = ROOT / "eval" / "q4-comparison"
EVID = HERE.parent / "noxmem-evidence"
PAY = EVID / "payload"
LEGACY_ZIP = HERE / "legacy-input" / "nox-mem-section6-evidence-1.0.0.v105-scorer.zip"
OUT = HERE / "out"
AGG_OUT = HERE / "aggregates"
K = 10

# The ten checks (nine distinct values; R11 and A05 are the same number) that the scorer
# correction changed at printed precision. SCORER-FIX.md section 4, dataset README table.
EXPECTED_CHANGED = {"R07", "R08", "R11", "A05", "R17", "E10", "C13", "C14", "C18", "C19"}
PAYLOAD_RUN_DIRS = {"rc4": "rc4-2026-06-29", "rc4-ablation": "rc4-ablation-2026-06-29",
                    "2026-09-10": "2026-09-10"}

fails: list[str] = []


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_module(name: str, path: Path, scripts_dir: Path | None = None):
    """Load a module from a path. A verifier does `from aggregate import ...` at import time,
    so the cached `aggregate` is dropped and its own scripts/ directory is put first."""
    if scripts_dir is not None:
        sys.modules.pop("aggregate", None)
        sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    finally:
        if scripts_dir is not None:
            sys.path.remove(str(scripts_dir))
            sys.modules.pop("aggregate", None)
    return mod


def read_sums(path: Path) -> dict[str, str]:
    sums = {}
    for line in path.read_text().splitlines():
        if line.strip():
            h, n = line.split(None, 1)
            sums[n.strip()] = h
    return sums


# ------------------------------------------------------------------ pin the inputs
def pin_inputs() -> dict:
    rec: dict = {}
    man = json.loads((Q4 / "MANIFESTO-LASTRO.json").read_text())["artefatos"]
    for rel, v in man.items():
        if "/output/" in rel and rel.endswith(".json"):
            got = sha((ROOT / rel).read_bytes())
            rec[rel] = {"pinned_by": "MANIFESTO-LASTRO.json", "ok": got == v["sha256"]}
            if got != v["sha256"]:
                fails.append(f"{rel}: sha256 differs from MANIFESTO-LASTRO.json")
    prov = json.loads((PAY / "PROVENANCE.json").read_text())["files"]
    for k, v in prov.items():
        if not k.startswith("runs/"):
            continue
        got = sha((ROOT / v["original_path"]).read_bytes())
        rec.setdefault(v["original_path"], {"pinned_by": "payload PROVENANCE.json"})
        rec[v["original_path"]]["ok_provenance"] = got == v["original_sha256"]
        if got != v["original_sha256"]:
            fails.append(f"{v['original_path']}: sha256 differs from PROVENANCE.json")
    for n, h in read_sums(PAY / "SHA256SUMS").items():
        ok = sha((PAY / n).read_bytes()) == h
        if n.startswith("runs/") or n in ("verify_dataset.py", "scripts/aggregate.py"):
            rec["payload/" + n] = {"pinned_by": "payload SHA256SUMS", "ok": ok}
        if not ok:
            fails.append(f"payload/{n}: sha256 differs from SHA256SUMS")
    return rec


def extract_legacy(dest: Path) -> Path:
    """Extract the v1.0.5-scorer record and check every member against its own SHA256SUMS."""
    with zipfile.ZipFile(LEGACY_ZIP) as z:
        root = z.namelist()[0].split("/")[0]
        z.extractall(dest)
    base = dest / root
    for n, h in read_sums(base / "SHA256SUMS").items():
        if sha((base / n).read_bytes()) != h:
            fails.append(f"legacy zip: {n} does not match the zip's SHA256SUMS")
    return base


def stored_vs(VD, S, label: str) -> int:
    """Stored per-query metrics of a record == the scorer that record claims to use."""
    n = 0
    for g in ("SM", "RC", "AB", "NT"):
        for name, p in getattr(VD, g).items():
            for q in p["queries"]:
                gold = set(q.get("gold_chunk_ids") or [])
                if not gold:
                    continue
                i = VD.ids(q)
                got = (S.ndcg_at_k(i, gold, K), S.recall_at_k(i, gold, K), S.reciprocal_rank(i, gold))
                m = q["metrics"]
                if (m["ndcg@10"], m["recall@10"], m["rr"]) != got:
                    fails.append(f"{label} {g}/{name} {q['question_id']}: stored metric != scorer")
                n += 1
    return n


def evaluate(VD, S) -> dict:
    """Rescore every query of VD's data with scorer S, swap VD's globals, run its 135 checks."""
    base = {name: copy.deepcopy(getattr(VD, name)) for name in ("SM", "RC", "AB", "NT")}
    for d in base.values():
        for p in d.values():
            for q in p["queries"]:
                gold = set(q.get("gold_chunk_ids") or [])
                if gold:
                    i = VD.ids(q)
                    q["metrics"] = {"ndcg@10": S.ndcg_at_k(i, gold, K),
                                    "recall@10": S.recall_at_k(i, gold, K),
                                    "rr": S.reciprocal_rank(i, gold)}
    saved = {name: getattr(VD, name) for name in ("SM", "RC", "AB", "NT", "AGG", "CN", "CM", "CA")
             if hasattr(VD, name)}
    try:
        for name, d in base.items():
            setattr(VD, name, d)
        VD.AGG = {"rc4n": S.score_system(VD.RC["nox_mem"], K), "rc4m": S.score_system(VD.RC["mem0"], K),
                  "abn": S.score_system(VD.AB["nox_mem"], K), "abm": S.score_system(VD.AB["mem0"], K),
                  "ev": S.score_system(VD.NT["evermind"], K), "zp": S.score_system(VD.NT["zep"], K),
                  "smn": S.score_system(VD.SM["nox_mem"], K), "smm": S.score_system(VD.SM["mem0"], K)}
        VD.CN, VD.CM, VD.CA = VD.cats(VD.RC["nox_mem"]), VD.cats(VD.RC["mem0"]), VD.cats(VD.AB["nox_mem"])
        rows = {}
        for i, sec, what, paper, rule, quotes, fn in VD.N:
            raw = fn()
            ok, shown = VD.compare(paper, rule, raw)
            rows[i] = {"section": sec, "quantity": what, "paper": paper, "rule": rule,
                       "ok_vs_paper": ok, "shown": shown.split(" (raw")[0],
                       "raw": raw if isinstance(raw, (int, float, str, bool)) else str(raw)}
        over = [(g, n, q["question_id"]) for g, d in base.items() for n, p in d.items() for q in p["queries"]
                if q.get("metrics", {}).get("ndcg@10") is not None
                and (q["metrics"]["ndcg@10"] > 1 + 1e-12 or q["metrics"]["recall@10"] > 1)]
        return {"rows": rows, "over_one": over, "agg": copy.deepcopy(VD.AGG)}
    finally:
        for name, v in saved.items():
            setattr(VD, name, v)


def strip_metrics(VD) -> dict:
    out = {}
    for g in ("SM", "RC", "AB", "NT"):
        for name, p in getattr(VD, g).items():
            out[f"{g}/{name}"] = [(q["question_id"], VD.ids(q), sorted(q.get("gold_chunk_ids") or []))
                                  for q in p["queries"]]
    return out


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="run every leg and write nothing")
    args = ap.parse_args()

    pins = pin_inputs()
    fixed_path = Q4 / "aggregate.py"
    if fixed_path.read_bytes() != (PAY / "scripts" / "aggregate.py").read_bytes():
        fails.append("harness aggregate.py and payload/scripts/aggregate.py differ")
    if not LEGACY_ZIP.is_file():
        print(f"FAIL: legacy record missing: {LEGACY_ZIP}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="v105-record-") as tmp:
        legacy_dir = extract_legacy(Path(tmp))
        legacy_scorer = legacy_dir / "scripts" / "aggregate.py"
        if legacy_scorer.read_bytes() == fixed_path.read_bytes():
            fails.append("legacy scorer is byte-identical to the fixed scorer: legacy-input/ is not the v1.0.5 record")
        LEG = load_module("aggregate_legacy", legacy_scorer)
        FIX = load_module("aggregate_fixed", fixed_path)
        VD5 = load_module("verify_dataset_v105", legacy_dir / "verify_dataset.py", legacy_dir / "scripts")
        VD6 = load_module("verify_dataset_v106", PAY / "verify_dataset.py", PAY / "scripts")

        # (C) same checks, same retrieved ids
        ids5 = [r[0] for r in VD5.N]
        ids6 = [r[0] for r in VD6.N]
        if ids5 != ids6:
            fails.append(f"the two verifiers hold different check ids: {sorted(set(ids5) ^ set(ids6))}")
        if strip_metrics(VD5) != strip_metrics(VD6):
            fails.append("retrieved or gold ids differ between the v1.0.5 record and the v1.0.6 payload")

        # (A) and (B): stored metrics agree with the scorer each record claims
        n5 = stored_vs(VD5, LEG, "v1.0.5 record")
        n6 = stored_vs(VD6, FIX, "v1.0.6 payload")

        old, new = evaluate(VD5, LEG), evaluate(VD6, FIX)
        cross_old_rule_on_new_table = evaluate(VD6, LEG)  # legacy scorer, v1.0.6 table

    bad_old = [i for i, r in old["rows"].items() if not r["ok_vs_paper"]]
    bad_new = [i for i, r in new["rows"].items() if not r["ok_vs_paper"]]
    if bad_old:
        fails.append(f"legacy scorer does not reproduce the v1.0.5 printed values on: {bad_old}")
    if bad_new:
        fails.append(f"fixed scorer does not reproduce the v1.0.6 printed values on: {bad_new}")
    if new["over_one"]:
        fails.append(f"fixed scorer still scores > 1 on {new['over_one']}")
    if not old["over_one"]:
        fails.append("legacy scorer scores no query above 1: it is not the v1.0.5 rule")

    printed_changed = {i for i in ids6 if i in old["rows"] and old["rows"][i]["paper"] != new["rows"][i]["paper"]}
    scorer_changed = {i for i in ids6 if cross_old_rule_on_new_table["rows"][i]["shown"] != new["rows"][i]["shown"]}
    if printed_changed != EXPECTED_CHANGED:
        fails.append(f"printed values changed v1.0.5 -> v1.0.6 on {sorted(printed_changed)}, "
                     f"expected {sorted(EXPECTED_CHANGED)}")
    if scorer_changed != EXPECTED_CHANGED:
        fails.append(f"legacy vs fixed scorer differ at printed precision on {sorted(scorer_changed)}, "
                     f"expected {sorted(EXPECTED_CHANGED)}")

    changed = [{"id": i, "section": new["rows"][i]["section"], "quantity": new["rows"][i]["quantity"],
                "paper_v105": old["rows"][i]["paper"], "paper_v106": new["rows"][i]["paper"],
                "legacy_scorer": old["rows"][i]["shown"], "fixed_scorer": new["rows"][i]["shown"],
                "old_raw": old["rows"][i]["raw"], "new_raw": new["rows"][i]["raw"]}
               for i in ids6 if i in printed_changed]

    # ---------------- duplicate census over every local output with per-query results
    def L(v):
        if isinstance(v, list):
            return v
        if v in (None, "", "None"):
            return []
        return ast.literal_eval(v)

    census = {}
    files = sorted(set(glob.glob(str(Q4 / "output" / "*.json")) + glob.glob(str(Q4 / "output" / "rc4*" / "*.json"))
                       + glob.glob(str(Q4 / "output-2026-09-10" / "*.json"))))
    for f in files:
        if "/_aggregate" in f or f.endswith(".dry-run.json"):
            continue
        d = json.loads(Path(f).read_text())
        qs = d.get("queries") if isinstance(d, dict) else None
        if not qs:
            continue
        rep, repg, examples = 0, 0, []
        for q in qs:
            r = [str(x.get("id") or "") for x in L(q.get("results"))][:K]
            if len(r) != len(set(r)):
                rep += 1
                g = set(L(q.get("gold_chunk_ids")))
                dup = sorted({x for x in r if r.count(x) > 1})
                if g & set(dup):
                    repg += 1
                    examples.append({"question_id": q.get("question_id"), "dataset": q.get("dataset"),
                                     "repeated_gold": sorted(g & set(dup)),
                                     "ndcg_legacy": round(LEG.ndcg_at_k(r, g, K), 4),
                                     "ndcg_fixed": round(FIX.ndcg_at_k(r, g, K), 4),
                                     "recall_legacy": LEG.recall_at_k(r, g, K),
                                     "recall_fixed": FIX.recall_at_k(r, g, K)})
        census[str(Path(f).relative_to(ROOT))] = {"system": (d.get("meta") or {}).get("system"),
                                                   "n_queries": len(qs), "top10_repeat_any_id": rep,
                                                   "top10_repeat_gold_id": repg, "gold_examples": examples}

    # ---------------- aggregates: legacy rebuild == pinned run-time file; fixed == payload file
    runs = {"rc4": Q4 / "output" / "rc4", "rc4-ablation": Q4 / "output" / "rc4-ablation",
            "2026-09-10": Q4 / "output-2026-09-10"}
    agg_report, agg_fixed = {}, {}
    for run, src in runs.items():
        payloads = [json.loads(p.read_text()) for p in sorted(src.glob("*.json"))
                    if not p.name.startswith("_") and not p.name.endswith(".dry-run.json")]

        def build(S):
            summ = [S.score_system(x, K) for x in payloads]
            summ.sort(key=lambda s: s["overall"]["ndcg@k"], reverse=True)
            return json.dumps({"k": K, "systems": summ}, indent=2), S.render_markdown(summ, K)

        lj, lm = build(LEG)
        pinned_j, pinned_m = (src / "_aggregate.json").read_text(), (src / "_aggregate.md").read_text()
        legacy_equal = (lj == pinned_j, lm == pinned_m)
        if not all(legacy_equal):
            fails.append(f"{run}: legacy rebuild != pinned run-time _aggregate (json {legacy_equal[0]}, md {legacy_equal[1]})")
        fj, fm = build(FIX)
        shipped = PAY / "runs" / PAYLOAD_RUN_DIRS[run]
        fixed_eq_payload = (fj == (shipped / "_aggregate.json").read_text(),
                            fm == (shipped / "_aggregate.md").read_text())
        if not all(fixed_eq_payload):
            fails.append(f"{run}: fixed rebuild != payload runs/{PAYLOAD_RUN_DIRS[run]}/_aggregate "
                         f"(json {fixed_eq_payload[0]}, md {fixed_eq_payload[1]})")
        agg_fixed[run] = (fj, fm)
        agg_report[run] = {"source_dir": str(src.relative_to(ROOT)),
                           "legacy_rebuild_byte_identical_to_pinned_runtime": {"json": legacy_equal[0], "md": legacy_equal[1]},
                           "fixed_rebuild_byte_identical_to_payload": {"json": fixed_eq_payload[0], "md": fixed_eq_payload[1]},
                           "fixed_identical_to_pinned_runtime": {"json": fj == pinned_j, "md": fm == pinned_m},
                           "pinned_sha256": {"json": sha(pinned_j.encode()), "md": sha(pinned_m.encode())},
                           "fixed_sha256": {"json": sha(fj.encode()), "md": sha(fm.encode())}}

    report = {
        "what": "Section 6 values: legacy scorer (report v1.0.5) vs fixed scorer (v1.0.6, each id credited once)",
        "k": K,
        "legacy_record": str(LEGACY_ZIP.relative_to(ROOT)),
        "legacy_record_sha256": sha(LEGACY_ZIP.read_bytes()),
        "input_pins": pins,
        "stored_metrics_checked": {"v105_record": n5, "v106_payload": n6},
        "legacy_reproduces_v105": not bad_old,
        "fixed_reproduces_v106": not bad_new,
        "n_checks": len(new["rows"]),
        "expected_changed": sorted(EXPECTED_CHANGED),
        "n_changed_at_printed_precision": len(changed),
        "changed": changed,
        "fixed_over_one": new["over_one"],
        "legacy_over_one": old["over_one"],
        "checks": {i: {"section": new["rows"][i]["section"], "quantity": new["rows"][i]["quantity"],
                       "paper_v105": old["rows"][i]["paper"], "legacy_scorer": old["rows"][i]["shown"],
                       "paper_v106": new["rows"][i]["paper"], "fixed_scorer": new["rows"][i]["shown"]}
                   for i in ids6},
        "aggregates": agg_report,
        "headline_fixed": {k: {"overall": v["overall"], "per_dataset": v["per_dataset"]} for k, v in new["agg"].items()},
        "headline_legacy": {k: {"overall": v["overall"], "per_dataset": v["per_dataset"]} for k, v in old["agg"].items()},
        "fails": fails,
    }
    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)
        for run, (fj, fm) in agg_fixed.items():
            dest = AGG_OUT / run
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "_aggregate.json").write_text(fj)
            (dest / "_aggregate.md").write_text(fm)
        (OUT / "section6-old-vs-new.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
        (OUT / "duplicate-census.json").write_text(json.dumps(census, indent=2, ensure_ascii=False) + "\n")

    print(f"inputs pinned: {sum(1 for v in pins.values() if v.get('ok', v.get('ok_provenance')))} / {len(pins)}")
    print(f"stored metrics: v1.0.5 record == legacy scorer ({n5} queries); v1.0.6 payload == fixed scorer ({n6})")
    print(f"legacy reproduces v1.0.5: {not bad_old}; fixed reproduces v1.0.6: {not bad_new} ({len(new['rows'])} checks)")
    print(f"queries scored above 1: legacy {len(old['over_one'])}, fixed {len(new['over_one'])}")
    print(f"changed at printed precision: {len(changed)} (expected {len(EXPECTED_CHANGED)})")
    for c in changed:
        print(f"  {c['id']:5} §{c['section']:8} {c['quantity'][:52]:52} {c['paper_v105']:>8} -> {c['paper_v106']}")
    for run, a in agg_report.items():
        print(f"  aggregates/{run}: legacy==pinned run-time {a['legacy_rebuild_byte_identical_to_pinned_runtime']}, "
              f"fixed==payload {a['fixed_rebuild_byte_identical_to_payload']}")
    print("mode: --check (nothing written)" if args.check else "wrote out/ and aggregates/")
    if fails:
        print("FAIL:\n  " + "\n  ".join(fails), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
