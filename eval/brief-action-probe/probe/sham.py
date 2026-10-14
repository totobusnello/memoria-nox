"""BS (wrong-agent memory) construction, spec §3.

Overlap is Jaccard over distinctive tokens: tokens of >= 4 chars (7a definition) minus `common`, the
tokens present in >= 5% of all distinct brief items of the window (frozen in the manifest).
Repeated chunk ids in the candidate sequence are kept once (first occurrence).
"""
import re

TOK = re.compile(r"[^\w./]+")


def item_tokens(text):
    return {t for t in TOK.split(text.lower()) if len(t) >= 4}


def common_tokens(texts, share=0.05):
    df = {}
    for t in texts:
        for x in item_tokens(t):
            df[x] = df.get(x, 0) + 1
    n = max(1, len(texts))
    return {x for x, c in df.items() if c / n >= share}


def _jaccard(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def filter_candidates(cands, b1, t, common, max_overlap=0.3):
    b1_ids = {x["id"] for x in b1}
    b1_toks = [item_tokens(x["text"]) - common for x in b1]
    out, seen = [], set()
    for c in cands:
        if c["id"] in b1_ids or c["id"] in seen or c["created_at"] > t:
            continue
        ct = item_tokens(c["text"]) - common
        if any(_jaccard(ct, bt) > max_overlap for bt in b1_toks):
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def build_sham(filtered, k, b1_len, render_len, tol=0.10):
    """First window of k consecutive items whose rendered length is within ±tol of b1_len."""
    for start in range(0, len(filtered) - k + 1):
        window = filtered[start:start + k]
        if abs(render_len(window) - b1_len) <= tol * b1_len:
            return window
    return None
