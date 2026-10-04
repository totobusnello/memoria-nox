#!/usr/bin/env python3
"""Census of EVERY artifact path the Paper A manuscript cites -- mechanically
extracted, never a hand list -- and where each one lives.

Adapted from scripts/censo-lastro-do-manuscrito.py (Paper 1). Differences that
matter for Paper A:

  * Paper A cites most artifacts by BARE NAME (`CEILING-GRANULARITY-2026-08-28.json`,
    `superficie-de-exposicao.py`), with no slash. The Paper 1 extractor demanded a
    slash and would have dropped them all. Here a token qualifies if it carries a
    known file extension OR ends in `/`.
  * Brace sets (`out/gran-{seg,min,hora,dia}.json`) and globs (`out/sens-*.json`)
    are expanded; a glob that matches nothing is MISSING, not silently skipped.
  * Line anchors (`brief.ts:588`) are stripped to the file.
  * Besides the repo, every path is also looked up in
      - the local trial lastro  ~/Backups/paper2-ensaio-2026-09-21/   (read-only)
      - the PUBLISHED Paper A deposit v1.0 (Zenodo 10.5281/zenodo.22181415), via the
        published MANIFEST.json + zip listings downloaded into the sprint evidence dir
      - the nox-mem serving source trees (for `*.ts` line anchors)
  * "versioned" is read from .git/index directly (format v2) -- this script runs
    NO git command, because other agents share the working tree.
  * Every cited path is also marked as listed / not listed in Appendix D.

What it does NOT do: check that a file has the content the paper claims. It
measures existence and reach, not correspondence.

Controls
  negative  -- a SENTINEL path injected into the read text must come out MISSING;
               otherwise a census that extracted nothing would read "nothing missing".
  positive  -- `DEVIATIONS-FOR-PAPER.md` (bare, no slash) must be extracted and resolved;
               `out/gran-{seg,min,hora,dia}.json` must expand to 4 resolved files.

Exit: 0 nothing missing; 1 some cited path resolves nowhere; 2 instrument fault.
"""
import argparse
import fnmatch
import itertools
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.dirname(HERE)                       # paper2-interventional/
REPO = os.path.dirname(P2)                       # memoria-nox/
LASTRO = os.path.expanduser("~/Backups/paper2-ensaio-2026-09-21")
EVID = os.path.join(P2, "_sprint-2026-10-04", "A-recon-evidence", "deposited-22181415")
SERVING_ROOTS = [
    os.path.expanduser("~/Claude/Projetos/nox-supermem/nox-mem"),
    os.path.expanduser("~/Claude/Projetos/nox-workspace/tools/nox-mem"),
]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".venv-zep", "_sprint-2026-10-04"}

EXT = ("json", "md", "py", "mjs", "js", "ts", "sh", "db", "ndjson", "jsonl", "csv",
       "svg", "txt", "log", "html", "zip", "pdf", "plist", "yml", "sql", "tex", "png", "cff")
RE_BACKTICK = re.compile(r"`([^`\n]{2,250})`")
RE_PLAIN = re.compile(r"(?<![\w/.\-{}*])([\w.\-/{}*,]+\.(?:%s))(?![\w])" % "|".join(EXT))
RE_PATHWORD = re.compile(r"^[\w./\-{}*,]+$")
SENTINEL = "out/SENTINEL-that-does-not-exist-2026-10-04.json"

# Cited paths whose absence from the repo is DECLARED (by the manuscript itself or by
# their nature). They are still reported, under their own status, so that a reader can
# tell "outside by declaration" from "pointing at nothing". Each note says what was
# searched. ts-350.txt is deliberately NOT here: nothing declares it outside.
KNOWN_OUTSIDE = {
    "e20260826T060003Z.db": "epoch snapshot on the serving VPS; the manuscript (§5.7.2) states it was rotated",
    "campo-churn.json": "on the serving machine per §5.7.2, which also declares the pair unusable",
    "campo-churn-sem-exclusao.json": "on the serving machine per §5.7.2, which also declares the pair unusable",
    "lessons.md": "corpus file of the production memory workspace, not a paper artifact",
    "memory/lessons.md": "corpus file of the production memory workspace, not a paper artifact",
}


