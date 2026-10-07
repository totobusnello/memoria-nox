# PR-B privacy pass (Paper B files for the public repository)

Date: 2026-10-07. Scope: untracked Paper B files under `paper2-interventional/` plus
`scripts/estende-lastro-p2.py`, enumerated with `git status --porcelain --untracked-files=all`
(392 untracked paths in total). Nothing was staged, committed or pushed; no file in the list was edited.

Publish list: `PR-B-FILES.txt` (229 lines = 227 Paper B files + this file + the list itself).
The 227 files total 12,651,650 bytes; the largest is `B-sham-v2/job-janela2/PROGRESSO.ndjson` (622,468 B).

## What is in the list

| group | files |
|---|---:|
| `B-v2-rc3.md` … `B-v2-rc27.md` | 25 |
| `APPLY-B-rc3` … `rc25` | 23 |
| `REVIEW-B-*` | 7 |
| `LASTRO-B-item10.md` | 1 |
| `B-rc3/` … `B-rc27/` (parity/checks scripts and outputs, Zenodo record JSON of v1.10/v1.12) | 42 |
| `B-registered/` | 19 |
| `B-censo/` (without `raw/`) | 12 |
| `B-sham-v2/` (`janela-lancamento/`, `job-janela2/` metadata, `job-v1/` metadata, `job-v2b/HEARTBEAT`) | 37 |
| `figures/figB1-h1a-inversao-registrado*` (v1–v4: png, svg, run.json) | 12 |
| `receipts/` (23 codex receipts; each one is cited by at least one Paper B file) | 23 |
| `deposit/paperB/` (scripts, md, html, MANIFEST, SHA256SUMS, SCRUBBED, READY, DRAFT-READBACK, .gitignore) | 11 |
| `measurement/` (ITT estimator, C12, determinism, figB1 v1–v4) | 7 |
| `out/` (ITT-REGISTRADO v1–v4, C12 ×3) | 7 |
| `scripts/estende-lastro-p2.py` | 1 |

Paper B membership was checked by citation. Every `measurement/`, `out/`, `figures/` file and
`scripts/estende-lastro-p2.py` is cited by B-v2-rc27, an APPLY-B file or `deposit/paperB/`, and none of
them by any A-* file.

## Scans run

1. **Pattern scan** over all candidates: personal home paths, `/home/<user>`, VPS host names (`srv` + digits),
   tailnet and hosting-provider names, IPv4, e-mail, Slack/OpenAI/Google/GitHub/npm/Bearer credential
   shapes, `root@host`.
2. **The deposit's own privacy gate** (`deposit/paperB/build-package.py`, functions `privado` and
   `episode_fingerprints`, imported read-only): home path, host name, non-loopback IP, e-mail,
   credential, **episode text** (607,355 48-char fingerprints of 24,431 strings from the 10 episode and
   panel sources, all present), and JSON keys that carry excerpts. Windows that already appear in public
   `origin/main` text are cleared, as the gate does (4 cleared). Positive control: 21/21 episode slices
   of 300 chars were caught.
3. **gitleaks** (`gitleaks dir`, repository `.gitleaks.toml`) over a copy of the 227 files.
4. **PNG/SVG metadata** of the figures: no paths, hosts or authorship strings.
5. **Census of manuscript citations** (`MANIFEST-v2.0.json` → `census.rows`, 291 rows) against the list:
   127 in the list, 77 already tracked, 85 not on disk or declared (covered by the Zenodo package
   or declared), and 2 untracked and not listed: `B-censo/raw/gate1-calls.jsonl` (episode text,
   excluded on purpose) and `B-sham-v2/job-janela2-runs.tgz` (> 5 MB, in the Zenodo package).

## Findings

- **Episode text: none** in any listed file (gate 2, after the 4 public-text clearances).
- **Real personal data: 2 files, both excluded from the list (see below).**
- The rest are **detector literals and synthetic fixtures**, kept as they are. They are the regexes of
  the parity scripts' privacy checks (`B-rc3…rc11/parity-*.py`), mutation tests that inject a fake path,
  IP or token (`parity-rc8/9/10/11/12/13/23.py`), and the gate's own patterns and synthetic controls
  (`deposit/paperB/build-package.py`). In `APPLY-B-rc12/rc13.md` the home path appears only as the
  literal prefix with no user name.
- No credential of any kind. `B-censo/GATES.md` mentions that a Slack user token exists inside episode
  data, and shows it only as the redacted prefix `xoxp-…`. The data itself is in `raw/`, which is excluded.
- Receipts already carry `host: (redacted)` and a home-relative `cwd: ~/…`.

## Edits made

None. The only two files that needed a fix are hash-pinned, so they were left byte-identical and excluded.

