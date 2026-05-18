# LICENSE-CLARIFICATIONS.md

> **Scope:** This document is a companion to the root [`LICENSE`](../LICENSE) file. It clarifies how the MIT License applies to specific scenarios that contributors, forks, and downstream users commonly ask about. It does **not** modify or supersede the LICENSE text — that file is the legal instrument.
>
> **Bottom line up front:** memoria-nox is MIT. You can use it, fork it, sell it, and build commercial products with it. You must keep the copyright notice. See below for nuances.

---

## 1. Contributor IP — Who Owns Your Contributions?

### Current status (no CLA)

memoria-nox does **not** currently require a Contributor License Agreement (CLA). When you open a pull request, you:

1. Represent that you have the right to license the contribution.
2. Grant the project (and all downstream users) the same MIT rights as the rest of the codebase — by submitting to a MIT-licensed project without a CLA, the contribution is understood to be offered under MIT.

This is the default open-source convention and is legally sufficient for a project of this size.

### What you retain

You retain copyright in your contributions. MIT does not transfer ownership — it grants a license. If the project were relicensed (see Section 5), contributors could not be compelled to relicense their past contributions without consent.

### When a CLA would make sense

A CLA (like Google's or the Apache ICLA) becomes valuable if:
- The project plans to offer a commercial license alongside the open-source MIT license (dual licensing)
- The project might migrate to Apache-2.0 for the patent grant and needs to ensure past contributions are covered
- The project anticipates litigation requiring proof that all contributions were properly licensed

**Current recommendation:** No CLA needed. If any of the above becomes relevant (particularly dual licensing for Nuvini portfolio or Galapagos capital allocation), revisit this. Document the decision in [`docs/DECISIONS.md`](DECISIONS.md) before implementing a CLA process.

---

## 2. Code vs. Documentation

### Code (`src/`, `scripts/`, `sdk/`, `staged-*/`)

MIT License. Full text in [`LICENSE`](../LICENSE). Covers all TypeScript, JavaScript, and shell source files.

### Documentation (`docs/`, `*.md`, `specs/`, `audits/`, `paper/`)

Also MIT for the moment — the same LICENSE file covers the entire repository.

**Practical consideration:** Docs-specific licenses like CC-BY-4.0 are sometimes preferred for narrative content because they require attribution without the software-centric warranty disclaimer. However, splitting licenses adds complexity (two LICENSE files, per-file headers, contributor confusion).

**Recommendation:** Keep docs under MIT for now. If the paper (`paper/paper-tecnico-nox-mem.md`) is submitted to an academic venue, that venue will specify its own licensing terms. CC-BY can be applied to the paper individually at that point via a comment in the file header, without changing the repo-wide license.

---

## 3. AI-Generated Code

### The pattern

A significant portion of this codebase was written with Claude (Anthropic) as a pair programmer. Some commits are entirely AI-assisted; others are human-written with AI suggestions applied selectively.

### Legal status

Under current law in most jurisdictions (including Brazil and the US as of 2026):

- AI-generated content is **not** copyrightable by the AI or by Anthropic.
- The human who directs, reviews, selects, and commits the output is the author for copyright purposes.
- Anthropic's usage policies permit using Claude outputs in commercial and open-source projects without restriction on IP ownership (see Anthropic's published terms).

**Practical implication:** AI-assisted commits carry the same copyright as human commits. The copyright holder is Luiz Antonio Busnello (Toto), as stated in the LICENSE file.

### What this means for contributors

If you use an AI assistant to help write your contribution, you are still the contributor of record. The same rules apply as Section 1 — you represent that you have the right to license the contribution.

---

## 4. Trademark — "nox-mem" and "memoria-nox"

### Current status

"nox-mem" and "memoria-nox" are **unregistered trademarks** of Luiz Antonio Busnello. No formal trademark registration exists as of 2026-05-18.

### What MIT does not cover

The MIT License grants rights to use, copy, modify, and distribute the **software**. It does not grant rights to:
- Use the "nox-mem" or "memoria-nox" names in product names that imply official association
- Use the logo or visual identity in marketing materials
- Present a fork as the "official" nox-mem

### Usage policy for forks and derivatives

You are free to:
- Fork this repository and call your fork anything (including nox-mem with a distinguishing prefix/suffix like "my-nox-mem")
- Reference memoria-nox by name in attribution, documentation, or descriptions of compatibility
- Build commercial products on top of the code without trademark permission

You should **not**:
- Name a competing product "nox-mem" or "memoria-nox" without permission
- Use the original logo without permission
- Imply your fork is the official project

If formal trademark registration becomes relevant (e.g., for the Nuvini / Galapagos portfolio context), document the decision in [`docs/DECISIONS.md`](DECISIONS.md) and pursue registration in Brazil (INPI) as the primary market.

---

## 5. Patent Grant

### What MIT provides

MIT is intentionally silent on patents. The text grants rights to "use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies" — but does **not** include an explicit patent license.

In practice, for most software projects this does not matter: the copyright license is what controls distribution, and patent litigation against MIT-licensed software is uncommon for projects of this scale.

