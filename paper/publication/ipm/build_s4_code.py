#!/usr/bin/env python3
"""Build supplementary material S4 for the IP&M submission: the code and evidence, anonymized.

S4 is one zip, `supplement/S4-code-and-evidence.zip`, with five parts (scope decided on 2026-11-27,
`SUBMISSION-CHECKLIST.md`):

  nox-mem/                 the system's source, `nox-mem/` of the public code repository at tag
                           v3.4.0 (2026-09-28), the first tagged release and the nearest to the runs;
  harness/q4-comparison/   the cross-system harness of Section 4, `eval/q4-comparison/` at HEAD,
                           without `cache/`, `ambiente-congelado/` and the raw outputs (they carry
                           benchmark text, LoCoMo is CC BY-NC 4.0; the stripped per-query outputs
                           are in `evidence/`);
  harness/evermembench/    the EverMemBench harness of Section 5, `eval/evermembench/` at HEAD;
  specs/        the execution plan committed before the first run of the comparison;
  evidence/     the deposited evidence record v1.0.0 (per-query outputs and `verify_dataset.py`),
                taken from the published zip, whose md5 is pinned below.

The files are copied as they stand. The only changes are the replacements in RULES (author,
handle, e-mail, DOIs, repository and image links, the user name in a macOS path, the
operator's nickname and the agents' names) and, in `nox-mem/package.json`, the author/homepage/repository/bugs fields. In
`evidence/`, the data files are byte-identical to the record; only text files that carried an
identifier change, and `SHA256SUMS` is regenerated so `verify_dataset.py` still passes (the build
runs it and fails if it does not).

    python3 -I build_s4_code.py --nox-mem <clone of the code repository> \
        --evidence-zip <nox-mem-section6-evidence-1.0.0.zip>
    python3 -I build_s4_code.py --check ...   # rebuild in memory; exit 1 if the zip differs or an identifier remains
"""
import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "supplement" / "S4-code-and-evidence.zip"
TOP = "S4-code-and-evidence"

NOX_MEM_TAG = "v3.4.0"
EVIDENCE_MD5 = "3abd9a47823d561ca392f1bb30f0e4e6"  # zenodo.org/api/records/23146656, checked 2026-11-27
EVIDENCE_PREFIX = "nox-mem-section6-evidence-1.0.0/"
HARNESSES = {"eval/q4-comparison/": "harness/q4-comparison/", "eval/evermembench/": "harness/evermembench/"}
HARNESS_EXCLUDE = re.compile(r"^eval/q4-comparison/(cache|output|output-2026-09-10|ambiente-congelado)/|/__pycache__/")
SPEC = "specs/2026-05-23-Q4-comparison-execution-plan.md"
FIXED_DATE = (2026, 11, 27, 0, 0, 0)

AGENTS = {"Nox": "Agent A", "Boris": "Agent B", "Forge": "Agent C",
          "Atlas": "Agent D", "Cipher": "Agent E", "Lex": "Agent F"}  # same map as S1-S3

WITHHELD = "[withheld for review]"
RULES = [
    (re.compile(r"ghcr\.io/totobusnello/[\w.:/-]+"), "[container image withheld for review]"),
    (re.compile(r"(git\+)?(https?://)?(www\.)?github\.com/totobusnello/[\w.-]+(/[\w./#-]*)?"),
     "[repository withheld for review]"),
    (re.compile(r"(https?://doi\.org/)?10\.5281/zenodo\.\d+"), "[DOI withheld for review]"),
    (re.compile(r"Luiz Antonio Busnello( \(Toto\))?"), "[author withheld for review]"),
    (re.compile(r"Busnello, L\. ?A\."), "[Author]"),
    (re.compile(r"\bZenodo\b"), "[data repository]"),
    (re.compile(r"\bmemoria-nox\b"), "research-repo"),  # slug-safe: it is also a scope value in tests
    (re.compile(r"Totó|\bToto\b"), "Operator"),
    (re.compile(r"\btoto\b"), "operator"),
    (re.compile(r"/Users/lab\b"), "/Users/user"),
    (re.compile(r"\bnuvini\b"), "acme"),
    (re.compile(r"\bNUVIVI\b"), "ACME"),
    # case-sensitive, and not before a hyphen: "Nox-mem" and "nox-mem" are the system
    (re.compile(r"\b(" + "|".join(AGENTS) + r")\b(?!-)"), lambda m: AGENTS[m.group(1)]),
]

