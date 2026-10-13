#!/usr/bin/env python3
"""Builds payload/ from the repository's Q4 artifacts. Read-only on the repository.

- checks every unversioned input against MANIFESTO-LASTRO.json (sha256) before use;
- strips per-query outputs with payload/scripts/strip_outputs.py;
- exports id-only censuses of the three stores (no text), from copies of the DBs
  in a scratch directory (opened immutable; sha256 re-checked after the read);
- copies scripts verbatim, the aggregates, the manifest, and a path-redacted run log.
Usage: python3 build_payload.py SCRATCH_DIR
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAY = HERE / "payload"
REPO = HERE.parents[2]
Q4 = REPO / "eval" / "q4-comparison"
SCR = Path(sys.argv[1])
sys.path.insert(0, str(PAY / "scripts"))

REDACT = [(str(REPO) + "/", "<repo>/"), (str(Path.home()) + "/", "<home>/")]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


man = json.loads((Q4 / "MANIFESTO-LASTRO.json").read_text())["artefatos"]


def checked(rel: str) -> Path:
    p = REPO / rel
    if rel in man:
        got = sha(p)
        if got != man[rel]["sha256"]:
            sys.exit(f"MANIFEST MISMATCH {rel}: {got}")
    return p


# 1. scripts (verbatim copies) -------------------------------------------------
S = PAY / "scripts"
shutil.copyfile(Q4 / "aggregate.py", S / "aggregate.py")
shutil.copyfile(REPO / "paper/measurement/recompute-rc4-categories.py", S / "recompute-rc4-categories.repo-original.py")
shutil.copyfile(Q4 / "lib/category_labeler.py", S / "category_labeler.py")

import strip_outputs as so  # noqa: E402  (after aggregate.py is in place)

LOC = Q4 / "cache/raw/locomo10.json"
LME = Q4 / "cache/raw/longmemeval_oracle.json"
loc, lm = so.native_maps(LOC, LME)

RUNS = {
    "smoke-2026-05": {"nox_mem.json": "eval/q4-comparison/output/nox_mem.json",
                      "mem0.json": "eval/q4-comparison/output/mem0.json",
                      "zep.json": "eval/q4-comparison/output/zep.json"},
    "rc4-2026-06-29": {"nox_mem.json": "eval/q4-comparison/output/rc4/nox_mem.json",
                       "mem0.json": "eval/q4-comparison/output/rc4/mem0.json",
                       "_aggregate.json": "eval/q4-comparison/output/rc4/_aggregate.json",
                       "_aggregate.md": "eval/q4-comparison/output/rc4/_aggregate.md"},
    "rc4-ablation-2026-06-29": {"nox_mem.json": "eval/q4-comparison/output/rc4-ablation/nox_mem.json",
                                "mem0.json": "eval/q4-comparison/output/rc4-ablation/mem0.json",
                                "_aggregate.json": "eval/q4-comparison/output/rc4-ablation/_aggregate.json",
                                "_aggregate.md": "eval/q4-comparison/output/rc4-ablation/_aggregate.md"},
    "2026-09-10": {"evermind.json": "eval/q4-comparison/output-2026-09-10/evermind.json",
                   "zep.json": "eval/q4-comparison/output-2026-09-10/zep.json",
                   "_aggregate.json": "eval/q4-comparison/output-2026-09-10/_aggregate.json",
                   "_aggregate.md": "eval/q4-comparison/output-2026-09-10/_aggregate.md"},
}
VERSIONED = {  # tracked in the public GitHub repository at the time of building
    "eval/q4-comparison/output/nox_mem.json", "eval/q4-comparison/output/mem0.json",
    "eval/q4-comparison/output/zep.json", "eval/q4-comparison/output-2026-09-10/evermind.json",
    "eval/q4-comparison/output-2026-09-10/zep.json", "eval/q4-comparison/output-2026-09-10/_aggregate.json",
    "eval/q4-comparison/output-2026-09-10/_aggregate.md", "eval/q4-comparison/output/rc4-run.log",
}

prov = {"_what": "provenance of every file in runs/ and corpus/: original repository path, sha256 and size",
        "repository": "https://github.com/totobusnello/memoria-nox",
        "dataset_sources": {
            "locomo10.json": {"sha256": sha(LOC), "bytes": LOC.stat().st_size,
                              "upstream": "https://github.com/snap-research/locomo/blob/main/data/locomo10.json",
                              "upstream_identical": True, "licence": "CC BY-NC 4.0"},
            "longmemeval_oracle.json": {"sha256": sha(LME), "bytes": LME.stat().st_size,
                                        "upstream": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/blob/main/longmemeval_oracle.json",
                                        "upstream_identical": True, "licence": "MIT"},
            "eval/q4-comparison/cache/locomo.jsonl": {"sha256": sha(Q4 / "cache/locomo.jsonl"), "lines": 5882,
                                                      "what": "offered corpus, LoCoMo part (derived from locomo10.json)"},
            "eval/q4-comparison/cache/longmemeval.jsonl": {"sha256": sha(Q4 / "cache/longmemeval.jsonl"), "lines": 948,
                                                           "what": "offered corpus, LongMemEval part (derived from longmemeval_oracle.json)"},
            "eval/q4-comparison/cache/queries-rc4-all.jsonl": {"sha256": sha(Q4 / "cache/queries-rc4-all.jsonl"), "lines": 2482,
                                                               "what": "the n=2,482 query set (question text included; not distributed)"},
        },
        "files": {}}

for run, files in RUNS.items():
    d = PAY / "runs" / run
    d.mkdir(parents=True, exist_ok=True)
    for name, rel in files.items():
        src = checked(rel)
        entry = {"original_path": rel, "original_sha256": sha(src), "original_bytes": src.stat().st_size,
                 "in_manifest": rel in man, "versioned_in_github_repo": rel in VERSIONED}
        if name.startswith("_"):
            txt = src.read_text(encoding="utf-8")
            if so.FORBIDDEN.search(txt):
                sys.exit(f"path/host in {rel}")
            shutil.copyfile(src, d / name)
            entry["transform"] = "verbatim copy"
        else:
            obj = so.strip(json.loads(src.read_text(encoding="utf-8")), loc, lm)
            sf = {"original_path": rel, "original_sha256": entry["original_sha256"],
                  "original_bytes": entry["original_bytes"], "transform": "scripts/strip_outputs.py"}
            (d / name).write_text(so.dump(obj, sf), encoding="utf-8")
            entry["transform"] = "scripts/strip_outputs.py (query text and passage text removed)"
        prov["files"][f"runs/{run}/{name}"] = entry

# 2. id-only store censuses --------------------------------------------------------
C = PAY / "corpus"
C.mkdir(exist_ok=True)
with (C / "offered_corpus_ids.tsv").open("w", encoding="utf-8") as f:
    f.write("line\tsource_file\tid\n")
    n = 0
    for part in ("locomo.jsonl", "longmemeval.jsonl"):
        for i, line in enumerate((Q4 / "cache" / part).read_text(encoding="utf-8").splitlines(), 1):
            f.write(f"{i}\t{part}\t{json.loads(line)['id']}\n")
            n += 1
assert n == 6830, n
prov["files"]["corpus/offered_corpus_ids.tsv"] = {
    "derived_from": ["eval/q4-comparison/cache/locomo.jsonl", "eval/q4-comparison/cache/longmemeval.jsonl"],
    "transform": "id of each offered document, in file order (text removed)"}

for rel, out, label in (("eval/q4-comparison/cache/rc4-nox-hybrid.db", "rc4-nox-hybrid.eval_chunks.ids.txt", "rc4 nox-mem arm store"),
                        ("eval/q4-comparison/cache/rc4-nox-generic.db", "rc4-nox-generic.eval_chunks.ids.txt", "task-type ablation nox-mem arm store")):
    cp = SCR / Path(rel).name
    want = man[rel]["sha256"]
    assert sha(cp) == want, f"scratch copy of {rel} differs from manifest"
    con = sqlite3.connect(f"file:{cp}?immutable=1", uri=True)
    ids = [r[0] for r in con.execute("SELECT id FROM eval_chunks ORDER BY rowid")]
    con.close()
    assert sha(cp) == want, "read changed the copy"
    (C / out).write_text("\n".join(ids) + "\n", encoding="utf-8")
    prov["files"][f"corpus/{out}"] = {"derived_from": rel, "source_sha256": want, "rows": len(ids),
                                      "transform": f"SELECT id FROM eval_chunks ORDER BY rowid ({label}; text removed)"}

rel = "eval/q4-comparison/.mem0-chroma-rc4/chroma.sqlite3"
cp = SCR / "chroma.sqlite3"
assert sha(cp) == man[rel]["sha256"]
con = sqlite3.connect(f"file:{cp}?immutable=1", uri=True)
rows = con.execute("""
  SELECT e.id, e.created_at,
         (SELECT string_value FROM embedding_metadata m WHERE m.id=e.id AND m.key='chunk_id'),
         (SELECT COUNT(*) FROM embedding_metadata m WHERE m.id=e.id AND m.key='text_lemmatized')
  FROM embeddings e ORDER BY e.id""").fetchall()
con.close()
assert sha(cp) == man[rel]["sha256"]
with (C / "rc4-mem0-chroma.rows.tsv").open("w", encoding="utf-8") as f:
    f.write("row_id\tcreated_at_utc\tchunk_id\thas_text_lemmatized_key\n")
    for r in rows:
        f.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\n")
prov["files"]["corpus/rc4-mem0-chroma.rows.tsv"] = {
    "derived_from": rel, "source_sha256": man[rel]["sha256"], "rows": len(rows),
    "transform": "embeddings.id, embeddings.created_at, metadata chunk_id, and whether the row carries a "
                 "'text_lemmatized' metadata key (1/0); documents, lemmatized text and vectors removed"}

# 3. manifest, redacted logs ------------------------------------------------------------
shutil.copyfile(Q4 / "MANIFESTO-LASTRO.json", PAY / "MANIFESTO-LASTRO.json")
E = PAY / "evidence"
E.mkdir(exist_ok=True)
for rel, out in (("eval/q4-comparison/output/rc4-run.log", "rc4-run.redacted.log"),
                 ("eval/q4-comparison/output/rc4-ablation-run.log", "rc4-ablation-run.redacted.log")):
    txt = (REPO / rel).read_text(encoding="utf-8")
    for a, b in REDACT:
        txt = txt.replace(a, b)
    if so.FORBIDDEN.search(txt):
        sys.exit(f"path/host left in {rel}: {so.FORBIDDEN.search(txt).group(0)}")
    (E / out).write_text(txt, encoding="utf-8")
    prov["files"][f"evidence/{out}"] = {"original_path": rel, "original_sha256": sha(REPO / rel),
                                        "versioned_in_github_repo": rel in VERSIONED,
                                        "transform": "absolute local paths replaced by <repo>/ and <home>/; nothing else changed"}

(PAY / "PROVENANCE.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("payload built")
