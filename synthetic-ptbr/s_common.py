"""Shared pieces of the synthetic PT-BR corpus (PLANO.md, «Objetivo (2026-11-25)»).

Stdlib only. Every script here runs with `python3 -I`, which drops the script directory from
sys.path, so each one inserts its own directory before importing this module.

The one idea this module carries: a planted value is identified by its FORMS (the literal plus
the declared variants, e.g. "3.417" and "3417"), and a form counts as present only at a token
boundary, so "3.417" does not match inside "13.417" or "3.4170".
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
PLAN_DIR = HERE / "plan"
PLAN_FILE = PLAN_DIR / "plan.json"

# A form is present when it is not glued to a word character or to a digit group on either side.
def form_regex(form):
    return re.compile(r"(?<![\w])" + re.escape(form) + r"(?![\w]|[.,]\d)")


def form_spans(text, form):
    return [(m.start(), m.end()) for m in form_regex(form).finditer(text)]


def load_plan(path=PLAN_FILE):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def dump_json(obj):
    """The one serialisation used for every committed JSON, so a byte comparison is meaningful."""
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def all_value_forms(plan):
    """[(value_id, form)] for every planted value: facts and context negatives."""
    out = []
    for f in plan["facts"]:
        for form in f["forms"]:
            out.append((f["id"], form))
        for n in f.get("negatives", []):
            for form in n["forms"]:
                out.append((n["id"], form))
    return out


def form_collisions(pairs):
    """Pairs of forms from DIFFERENT values where one is found inside the other at a boundary.
    Two such values could not be told apart by a text check, so the planner must refuse them."""
    bad = []
    for i, (vi, fi) in enumerate(pairs):
        for vj, fj in pairs[i + 1:]:
            if vi == vj:
                continue
            if form_spans(fi, fj) or form_spans(fj, fi):
                bad.append((vi, fi, vj, fj))
    return bad


# Entity files follow the nox-mem entity format: YAML frontmatter between the first two `---`
# lines, then the compiled truth, then `## Timeline` (case-insensitive) with one bullet per event.
_TIMELINE = re.compile(r"^##\s+timeline\s*$", re.I | re.M)


def entity_sections(text):
    """{'frontmatter': str, 'compiled': str, 'timeline': str} for an entity file."""
    sec = {"frontmatter": "", "compiled": "", "timeline": ""}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            sec["frontmatter"] = text[4:end]
            body = text[end + 5:]
    m = _TIMELINE.search(body)
    if m:
        sec["compiled"], sec["timeline"] = body[:m.start()], body[m.end():]
    else:
        sec["compiled"] = body
    return sec
