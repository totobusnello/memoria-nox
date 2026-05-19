# GTM — README Hero Visual Upgrade (post-Q4 gate)

**Spec ID:** 2026-05-17-GTM-readme-hero-upgrade
**Status:** READY-TO-EXECUTE (gated on Q4 COMPARISON wins)
**Author:** Prometheus (overnight automode 2026-05-17)
**Sign-off:** Toto (tagline + sub-tagline locked)
**Gate:** GTM Phase 2 — execute ONLY when `paper/publication/Q4-COMPARISON.md` shows nox-mem at top of relevant benchmarks (or tied #1)
**Branch on execution:** `gtm/readme-hero-v1`
**Order in roadmap:** post-Q4, pre-launch (Twitter/X + HN + Trendshift)

---

## 1. Motivação

O README atual de memoria-nox tem **23 shields.io badges empilhadas** no topo, zero logo, zero demo visual, zero diagrama de arquitetura. Apesar do conteúdo técnico ser excelente (nDCG 0.6813, 69k chunks, paper v1.1, schema v10, KG com 21k relations, retrieval híbrido com RRF, salience formula, shadow-mode discipline), a primeira impressão visual transmite **"projeto de engenharia"** — não **"produto que faz ship"**.

Quando os números Q4 provarem liderança técnica (Q1 LoCoMo R@5 winner + Q2 LongMemEval accuracy + Q3 latency + Q4 OPEX), o README precisa **comunicar essa vitória instantaneamente** — não esconder atrás de wall-of-badges. Visual hero é o single biggest GTM lever entre "stars/dia constante" e "viral inflection."

**Por que gated em Q4:**
- Visual hype sem números = vaporware vibe
- Visual hero + números provados = product-led signal forte
- Trendshift/HN/Show HN só funcionam quando há **prova quantitativa visível**
- Stats cards SVG fazem sentido apenas quando os stats são reais e top-1

**Análise competitiva (2026-05-17, memory file `repo-visual-style-inspiration`):**
- **memanto (126 stars):** logo SVG 500px, tagline H1, 3 CTA badges + 5 trust, arch PNG 1000px, YouTube embed
- **agentmemory (11.3k stars):** banner PNG 720px, Trendshift 250x55, Star History dark/light via `<picture>`, viral GitHub Gist orange badge, 4 trust badges, **6 stat SVGs custom dark/light**, demo.gif 720px, TOC anchor bar, 8x2 agent integration grid

Direção: **híbrido memanto + agentmemory**, com identidade própria via brand colors (TBD em open question 1).

---

## 2. Hero Structure (top-to-bottom)

Cada elemento numerado, ordem locked, copy locked onde indicado.

### 2.1 Banner PNG (centered, 720px wide)

- **Asset:** `assets/readme/banner-{dark,light}.svg` (rendered to PNG fallback opcional)
- **Tamanho:** 720x200 (banner aspect)
- **Conteúdo:** abstract memory/graph visualization (não logo literal de cérebro — algo geometricamente abstrato: nodes + edges + glow sutil, dark mode amber/orange, light mode deep blue/teal — depende da open question 1)
- **Tagline embedded:** "Pain-weighted hybrid memory with shadow discipline" em uppercase no topo do banner; "yours by design" smaller em italic abaixo
- **Picture tag:**
  ```markdown
  <p align="center">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/readme/banner-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="assets/readme/banner-light.svg">
      <img alt="nox-mem — Pain-weighted hybrid memory with shadow discipline" src="assets/readme/banner-light.svg" width="720">
    </picture>
  </p>
  ```

### 2.2 Tagline H1 (centered)

```markdown
<h1 align="center">Pain-weighted hybrid memory with shadow discipline — yours by design.</h1>
```

**LOCKED.** Não decidir copy alternativo. Toto sign-off 2026-05-17.

### 2.3 Sub-tagline (1 sentence, centered, italicized)

```markdown
<p align="center"><em>The only agent memory that's genuinely yours. SQLite on your disk, provider your choice, zero vendor lock-in.</em></p>
```

**LOCKED.** Duas alternativas A/B test apenas pós-launch (ver seção 9):
- **A (current locked):** "The only agent memory that's genuinely yours. SQLite on your disk, provider your choice, zero vendor lock-in."
- **B (alternative for week-2 test):** "Hybrid retrieval + knowledge graph + shadow discipline. Runs on your laptop, scales to your fleet."

### 2.4 Trendshift Badge (250x55, conditional)

Só inseridos APÓS trending real. Placeholder bloco:

```markdown
<p align="center">
  <!-- Trendshift badge — insert after first trending event -->
  <a href="https://trendshift.io/repositories/XXXXX" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/XXXXX" alt="nox-mem | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
  </a>
</p>
```

### 2.5 Star History Chart (dark/light via `<picture>`)

```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=totobusnello/memoria-nox&type=Date&theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=totobusnello/memoria-nox&type=Date">
    <img alt="Star History" src="https://api.star-history.com/svg?repos=totobusnello/memoria-nox&type=Date" width="600">
  </picture>
</p>
```

### 2.6 4 Trust Badges (for-the-badge style)

Substituem 23 shields atuais. Single row, centered:

```markdown
<p align="center">
  <a href="https://www.npmjs.com/package/nox-mem"><img src="https://img.shields.io/npm/v/nox-mem?style=for-the-badge&color=orange" alt="npm"></a>
  <a href="https://github.com/totobusnello/memoria-nox/actions"><img src="https://img.shields.io/github/actions/workflow/status/totobusnello/memoria-nox/ci.yml?style=for-the-badge" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/totobusnello/memoria-nox?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/totobusnello/memoria-nox/stargazers"><img src="https://img.shields.io/github/stars/totobusnello/memoria-nox?style=for-the-badge&color=yellow" alt="Stars"></a>
</p>
```

Demais 19 badges (build, coverage, deps, etc) movidas para footer ou removidas.

### 2.7 6 Custom Stat SVGs (dark/light variants)

Branded stat cards, **hand-designed em SVG**, NÃO shields.io. Cada 38px tall, layout 3 colunas x 2 linhas:

```markdown
<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-locomo-dark.svg"><img src="assets/readme/stat-locomo-light.svg" alt="95.7% LoCoMo R@5" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-longmemeval-dark.svg"><img src="assets/readme/stat-longmemeval-light.svg" alt="92.4% LongMemEval" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-latency-dark.svg"><img src="assets/readme/stat-latency-light.svg" alt="<80ms p95" height="38"></picture>
  <br>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-scale-dark.svg"><img src="assets/readme/stat-scale-light.svg" alt="69k chunks · 21k relations" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-opex-dark.svg"><img src="assets/readme/stat-opex-light.svg" alt="<$11/mo all-in" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-tests-dark.svg"><img src="assets/readme/stat-tests-light.svg" alt="950+ tests passing" height="38"></picture>
</p>
```

**6 stats featured (numbers updated when Q4 lands — placeholders OK in v0.1):**
1. Q1 R@5 LoCoMo: `XX.X% LoCoMo R@5` (placeholder "95.7%")
2. Q2 LongMemEval: `XX.X% LongMemEval` (placeholder "92.4%")
3. Q3 latency: `<XXms p95` (placeholder "<80ms")
4. Schema/scale: `69k chunks · 21k relations`
5. OPEX: `<$XX/mo all-in` (placeholder "<$11/mo")
6. Tests: `950+ tests passing` (verify atual em CI antes de produzir)

**Design specs por card:**
- Width: ~180px (auto-fit content)
- Height: 38px (fixed)
- Layout: ícone 24x24 esquerda + label uppercase + value bold colorido
- Dark variant: bg `#1a1a1a`, text `#e0e0e0`, value brand color
- Light variant: bg `#f5f5f5`, text `#1a1a1a`, value brand color
- Border-radius: 6px
- Font: system-ui or Inter
- **Brand color:** TBD open question 1

### 2.8 Demo GIF (720px wide)

```markdown
<p align="center">
  <img src="assets/readme/demo.gif" alt="nox-mem demo: search → KG path → answer with citations" width="720">
</p>
```

**Storyboard (5 cenas, ~15s total, <5MB):**
1. **0-2s:** terminal prompt `nox-mem search "what's the salience formula?"` typed in
2. **2-5s:** results streaming — top chunk with score, then 2 more with snippet preview
3. **5-8s:** `nox-mem kg-path salience pain importance` showing graph traversal output
4. **8-12s:** `nox-mem answer "explain how shadow mode validates ranking changes"` with streaming output and `[chunk:1234, chunk:5678]` citations inline
5. **12-15s:** final answer block with citation footer

**Tools:** `asciinema rec` → `asciicast2gif` (preferred, smaller output) OR `kap` (macOS, larger but easier). Target <5MB. If overshoot, drop to 5fps or 480px.

### 2.9 TOC Anchor Bar

```markdown
<p align="center">
  <a href="#-quick-start">Install</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-benchmarks">Benchmarks</a> ·
  <a href="#vs-competitors">vs Competitors</a> ·
  <a href="#%EF%B8%8F-architecture">Architecture</a> ·
  <a href="#-api">API</a> ·
  <a href="#-paper--research">Paper</a>
</p>

---
```

---

## 3. Section Structure (below hero, in order)

Seções abaixo da hero, ordem locked. Cada seção ≤80 linhas markdown. Total README ≤500 linhas (orçamento seção 8).

### 3.1 🏗️ Architecture
- **Asset:** `assets/readme/architecture-{dark,light}.png` (1000x600, rendered from Mermaid source)
- **Conteúdo:** hybrid retrieval pipeline (FTS5 BM25 → Gemini semantic → RRF fusion) + KG layer + salience formula + shadow-mode validation
- Mermaid source em `assets/readme/architecture.mmd` para regeneração
- Render via `mmdc -i architecture.mmd -o architecture-light.png -t default -w 1000` e variant dark com `-t dark`

### 3.2 🚀 Quick Start
- 3-command install:
  ```bash
  npm install -g nox-mem
  nox-mem init ~/my-memory
  nox-mem search "your first query"
  ```
- Link para `docs/QUICKSTART.md` se quiser deep dive

### 3.3 📊 Benchmarks
- Summary table (LoCoMo, LongMemEval, NQ, latency, OPEX) com winner rows highlighted
- Link para `benchmark/locomo/`, `benchmark/longmemeval/`, etc para reproduzir
- Methodology disclosure: gemini-3072d, RRF k=60, hardware specs

### 3.4 vs Competitors
- Abridged Q4 COMPARISON table (top 5 competitors only)
- Link para `paper/publication/Q4-COMPARISON.md` for full table
- Highlight rows where nox-mem wins (bold + ✅)

### 3.5 🤖 Works with every agent
- Tier A premium grid (Claude Code, ChatGPT, OpenClaw, Cursor, Cline) com logos 48x48
- Tier B grid (Continue, Aider, Codex, Roo, Tabnine, Windsurf, etc) 8x2 com logos menores
- Link para `docs/integrations/` para cada

### 3.6 🧠 How It Works
- Memory pipeline narrativo: ingest → privacy filter → embed → store → search → answer
- 5 etapas com 1-2 linhas cada, link para deep dive em `paper/paper-tecnico-nox-mem.md`

### 3.7 📄 Paper & Research
- arXiv link (TBD pós-submission)
- Abstract preview (200 words)
- BibTeX citation block (locked once arXiv landed):
  ```bibtex
  @article{busnello2026noxmem,
    title={nox-mem: Hybrid Memory with Shadow Discipline for AI Agents},
    author={Busnello, Toto},
    year={2026},
    journal={arXiv preprint arXiv:XXXX.XXXXX},
    url={https://arxiv.org/abs/XXXX.XXXXX}
  }
  ```

### 3.8 🔧 Configuration
- Env vars table (compact, only top 10): `NOX_API_PORT`, `NOX_SALIENCE_MODE`, `NOX_SEARCH_LOG_TEXT`, etc
- Link para `docs/CONFIGURATION.md` for full reference

### 3.9 📞 Support & Documentation
- Discord/Slack link (if any — open question 2)
- Issues link
- Discussion link
- Paper repo link

---

## 4. Visual Assets to Produce

| Asset | Path | Dimensions | Tool/Skill | Variants |
|-------|------|------------|------------|----------|
| Banner | `assets/readme/banner-{dark,light}.svg` | 720x200 | `design` skill (Gemini 3.1 Pro) | dark + light |
| Stat cards ×6 | `assets/readme/stat-{name}-{dark,light}.svg` | ~180x38 | `banner-design` skill | dark + light |
| Architecture diagram | `assets/readme/architecture-{dark,light}.png` | 1000x600 | Mermaid via `mmdc` | dark + light |
| Demo GIF | `assets/readme/demo.gif` | 720px wide, <5MB | `asciinema` + `asciicast2gif` | single (no theme variant) |
| Logo (favicon-ready) | `assets/readme/logo.svg` | 256x256 | derived from banner mark | single |

**Total asset count:** 5 banner files (1 light + 1 dark, +PNG fallback opt) + 12 stat files (6 stats × 2 variants) + 2 architecture files + 1 demo.gif + 1 logo = **~20 files**.

---

## 5. Copy/Marketing — Scripted Elements

Tudo abaixo é **locked** (Toto sign-off 2026-05-17) ou **scripted** (não decidir ad-hoc no momento da execução).

### 5.1 Tagline (LOCKED)
> "Pain-weighted hybrid memory with shadow discipline — yours by design."

### 5.2 Sub-tagline (LOCKED v1, alternative for week-2 A/B in section 9)
> A: "The only agent memory that's genuinely yours. SQLite on your disk, provider your choice, zero vendor lock-in."
> B (alt): "Hybrid retrieval + knowledge graph + shadow discipline. Runs on your laptop, scales to your fleet."

### 5.3 First-paragraph answer to "what is this" (LOCKED, 50-80 words)

> nox-mem is a hybrid memory engine for AI agents. It combines FTS5 keyword search with Gemini 3072-dimensional embeddings via Reciprocal Rank Fusion, layered with a knowledge graph (21k+ relations) and shadow-mode validation discipline. Everything runs on local SQLite — portable, auditable, yours. No vendor lock-in, no cloud round-trips for retrieval. Published research, reproducible benchmarks, production-tested. Ready to evaluate? See [Benchmarks](#-benchmarks).

(72 words)

### 5.4 Section emoji prefixes (LOCKED)
🏗️ Architecture · 🚀 Quick Start · 📊 Benchmarks · 🤖 Works with every agent · 🧠 How It Works · 📄 Paper & Research · 🔧 Configuration · 📞 Support

### 5.5 BibTeX citation block (LOCKED — fields filled when arXiv lands)
(see section 3.7)

---

## 6. Marketing Channels (post-launch playbook)

### 6.1 Twitter/X Thread (5 tweets)
- **T1 (hook):** "memory for AI agents is broken. cloud lock-in, no portability, opaque ranking. so I built nox-mem — hybrid memory with shadow discipline, yours by design. 🧵👇"
- **T2 (proof):** "95.7% LoCoMo R@5, 92.4% LongMemEval, <80ms p95, <$11/mo all-in. SQLite on your disk, Gemini embeddings, RRF fusion, KG layer. [link to benchmarks]"
- **T3 (philosophy screenshot):** "shadow-mode discipline = every ranking change ships in `NOX_SALIENCE_MODE=shadow` for ≥1 week before going live. no silent regressions. [screenshot of /api/health.salience]"
- **T4 (architecture screenshot):** [architecture diagram PNG]
- **T5 (CTA):** "open source, MIT, 950+ tests. paper on arXiv: [link]. star → github.com/totobusnello/memoria-nox. AMA in replies."

### 6.2 LinkedIn Post Template
Already drafted in `paper/publication/distribution/linkedin-post.md`. Update with banner + 1 stat card screenshot.

### 6.3 HN Show HN
- **Title:** "Show HN: nox-mem – Pain-weighted hybrid memory with shadow discipline for AI agents"
- **Body:** Why I built it (vendor lock-in pain) → what it does (hybrid + KG + shadow) → numbers (Q1-Q4 wins) → how to try (3-command install) → paper link → AMA
- **Submit time:** Tuesday or Wednesday 14:00 UTC (HN US-morning peak)
- **Second-chance pool:** if first attempt <50 points, request second-chance pool 24h later

### 6.4 dev.to + Substack
Drafts already in `paper/publication/distribution/`. Add hero banner + 3 stat cards inline.

### 6.5 Viral Gist Template (extends recognized pattern)
- Pattern candidate: "extends Karpathy's LLM Wiki memory model" OR "extends Andrej's nanoGPT discipline to memory layer" — **TBD open question 3**
- Asset: GitHub Gist with markdown + embed banner + 1-paragraph philosophy
- Cross-link in Twitter T3 + dev.to footer

### 6.6 Product Hunt Launch Checklist
- [ ] PH page draft with banner + 3 stat cards + demo.gif
- [ ] Hunter lined up (Toto OR friendly OS founder)
- [ ] Launch Tuesday 00:01 PT
- [ ] Pre-launch tease: 1 tweet 24h before
- [ ] Maker comment at 09:00 PT with deeper context
- [ ] Reply to every comment first 6h

---

## 7. Dark/Light Mode Hygiene

**All visual assets MUST ship both variants via `<picture>` tag.**

### 7.1 Asset Pair Convention
```
assets/readme/<name>-dark.svg
assets/readme/<name>-light.svg
```

### 7.2 `<picture>` Pattern (mandatory for every asset)
```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/X-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/readme/X-light.svg">
  <img alt="X" src="assets/readme/X-light.svg" width="WIDTH">
</picture>
```

### 7.3 Exception
Demo GIF: single variant only (terminal output already has dark theme; light-mode users see dark terminal — acceptable, mirrors real product UX).

### 7.4 Color Tokens (TBD open question 1)
- **Brand primary:** TBD (amber/orange? deep teal? other?)
- **Brand secondary:** TBD
- **Dark mode bg:** `#0d0d0d` (GitHub dark match)
- **Light mode bg:** `#ffffff` (GitHub light match)
- **Dark mode text:** `#e6edf3`
- **Light mode text:** `#1f2328`

---

## 8. README Size Budget

| Section | Max Lines | Notes |
|---------|-----------|-------|
| Hero (2.1-2.9) | 80 | most visual, least prose |
| Architecture (3.1) | 40 | mostly image + 2 paragraphs |
| Quick Start (3.2) | 30 | code block + 2 paragraphs |
| Benchmarks (3.3) | 60 | table + methodology |
| vs Competitors (3.4) | 50 | abridged table |
| Works with every agent (3.5) | 60 | logo grids |
| How It Works (3.6) | 50 | pipeline narrative |
| Paper & Research (3.7) | 40 | abstract + bibtex |
| Configuration (3.8) | 40 | env vars table |
| Support (3.9) | 20 | links only |
| Footer | 30 | secondary badges, license, etc |
| **TOTAL** | **≤500** | hard cap |

**Wall-of-badges current ROADMAP.md v1 (631 lines) é warning sign documentado** — não repetir.

---

## 9. A/B Testing Methodology

### 9.1 What to Test
- Sub-tagline A vs B (section 2.3)
- Stat order (LoCoMo first vs OPEX first)
- Banner color palette (post-decision on open question 1)

### 9.2 How to Measure
**Simpler approach (no tooling required):** deploy variant A for 7 days, variant B for 7 days, compare:
- Stars/day delta (primary signal)
- Forks/day delta (secondary)
- README traffic via GitHub Insights (Traffic → Visitors)
- npm install rate via npmtrends

**Why not shields.io referrer:** custom analytics on a public README is privacy-iffy and adds complexity.

### 9.3 Decision Rule
- Stars/day delta ≥15% over 7d → ship the winner
- Delta <15% → keep current, no flip
- Run only 1 A/B at a time (avoid confounding)

---

## 10. Localization

- **v1:** English only (international audience, HN/Twitter/X primary distribution)
- **v2 (deferred):** Portuguese translation for Nox-Supermem landing page integration (Brasil/Hotmart)
- README.pt-BR.md as separate file, linked from header `<a href="README.pt-BR.md">🇧🇷 Português</a>` after v1 ships and is stable

---

## 11. Tests Plan

### 11.1 Automated Checks (CI on every PR to README)
- **Link checker:** `lychee README.md` — all anchors and external URLs resolve
- **Broken image checker:** verify every `assets/readme/*.svg` and `*.png` referenced actually exists
- **Lighthouse audit:** run on rendered GitHub page (manual ou CI via Puppeteer), score ≥90 for SEO + accessibility
- **SVG accessibility:** every `<img>` has `alt` text, color contrast ≥4.5:1 (WCAG AA)

### 11.2 Manual Checks (pre-launch)
- [ ] Hero loads in <2s on broadband (Lighthouse Performance ≥85)
- [ ] Dark mode + light mode visual check on GitHub.com (toggle browser theme)
- [ ] Mobile rendering (GitHub mobile app + Safari iOS)
- [ ] Cross-browser: Chrome, Safari, Firefox
- [ ] Demo GIF plays smoothly (no jank, no crop)
- [ ] All `<picture>` tags fall back gracefully when JS disabled

### 11.3 CI Script (proposed)
`scripts/readme-validate.sh`:
```bash
#!/usr/bin/env bash
set -e
lychee README.md
for f in $(grep -oE 'assets/readme/[^"]+' README.md | sort -u); do
  test -f "$f" || { echo "MISSING: $f"; exit 1; }
done
echo "README validation passed."
```

---

## 12. Definition of Done

Numbered acceptance criteria — **all must pass before merge**:

1. **Hero loads <2s** on broadband (Lighthouse Performance ≥85 on GitHub rendered page)
2. **Dark/light pair complete:** every `<picture>` has both `-dark.svg` and `-light.svg`, both render correctly when theme toggled in browser
3. **No broken links/images:** `scripts/readme-validate.sh` exits 0
4. **Stat SVGs reflect post-Q4 real numbers** (not placeholders) — Q1/Q2/Q3 winner numbers locked in `paper/publication/Q4-COMPARISON.md` before stat SVG generation
5. **Demo GIF <5MB** and ≤15s, shows real CLI output (not mocked)

---

## 13. NÃO-fazemos (v1 explicit cuts)

- **NO animated banner.** Static SVG only. GitHub markdown renderer strips `<animate>` and `<animateTransform>` tags inconsistently.
- **NO embedded video.** YouTube link in section 3.9 (Support) is fine, but no `<video>` tag — GitHub strips it.
- **NO interactive demo.** Static GIF only. CodeSandbox/StackBlitz embeds blocked by GitHub.
- **NO auto-rebuild of stat SVGs from CI.** Manual update on each milestone (Q1/Q2/Q3/Q4 lands → update). CI auto-update tempting but adds rendering pipeline complexity not worth it for v1.
- **NO carbon-neutral badge / DEI badge / generic "awesome" badges.** Signal-to-noise budget reserved for trust badges only.
- **NO sponsor badges / GitHub Sponsors CTA** in hero. Move to footer if needed (TBD).
- **NO Discord widget embed.** Slow load, GitHub strips iframe — link only.

---

## 14. Order of Execution (when Q4 gate opens)

### Day 0 — Asset Production (1 day)
- [ ] Confirm brand palette decision (open question 1)
- [ ] Skill `design` (Gemini 3.1 Pro): generate banner-{dark,light}.svg
- [ ] Skill `banner-design`: generate 6 stat cards × 2 variants = 12 SVGs
- [ ] Mermaid: architecture-{dark,light}.png via `mmdc`
- [ ] asciinema + asciicast2gif: demo.gif (storyboard in 2.8)
- [ ] Logo derived from banner mark

### Day 1 — README Rewrite
- [ ] Branch `gtm/readme-hero-v1`
- [ ] Replace `README.md` with new structure (sections 2 + 3)
- [ ] Move secondary badges to footer
- [ ] Run `scripts/readme-validate.sh`
- [ ] PR review (self + 1 reviewer if available)

### Day 2 — Deploy + Launch
- [ ] Merge to main
- [ ] Twitter/X thread (section 6.1) — schedule 14:00 UTC
- [ ] Trendshift submit
- [ ] LinkedIn post (section 6.2)

### Day 3 — Distribution Wave 2
- [ ] HN Show HN (section 6.3) — Tuesday/Wednesday 14:00 UTC
- [ ] Viral gist publish (section 6.5)
- [ ] dev.to + Substack (section 6.4)

### Day 7 — Measure
- [ ] Stars/day delta vs pre-launch baseline
- [ ] GitHub traffic insights (visitors, referrers)
- [ ] npm install rate
- [ ] HN/Twitter engagement metrics
- [ ] Decision: A/B test variant B (section 9) OR iterate banner/stats

### Day 14 — Iterate
- [ ] A/B test sub-tagline B if Day 7 results suggest room
- [ ] Update stat numbers if Q5 evals shipped
- [ ] Refresh demo.gif if major CLI changes

---

## 15. Riscos & Mitigations

| Risco | Severidade | Mitigation |
|-------|------------|------------|
| Stat SVGs ficam stale (números mudam, README esquecido) | MEDIUM | Link `[live →]` next to each stat pointing to `benchmark/*.md` (live truth); README footer note "stats updated YYYY-MM-DD" |
| Demo GIF mostra CLI desatualizada | MEDIUM | Re-record on every major version bump; checklist em release process |
| Viral attempt flopa (HN <50 points, Twitter <1k impressions) | HIGH | HN second-chance pool 24h later; alternative angle ("shadow discipline" philosophy vs "hybrid retrieval" tech); plan B = focus on dev.to + LinkedIn organic |
| Brand palette decisão atrasada (open question 1) | MEDIUM | Default fallback: GitHub native colors (orange `#fb8500` for primary, teal `#2ca5b3` for secondary) — production-ready if Toto não decidir até Day 0 |
| Trendshift submit rejeitado | LOW | Plan B: organic Twitter mentions, no Trendshift badge |
| GitHub renderer strips `<picture>` em algum contexto edge | LOW | Fallback `<img src="...-light.svg">` sempre presente; degrada gracefully |
| Render Mermaid PNG inconsistente entre máquinas | MEDIUM | Lock `mmdc` version em `package.json` devDeps; document exact render command em `assets/readme/README.md` |
| Mobile rendering quebra (banner cortado) | MEDIUM | Test seção 11.2 mandatório; max-width 100% nos `<img>` |

---

## 16. Open Questions (NÃO-decididas por Prometheus — Toto sign-off needed)

### Q1: Brand color palette
**Question:** Quais são as brand colors primárias e secundárias do nox-mem?
**Why blocking:** Banner, stat cards, e architecture diagram precisam de palette consistente. Sem decisão, assets ficam vibe-driven e podem clashar.
**Options:**
- A) Amber/orange (`#fb8500` + `#ffb703`) — warmth, "memory" semiotic
- B) Deep teal/cyan (`#2ca5b3` + `#0a9396`) — technical, "data" semiotic
- C) Purple/violet (`#7209b7` + `#3a0ca3`) — premium, "AI" semiotic
- D) Black/white minimal (high contrast, brand-agnostic)
**Recommendation (if Toto silent até Day 0):** D (black/white minimal) — safe default, can be re-skinned em v2 once brand identity matures.

