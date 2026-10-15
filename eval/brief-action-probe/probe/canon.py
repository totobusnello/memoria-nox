"""Canonical serialization of a first assistant message, and divergence (spec §5.1–5.2).

Frozen by the pilot (§5): changing anything here after `frozen/params.json` exists invalidates the
main run. `freeze_params.py` records the sha256 of this file.
"""
import json
import re
import shlex

CANON_VERSION = "1"
MAX_TOKENS = 2000

# Closed mask set, applied in this order (§5.1).
MASKS = (
    (re.compile(r"/tmp/[\w.\-/]+"), "<TMP>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"), "<DATE>"),
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"), "<TIME>"),
    (re.compile(r"\b[0-9a-fA-F]{12,64}\b"), "<HASH>"),
)
TOKEN = re.compile(r"<[A-Z]+>|\w+|[^\w\s]")
SHELL_OPS = {"&&", "||", "|", ";", "&", "(", ")", ";;", "|&"}
# A Bash `description` is prose about the call, not an argument of the action.
BASH_DROP_KEYS = {"description"}


def mask(s: str) -> str:
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s


def tokens(s: str) -> list:
    return TOKEN.findall(mask(s))


def canon_bash(command: str) -> str:
    """argv with options sorted inside each simple command; raw string if unparseable."""
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return command
    out, seg = [], []

    def flush():
        if seg:
            name, rest = seg[0], seg[1:]
            opts = sorted(t for t in rest if t.startswith("-") and len(t) > 1)
            pos = [t for t in rest if not (t.startswith("-") and len(t) > 1)]
            out.extend([name, *opts, *pos])
            seg.clear()

    for t in toks:
        if t in SHELL_OPS:
            flush()
            out.append(t)
        else:
            seg.append(t)
    flush()
    return " ".join(out)


def canon_call(name: str, inp) -> str:
    if name == "Bash" and isinstance(inp, dict) and isinstance(inp.get("command"), str):
        rest = {k: v for k, v in inp.items() if k != "command" and k not in BASH_DROP_KEYS}
        tail = (" " + json.dumps(rest, sort_keys=True, ensure_ascii=False)) if rest else ""
        return canon_bash(inp["command"]) + tail
    return json.dumps(inp, sort_keys=True, ensure_ascii=False)


def serialize(msg: dict) -> list:
    seq = []
    for call in msg.get("tool_calls") or []:
        seq += ["<CALL>", str(call.get("name"))] + tokens(canon_call(call.get("name"), call.get("input")))
    text = msg.get("text") or ""
    if text.strip():
        seq += ["<TEXT>"] + tokens(text)
    return seq[:MAX_TOKENS]


def divergence(a: list, b: list) -> float:
    """Normalized Levenshtein distance over token sequences (edit distance / longer length)."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1] / max(len(a), len(b))