### The gap

If the retrieval algorithms in memoria-nox (hybrid BM25+semantic+RRF fusion, the salience formula, conflict detection methodology) were patentable, MIT would not shield downstream users from patent claims. They would need a separate patent license.

### Apache-2.0 as the alternative

Apache-2.0 includes an explicit patent grant (Section 3 of the Apache License) and a patent retaliation clause. If you file a patent suit against Apache-2.0 software, your license terminates.

**Recommendation:** Keep MIT for now. The project's retrieval approaches are heavily based on published academic work (BM25 is from Robertson et al. 1994, RRF from Cormack et al. 2009) and are not novel enough to be patentable. If the project develops a genuinely novel approach (e.g., the salience formula evolves into something defensible), revisit Apache-2.0 migration.

**Migration path if needed:**
1. Gather contributor consent (everyone who has merged PRs)
2. Or: apply Apache-2.0 prospectively from a specific version forward, keeping MIT for prior code
3. Update LICENSE file + all package.json `"license"` fields
4. Update CONTRIBUTING.md and this document

---

## 6. Dependencies — Copyleft Caveats

### No copyleft in the dependency graph

As documented in [`DEPENDENCIES.md`](../DEPENDENCIES.md) and enforced by CI via the dependency-review-action, **no GPL, LGPL, AGPL, or other copyleft-licensed packages** are in the runtime dependency graph.

All runtime dependencies are MIT or Apache-2.0. All dev dependencies follow the same allowlist.

### What would be problematic

If a future dependency introduced GPL-licensed code into the runtime build:

- Distributing the compiled binary would require releasing the entire work under GPL
- The DEPENDENCY-POLICY.md explicitly blocks this; the CI gate enforces it

### Static vs. dynamic linking

For libraries that are only in `devDependencies` and are not linked into the distributed binary (e.g., Jest, ts-jest, Playwright), copyleft exposure is minimal even if an LGPL package appeared — because it is not shipped. However, the policy still blocks LGPL in devDeps to avoid toolchain contamination and ambiguity.

---

## 7. Commercial Use

MIT explicitly permits commercial use. The full grant is:

> "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software..."

**This means:**
- You can sell a product built on nox-mem
- You can offer memoria-nox as part of a SaaS without open-sourcing your application code
- You can include it in a commercial data platform
- Nuvini, FII Treviso, Fundo Lombardia, Granix, and Galapagos portfolio companies can use this codebase internally or commercially without any special license

**The only obligation:**
- Include the copyright notice and the MIT license text in any distribution of the software itself (not your product, but if you ship the nox-mem source or binaries).

---

## 8. Liability Limitation

The MIT License includes a liability exclusion:

> "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY..."

**What this means in practice:**
- If the memory system loses data, returns incorrect results, or causes a downstream problem, the maintainer has no legal liability.
- This does **not** mean the project takes data integrity lightly — the incident log (`docs/INCIDENTS.md`), op-audit system (`src/lib/op-audit.ts`), and operational guardrails exist precisely because the system matters. But the legal protection is the standard MIT "no warranty" clause.
- For production deployments where liability matters (e.g., regulated financial contexts at Galapagos), consider whether a commercial support agreement or indemnification clause is needed at the business level.

---

## 9. Summary Table

| Question | Answer |
|----------|--------|
| Can I fork and sell? | Yes |
| Can I use commercially without open-sourcing my app? | Yes |
| Do I need to attribute? | Yes — keep the copyright notice in distributions of the software |
| Do I need a CLA to contribute? | No |
| Who owns my contributions? | You do (MIT grant only) |
| Is AI-assisted code allowed? | Yes — contributor is the human who commits |
| Patent protection included? | No — MIT is silent on patents (Apache-2.0 would add this) |
| Are docs covered? | Yes — same MIT license |
| Can I use the "nox-mem" trademark? | With limitations — see Section 4 |
| Any GPL/copyleft in deps? | No — enforced by CI gate |
| Liability for data loss? | No — standard MIT disclaimer |

---

## 10. Future License Considerations

This section tracks open questions. Decisions are not made here — document final choices in [`docs/DECISIONS.md`](DECISIONS.md).

| Topic | Status | Trigger for revisiting |
|-------|--------|----------------------|
| CLA adoption | Not needed today | Dual licensing, commercial license offering, or litigation risk |
| Apache-2.0 migration (patent grant) | Not needed today | Novel algorithm development, enterprise adoption requiring indemnification |
| CC-BY for docs | Not needed today | Academic paper submission or doc-only contributors wanting explicit CC attribution |
| Trademark registration (INPI Brazil) | Not needed today | Commercial product launch with "nox-mem" brand in Brazilian market |
| Dual license (MIT + commercial) | Not needed today | Nuvini/Galapagos portfolio wanting a commercial license without MIT obligations |

---

*Document version: 1.0.0 — 2026-05-18. This is a companion to `LICENSE` and has no legal force of its own. For legal questions, consult a qualified attorney.*
