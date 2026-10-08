#!/usr/bin/env python3
"""Builds the Paper B deposit package (Zenodo concept 10.5281/zenodo.21964093, new version after v1.12).

Reads the repository and the ballast; writes ONLY inside deposit/paperB/. No network, no git write.

Output (this folder):
  artifacts-v2.0.zip, scripts-v2.0.zip   deterministic zips (sorted members, fixed date)
  MANIFEST-v2.0.json                       sha256 of every packaged file, census, gate, exclusions
  SHA256SUMS                               sha256 of every file to upload
  SCRUBBED.txt                             every packaged copy that differs from its source, and why

Version DOI: the release candidate carries the placeholder token PLACEHOLDER exactly PLACEHOLDER_COUNT times
  (rc27 and rc28: twice, in the status header and in working-list item 8); the build substitutes EVERY occurrence.
  python3 build-package.py --doi 10.5281/zenodo.NNNN    (or PAPERB_DOI=… in the environment)
      writes the loose .md as FONTE with the placeholder replaced by that DOI, builds the PDF with it
      (build/build-pdf.sh, PAPERB_DOI), and FAILS if the placeholder survives in any packaged byte;
  python3 build-package.py --no-doi                     (dry run, before the draft reserves the DOI)
      keeps the placeholder, marks the manifest `dry_run: true`, and says DRY RUN: not for deposit.
  With neither, the build refuses to run.

Gates (exit 1 if any fails; the package must then not be deposited):
  1. manuscript: the loose .md is the frozen release candidate (FONTE, pinned) byte for byte, except
     the placeholder replaced by the DOI (nothing replaced under --no-doi);
  2. census: every path the manuscript cites is in the package, versioned unchanged in the public
     repository (origin/main), a published file of v1.12 (same md5), or declared in DECLARED;
  3. privacy: no packaged byte (loose files, every zip member, every member of every .tgz, and the
     text a reader extracts from the PDF) carries a personal home path, a host name or a
     non-loopback IP, an e-mail address (v1.12 published none), a credential-like string, or
     episode text (fingerprints of every string of the episode and panel files, and JSON keys
     that carry excerpts).
Paths inside the zips are relative to paper2-interventional/; files of the repository root go
under `_repo/`, files of the ballast (outside the repository) under `_ballast/`.
"""
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
P2 = HERE.parent.parent                      # paper2-interventional/
REPO = P2.parent                             # memoria-nox/
BALLAST = pathlib.Path.home() / "Backups" / "paper2-ensaio-2026-09-21"
SPRINT = "_sprint-2026-10-04"

VERSION = "2.0"
SLUG = "registered-horizon-outlived-the-intervention-the-trial-ran"
MD = f"{SLUG}-v{VERSION}.md"
PDF = f"{SLUG}-v{VERSION}.pdf"
FONTE = f"{SPRINT}/B-v2-rc28.md"
FONTE_SHA = "449d4dec5abada6ae69135d86be2a8bc39fa127f1429580ce253ac7adda5a71f"
PLACEHOLDER = "[VERSION-DOI]"
PLACEHOLDER_COUNT = 2                         # rc27/rc28: status header + working-list item 8; exact, read by B-rc27/parity-rc27.py and B-rc28/parity-rc28.py
DOI_RE = r"10\.5281/zenodo\.\d{6,10}"
# Derived files (written by sanitize-verdicts.py, from sources that are never packaged), under _derived/.
DERIVED_DIR = HERE / "build" / "derived"
DEPOSIT_SCRIPTS = ["sanitize-verdicts.py"]    # packaged under deposit-paperB/ (build-package.py itself holds
                                              # the privacy patterns as literals, so it is not packaged)
ZA, ZS = f"artifacts-v{VERSION}.zip", f"scripts-v{VERSION}.zip"
DATA_FIXA = (2026, 10, 7, 0, 0, 0)
V112_FILES = P2 / SPRINT / "B-rc18" / "zenodo-22110203-files.json"

