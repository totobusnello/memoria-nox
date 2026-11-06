#!/usr/bin/env python3
"""Paper B: structural census of the knowledge graph an LLM extracted, on one frozen snapshot.

No model call. Read-only (mode=ro) on the snapshot given as the first argument; writes only the
JSON named as the second. Every figure is a count or a share; no entity name, predicate text,
evidence text or source path leaves the host. Evidence sources are reported in fixed buckets
(BUCKETS below), never as raw paths, because paths can name private documents.

  python3 -I b-census.py <snapshot.db> <out.json> [--snapshot-name N --snapshot-sha256 H]

What it measures, each against the October audit it updates (audits/2026-10-22-kg-s1-precision.md,
audits/2026-10-23-kg-s1-quatro-principios.md):
  size          entities, relations, relations with evidence, with live evidence
  predicates    distinct relation_type, hapax types (used once), relations whose type is hapax
  reasons       relation_reason distribution (the closed enum)
  evidence      relations by evidence-source bucket
  time          relations by created_at month; created since 2026-09-01
  provenance    extraction_method NULL share; confidence value counts
  supersession  relations superseded
"""
import collections
import json
import re
import sqlite3
import sys

BUCKETS = [  # first match wins; patterns over chunks.source_file
    ("document vault", re.compile(r"^memory/mac-docs/")),
    ("entity files", re.compile(r"^memory/entities/")),
    ("daily notes", re.compile(r"^memory/\d{4}-\d{2}-\d{2}[^/]*\.md$")),
    ("distilled sessions", re.compile(r"^sessions/")),
    ("workspace documents", re.compile(r"^(memory|shared)/[^/]+\.md$")),
]


def bucket(path):
    for name, rx in BUCKETS:
        if path and rx.search(path):
            return name
    return "other"


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    db_path, out = argv[0], argv[1]
    opts = dict(zip(argv[2::2], argv[3::2]))
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    one = lambda sql, *a: con.execute(sql, a).fetchone()[0]

    rel = one("SELECT COUNT(*) FROM kg_relations")
    ent = one("SELECT COUNT(*) FROM kg_entities")
    with_ev = one("SELECT COUNT(*) FROM kg_relations WHERE evidence_chunk_id IS NOT NULL")
    live_ev = one("SELECT COUNT(*) FROM kg_relations r JOIN chunks c ON c.id = r.evidence_chunk_id")

    types = collections.Counter(t for (t,) in q("SELECT relation_type FROM kg_relations"))
    hapax = {t for t, n in types.items() if n == 1}

    reasons = collections.Counter(r if r is not None else "NULL"
                                  for (r,) in q("SELECT relation_reason FROM kg_relations"))
    ev = collections.Counter(bucket(s) for (s,) in q(
        "SELECT c.source_file FROM kg_relations r JOIN chunks c ON c.id = r.evidence_chunk_id"))
    months = collections.Counter(m or "NULL" for (m,) in q(
        "SELECT substr(created_at, 1, 7) FROM kg_relations"))
    since_sep = one("SELECT COUNT(*) FROM kg_relations WHERE created_at >= '2026-09-01'")
    em_null = one("SELECT COUNT(*) FROM kg_relations WHERE extraction_method IS NULL")
    conf = collections.Counter(("NULL" if c is None else f"{c:.2f}")
                               for (c,) in q("SELECT confidence FROM kg_relations"))
    superseded = one("SELECT COUNT(*) FROM kg_relations WHERE superseded_by_relation_id IS NOT NULL "
                     "OR superseded_at IS NOT NULL")

    share = lambda k, n: round(k / n, 4) if n else None
    res = {
        "snapshot": {"name": opts.get("--snapshot-name"), "sha256": opts.get("--snapshot-sha256")},
        "size": {"entities": ent, "relations": rel, "relations_with_evidence": with_ev,
                 "relations_with_live_evidence": live_ev},
        "predicates": {"distinct_relation_type": len(types), "hapax_types": len(hapax),
                       "hapax_type_share": share(len(hapax), len(types)),
                       "relations_with_hapax_type": len(hapax),
                       "relations_with_hapax_type_share": share(len(hapax), rel),
                       "top10_type_relation_share": share(sum(n for _, n in types.most_common(10)), rel)},
        "relation_reason": dict(reasons.most_common()),
        "evidence_bucket": {"relations": dict(ev.most_common()),
                            "share": {k: share(v, live_ev) for k, v in ev.most_common()},
                            "buckets": [b for b, _ in BUCKETS] + ["other"]},
        "created_month": dict(sorted(months.items())),
        "created_since_2026_09_01": since_sep,
        "extraction_method_null": em_null,
        "extraction_method_null_share": share(em_null, rel),
        "confidence_values": dict(conf.most_common(12)),
        "superseded": superseded,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: res[k] for k in ("size", "predicates")}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
