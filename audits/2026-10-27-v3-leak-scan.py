"""Before v3 goes into a PUBLIC repo: what do the new anchors actually contain?

v2's anchors are already public and are verbatim corpus spans, so the precedent
exists — but v2 capped them near 160 chars and the uniqueness fix here allowed
up to 600, from files like agents/forge/memory/outcome-log.md and sessions/.
gitleaks on CI matches credential PATTERNS; it does not read prose. So this
scans what gitleaks cannot, and reports length so the exposure is a number
rather than an impression.
"""
import json, re, sys
from collections import Counter

P = sys.argv[1] if len(sys.argv) > 1 else "/root/medicoes/golden-queries-v3.jsonl"
rows = [json.loads(l) for l in open(P, encoding="utf-8") if l.strip()]
new = [(r["query_id"], g) for r in rows for g in r.get("gold", [])
       if "provenance" in g]
print(f"anchors created today: {len(new)}")
L = [len(g["anchor"]) for _, g in new]
print(f"  length: min {min(L)} · median {sorted(L)[len(L)//2]} · max {max(L)}")
print(f"  over 160 chars (v2's cap): {sum(1 for x in L if x > 160)}")

PATTERNS = {
 "slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
 "openai/anthropic key": r"\b(sk|sk-ant)-[A-Za-z0-9_-]{16,}",
 "google api key": r"\bAIza[0-9A-Za-z_-]{30,}",
 "aws key id": r"\bAKIA[0-9A-Z]{16}\b",
 "bearer token": r"(?i)bearer\s+[A-Za-z0-9._-]{20,}",
 "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY",
 "discord webhook": r"discord(?:app)?\.com/api/webhooks/\d+",
 "generic secret=": r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{8,}",
 "jwt": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
 "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
 "ipv4 (non-private)": r"\b(?!10\.|192\.168\.|127\.|172\.(?:1[6-9]|2\d|3[01])\.)"
                       r"(?:\d{1,3}\.){3}\d{1,3}\b",
 "cpf/cnpj": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
}
hits = Counter()
for qid, g in new:
    a = g["anchor"]
    for name, rx in PATTERNS.items():
        for m in re.finditer(rx, a):
            hits[name] += 1
            print(f"  ! Q{qid} [{name}] ...{a[max(0,m.start()-24):m.start()]}"
                  f"<<{m.group()[:28]}>>...")
print(f"\npattern hits: {dict(hits) if hits else 'none'}")

# which files the new anchors come from — a session transcript is a different
# kind of exposure from a docs file
src = Counter(g["source_file"].split("/")[0] for _, g in new)
print(f"top-level dirs: {dict(src)}")
sess = [(q, g["source_file"]) for q, g in new
        if g["source_file"].startswith(("sessions/", "events/"))]
print(f"anchors from sessions/ or events/ (conversation prose): {len(sess)}")
for q, sf in sess:
    print(f"    Q{q} {sf[:72]}")
