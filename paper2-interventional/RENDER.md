# How the PDF and HTML are produced

The Markdown is authoritative. The rendered copies exist so the registration can
be read without a Markdown viewer, and they are reproducible from this
repository alone:

```sh
python3 render_ascii.py PREREG-DRAFT.md /tmp/prereg-ascii.md
pandoc /tmp/prereg-ascii.md -s --embed-resources --css=render.css \
  --metadata title="OSF Pre-Registration - Interventional Memory" \
  -o PREREG-<version>.html
chrome --headless --no-pdf-header-footer \
  --print-to-pdf=PREREG-<version>.pdf file:///path/to/PREREG-<version>.html
```

**Why an ASCII step.** Rendering from ASCII keeps the output identical across
font stacks, and the numbers in the PDF are verified by extracting its text —
which needs a predictable character set.

**Why `render_ascii.py` refuses more often than it succeeds.** It transliterates
symbols, never values, and aborts if the multiset of value-like numeric tokens
differs between input and output. That guard took four attempts to get right,
and each failure is recorded in the file's comments, because each was a way of
being wrong that looked like being right:

1. comparing with `not in` — blind to multiplicity, so it aborted while
   reporting `lost: [] new: []`, a failure message that says nothing;
2. counting subscript and identifier digits (`lambda_0`, `p0_hat`) as values;
3. mapping `x` for the multiplication sign without spacing, which glued
   `)x0.098459` and made the guard see a number that was never written;
4. building the combining-mark table from `chr()` when `str.translate` keys are
   **ordinals** — a no-op that reported success.

The guard exists because a mechanical rewrite already damaged this document
once: the decimal-separator pass of v1.4 turned `a ∈ {0,1}` into `a ∈ {0.1}` and
it stood in four deposits. `PREREG-DRAFT.md` records it in the **v1.9 entry** of
its version history — no longer the topmost note, since v1.11 opens the document.
