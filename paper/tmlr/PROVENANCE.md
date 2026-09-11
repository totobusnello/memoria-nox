# Official TMLR style file — vendored copy

These files are **not ours**. They are the official LaTeX style file for
*Transactions on Machine Learning Research*, copied unmodified so that the
submission PDF can be rebuilt without network access.

| field | value |
|---|---|
| upstream | `https://github.com/JmlrOrg/tmlr-style-file` |
| archive fetched | `https://github.com/JmlrOrg/tmlr-style-file/archive/refs/heads/main.zip` |
| fetched on | 2026-09-11 |
| licence | Apache License 2.0 (see `LICENSE`, copied verbatim from upstream) |
| modifications | **none** — byte-identical to upstream |

## Contents and SHA-256

```
816214ff5919aa457b6b443bee52b15d9561421417b7f8a50cc84651519f0002  tmlr.sty
306fd454cf40771bee01293eeb98d2c1cd5f4e11ed0cd7296b335f354fc45206  tmlr.bst
c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4  LICENSE
```

Re-verify with `shasum -a 256 -c SHA256SUMS`.

## What was deliberately *not* vendored

- `fancyhdr.sty` — `tmlr.sty` line 14 does `\RequirePackage{fancyhdr}`, and
  fancyhdr ships with TeX Live (confirmed present in the TeX Live 2026
  installation used to build). Vendoring a second copy would shadow the
  distribution's and is the kind of divergence nobody notices until it
  breaks.
- `math_commands.tex` — optional in upstream's `main.tex`
  (`\input{math_commands.tex}`); this manuscript defines no custom math
  macros and pandoc emits `amsmath` directly.
- `main.tex`, `main.bib`, `main.pdf`, `main-accepted.pdf` — upstream's
  *example* document. Our wrapper is `paper/tmlr-wrapper.tex`.

## Why `tmlr.bst` is here despite being unused today

The manuscript carries its references as hand-written footnotes, not BibTeX
keys (`grep -c '\[@' paper/paper-tecnico-nox-mem.md` = 0), so `natbib` and
`tmlr.bst` are loaded and never exercised. It is vendored anyway because it
is half of the citation contract the venue defines, and a camera-ready that
converts the footnotes to BibTeX must use *this* `.bst` and no other.

## The three package options

`tmlr.sty` lines 29–40 declare them:

| option | effect | when |
|---|---|---|
| *(none)* | line 132 emits `Anonymous authors \\ Paper under double-blind review` | **submission** — what we build |
| `[accepted]` | prints real authors + `Published in TMLR (\month/\year)` header + OpenReview link | camera-ready, only after acceptance |
| `[preprint]` | de-anonymises and drops the TMLR mentions | posting to a preprint server |

The `[accepted]` path is the only one that reads `\month`, `\year` and
`\openreview` (lines 114 and 129), which is why the anonymous wrapper does
not define them. Defining `\month` would in fact override a TeX primitive
count register for no benefit.