FORBIDDEN = re.compile(
    r"Busnello|\bToto\b|Totó|\bLuiz\b|ORCID|0009-0007|generantis|nuvini|nuvivi|labf|totobusnello"
    r"|zenodo|10\.5281|memoria-nox|/Users/lab\b|srv\d{4,}"
    r"|[\w.+-]+@[\w-]+\.(com|br|org|ai|io|net)\b", re.I)
AGENT_NAMES = re.compile(r"\b(" + "|".join(AGENTS) + r")\b(?!-)")
IPV4 = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\w.])")
# loopback, unspecified and the three documentation ranges (RFC 5737) identify nobody
IP_OK = re.compile(r"^(127\.|0\.0\.0\.0$|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|10\.0\.0\.0$)")
# fictional addresses inside EverMemBench questions (benchmark text, not anyone's address)
BENCHMARK_TEXT_OK = {"contact@greentech.com"}


def git(*args, cwd=REPO):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def collect(nox_mem, evidence_zip):
    """Return {path inside TOP: bytes} before anonymization, and the set of evidence data paths."""
    files = {}
    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", NOX_MEM_TAG, "nox-mem", cwd=nox_mem)))
    for m in tar.getmembers():
        if m.isfile():
            files[m.name] = tar.extractfile(m).read()
    for src, dst in HARNESSES.items():
        for p in git("ls-files", "-z", src).decode().split("\0"):
            if p and not HARNESS_EXCLUDE.search(p):
                files[dst + p[len(src):]] = git("show", "HEAD:" + p)
    files["specs/" + pathlib.Path(SPEC).name] = git("show", "HEAD:" + SPEC)
    raw = pathlib.Path(evidence_zip).read_bytes()
    if hashlib.md5(raw).hexdigest() != EVIDENCE_MD5:
        sys.exit(f"{evidence_zip}: md5 differs from the published record ({EVIDENCE_MD5})")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            if not n.endswith("/"):
                files["evidence/" + n[len(EVIDENCE_PREFIX):]] = z.read(n)
    return files


