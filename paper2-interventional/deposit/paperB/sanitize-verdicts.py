#!/usr/bin/env python3
"""Derived, depositable copy of the trial's panel verdicts, with every free-text field removed.

Sources (outside the repository, not deposited): the two panel-verdict files the manuscript cites,
ensaio-20260921-PRIMARIO-3fam.jsonl (three families) and ensaio-20260921-SENSIB-deepseek.jsonl
(fourth family, sensitivity), in the author's verdict directory (~/.paper2-verdicts/).

Each row keeps only the fields in KEEP, all identifiers or short enumerations: episode id, panelist,
family, model requested, model served, the label (verdict, severity level), call status, stop
reason and attempts. Removed: `reason` (the panelist's free-text reason about the episode) and
`detail` (free-text error note). The source rows carry no timestamp field, so none is kept.
Rows stay in source order, one JSON object per line, keys sorted.

Refuses (exit 1) if a source row has a field outside KEEP | DROP (a new field is not guessed
about), or if a kept value is not None, an int, or a short token (<= 40 chars of [A-Za-z0-9._-]).

Writes ONLY build/derived/panel-verdicts/ in this folder:
  <name>.no-reason.jsonl     the derived copy
  SANITIZED.json             per file: source sha256 and rows, derived sha256 and rows, fields
                             kept and removed, label counts
"""
import collections
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC_DIR = pathlib.Path.home() / ".paper2-verdicts"
OUT = HERE / "build" / "derived" / "panel-verdicts"
NAMES = ["ensaio-20260921-PRIMARIO-3fam.jsonl", "ensaio-20260921-SENSIB-deepseek.jsonl"]
KEEP = ["episode_id", "panelist", "family", "model", "model_served", "verdict", "level", "status",
        "stop_reason", "attempts"]
DROP = {"reason": "the panelist's free-text reason about the episode (episode-derived text)",
        "detail": "free-text error note of a failed call"}
TOKEN = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def derived_name(n):
    return n[:-len(".jsonl")] + ".no-reason.jsonl"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary, falhas = {"generated_by": "deposit/paperB/sanitize-verdicts.py", "kept": KEEP,
                       "removed": DROP, "timestamps": "none: the source rows carry no timestamp field",
                       "files": {}}, []
    for n in NAMES:
        raw = (SRC_DIR / n).read_bytes()
        rows, lab = [], collections.Counter()
        for k, ln in enumerate(raw.decode("utf-8").splitlines(), 1):
            d = json.loads(ln)
            extra = set(d) - set(KEEP) - set(DROP)
            if extra:
                falhas.append(f"{n}:{k}: field(s) outside KEEP/DROP: {sorted(extra)}")
            out = {f: d.get(f) for f in KEEP}
            for f, v in out.items():
                if not (v is None or isinstance(v, int) or (isinstance(v, str) and TOKEN.match(v))):
                    falhas.append(f"{n}:{k}: kept field {f} is not a short token: {str(v)[:30]!r}")
            lab[(out["panelist"], out["verdict"])] += 1
            rows.append(json.dumps(out, ensure_ascii=False, sort_keys=True))
        data = ("\n".join(rows) + "\n").encode("utf-8")
        (OUT / derived_name(n)).write_bytes(data)
        summary["files"][derived_name(n)] = {
            "source": n, "source_sha256": hashlib.sha256(raw).hexdigest(), "source_rows": len(rows),
            "sha256": hashlib.sha256(data).hexdigest(), "rows": len(rows),
            "labels": {f"{p}/{v}": c for (p, v), c in sorted(lab.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))},
        }
    if falhas:
        print("\n".join("FAIL " + f for f in falhas[:20]))
        return 1
    (OUT / "SANITIZED.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in summary["files"].items():
        print(f"{k}: {v['rows']} rows (source {v['source_rows']}), sha256 {v['sha256'][:12]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