## Excluded, and why

| path | why |
|---|---|
| `B-sham-v2/JANELA-LANCAMENTO.md` | names the research VPS host (line 7). **Hash-pinned**: `sha256_source` in `deposit/paperB/MANIFEST-v2.0.json`, `PINS["janela"]` in `B-rc23/parity-rc23.py`, cited by rc27. Its redacted copy (rule R5) is in `artifacts-v2.0.zip` |
| `REVIEW-B-rc23-codex-2026-10-07.md` | 5 absolute home paths (lines 12–16). **Hash-pinned**: `sha256_source` in MANIFEST-v2.0.json. Its redacted copy (R2 ×5) is in `artifacts-v2.0.zip` |
| `B-sham-v2/job-janela2-runs.tgz`, `job-janela2/runs/*.json` (21) | > 5 MB (blob guard). They are in the Zenodo package (tgz) and in the ballast |
| `B-sham-v2/job-v1/runs/*` (13), `job-v2b/runs/*` (21) | per-run outputs, ~2.4 MB each (~83 MB in all). The manifest's `never_packaged` rule says *"per-run outputs; packaged as the job's -runs.tgz"*. `job-v2b-runs.tgz` is already tracked, and the `job-v1` runs are byte-identical to `job-v2b` (sha256, all 13; `REAL.json` also matches the copy inside the tracked tgz) |
| `B-censo/raw/` (incl. its `.gitignore`) | episode excerpts and panelist reasons |
| `deposit/paperB/artifacts-v2.0.zip` (17.1 MB), `scripts-v2.0.zip`, `*.pdf`, `build/` | build outputs (and `build/` is ignored by the root `.gitignore`) |
| `measurement/sprint-stanford-telemetry-deposit.py`, `stanford-deposit/` | Stanford dataset, not Paper B |
| `A-v1.1-rc3…rc7.md` | Paper A leftovers |
| `metodologia*`, `noxmem-*`, `phase2-inputs/`, `apelacao-formulario-preenchido-2026-10-04.jpg` | not Paper B |

If the two pinned files must be public, there are two options. One is to publish the redacted copies
from `artifacts-v2.0.zip`; their hash is the MANIFEST's `sha256`, but `parity-rc23.py` would then fail
its JANELA pin. The other is to edit them and accept that `sha256_source` and that pin go stale. The
redacted copies are already public through Zenodo once the deposit is made.

## Guards run

| guard | result |
|---|---|
| `scripts/guarda-blob-grande.sh tudo` | exit 0, no new blob > 5 MB |
| the same guard logic fed this list (scratch copy that adds a list-file mode) | exit 0. Positive control: the excluded paths flag 23 blobs |
| `scripts/censo-lastro-do-manuscrito.py` (default, Paper 1) | exit 0 |
| same, `--doc` B-v2-rc27.md | exit 1: `scripts/adversary-run.sh` is cited, but it lives in the umbrella repo, not here. 168 paths are "not resolved" because Paper B cites them relative to `paper2-interventional/`. The MANIFEST census above is the check that applies to Paper B |
| gitleaks with the repo config | **20 findings, all false positives** (see below) |

## Blocks publication: gitleaks in CI (`security.yml`, runs on `pull_request`)

The 20 findings fall into three groups:

- 18 × `generic-api-key` in `B-rc18/zenodo-22110203-{files,record}.json` and
  `B-rc19/zenodo-21978476-{files,record}.json`. The `key` field is the deposited file name, the same
  false positive already allowlisted for `A-recon-evidence/zenodo-*.json`.
- 1 × `generic-api-key` at `deposit/paperB/build-package.py:490`: the gate's synthetic Slack-shaped
  control value.
- 1 × `sumologic-access-token` at `B-rc23/parity-rc23.py:71`: a sha256 pin.

Proposed `.gitleaks.toml` change, tested (0 leaks on the copy). Add one path to `[allowlist].paths`:

```
  '''paper2-interventional/_sprint-2026-10-04/B-rc1[89]/zenodo-[0-9]+-(files|record)\.json''',
```

Add a `regexes` list to the same `[allowlist]` with two anchored entries: the exact synthetic value on
`build-package.py:490` (`"credential": …`) and the exact 64-hex value on `parity-rc23.py:71`. They are
not repeated here, so that this file does not trigger the same rule.

## Notes for the commit

- Add files only from `PR-B-FILES.txt`. Never add `deposit/paperB/` or `B-sham-v2/` whole, because
  the zips, PDF and `runs/` are not ignored there.
- `deposit/paperB/.gitignore` does not ignore `*.zip` or `*.pdf`. (Paper A's v1.1 zip was versioned
  on purpose, so this was left as it is.)
