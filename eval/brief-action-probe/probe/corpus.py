"""Transcript parsing and strata (spec §2). Transcripts: Claude CLI jsonl under
/root/.claude-nuvini-team/projects/-root--openclaw-workspace[-agents-<a>]/."""
import glob
import json
import os
import random
import re

HEARTBEAT = re.compile(r"HEARTBEAT|heartbeat")
AUTO = re.compile(r"\[cron|cron:|scheduled|BOOT\.md|Subagent Context", re.I)
HUMAN = re.compile(r"conversation_label|sender|whatsapp|discord|slack|webchat", re.I)
RETRY = "[Retry after the previous model attempt failed"
DIR_RE = re.compile(r"-root--openclaw-workspace(?:-agents-(\w+))?$")


def classify(text):
    head = text[:600]
    if HEARTBEAT.search(head):
        return "heartbeat"
    if "<task-notification>" in text[:100]:
        return "task-notification"
    if AUTO.search(head):
        return "auto"
    if "Inter-session message" in head:
        return "inter-agent"
    if HUMAN.search(head):
        return "human"
    return "other"


def _normalize(text):
    s = re.sub(r"\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun) [^\]]*\]", "", text)
    s = re.sub(r"\[Retry after[^\]]*\]", "", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}[T ]?[\d:.]*Z?|\b\d{1,2}:\d{2}\b|[0-9a-f]{8}-[0-9a-f-]{27}|\b\d{3,}\b", "#", s)
    return re.sub(r"\s+", " ", s).strip()


def template_key(agent, text):
    return f"{agent}|{_normalize(text)[:120]}"


def _user_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content):
            return None
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return None


def load_turns(projects_dir, start_iso, end_iso):
    turns = []
    for d in sorted(glob.glob(os.path.join(projects_dir, "-root--openclaw-workspace*"))):
        m = DIR_RE.search(os.path.basename(d))
        if not m:
            continue
        agent = m.group(1) or "main"
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            last_key = None
            with open(path, errors="replace") as f:
                for n, raw in enumerate(f):
                    try:
                        o = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") != "user":
                        continue
                    ts = o.get("timestamp") or ""
                    if not (start_iso <= ts < end_iso):
                        continue
                    text = _user_text((o.get("message") or {}).get("content"))
                    if not text or not text.strip():
                        continue
                    key = template_key(agent, text)
                    if RETRY in text and key == last_key:
                        continue
                    last_key = key
                    turns.append({"unit_id": o.get("uuid") or f"{os.path.basename(path)}:{n}", "agent": agent,
                                  "ts": ts, "text": text, "kind": classify(text), "template": key,
                                  "session": os.path.basename(path)})
    return sorted(turns, key=lambda t: (t["ts"], t["unit_id"]))


def evenly(n, k):
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def build_strata(turns, cap=8, n_pilot=20, big=5, seed=0):
    human = [t for t in turns if t["kind"] == "human"]
    rest = [t for t in turns if t["kind"] in ("auto", "inter-agent", "other")]
    by_tpl = {}
    for t in sorted(rest, key=lambda x: (x["ts"], x["unit_id"])):
        by_tpl.setdefault(t["template"], []).append(t)
    main_c, surplus = [], {}
    for tpl, ts in sorted(by_tpl.items()):
        idx = set(evenly(len(ts), cap))
        main_c += [x for i, x in enumerate(ts) if i in idx]
        surplus[tpl] = [x for i, x in enumerate(ts) if i not in idx]
    big_tpls = sorted(by_tpl, key=lambda k: (-len(by_tpl[k]), k))[:big]
    rng, pilot = random.Random(seed), []
    per = n_pilot // max(1, len(big_tpls))
    for tpl in big_tpls:
        pilot += rng.sample(surplus[tpl], min(per, len(surplus[tpl])))
    return {"C": main_c, "R": human, "pilot_C": pilot}
