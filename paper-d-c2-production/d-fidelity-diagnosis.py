#!/usr/bin/env python3
"""Paper D, after the reading: why the fidelity control failed (|P - V| = 0.19 > 0.05). Not a
registered script; written after the result, so everything it prints is diagnosis, not a test.

  python3 -I d-fidelity-diagnosis.py --private <dir>

Offline and free: reads the frozen transcripts, production.json and questions.jsonl in <dir>. For
the sessions production sent to the model (logged message_count >= 3) it rebuilds the text
production's distiller would have sent (src/session-distill.ts: extractMessages, which drops a
message starting with "[cron:", then the static part of isNoise and the 2,000-char blocks) up to
processed_at, and compares it with the text arm V sent (visible prefix of the cleaned turns, then
lme-run.py session_blocks). It then classifies every question by where its citations sit: all in
a turn whose text starts with "[cron:" (a scheduled job's prompt), none, or both. Prints counts
only, no id and no text.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = load("dcommon", HERE / "d-common.py")
S = load("dselect", HERE / "d-select.py")
L = C.load("lme", HERE.parent / "paper3-construction/lme-run.py")
HB = re.compile(r"^heartbeat[_ ]ok\b", re.I)


def prod_lines(path, processed_at):
    """The lines production would build, in file order, up to the first message after processed_at."""
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        m = e.get("message")
        if not m or e.get("type") not in ("message", "user", "assistant"):
            continue
        if m.get("role") not in ("user", "assistant"):
            continue
        c = m.get("content")
        if isinstance(c, str):
            t = c.strip()
        elif isinstance(c, list):
            t = "\n".join(x["text"] for x in c if isinstance(x, dict) and x.get("type") == "text"
                          and x.get("text")).strip()
        else:
            t = ""
        if not t or t.startswith(("[cron:", "HEARTBEAT", "The conversation history before this point")) \
                or len(t) < 5 or HB.match(t):
            continue
        ts = C.norm_ts(e.get("timestamp"))
        if ts and ts > processed_at:
            break
        out.append(f"[{m['role'].upper()}]: {t}")
    return [x for x in out if not L.is_noise_static(x.split(": ", 1)[1])]


def is_cron(text):
    return text.strip().startswith("[cron:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", required=True)
    a = ap.parse_args()
    P = pathlib.Path(a.private).expanduser()
    F = P / "freeze"
    prod = json.loads((F / "production.json").read_text(encoding="utf-8"))
    order = json.loads((F / "frame.json").read_text(encoding="utf-8"))["order"]
    Q = [json.loads(x) for x in (P / "questions.jsonl").read_text(encoding="utf-8").splitlines() if x]
    used = sorted({q["uuid"] for q in Q})
    path = {o["uuid"]: F / "sessions" / pathlib.Path(o["path"]).name for o in order}

    inp = collections.Counter()
    turns = collections.Counter()
    for u in used:
        p = prod[u]
        if p["message_count"] < 3:
            continue
        inp["sessions_sent"] += 1
        pb = L.blocks_of(prod_lines(path[u], p["processed_at"]))
        vt = C.visible_prefix(C.turns(path[u], S), p["processed_at"])
        vb = L.session_blocks(vt)
        inp["production_blocks"] += len(pb)
        inp["production_chars"] += sum(map(len, pb))
        inp["V_blocks"] += len(vb)
        inp["V_chars"] += sum(map(len, vb))
        inp["sessions_sent_with_a_cron_prompt"] += any(is_cron(t["content"]) for t in vt)
        for t in vt:
            k = "cron_prompt" if is_cron(t["content"]) else "other"
            turns[f"V_{k}_turns"] += 1
            turns[f"V_{k}_chars"] += len(t["content"].strip())

    qs = collections.Counter()
    sess_cron = 0
    for u in used:
        ts = C.turns(path[u], S)
        full, spans = C.layout(ts)
        cron = [is_cron(t["content"]) for t in ts]
        sess_cron += any(cron)
        for q in (q for q in Q if q["uuid"] == u):
            kinds = set()
            for c in q["citations"]:
                i = full.find(c, max(0, q["ev_lo"]))
                if i < 0:
                    i = full.find(c)
                k = next((j for j, (lo, hi) in enumerate(spans) if lo <= i < hi), None) if i >= 0 else None
                if k is not None:
                    kinds.add(cron[k])
            where = ("unlocated" if not kinds else "all_in_cron_prompt" if kinds == {True}
                     else "none_in_cron_prompt" if kinds == {False} else "mixed")
            qs[f"{q['set']}:{where}"] += 1
    print(json.dumps({"sessions_used": len(used), "sessions_with_a_cron_prompt": sess_cron,
                      "input_on_sessions_sent": dict(inp), "V_turns_on_sessions_sent": dict(turns),
                      "questions_by_citation_location": dict(sorted(qs.items()))}, indent=1))


if __name__ == "__main__":
    main()
