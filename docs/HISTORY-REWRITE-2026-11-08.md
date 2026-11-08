# History rewrite of 2026-11-08

On 2026-11-08 the author decided to remove from this repository's public history 14 files that held
material from the private corpus, including data about third parties. The files had already been
taken off `main` (PRs #636 on 2026-11-04 and #713 on 2026-11-08); this rewrite removes them from
every earlier commit as well.

## What was removed

| path | what it held |
|---|---|
| `eval/golden-queries-v2.jsonl`, `eval/golden-queries-v3.jsonl` | the PT-BR ruler: queries with literal anchors from the private corpus |
| `eval/golden-negatives-v1.jsonl`, `eval/golden-negatives-v2.jsonl` | negatives drawn from the same corpus |
| `eval/gold-proposals-2026-10-27.jsonl` | proposed gold anchors (corpus excerpts) |
| `audits/out/kg-s1-precision-2026-10-22.json` | KG precision sample with relation evidence (corpus excerpts) |
| `audits/out/abstention-baseline-2026-10-22.json`, `audits/out/resolve-gold-anchors-2026-10-22.json` | system answers and anchor resolution over the corpus |
| six audits of 2026-10-22/27 (`abstention-baseline`, `abstention-the-durable-fix`, `does-the-recorded-gold-answer-the-question.py`, `the-oracle-pass-and-what-the-judge-got-wrong`, `the-ruler-is-deflated-not-inflated`, `v3-build.py`) | literal excerpts, system answers and private paths |

Their sha256 values stay in the provenance files (`paper-a-eval-ptbr/PROVENANCE.json` marks them
`artifact_private`), and a private copy is kept, so the numbers computed from them remain checkable
by the author on request.

## How

`git filter-repo --invert-paths` on exactly those 14 paths, limited to the commits that descend from
the first commit that added one of them (2026-10-22). Commits before that were not touched and keep
their hashes, so the tags `paper-v1.0.2`, `datanote-v1.0`, `paper2-v1.12`, `paper2-v2.0`,
`v1.0.0`, `v1.0.0-rc1`, `v1.0.0-paper-draft` and the two `archive/` tags are unchanged. Every commit was kept (no commit was
pruned); the tree of `main` is byte-identical before and after. 168 commits got new hashes; the full
old-to-new map is [`history-rewrite-2026-11-08-commit-map.txt`](history-rewrite-2026-11-08-commit-map.txt).

Checked after the push, from a fresh clone: none of the 19 blob versions of those files is
reachable from any branch or tag.

## Tags that moved

The content of every tagged tree is the same; only the commit ids changed. Documents written before
the rewrite cite the old ids, so read them through this table.

| tag | old commit | new commit |
|---|---|---|
| `paper-a-prereg-v1.0` | `6c6879b` | `c473958` |
| `paper-b-prereg-v1.0` | `c6c86a1` | `c141f86` |
| `paper-b2-prereg-v1.0` | `18c20ee` | `c77c16b` |
| `paper-d-prereg-v1.0` | `5307a6f` | `16e0b14` |
| `paper-d-shadow-prereg-v1.0` | `6ac8272` | `e10454b` |
| `paper-e-prereg-v1.0` | `7113c3f` | `83dfe53` |
| `paper3-prereg-v1.0` | `23ee59f` | `76bf84f` |
| `paper3-prereg-v1.1` | `f920303` | `1f4f352` |
| `paper3-prereg-v1.2-calibration` | `7d48644` | `1026a25` |
| `paper3-prereg-v1.3` | `dd380ea` | `eb388d7` |
| `paper3-prereg-v1.3-calibration` | `8996cc7` | `096d2ea` |
| `paper3-prereg-v1.4` | `bca912c` | `88fcd75` |
| `paper3-prereg-v1.5` | `977ec5f` | `8fd0452` |

## What this costs, said plainly

- **Timestamps of pre-registration.** Before the rewrite, a reader could check on GitHub that a
  pre-registration tag existed before its results. The new commits carry the original author and
  committer dates, but a rewritten commit is not independent evidence of when it was made. The
  original commits are kept in a private mirror of the full history before the rewrite, and in a
  local bundle (sha256 `dfb5d11c0a60554a9fc09d9a72fa03935f6f54788442089bbc86c30c6c4378a1`); the
  author can show either on request. The deposits on Zenodo keep their own dates.
- **Seeds.** Seeds that were derived from a tag commit keep their registered values. The only study
  still running, the C2 shadow, fixes its seed at `0x6ac8272d` (= 1791502125) and is now bound by
  `paper-d-shadow-prereg-v1.1` (`paper-d-c2-production/SHADOW-PREREGISTRATION.md` §10). Finished
  studies are not rerun; reproducing one means checking out its tag and reading its seed from its registered documents (the
  commitment files record it: Paper B 3335023133, B2 415370986, D 20261106), not from the new
  commit id.
- **Old pull-request pages** on GitHub may still show the removed files until GitHub purges the
  cached pull-request refs; the author is asking GitHub to purge them.