# ------------------------------------------------------------------ what goes in, besides what is cited
# Globs relative to paper2-interventional/ (files only; directories never recursed unless the glob says so).
EXTRA = [
    f"{SPRINT}/B-registered/*",
    f"{SPRINT}/B-censo/*",                                 # raw/ is a directory: not matched, and excluded below
    f"{SPRINT}/B-sham-v2/*.md", f"{SPRINT}/B-sham-v2/*.txt", f"{SPRINT}/B-sham-v2/*.sh",
    f"{SPRINT}/B-sham-v2/*.tgz", f"{SPRINT}/B-sham-v2/job-v1.sha256",
    f"{SPRINT}/B-sham-v2/job-janela2/*", f"{SPRINT}/B-sham-v2/job-v2b/*", f"{SPRINT}/B-sham-v2/job-v1/*",
    f"{SPRINT}/B-sham-v2/calibration/*", f"{SPRINT}/B-sham-v2/fidelity-110/*", f"{SPRINT}/B-sham-v2/diag-v2b/*",
    f"{SPRINT}/B-sham-v2/janela-lancamento/*", f"{SPRINT}/B-sham-v2/shams-impulsionavel/*",
    f"{SPRINT}/B-sham-v2/shams-todos/*",
    f"{SPRINT}/figures/*",
    f"{SPRINT}/receipts/*",
    f"{SPRINT}/B-rc*/checks-rc*.py", f"{SPRINT}/B-rc*/checks-rc*.json",
    f"{SPRINT}/B-rc18/zenodo-22110203-*.json", f"{SPRINT}/B-rc19/zenodo-21978476-*.json",
    f"{SPRINT}/REVIEW-B-*.md", f"{SPRINT}/APPLY-B-rc*.md", f"{SPRINT}/REVIEW-B-rc2-evidence/*",
    f"{SPRINT}/B-replay-fidelity/*", f"{SPRINT}/B-replay-fidelity.md", f"{SPRINT}/LASTRO-B-item10.md",
    f"{SPRINT}/B-related-work.md", f"{SPRINT}/B-related-work.bib", f"{SPRINT}/B-related-work.verification-log.md",
    "out/ITT-REGISTRADO-*.json",
    f"{SPRINT}/B-rc25/parity-rc25.py",
    f"{SPRINT}/B-rc26/parity-rc26.py",
    f"{SPRINT}/B-rc27/parity-rc27.py",
    f"{SPRINT}/B-rc28/parity-rc28.py",
    f"{SPRINT}/B-rc28/zenodo-21964093-versions.json",
]
# Ballast files (outside the repository) that the claims rest on; packaged under _ballast/.
BALLAST_IN = [
    "ITT-2026-09-21.json", "ITT-PRELIMINAR.json", "ITT-SENSIB-PRECOMPROMETIDA.json",
    "RERANDOMIZACAO-2026-09-21.json", "COBERTURA-M10-2026-09-21.json",
    "CONTROLES-JANELA-COMPLETA-2026-09-21.json", "ITEM7-DOSE-TOPO-2026-09-21.json",
    "estrato-b-ids-20260921.txt", "desliga-dose.ndjson", "p2-serving.ndjson",
    "MANIFESTO-LASTRO-P2.json",
    "RECIBO-ITEM10-20261005T125933Z.txt", "RECIBO-ITEM10B-20261005T130316Z.txt",
    "RECIBO-ITEM15-20261007T120404Z.txt", "recibos/*",
]
# Never packaged, whatever cites them (pattern on the path relative to its root -> reason).
NEVER = [
    (r"(^|/)B-censo/raw/", "episode excerpts and panelist reasons (Appendix B states it is not in the ballast either)"),
    (r"\.db$", "production corpus databases with real work content"),
    (r"(^|/)episodios-[^/]*\.jsonl$|(^|/)alvo-painel-[^/]*\.jsonl$", "episode text of the trial"),
    (r"(^|/)__pycache__/", "bytecode"),
    (r"(^|/)\.DS_Store$|(^|/)\.gitignore$", "filesystem metadata"),
    (r"(^|/)job-[^/]+/runs/", "per-run outputs; packaged as the job's -runs.tgz"),
    (r"^deposit/", "the deposit mechanism, not its object (this folder and Paper A's)"),
    (r"^docs/HANDOFF\.md$", "the project's working log (third-party e-mail addresses, network names); versioned in "
                            "the public repository, which is where the manuscript points"),
]
# Cited, deliberately not packaged and not in the public repository: token -> reason.
DECLARED = {
    "current.db": "the live production database pointer (epochs/current.db); a database, see NEVER",
    "corpus-SERVING-REAL-e20260903-recuperado.db": "production corpus database (kept off-machine, sha256 in BANCOS.sha256)",
    "corpus-preservado-20260908.db": "production corpus database (kept off-machine, sha256 in BANCOS.sha256)",
    "e20260826T060003Z.db": "a pruned epoch database; the manuscript states it no longer exists",
    "memory/lessons.md": "a file of the live agent workspace on the production host, not of this repository",
    "memory/entities/lessons/*.md": "files of the live agent workspace on the production host (the 19 designated items); their ids and hashes are in the designation artifacts",
    "src/api/brief.ts": "serving source of the nox-mem service on the production host; the manuscript cites the hash it matched, recorded in the sham INSTRUMENTO.sha256 files (packaged)",
    "scripts/adversary-run.sh": "the voice runner of the author's tooling repository (not this one); the fact the text uses (local-time stamp, no -u) is checked by parity-rc25.py S25/R1, which is packaged",
    "run.json": "suffix of the figure provenance files `*.run.json` (packaged under figures/), not a file name",
    "ensaio-20260921-PRIMARIO-3fam.jsonl": "panel verdicts of the trial (three families); each row carries the "
        "panelist's free-text reason about the episode, so it is episode-derived text; kept in the ballast "
        "(sha256 in MANIFESTO-LASTRO-P2.json, packaged), both copies verified; a derived copy without "
        "the free-text fields is packaged as _derived/panel-verdicts/ensaio-20260921-PRIMARIO-3fam.no-reason.jsonl",
    "ensaio-20260921-SENSIB-deepseek.jsonl": "panel verdicts of the fourth family (sensitivity); same reason; "
        "derived copy packaged as _derived/panel-verdicts/ensaio-20260921-SENSIB-deepseek.no-reason.jsonl",
    "ensaio-20260921-*.jsonl": "the two panel-verdict files above",
}
VERDICTS = pathlib.Path.home() / ".paper2-verdicts"
EXT_CIT = r"(?:json|jsonl|md|py|mjs|js|ts|sh|txt|csv|svg|png|tex|html|zip|tgz|gz|pdf|db|ndjson|sha256|bib)"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# ------------------------------------------------------------------ redaction of packaged copies
REDACAO = [
    ("R1", re.compile(r"/private/tmp/claude-\d+/-Users-[^/]+/[0-9a-f-]{36}/scratchpad/"), "<SCRATCH>/"),
    ("R2", re.compile(r"/Users/[^/\s\"'`]+/"), "<HOME>/"),
    ("R2b", re.compile(r"/Users/[^/\s\"'`]+(?=[\s\"'`,;)]|$)"), "<HOME>"),
    ("R2c", re.compile(r"/Users/"), "<HOME-ROOT>/"),
    ("R4", re.compile(r"/private/tmp\b"), "<TMP>"),
    ("R5", re.compile(r"\bsrv\d{5,}\b"), "<HOST>"),
]
# ------------------------------------------------------------------ privacy gate
PRIV = {
    "home path": re.compile(r"/Users/|Users-lab|/home/\w+|claude-\d{3}"),
    "host name": re.compile(r"\bsrv\d{5,}|MacBook|(?<!threading)\.local\b(?!\s*\()|hostinger|hstgr|tailscale|\.ts\.net\b|nuvini", re.I),
    "ip": re.compile(r"(?<![\d.])(?!127\.0\.0\.1(?![\d.]))(?!0\.0\.0\.0(?![\d.]))(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "e-mail": re.compile(r"[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "credential": re.compile(r"xox[abpr]-[\w-]{6,}|(?<![\w-])sk-[\w-]{8,}|AIza[\w-]{20,}|\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}"
                             r"|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}"),
}
EMAIL_ALLOW = set()   # v1.12 (record 22110203) published no e-mail address
EXCERPT_KEYS = {"input_excerpt", "output_excerpt", "excerpt", "texto", "text", "content", "conteudo",
                "reason", "razao", "rationale", "justificativa", "message", "prompt", "episode_text", "transcript"}
EPISODE_SOURCES = [P2 / SPRINT / "B-censo" / "raw" / n for n in
                   ("gate2-episodes.jsonl", "gate2-verdicts.jsonl", "gate2-calls.jsonl", "gate1-calls.jsonl",
                    "gate1-results.jsonl")] + [BALLAST / n for n in
                   ("episodios-ensaio-20260921.jsonl", "episodios-janela-20260921.jsonl", "alvo-painel-20260921.jsonl")] + [
                   pathlib.Path.home() / ".paper2-verdicts" / n for n in
                   ("ensaio-20260921-PRIMARIO-3fam.jsonl", "ensaio-20260921-SENSIB-deepseek.jsonl")]
WIN = 48


def sha(b):
    return hashlib.sha256(b).hexdigest()


def md5(b):
    return hashlib.md5(b).hexdigest()


def _falso_ip(s):
    return any(int(x) > 255 for x in s.split("."))


def _norm(s):
    s = s.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"').replace("\\\\", "\\")
    return re.sub(r"\s+", " ", s).strip().lower()


def _windows(s, pos=False):
    """48-char windows of a normalized string starting at word boundaries, only text-like ones."""
    out = []
    starts = [0] + [m.end() for m in re.finditer(r" ", s)]
    for i in starts:
        w = s[i:i + WIN]
        if len(w) == WIN and len(re.findall(r"[a-zà-ÿ]{3,}", w)) >= 4:
            out.append((i, hash(w)) if pos else hash(w))
    return out


# A window that also occurs in text the public repository already holds (origin/main, paper2-interventional/)
# is not a new disclosure: episodes are agent sessions on this repository and quote its files. Such
# matches are cleared and counted, never silently dropped.
PUBLIC_TEXT = None
CLEARED = []


def public_text():
    ls = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-l", "origin/main", "paper2-interventional/"],
                        capture_output=True, text=True, check=True).stdout
    shas = [ln.split()[2] for ln in ls.splitlines()
            if re.search(r"\.(md|py|mjs|js|ts|sh|txt|json|csv|html|tex)$", ln) and ln.split()[3] != "-" and int(ln.split()[3]) < 5_000_000]
    out = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"], input="\n".join(shas).encode(),
                         capture_output=True, check=True).stdout
    return _norm(out.decode("utf-8", "replace"))


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def episode_fingerprints():
    fp, n_str, missing = set(), 0, []
    for p in EPISODE_SOURCES:
        if not p.exists():
            missing.append(str(p.name))
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                strs = list(_strings(json.loads(line)))
            except Exception:
                strs = [line]
            for s in strs:
                if len(s) >= WIN:
                    n_str += 1
                    fp.update(_windows(_norm(s)))
    return fp, n_str, missing


