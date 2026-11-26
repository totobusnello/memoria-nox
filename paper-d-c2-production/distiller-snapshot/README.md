# Production distiller, pinned copy (2026-11-26)

The session distiller that production runs, and the C2 shadow that sits beside it, copied
byte-for-byte from the production workspace so that the shadow reading (not before 2026-12-01, see
`../SHADOW-PROTOCOL.md`) and any later replay can name the exact code without access to the host.

| file | source commit (production workspace repository, private) | committed | sha256 |
|---|---|---|---|
| `session-distill.ts` | `9ec24c393bc0204b170cd42f031fbc13c54b8c5d` | 2026-11-15 | `c3131d5c620972c9a8275927827ac91d4fce8e310f8a45deeb8edb3390cfdd4b` |
| `distill-shadow.ts` | `ac642951d92a4935850239a0e9d8b4556f0d4e1f` | 2026-11-06 | `cd2d30e1ee6a60ad17417fa39439b7587bbac38132a9c61d4883bd1f2b2c4f47` |

Copied on 2026-11-26 from the deployed `tools/nox-mem/src/`, with the workspace at
`fb5bca8bca4f219f30df875bcdf3297f3ae49d31` and no uncommitted change to either file.

What this copy is and is not:

- It is the code that ran, not a buildable package: it imports modules of the deployed nox-mem
  (`db`, `dedup`, `noise-filter`, `metrics`, `lib/provider-cost`) that are not copied here.
- The public package `nox-mem` carries a generalised version of the same distiller (paths and
  agent list from the environment, no shadow); it is not byte-identical to this one.
- `session-distill.ts` changed four times after the shadow was switched on (2026-11-06), so the
  shadow reading has to say that the distiller changed during collection:
  - 2026-11-08 `5c1a0b1a`: distilled chunks are inserted with no retention (never decay);
  - 2026-11-13 `5824bee7`: the Groq fallback is removed (it had failed 21 of 21 calls since
    2026-09-13, so no block it produced is lost) and the reason a block yields nothing is counted;
  - 2026-11-14 `9ce06d7c`: one line of counts per run is appended to a log;
  - 2026-11-15 `9ec24c39`: sessions too short to distil no longer count against the per-run cap,
    which changes which sessions a run reaches, not how a block is distilled.
  None of the four changes the distillation prompt.
- Keys are read from the environment; nothing secret is in either file.

Check that a file is the pinned one: `shasum -a 256 -c` against the table above.
