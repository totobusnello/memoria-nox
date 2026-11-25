#!/usr/bin/env python3
"""Gate «S: corpus» (PLANO.md): the corpus on disk is exactly what plan.json says was planted.

  python3 -I synthetic-ptbr/check-corpus.py --corpus <dir> [--plan <plan.json>]

Exit 0 only if ALL of these hold; every failure is listed, then exit 1:
  1. the corpus holds exactly the planned files (no missing, no extra .md);
  2. every planted item (primary, paraphrase, negative) appears in its file exactly `count`
     times (2 for a duplicated primary), in its declared section for entity files, and in no
     other file;
  3. every occurrence of every FORM of every planted value lies inside an item of that value
     (so a value copied into free text, or a declared variant written outside T, fails);
  4. free text has NO digits: digits are allowed only inside planted items, in an entity file's
     frontmatter, on the first line when it is a `# ` title, and in `**YYYY-MM-DD**` timeline
     dates. This is what keeps the generator from restating a value in numeric form, or from
     inventing a value for a false-premise query;
  5. no two planted values collide (a form of one found inside a form of another);
  6. no '@' and no link anywhere (the account e-mail reaches the generator's context; generate.py
     also refuses the account's terms, read at run time, which this public gate cannot know).

What it cannot see, by construction: a value restated in words by the generator ("três mil e
quatrocentos"). PLANO.md declares that residue as a hypothesis audited by a blind sample.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import s_common as C  # noqa: E402

DIGIT = re.compile(r"\d")
TIMELINE_DATE = re.compile(r"\*\*\d{4}-\d{2}-\d{2}\*\*")


def allowed_digit_spans(text, kind):
    spans = []
    first_nl = text.find("\n")
    first = text if first_nl == -1 else text[:first_nl]
    if first.startswith("# "):
        spans.append((0, len(first)))
    if kind == "entity" and text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            spans.append((0, end + 5))
    spans += [(m.start(), m.end()) for m in TIMELINE_DATE.finditer(text)]
    return spans


def inside(pos, spans):
    return any(a <= pos < b for a, b in spans)


def check(plan, root):
    fails = []
    root = pathlib.Path(root)
    planned = {f["path"]: f for f in plan["files"]}
    on_disk = {str(p.relative_to(root)): p for p in root.rglob("*.md")}
    for p in sorted(set(planned) - set(on_disk)):
        fails.append(f"missing file: {p}")
    for p in sorted(set(on_disk) - set(planned)):
        fails.append(f"file not in plan: {p}")
    texts = {p: on_disk[p].read_text(encoding="utf-8") for p in planned if p in on_disk}

    item_owner = {}                                   # item text -> path it belongs to
    value_of_item = {}
    for f in plan["files"]:
        for it in f["items"]:
            item_owner[it["text"]] = f["path"]
            value_of_item[it["id"]] = it["value"]

    forms_by_value = {}
    for vid, form in C.all_value_forms(plan):
        forms_by_value.setdefault(vid, []).append(form)

    for path, text in texts.items():
        f = planned[path]
        # 2. items: count, section
        item_spans = []                               # (start, end, value_id)
        for it in f["items"]:
            n = text.count(it["text"])
            if n != it["count"]:
                fails.append(f"{path}: item {it['id']} found {n}x, want {it['count']}x")
            if it.get("section") and f["kind"] == "entity":
                if it["text"] not in C.entity_sections(text)[it["section"]]:
                    fails.append(f"{path}: item {it['id']} not in section {it['section']}")
            start = 0
            while True:
                i = text.find(it["text"], start)
                if i == -1:
                    break
                item_spans.append((i, i + len(it["text"]), it["value"]))
                start = i + 1
        #    ... and in no other file
        for t, owner in item_owner.items():
            if owner != path and t in text:
                fails.append(f"{path}: carries an item planted for {owner}")
        # 3. value forms only inside items of that value
        for vid, forms in forms_by_value.items():
            for form in forms:
                for a, b in C.form_spans(text, form):
                    if not any(s <= a and b <= e and v == vid for s, e, v in item_spans):
                        fails.append(f"{path}: value {vid} form «{form}» outside its items (pos {a})")
        # 4. digits in free text
        ok_spans = [(s, e) for s, e, _ in item_spans] + allowed_digit_spans(text, f["kind"])
        for m in DIGIT.finditer(text):
            if not inside(m.start(), ok_spans):
                ctx = text[max(0, m.start() - 20):m.start() + 20].replace("\n", " ")
                fails.append(f"{path}: digit in free text: «{ctx}»")
                break
    # 6. no e-mail address or link anywhere: nothing planted carries one, so any is the model's
    for path, text in texts.items():
        if "@" in text or re.search(r"https?:|www\.", text, re.I):
            fails.append(f"{path}: e-mail or link")
    # 5. collisions
    for vi, fi, vj, fj in C.form_collisions(C.all_value_forms(plan)):
        fails.append(f"values collide: {vi} «{fi}» × {vj} «{fj}»")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--plan", default=str(C.PLAN_FILE))
    a = ap.parse_args()
    fails = check(C.load_plan(a.plan), a.corpus)
    for x in fails[:50]:
        print(f"  ! {x}")
    if len(fails) > 50:
        print(f"  ... and {len(fails) - 50} more")
    print(f"check-corpus: {'FAIL, ' + str(len(fails)) + ' problem(s)' if fails else 'ok'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