def anonymize(name, data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data  # binary: checked by residual() on its bytes
    if name == "nox-mem/package.json":
        pkg = json.loads(text)
        pkg["author"] = "[author withheld for review]"
        for k in ("homepage", "repository", "bugs"):
            pkg.pop(k, None)
        text = json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"
    for pat, rep in RULES:
        text = pat.sub(rep, text)
    return text.encode("utf-8")


def residual(name, data):
    text = data.decode("utf-8", errors="replace")
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in list(FORBIDDEN.finditer(line)) + list(AGENT_NAMES.finditer(line)):
            if m.group(0) not in BENCHMARK_TEXT_OK:
                hits.append((i, m.group(0), line.strip()[:120]))
        for m in IPV4.finditer(line):
            if all(int(g) <= 255 for g in m.groups()) and not IP_OK.match(m.group(0)):
                hits.append((i, m.group(0), line.strip()[:120]))
    return hits


def regenerate_sums(files):
    names = sorted(n[len("evidence/"):] for n in files if n.startswith("evidence/") and n != "evidence/SHA256SUMS")
    old = files["evidence/SHA256SUMS"].decode()
    listed = sorted(l.split("  ", 1)[1] for l in old.splitlines() if l.strip())
    if listed != names:
        sys.exit("evidence: SHA256SUMS of the record does not list exactly the record's files")
    files["evidence/SHA256SUMS"] = "".join(
        f"{hashlib.sha256(files['evidence/' + n]).hexdigest()}  {n}\n" for n in names).encode()


README = """# Supplementary material S4: code and evidence (anonymized)

Prepared for double-anonymized review. The author's name, handle and e-mail address, DOIs,
repository and container-image links, the repository's name (now `research-repo`), the user name
in a macOS path, the operator's nickname (now "Operator") and the agents' names (now "Agent A" to "Agent F", the same map as in S1 to S3) are
replaced; no other line is changed. Paths under `/root/.openclaw/` are the agent platform's
defaults, identify no one, and are kept because tests derive values from them. The public
locations are on the title page.

| directory | what it is | backs in the article |
|---|---|---|
| `nox-mem/` | the system: TypeScript source, tests, prompts, `package.json` (MIT), at release {tag} (2026-09-28), the first tagged release and the nearest to the runs | Section 3 |
| `harness/q4-comparison/` | the cross-system harness: runners, one adapter per system, corpus loader, aggregation and scorer, tests and the compose file; `adapters/nox_mem.py` is the hybrid pipeline that Section 4 measured | Section 4 |
| `harness/evermembench/` | the EverMemBench harness: adapter, batch runners, aggregation scripts, per-batch results and the backbone matrix | Section 5 |
| `specs/` | the execution plan of the comparison, committed to the public repository before the first run | Section 4 (pre-specification) |
| `evidence/` | the deposited evidence record v1.0.0: per-query outputs of the full-set runs and `verify_dataset.py` | Section 4 figures |

## Checking the Section 4 figures

    cd evidence
    python3 verify_dataset.py

Python 3.9 or later, standard library only; it writes nothing and exits 0 only if every check
passes (`evidence/README.md` lists the checks). The data files under `evidence/runs/` and
`evidence/corpus/` are byte-identical to the deposited record. {n_edited} text files of the record
carried an identifier and were edited ({edited}); `SHA256SUMS` was regenerated for them, so its
lines for those files differ from the record's.

## What is not here, and why

- The raw outputs and caches of the Section 4 harness (`output*/`, `cache/`): they contain
  LoCoMo and LongMemEval text, and LoCoMo is CC BY-NC 4.0. The stripped outputs in `evidence/`
  keep every id, rank, score and latency needed to score the runs.
- The benchmarks themselves, which come from their authors under their own licences;
  `harness/q4-comparison/lib/corpus_loader.py` downloads LoCoMo and LongMemEval.
- The outputs of the canonical 2026-06-15 run (n = 100 per dataset), which were not retained;
  the article and `evidence/README.md` say so.
- Operational material of the author's deployment (installation guide, server runbooks, agent
  profiles), which is not part of the method.
- Git history. Commit dates (for example, that the execution plan predates the first run) can be
  checked in the public repository named on the title page.
"""


def build(nox_mem, evidence_zip):
    raw = collect(nox_mem, evidence_zip)
    files = {n: anonymize(n, d) for n, d in raw.items()}
    edited = sorted(n[len("evidence/"):] for n in files
                    if n.startswith("evidence/") and files[n] != raw[n])
    data_edited = [n for n in edited if n.startswith(("runs/", "corpus/"))]
    if data_edited:
        sys.exit(f"evidence data files changed by anonymization: {data_edited}")
    regenerate_sums(files)
    files["README-REVIEW.md"] = README.format(tag=NOX_MEM_TAG, n_edited=len(edited),
                                       edited=", ".join(f"`{e}`" for e in edited)).encode()
    return files


def residuals(files):
    out = []
    for name in sorted(files):
        for i, tok, ctx in residual(name, files[name]):
            out.append(f"{name}:{i}: identifier {tok!r}: {ctx}")
        if AGENT_NAMES.search(name) or FORBIDDEN.search(name):
            out.append(f"{name}: identifier in the path")
    return out


def verify_evidence(files):
    with tempfile.TemporaryDirectory() as tmp:
        for n, d in files.items():
            if n.startswith("evidence/"):
                p = pathlib.Path(tmp, n)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(d)
        r = subprocess.run([sys.executable, "-I", "verify_dataset.py"], cwd=pathlib.Path(tmp, "evidence"),
                           capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-3:]


def to_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(f"{TOP}/{name}", FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[name])
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nox-mem", required=True, help="clone of the public code repository (has tag %s)" % NOX_MEM_TAG)
    ap.add_argument("--evidence-zip", required=True, help="nox-mem-section6-evidence-1.0.0.zip as published")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = build(a.nox_mem, a.evidence_zip)
    bad = residuals(files)
    for line in bad:
        print(line)
    rc, tail = verify_evidence(files)
    print(f"verify_dataset.py on the anonymized evidence: exit {rc}: {' | '.join(tail)}")
    blob = to_zip(files)
    if a.check:
        if not OUT.exists() or OUT.read_bytes() != blob:
            print(f"{OUT.name}: stale, rerun build_s4_code.py")
            bad.append("stale")
        sys.exit(1 if bad or rc else 0)
    if bad or rc:
        sys.exit(f"{len(bad)} identifier(s), verify exit {rc}; nothing written")
    OUT.write_bytes(blob)
    print(f"wrote {OUT.relative_to(REPO)}: {len(files)} files, {len(blob):,} bytes, "
          f"sha256 {hashlib.sha256(blob).hexdigest()}")


if __name__ == "__main__":
    main()
