# The memory the agent does not consult (data note)

Status: draft (`NOTE.md`), on its way to a Zenodo deposit by the same route as Paper A.

## Files

| file | what it is |
|---|---|
| `NOTE.md` | the note |
| `skill-eval-PROTOCOL.md` | the evaluation protocol, a verbatim copy of `docs/skill-eval/PROTOCOL.md` at commit `438e3a6` of the product repository's branch `docs/memory-skill-draft` |
| `field-recount-2026-11-20.md` | read-only recount of the two field figures that came from queries on the production host |

## Why the protocol is copied here

The note cites the protocol by line (`P:<line>` in its provenance table). The branch that holds it
is kept private because it also carries the archived skill; the protocol itself names no host,
person or private path. A copy in this public repository lets a reader check every `P:` row, and
lets the provenance gate check the locators.

The copy is byte for byte: its git blob is `1f06a9962721f4d6314445eaa65ddbd0346487b5`, the same as
`438e3a6:docs/skill-eval/PROTOCOL.md`, and its sha256 is
`af7dd2939c763292c15d7dfbec6a8b8633b51e3d6f63bec0ee4055b3fda4238c`. Do not edit it: a correction to the
protocol belongs in the product repository, and a new copy here under a new name.