def git_index_paths(repo):
    """Parse .git/index (v2/v3) without running git."""
    p = os.path.join(repo, ".git", "index")
    data = open(p, "rb").read()
    if data[:4] != b"DIRC":
        raise RuntimeError("not a git index")
    ver = int.from_bytes(data[4:8], "big")
    n = int.from_bytes(data[8:12], "big")
    if ver not in (2, 3):
        raise RuntimeError(f"index v{ver} not supported")
    off, out = 12, set()
    for _ in range(n):
        flags = int.from_bytes(data[off + 60:off + 62], "big")
        ext = 2 if (ver == 3 and flags & 0x4000) else 0
        start = off + 62 + ext
        end = data.index(b"\x00", start)
        out.add(data[start:end].decode("utf-8", "replace"))
        entlen = 62 + ext + (end - start)
        off += (entlen + 8) & ~7
    return out


def walk_files(root):
    res = {}
    if not os.path.isdir(root):
        return res
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in SKIP_DIRS]
        for f in fs:
            res.setdefault(f, []).append(os.path.join(r, f))
    return res


def expand_braces(tok):
    m = re.search(r"\{([^{}]+)\}", tok)
    if not m:
        return [tok]
    opts = m.group(1).split(",")
    return list(itertools.chain.from_iterable(
        expand_braces(tok[:m.start()] + o + tok[m.end():]) for o in opts))


def extract(text):
    """Return {token: {"lines": set, "origin": set}} -- lexical only."""
    found, excluded = {}, {}
    lines = text.split("\n")
    for ln, line in enumerate(lines, 1):
        bt_spans = []
        for m in RE_BACKTICK.finditer(line):
            bt_spans.append((m.start(), m.end()))
            for word in re.split(r"[\s|]+", m.group(1).strip()):
                w = word.strip().rstrip(".,;:)").lstrip("(")
                if not w:
                    continue
                w = re.sub(r":[\d,\-]+$", "", w)          # brief.ts:135,642 -> brief.ts
                has_ext = re.search(r"\.(%s)$" % "|".join(EXT), w) is not None
                is_dir = w.endswith("/") and len(w) > 1
                if not (has_ext or is_dir):
                    if "/" in w:
                        excluded.setdefault(w, set()).add(
                            (ln, "slash but no file extension (ratio/date/endpoint/pattern)"))
                    continue
                if w.startswith(".") and "/" not in w and w.count(".") == 1:
                    excluded.setdefault(w, set()).add((ln, "extension only, not a file"))
                    continue
                if not RE_PATHWORD.match(w):
                    excluded.setdefault(w, set()).add((ln, "pattern (%, <, …), not a file"))
                    continue
                if w.startswith(("http", "10.5281/", "/api/")):
                    excluded.setdefault(w, set()).add((ln, "URL/DOI/endpoint"))
                    continue
                e = found.setdefault(w, {"lines": set(), "origin": set()})
                e["lines"].add(ln)
                e["origin"].add("backtick")
        # plain-text mentions outside backticks
        for m in RE_PLAIN.finditer(line):
            if any(a <= m.start() < b for a, b in bt_spans):
                continue
            w = m.group(1).rstrip(".,;:)")
            if re.match(r"^\d", w) or "." not in w:
                continue
            e = found.setdefault(w, {"lines": set(), "origin": set()})
            e["lines"].add(ln)
            e["origin"].add("plain")
    return found, excluded


def appendix_d(text):
    m = re.search(r"^## Apêndice D.*?(?=^## )", text, re.S | re.M)
    if not m:
        return set()
    toks = set()
    for t in RE_BACKTICK.findall(m.group(0)):
        for w in re.split(r"[\s|·]+", t):
            w = w.strip()
            for x in expand_braces(w):
                toks.add(os.path.basename(x.rstrip("/")) or x)
    return toks