### Q2: Discord/Slack community?
**Question:** Existe canal Discord/Slack para community? Se sim, link público?
**Why:** Section 3.9 (Support) currently has placeholder. Either add link OR remove the line entirely.
**Recommendation (if silent):** Remove line — não fingir community que não existe; GitHub Discussions only.

### Q3: Viral gist pattern
**Question:** Qual pattern "extends X" usar no viral gist (section 6.5)?
**Why:** "Extends Karpathy LLM Wiki" funciona se ele já mencionou memory; sem fit forçado parece cringe.
**Options:**
- A) "Extends Karpathy's LLM Wiki memory model"
- B) "Extends nanoGPT discipline to the memory layer"
- C) "Extends MemGPT's hierarchy with shadow-mode validation"
- D) No "extends X" framing — original positioning only
**Recommendation (if silent):** D (no forced pattern) — risk of cringe > reward of recognition.

### Q4: arXiv submission target date?
**Question:** Quando paper vai pra arXiv? Impacta seção 3.7 (link + BibTeX live).
**Why:** Se paper landed ANTES do gate Q4 opens, podemos linkar real arXiv URL. Se depois, README ships com placeholder.
**Recommendation (if silent):** Ship com placeholder `arxiv.org/abs/TBD`, update PR no Day 1 quando paper landed.

