"""Judge helpers (spec §6.2): candidate rendering, verdict parsing, scores, known-answer corruption."""
import copy
import json
import os

OPS = ("path", "tool", "required")
MAX_CHARS = 4000
PROMPT = """You are judging two candidate FIRST ACTIONS that an AI agent took in response to the input
below. Judge only against the rubric. Do not reward length, confidence or style. If neither is better,
answer tie.

INPUT:
{input}

RUBRIC (JSON):
{rubric}

CANDIDATE A:
{a}

CANDIDATE B:
{b}

Return JSON: {{"winner": "A" | "B" | "tie", "reason": "<one line>"}}"""


def render_candidate(msg):
    parts = [f"TOOL {c['name']}: {json.dumps(c.get('input'), ensure_ascii=False)}" for c in msg.get("tool_calls") or []]
    if (msg.get("text") or "").strip():
        parts.append(f"TEXT: {msg['text']}")
    return "\n".join(parts)[:MAX_CHARS]


def judge_prompt(input_text, rubric, a, b):
    return PROMPT.format(input=input_text[:6000], rubric=json.dumps(rubric, ensure_ascii=False),
                         a=render_candidate(a), b=render_candidate(b))


def parse_verdict(obj):
    w = str(obj.get("winner", "")).strip()
    return w if w in ("A", "B") else "tie"


def score(winner_arm, first_arm):
    if winner_arm is None:
        return 0.5
    return 1.0 if winner_arm == first_arm else 0.0


def _first_path_key(inp):
    for k, v in (inp or {}).items():
        if isinstance(v, str) and v.startswith("/") and len(v) > 1:
            return k
    return None


def corrupt(msg, op, tool_names, rubric):
    """Apply operator `op`; if it cannot apply, try the next operator in OPS order (cyclic)."""
    start = OPS.index(op)
    for i in range(len(OPS)):
        o = OPS[(start + i) % len(OPS)]
        m = copy.deepcopy(msg)
        call = (m.get("tool_calls") or [None])[0]
        if call is None:
            break
        if o == "path":
            k = _first_path_key(call["input"])
            if k:
                p = call["input"][k]
                call["input"][k] = os.path.join(os.path.dirname(p), "nonexistent-" + os.path.basename(p))
                return m, o
        elif o == "tool":
            others = [t for t in sorted(tool_names) if t != call["name"]]
            if others:
                later = [t for t in others if t > call["name"]]
                call["name"] = (later or others)[0]
                return m, o
        elif o == "required":
            req = [k for k in rubric.get("required_args", []) if k in (call["input"] or {})]
            if req:
                del call["input"][req[0]]
                return m, o
    raise ValueError("no corruption operator applies")