def deposited_index():
    """Paths of the published v1.0 deposit, from the published MANIFEST + zip listings."""
    mpath = os.path.join(EVID, "MANIFEST.json")
    if not os.path.exists(mpath):
        return None
    man = json.load(open(mpath, encoding="utf-8"))
    paths = {it["path"]: it.get("no_deposito") for it in man["itens"]}
    zips = {}
    for z in ("artefatos.zip", "scripts.zip"):
        zp = os.path.join(EVID, z)
        if os.path.exists(zp):
            zips[z] = set(zipfile.ZipFile(zp).namelist())
    return {"manifest": paths, "zips": zips}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=os.path.join(P2, "MANUSCRIPT.md"))
    ap.add_argument("--json", default=None, help="write the full census here")
    a = ap.parse_args()

    text = open(a.doc, encoding="utf-8").read()
    found, excluded = extract(text + f"\nsentinel `{SENTINEL}`\n")

    vers = git_index_paths(REPO)
    repo_files = walk_files(REPO)
    lastro_files = walk_files(LASTRO)
    serving_files = {}
    for r in SERVING_ROOTS:
        for k, v in walk_files(os.path.join(r, "src")).items():
            serving_files.setdefault(k, []).extend(v)
    dep = deposited_index()
    appD = appendix_d(text)

    bases = [P2, os.path.join(P2, "out"), os.path.join(P2, "measurement"),
             os.path.join(P2, "measurement", "out"), REPO]

    def resolve_one(p):
        """-> (list_of_abs_paths, how)"""
        if p.startswith("/"):
            return ([p] if os.path.exists(p) else []), "absolute"
        if p.endswith(".ts"):
            return [], "serving source: looked up in nox-mem src trees, not in this repo"
        if "*" in p:
            hits = []
            for b in bases:
                d = os.path.join(b, os.path.dirname(p))
                if os.path.isdir(d):
                    hits += [os.path.join(d, f) for f in sorted(os.listdir(d))
                             if fnmatch.fnmatch(f, os.path.basename(p))]
                if hits:
                    return hits, f"glob under {os.path.relpath(b, REPO)}"
            return [], "glob matched nothing"
        for b in bases:
            c = os.path.normpath(os.path.join(b, p))
            if os.path.exists(c):
                return [c], f"relative to {os.path.relpath(b, REPO) or '.'}"
        bn = os.path.basename(p.rstrip("/"))
        hits = repo_files.get(bn, [])
        if "/" in p.rstrip("/"):
            hits = [h for h in hits if h.endswith("/" + p)]
        if len(hits) == 1:
            return hits, "basename, unique in repo"
        if len(hits) > 1:
            pref = [h for h in hits if h.startswith(P2 + os.sep)]
            if len(pref) == 1:
                return pref, f"basename, {len(hits)} in repo, 1 under paper2-interventional (taken)"
            return hits, f"AMBIGUOUS basename ({len(hits)} in repo)"
        return [], "not in repo"

    rows = []
    for tok in sorted(found):
        for p in expand_braces(tok):
            hits, how = resolve_one(p)
            bn = os.path.basename(p.rstrip("/"))
            rel = [os.path.relpath(h, REPO) for h in hits]
            in_lastro = lastro_files.get(bn, []) if "*" not in p else []
            serving = serving_files.get(bn, []) if p.endswith(".ts") else []
            # deposited?
            dep_hit = []
            if dep:
                for h in rel:
                    r2 = os.path.relpath(os.path.join(REPO, h), P2)
                    if r2 in dep["manifest"]:
                        dep_hit.append(f"{r2} [{dep['manifest'][r2]}]")
                if p.endswith(".ts"):
                    for k, where in dep["manifest"].items():
                        if k == "serving-" + bn:
                            dep_hit.append(f"{k} [{where}, renamed copy]")
                if not hits and not dep_hit:
                    for k, where in dep["manifest"].items():
                        if os.path.basename(k) == bn:
                            dep_hit.append(f"{k} [{where}, basename only]")
            if p == SENTINEL:
                status = "MISSING" if not hits and not in_lastro and not dep_hit else "FOUND"
            elif hits:
                status = "FOUND (repo)"
            elif serving:
                status = "FOUND (serving source tree, outside this repo)"
            elif in_lastro:
                status = "FOUND (local lastro only)"
            elif dep_hit:
                status = "FOUND (deposit only)"
            elif p in KNOWN_OUTSIDE:
                status = "OUTSIDE BY DECLARATION"
            else:
                status = "MISSING"
            versioned = [h for h in rel if h in vers or any(v.startswith(h.rstrip("/") + "/") for v in vers)]
            rows.append({
                "cited_as": tok, "path": p, "lines": sorted(found[tok]["lines"]),
                "origin": sorted(found[tok]["origin"]), "status": status, "how": how,
                "repo_paths": rel, "versioned": bool(versioned) if rel else None,
                "in_local_lastro": [os.path.relpath(x, LASTRO) for x in in_lastro],
                "serving_source": [os.path.relpath(x, os.path.expanduser("~/Claude/Projetos")) for x in serving],
                "in_deposit_v1_0": dep_hit,
                "listed_in_appendix_D": bn in appD,
                "note": KNOWN_OUTSIDE.get(p),
            })

    # controls
    sent = [r for r in rows if r["path"] == SENTINEL]
    if not sent or sent[0]["status"] != "MISSING":
        print("SENTINEL FAILED: injected path not reported MISSING => census is blind", file=sys.stderr)
        return 2
    dev = [r for r in rows if r["path"] == "DEVIATIONS-FOR-PAPER.md"]
    if not dev or not dev[0]["status"].startswith("FOUND"):
        print("POSITIVE CONTROL FAILED: bare `DEVIATIONS-FOR-PAPER.md` not extracted/resolved", file=sys.stderr)
        return 2
    gran = [r for r in rows if r["cited_as"] == "out/gran-{seg,min,hora,dia}.json"]
    if len(gran) != 4 or not all(r["status"] == "FOUND (repo)" for r in gran):
        print("POSITIVE CONTROL FAILED: brace expansion", file=sys.stderr)
        return 2
    if dep is None:
        print("deposit evidence missing => 'in_deposit_v1_0' NOT MEASURED", file=sys.stderr)

    rows = [r for r in rows if r["path"] != SENTINEL]
    by = {}
    for r in rows:
        by.setdefault(r["status"], []).append(r)
    summary = {
        "manuscript": os.path.relpath(a.doc, REPO),
        "manuscript_bytes": os.path.getsize(a.doc),
        "distinct_cited_tokens": len(found) - 1,
        "expanded_paths": len(rows),
        "by_status": {k: len(v) for k, v in sorted(by.items())},
        "excluded_tokens": {k: sorted(v) for k, v in sorted(excluded.items())},
        "controls": {"sentinel": "MISSING as required", "positive_bare_name": "ok",
                     "positive_brace_expansion": "ok (4/4)"},
        "deposit_reference": "Zenodo 10.5281/zenodo.22181415 v1.0 (published MANIFEST, 120 items)",
    }
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "rows": rows}, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    print(json.dumps(summary["by_status"], indent=1))
    print(f"tokens: {summary['distinct_cited_tokens']}  expanded paths: {len(rows)}")
    for r in rows:
        dflag = "D" if r["listed_in_appendix_D"] else "-"
        dep_s = "dep" if r["in_deposit_v1_0"] else "---"
        vflag = {True: "git", False: "untracked", None: "   "}[r["versioned"]]
        print(f"{r['status'][:28]:28} {dflag} {dep_s} {vflag:9} {r['path']}  L{r['lines'][:4]}")
    return 1 if by.get("MISSING") else 0


if __name__ == "__main__":
    sys.exit(main())