### Q5: Trendshift account ready?
**Question:** Trendshift account criada e nox-mem listado? Badge URL placeholder na seção 2.4.
**Why:** Submission process leva 24-48h; precisa começar Day 0 não Day 2.
**Recommendation (if silent):** Submit Day 0 morning, badge URL fica placeholder até approval; commit URL update separately.

---

## 17. Spec Versioning & Sign-off

- **v0.1 (2026-05-17):** initial spec — Prometheus overnight automode
- **v1.0 (TBD):** locked when Q4 gate opens, brand palette decided (Q1), viral pattern decided (Q3)
- **Sign-off required from Toto:** Q1, Q2, Q3, Q4, Q5 before execution

---

## 18. References

- Memory file `repo-visual-style-inspiration` (2026-05-17) — memanto + agentmemory competitor analysis
- `paper/publication/Q4-COMPARISON.md` — gate condition (must show nox-mem winning)
- `paper/publication/distribution/` — LinkedIn + dev.to + Substack drafts already written
- `docs/HANDOFF.md` — current state (v3.7, 62.9k chunks, schema v10)
- `docs/ROADMAP.md` — GTM Phase 2 position
- `specs/2026-05-10-E14-retrieval-evolution.md` — concurrent eval work (numbers feeding stats SVGs)
- This spec: `specs/2026-05-17-GTM-readme-hero-upgrade.md`

---

**END OF SPEC**

Execute on gate-open trigger only. Do NOT touch `README.md` before gate condition met (Q4 COMPARISON shows nox-mem #1 or tied #1).