def candidate_text(t):
    """Every line of >= 48 chars; _windows keeps only windows with >= 4 words of >= 3 letters."""
    return [m.group(0) for m in re.finditer(r"[^\n]{%d,}" % WIN, t)]


def privado(t, fp, name):
    achados = []
    for k, pat in PRIV.items():
        for m in pat.finditer(t):
            s = m.group(0)
            if k == "ip" and _falso_ip(s):
                continue
            if k == "e-mail" and s in EMAIL_ALLOW:
                continue
            achados.append((k, s))
    hits = 0
    for seg in candidate_text(t):
        ns = _norm(seg)
        for i, h in _windows(ns, pos=True):
            if h in fp:
                w = ns[i:i + WIN]
                if PUBLIC_TEXT is not None and w in PUBLIC_TEXT:
                    CLEARED.append((name, w))
                    continue
                hits += 1
                if hits <= 3:
                    achados.append(("episode text", seg[:90]))
                break
    if name.endswith((".json", ".jsonl", ".ndjson")):
        docs = []
        try:
            docs = [json.loads(t)]
        except Exception:
            for ln in t.splitlines()[:200000]:
                try:
                    docs.append(json.loads(ln))
                except Exception:
                    pass

        def walk(o):
            if isinstance(o, dict):
                for kk, v in o.items():
                    if kk.lower() in EXCERPT_KEYS and isinstance(v, str) and len(v) >= 120:
                        achados.append(("excerpt key", f"{kk}: {v[:60]}"))
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        for d in docs:
            walk(d)
    return achados


