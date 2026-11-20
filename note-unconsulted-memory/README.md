# The memory the agent does not consult (data note)

Status: draft (`NOTE.md`), on its way to a Zenodo deposit by the same route as Paper A.

## Files

| file | what it is |
|---|---|
| `NOTE.md` | the note |
| `skill-eval-PROTOCOL.md` | the evaluation protocol, a verbatim copy of `docs/skill-eval/PROTOCOL.md` at commit `438e3a6` (committed 2026-11-08 18:31 UTC; the real-use rule enters the protocol in this commit) of the product repository's branch `docs/memory-skill-draft` |
| `skill-eval/bank/` | the frozen task bank (80 tasks), the draw, the corpus manifest, the grader calibration set and the bank author's notes, verbatim from `438e3a6` |
| `skill-eval/harness/` | the runner, the grader, the corpus builder, the T and T2 server diffs and the smoke tasks, verbatim from `438e3a6` |
| `field-recount-2026-11-20.md` | read-only recount of the two field figures that came from queries on the production host |
| `PROVENANCE.json` | every number the note prints, with its source, locator and commit |
| `pdf-build/`, `deposit/` | the PDF build and the Zenodo deposit script (never publishes; `--plan` is read-only) |

## Why the protocol is copied here

The note cites the protocol by line (`P:<line>` in its provenance table). The branch that holds it
is kept private because it also carries the archived skill; the protocol itself names no host,
person or private path. A copy in this public repository lets a reader check every `P:` row, and
lets the provenance gate check the locators.

The copy is byte for byte: its git blob is `1f06a9962721f4d6314445eaa65ddbd0346487b5`, the same as
`438e3a6:docs/skill-eval/PROTOCOL.md`, and its sha256 is
`af7dd2939c763292c15d7dfbec6a8b8633b51e3d6f63bec0ee4055b3fda4238c`. Do not edit it: a correction to the
protocol belongs in the product repository, and a new copy here under a new name.

The same holds for `skill-eval/`: every file has the git blob it has at `438e3a6`.
`bank/tasks-v1.jsonl` matches the sha256 in the protocol's table of frozen artifacts.
`harness/run_eval.py` matches the protocol's last re-freeze (`3e8edf06…`, when arm T was added),
not the first hash in that table; the protocol records both changes. The skill file and the
evaluation database stay private: the skill because it was archived, the database because four of
the corpus files it was built from were later removed from the public history (they quoted a
private corpus). No task in the bank has its source in those four files.

Gate: `python3 -I tools/provenance.py --check note-unconsulted-memory`.