def redige(b, rel):
    if rel.endswith((".pdf", ".png", ".gz", ".tgz", ".zip")):
        return b, []
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return b, []
    regras = []
    for nome, pat, rep in REDACAO:
        t2, n = pat.subn(rep, t)
        if n:
            regras.append(f"{nome} x{n}")
            t = t2
    return t.encode("utf-8"), regras


# ------------------------------------------------------------------ census of cited paths
def _expande(tok):
    m = re.search(r"\{([^{}]*)\}", tok)
    if not m:
        return [tok]
    r = re.fullmatch(r"(\d+)\.\.(\d+)", m.group(1))
    opts = [str(i) for i in range(int(r.group(1)), int(r.group(2)) + 1)] if r else m.group(1).split(",")
    return [x for o in opts for x in _expande(tok[:m.start()] + o + tok[m.end():])]


def citados(text):
    achados = {}
    for ln, line in enumerate(text.split("\n"), 1):
        spans = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]+`", line)]
        cands = [w for a, b in spans for w in re.split(r"[\s·]+", line[a + 1:b - 1])]
        resto = "".join(" " if any(a <= i < b for a, b in spans) else ch for i, ch in enumerate(line))
        cands += re.findall(r"[\w./{},*…-]+\." + EXT_CIT + r"\b", resto)
        cands += re.findall(r"\]\(([^)\s]+)\)", line)            # image / link targets
        for w in cands:
            w = re.sub(r":\d[\d,-]*$", "", w.strip(".,;:()[]'\""))
            if w.startswith(("http", "10.5281", "//")) or not re.search(r"\." + EXT_CIT + r"$", w):
                continue
            achados.setdefault(w, set()).add(ln)
    return achados


def _ok_path(p):
    return p.is_file() and not (SKIP_DIRS & set(p.parts))


def resolve(tok):
    """-> set of keys: 'p2:<rel>', 'repo:<rel>', 'ballast:<rel>'."""
    hits = set()
    t = tok.lstrip("…")
    pats = [("*" + x if tok.startswith("…") else x) for x in _expande(t)]
    for x in pats:
        if x.startswith("/"):
            continue
        for base in ("", f"{SPRINT}/", "measurement/", "out/"):
            hits |= {"p2:" + str(p.relative_to(P2)) for p in P2.glob(base + x) if _ok_path(p)}
        hits |= {"repo:" + str(p.relative_to(REPO)) for p in REPO.glob(x) if _ok_path(p)
                 and not str(p.relative_to(REPO)).startswith("paper2-interventional/")}
        if BALLAST.exists():
            hits |= {"ballast:" + str(p.relative_to(BALLAST)) for p in BALLAST.glob(x) if p.is_file()}
            hits |= {"ballast:" + str(p.relative_to(BALLAST)) for p in BALLAST.glob("recibos/" + x) if p.is_file()}
    if not hits and "/" not in t:
        for x in pats:
            hits |= {"p2:" + str(p.relative_to(P2)) for p in P2.rglob(x) if _ok_path(p)
                     and not str(p.relative_to(P2)).startswith("deposit/")}
    return hits


def path_of(key):
    root, rel = key.split(":", 1)
    return {"p2": P2, "repo": REPO, "ballast": BALLAST}[root] / rel


def arc_of(key):
    root, rel = key.split(":", 1)
    return {"p2": "", "repo": "_repo/", "ballast": "_ballast/"}[root] + rel


def never(key):
    rel = key.split(":", 1)[1]
    for pat, why in NEVER:
        if re.search(pat, rel):
            return why
    return None


def git_origin_blobs():
    out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "origin/main"], capture_output=True, text=True, check=True).stdout
    blobs = {}
    for ln in out.splitlines():
        meta, path = ln.split("\t", 1)
        blobs[path] = meta.split()[2]
    return blobs


def git_blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def is_script(arc):
    return arc.endswith((".py", ".sh", ".mjs", ".js", ".ts")) or arc.startswith("pdf-build/")


# ------------------------------------------------------------------ main
def args():
    a = sys.argv[1:]
    no_doi = "--no-doi" in a
    doi = next((a[i + 1] for i, x in enumerate(a) if x == "--doi" and i + 1 < len(a)), None) or \
        os.environ.get("PAPERB_DOI", "").strip() or None
    if no_doi and doi:
        sys.exit("ERROR: --no-doi and a DOI (--doi / PAPERB_DOI) together")
    if not no_doi and not doi:
        sys.exit("ERROR: pass --doi 10.5281/zenodo.NNNN (or PAPERB_DOI), or --no-doi for a dry run")
    if doi and not re.fullmatch(DOI_RE, doi):
        sys.exit(f"ERROR: {doi!r} is not a Zenodo DOI")
    return doi, no_doi


def main():
    doi, no_doi = args()
    fonte = (P2 / FONTE).read_bytes()
    if sha(fonte) != FONTE_SHA:
        print(f"ERROR: {FONTE} is not the pinned rc28 bytes ({sha(fonte)[:12]}…)")
        return 1
    ft = fonte.decode("utf-8")
    if ft.count(PLACEHOLDER) != PLACEHOLDER_COUNT:
        print(f"ERROR: {FONTE} carries the placeholder {PLACEHOLDER} {ft.count(PLACEHOLDER)}x; "
              f"exactly {PLACEHOLDER_COUNT}x is required")
        return 1
    if doi and doi in ft:
        print(f"ERROR: {FONTE} already carries {doi}; the substitution count could not be verified")
        return 1
    dep_t = ft if no_doi else ft.replace(PLACEHOLDER, doi)          # every occurrence
    if not no_doi and (PLACEHOLDER in dep_t or dep_t.count(doi) != PLACEHOLDER_COUNT):
        print(f"ERROR: substitution left {dep_t.count(PLACEHOLDER)} placeholder(s) and wrote the DOI "
              f"{dep_t.count(doi)}x; expected 0 and {PLACEHOLDER_COUNT}")
        return 1
    dep = dep_t.encode("utf-8")
    (HERE / MD).write_bytes(dep)
    env = dict(os.environ)
    env.pop("PAPERB_DOI", None)
    if doi:
        env["PAPERB_DOI"] = doi
    r = subprocess.run(["bash", str(HERE / "build" / "build-pdf.sh")], env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        print("ERROR: build/build-pdf.sh failed")
        return 1
    print("pdf: " + " | ".join(ln for ln in r.stdout.splitlines() if ln.startswith(("missing glyphs", "Pages", "struck"))))
    r = subprocess.run([sys.executable, str(HERE / "sanitize-verdicts.py")], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        print("ERROR: sanitize-verdicts.py failed")
        return 1
    dep = (HERE / MD).read_bytes()
    if dep != dep_t.encode("utf-8"):
        print(f"ERROR: {MD} is not {FONTE} with the placeholder replaced; the deposited text must be the release candidate")
        return 1
    text = dep.decode("utf-8")

    # 1. selection: cited + EXTRA + BALLAST_IN, minus NEVER
    cites = citados(text)
    resolved = {tok: resolve(tok) for tok in cites}
    keys, excluded = set(), {}
    for tok, hs in resolved.items():
        for k in hs:
            (excluded.__setitem__(k, never(k)) if never(k) else keys.add(k))
    for g in EXTRA:
        for p in P2.glob(g):
            if _ok_path(p):
                k = "p2:" + str(p.relative_to(P2))
                (excluded.__setitem__(k, never(k)) if never(k) else keys.add(k))
    for g in BALLAST_IN:
        for p in BALLAST.glob(g):
            if p.is_file():
                k = "ballast:" + str(p.relative_to(BALLAST))
                (excluded.__setitem__(k, never(k)) if never(k) else keys.add(k))
    pdf_build = ["build/build-pdf.sh", f"build/preamble-paperB-v{VERSION}.tex"]
    derived = sorted(p for p in DERIVED_DIR.rglob("*") if p.is_file())
    if len(derived) != 3:
        print(f"ERROR: expected 3 derived files under build/derived/, found {len(derived)}")
        return 1

    # 2. privacy fingerprints
    global PUBLIC_TEXT
    PUBLIC_TEXT = public_text()
    fp, n_str, fp_missing = episode_fingerprints()
    if fp_missing:
        print(f"WARNING: episode fingerprint sources missing: {fp_missing}")
    # positive control: the gate must see what it is meant to see, or a zero means nothing
    ctl, ctl_hit = 0, 0
    for ln in EPISODE_SOURCES[0].read_text(encoding="utf-8").splitlines():
        for kk in ("input_excerpt", "output_excerpt"):
            v = json.loads(ln).get(kk) or ""
            if len(v) >= 200:
                ctl += 1
                ctl_hit += any(k == "episode text" for k, _ in privado(v[50:350], fp, "control.md"))
    synth = {"home path": "/Users/someone/x", "ip": "10.1.2.3", "e-mail": "a@b.org", "credential": "xoxb-1234567890-a",
             "host name": "srv1234567"}
    blind = [k for k, v in synth.items() if not any(kk == k for kk, _ in privado(v, fp, "control.md"))]
    if ctl == 0 or ctl_hit < ctl or blind:
        print(f"GATE BLIND: episode control {ctl_hit}/{ctl}, synthetic misses {blind} — the gate cannot certify a zero")
        return 1
    CLEARED.clear()

    # 3. zips
    itens, achados, scrubbed = [], [], []

    def scan(name, data):
        if name.endswith((".png", ".gz", ".pdf")):
            return
        if name.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                for m in tf.getmembers():
                    if m.isfile():
                        scan(f"{name}!{m.name}", tf.extractfile(m).read())
            return
        t = data.decode("utf-8", "replace")
        achados.extend((name, k, s) for k, s in privado(t, fp, name))

    members = {ZA: [], ZS: []}
    for k in sorted(keys):
        arc = arc_of(k)
        members[ZS if is_script(arc) else ZA].append((arc, path_of(k)))
    for rel in pdf_build:
        members[ZS].append(("pdf-build/" + rel.rsplit("/", 1)[1], HERE / rel))
    for p in derived:
        members[ZA].append(("_derived/" + str(p.relative_to(DERIVED_DIR)), p))
    for n in DEPOSIT_SCRIPTS:
        members[ZS].append(("deposit-paperB/" + n, HERE / n))
    for zname, lst in members.items():
        with zipfile.ZipFile(HERE / zname, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for arc, src in sorted(lst):
                orig = src.read_bytes()
                emp, regras = redige(orig, arc)
                zi = zipfile.ZipInfo(arc, DATA_FIXA)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o755 if arc.endswith(".sh") else 0o644) << 16
                z.writestr(zi, emp)
                it = {"path": arc, "in": zname, "bytes": len(emp), "sha256": sha(emp)}
                if regras:
                    it["sha256_source"] = sha(orig)
                    it["redaction"] = regras
                    scrubbed.append((arc, zname, regras, sha(orig), sha(emp)))
                itens.append(it)
                scan(arc, emp)
    for name in (MD, PDF):
        b = (HERE / name).read_bytes()
        itens.append({"path": name, "in": "loose", "bytes": len(b), "sha256": sha(b)})
    scan(MD, dep)
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"], capture_output=True, check=True).stdout
    scan(PDF + " (text)", txt)
    ph_n = {MD: text.count(PLACEHOLDER), PDF + " (text)": txt.decode("utf-8", "replace").count(PLACEHOLDER)}
    ph_left = [k for k, v in ph_n.items() if v]
    raw = (HERE / PDF).read_bytes().decode("latin-1")
    achados += [(PDF + " (bytes)", "home path", x) for x in re.findall(r"/Users/|Users-lab|claude-\d{3}", raw)]
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(HERE / PDF)], capture_output=True,
                                                             text=True, check=True).stdout).group(1))

    # 4. census
    packaged = {i["path"] for i in itens}
    origin = git_origin_blobs()
    v112 = {e["key"]: e["checksum"].split(":", 1)[1] for e in json.loads(V112_FILES.read_text())["entries"]}
    linhas, lacunas = [], []
    for tok, lns in sorted(cites.items()):
        hs = resolved[tok]
        cov = {}
        for k in hs:
            arc, p = arc_of(k), path_of(k)
            b = p.read_bytes()
            repo_rel = ("paper2-interventional/" + k[3:]) if k.startswith("p2:") else k[5:] if k.startswith("repo:") else None
            if arc in packaged:
                cov[k] = "package"
            elif repo_rel and origin.get(repo_rel) == git_blob(b):
                cov[k] = "public repo (origin/main, unchanged)"
            elif p.name in v112 and v112[p.name] == md5(b):
                cov[k] = "v1.12 record 22110203 (same md5)"
            elif k in excluded:
                cov[k] = f"declared: {excluded[k]}"
            else:
                cov[k] = None
        decl = DECLARED.get(tok)
        if decl and not any(cov.values()):
            where = ["declared"]
            ok = True
        elif "/" in tok.lstrip("…") and not tok.startswith("…"):
            ok = bool(hs) and all(cov.values())
            where = sorted({c for c in cov.values() if c})
        else:
            ok = any(cov.values())
            where = sorted({c for c in cov.values() if c})
        row = {"cited": tok, "lines": sorted(lns)[:6], "covered_by": where}
        if decl and where == ["declared"]:
            row["declared_why"] = decl
        linhas.append(row)
        if not ok:
            lacunas.append((tok, sorted(lns)[:5], {k: excluded.get(k) or "not covered" for k, c in cov.items() if not c} or "does not resolve"))
    stale_decl = sorted(set(DECLARED) - set(cites))

    sizes = {n: (HERE / n).stat().st_size for n in (MD, PDF, ZA, ZS)}
    man = {
        "generated_by": "deposit/paperB/build-package.py",
        "record": {
            "concept_doi": "10.5281/zenodo.21964093",
            "previous_version": "10.5281/zenodo.22110203 (v1.12, published 2026-08-26T12:01Z)",
            "new_version_of": "22110203 (POST /api/records/22110203/versions)",
            "version": VERSION,
            "doi": doi,
            "dry_run": no_doi,
            "note": ("DRY RUN (--no-doi): the version DOI placeholder is still in the text and the PDF; NOT FOR DEPOSIT"
                     if no_doi else "the version DOI reserved by the new-version draft, substituted for the placeholder"),
        },
        "manuscript": {
            "source": FONTE, "sha256_source": sha(fonte), "sha256_deposited": sha(dep),
            "placeholder": (f"the token VERSION-DOI in square brackets, {PLACEHOLDER_COUNT}x: the status header "
                            "and working-list item 8"),
            "placeholder_count": PLACEHOLDER_COUNT,
            "difference": ("none (dry run): the placeholder is kept" if no_doi else
                           f"the placeholder replaced by {doi} at all {PLACEHOLDER_COUNT} occurrences "
                           "(status header, working-list item 8); nothing else"),
            "pdf": f"pandoc + xelatex x2 via pdf-build/build-pdf.sh (in {ZS}); {pages} pages; 0 missing glyphs; "
                   "figures B1/B2 rendered from the PNG that the same generator wrote beside each SVG (no SVG converter "
                   "in this TeX install); the .md is not edited",
            "pdf_pages": pages,
        },
        "layout": {"zip paths": "relative to paper2-interventional/", "_repo/": "repository root (memoria-nox/)",
                   "_ballast/": "the trial ballast kept outside the repository (Appendix B: 79 artifacts outside)",
                   "pdf-build/": "the PDF build",
                   "_derived/": "files derived for this deposit from sources that are not deposited",
                   "deposit-paperB/": "the script that writes _derived/"},
        "derived": {
            "panel-verdicts/": "the two panel-verdict files the manuscript cites (ensaio-20260921-PRIMARIO-3fam.jsonl, "
                               "ensaio-20260921-SENSIB-deepseek.jsonl) with the free-text fields `reason` and `detail` "
                               "removed; kept per row: episode_id, panelist, family, model, model_served, verdict, "
                               "level, status, stop_reason, attempts (the sources carry no timestamp field). Written by "
                               "deposit-paperB/sanitize-verdicts.py; SANITIZED.json gives the source and derived sha256 "
                               "and the label counts. The manuscript does not cite these copies.",
        },
        "redaction_rules": {
            "R1": "absolute path of the local temporary scratchpad -> <SCRATCH>/",
            "R2": "author's absolute home directory -> <HOME>/ (R2b: at end of token -> <HOME>)",
            "R4": "macOS temporary directory -> <TMP>",
            "R5": "VPS host name -> <HOST>",
            "not redacted": "'~/' (home-relative, carries no user name): kept so receipts and ballast copies keep the bytes their recorded hashes cover",
        },
        "never_packaged": [{"pattern": a, "why": b} for a, b in NEVER],
        "excluded_cited_files": [{"path": arc_of(k), "why": v} for k, v in sorted(excluded.items())],
        "declared_not_packaged": [{"cited": t, "why": r} for t, r in sorted(DECLARED.items())],
        "census": {
            "scope": "every path-like token the manuscript cites (code spans, bare file names, link targets)",
            "cited": len(linhas),
            "in_package": sum(1 for x in linhas if "package" in x["covered_by"]),
            "only_public_repo": sum(1 for x in linhas if x["covered_by"] and "package" not in x["covered_by"]
                                    and any(c.startswith("public repo") for c in x["covered_by"])),
            "only_v1_12": sum(1 for x in linhas if x["covered_by"] == ["v1.12 record 22110203 (same md5)"]),
            "declared": sum(1 for x in linhas if x["covered_by"] and all(c.startswith("declared") for c in x["covered_by"])),
            "gaps": len(lacunas),
            "rows": linhas,
        },
        "privacy_gate": {
            "checks": list(PRIV) + ["episode text (48-char fingerprints)", "excerpt keys in JSON"],
            "episode_fingerprint_sources": [p.name for p in EPISODE_SOURCES if p.exists()],
            "episode_strings_fingerprinted": n_str, "fingerprints": len(fp),
            "findings": len(achados),
            "positive_control": f"{ctl_hit}/{ctl} episode excerpts (300-char slices) caught; 5/5 synthetic patterns caught",
            "cleared_public_matches": len(CLEARED),
            "cleared_public_matches_by_file": sorted({n for n, _ in CLEARED}),
            "cleared_rule": "an episode fingerprint window that also occurs in text of paper2-interventional/ on "
                            "origin/main (already public) is cleared: the episode quotes the repository",
        },
        "upload": {n: {"bytes": s} for n, s in sizes.items()} | {"MANIFEST-v%s.json" % VERSION: {}, "SHA256SUMS": {}},
        "zip_members": {ZA: len(members[ZA]), ZS: len(members[ZS])},
        "items": itens,
    }
    (HERE / f"MANIFEST-v{VERSION}.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    scan(f"MANIFEST-v{VERSION}.json", (HERE / f"MANIFEST-v{VERSION}.json").read_bytes())
    if achados:  # re-write the count after scanning the manifest itself
        man["privacy_gate"]["findings"] = len(achados)
        (HERE / f"MANIFEST-v{VERSION}.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ups = [MD, PDF, f"MANIFEST-v{VERSION}.json", ZA, ZS]
    (HERE / "SHA256SUMS").write_text("".join(f"{sha((HERE / n).read_bytes())}  {n}\n" for n in ups), encoding="utf-8")
    lines = ["SCRUBBED — packaged copies that differ from their source (Paper B v%s)" % VERSION, "",
             "The repository and the ballast were NOT overwritten: each copy below was redacted only inside the",
             "zip. MANIFEST-v%s.json keeps both hashes ('sha256_source', 'sha256') and the rules." % VERSION, ""]
    for arc, zname, regras, a, b in scrubbed:
        lines += [arc, f"  in:             {zname}  [{', '.join(regras)}]", f"  source sha256:  {a}", f"  packaged:       {b}", ""]
    (HERE / "SCRUBBED.txt").write_text("\n".join(lines), encoding="utf-8")

    total = sum((HERE / n).stat().st_size for n in ups + ["SHA256SUMS"])
    print(f"manuscript: {MD} == {FONTE} ({FONTE_SHA[:12]}…)" + (" (placeholder kept: --no-doi)" if no_doi else
          f" with the placeholder -> {doi}") + f"; PDF {pages} pages")
    print(f"zip members: {ZA} {len(members[ZA])}, {ZS} {len(members[ZS])}; redacted copies: {len(scrubbed)}")
    print(f"upload: {len(ups) + 1} files, {total:,} bytes")
    c = man["census"]
    print(f"census: {c['cited']} cited; package {c['in_package']}, only public repo {c['only_public_repo']}, "
          f"only v1.12 {c['only_v1_12']}, declared {c['declared']}, gaps {c['gaps']}")
    if stale_decl:
        print(f"WARNING: DECLARED entries no longer cited: {stale_decl}")
    rc = 0
    if lacunas:
        for tok, lns, falta in lacunas:
            print(f"  GAP  `{tok}` (lines {lns}): {falta}")
        print(f"CENSUS: {len(lacunas)} cited path(s) neither packaged, versioned, in v1.12 nor declared — do NOT deposit")
        rc = 1
    print(f"privacy fingerprints: {len(fp):,} windows from {n_str:,} episode/panel strings; "
          f"{len(CLEARED)} match(es) cleared as already-public repository text in {len({n for n, _ in CLEARED})} file(s)")
    if achados:
        from collections import Counter
        for (a, k, s), n in Counter(achados).most_common(60):
            print(f"  PRIVATE  {a}: [{k}] {s!r}" + (f" x{n}" if n > 1 else ""))
        print(f"GATE: {len(achados)} private occurrence(s) — do NOT deposit")
        rc = 1
    else:
        print("GATE: 0 home paths, host names, IPs, e-mails, credential-like strings or episode text in any packaged byte")
    if no_doi:
        print(f"DRY RUN (--no-doi): {PLACEHOLDER} kept: {', '.join(f'{k} {v}x' for k, v in ph_n.items())} — "
              "NOT FOR DEPOSIT; rebuild with --doi after the draft reserves the DOI")
        if set(ph_n.values()) != {PLACEHOLDER_COUNT}:
            print(f"ERROR: dry run expected the placeholder {PLACEHOLDER_COUNT}x in the .md and in the PDF text, "
                  f"found {ph_n}")
            rc = 1
    elif ph_left:
        print(f"GATE: the placeholder {PLACEHOLDER} survived: {ph_n} — do NOT deposit")
        rc = 1
    else:
        pdf_doi = txt.decode("utf-8", "replace").count(doi)
        print(f"placeholder: 0 left; {doi} {text.count(doi)}x in the .md, {pdf_doi}x in the PDF text "
              f"(the {PLACEHOLDER_COUNT} substitutions plus the PDF date line)")
        if text.count(doi) != PLACEHOLDER_COUNT or pdf_doi != PLACEHOLDER_COUNT + 1:
            print(f"ERROR: expected the DOI {PLACEHOLDER_COUNT}x in the .md and {PLACEHOLDER_COUNT + 1}x in the PDF text")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
