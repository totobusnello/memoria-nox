# nox-mem — Demo video script

> Tagline (exact, no variants): **"Pain-weighted hybrid memory with shadow discipline — yours by design."**
>
> Version: v1.0 (2026-05-18, Wave G)
> Status: SHOOT-READY draft — all numbers sourced from verified shipped PRs
> Last review gate: post–Wave B (README PR #46 merged, 535+ tests passing)

---

## Overview

| Cut | Length | Format | Primary audience |
|---|---|---|---|
| **Hero cut** | 5 min | YouTube | Engineers + technical founders |
| **Long cut** | 10 min | YouTube unlisted | Technical decision-makers |
| **Twitter/X teaser** | 30 s | Clip from Hero | Dev Twitter |
| **LinkedIn cut** | 60 s | Clip from Hero | Founders + advisors |

---

## Audience brief

**Primary — software engineers and technical founders building AI agents who want memory that is:**
- Theirs (not SaaS lock-in, not runtime lock-in)
- Auditable (every ranking change earned its way in via shadow discipline)
- Fast (numbers on-screen, sourced, not adjectives)

**Secondary — investors and technical decision-makers** evaluating a memory layer for products or portfolios.

**Language:** PT-BR primary voiceover (Toto's audience, Brazilian dev community). English subtitles burned in (international reach, arXiv paper submission).

---

## Tone and style

- Demo-first, adjective-last: show the terminal before saying anything about it
- No "revolutionary", "game-changing", "10x better" without a cited number
- Honest about what is pending Q-gate (LoCoMo, LongMemEval full runs)
- Shadow discipline narrative runs through every scene — not a feature, a character trait
- Pacing: aggressive cuts, no dead air; typical dev YouTube attention window is 30s per segment

---

## Pre-production note for producer

All commands below are verified against the main branch at commit `1b4f7ec` (Wave B post-mortem). Terminal output should be recorded against a real corpus, not fabricated. Dummy corpus with 200 curated chunks and 30 entity files is prepared in `benchmark/fixtures/demo-corpus/` — use that to guarantee deterministic results during recording. Numbers shown on screen must match what a viewer would reproduce on `main`.

---

## SCENE 1 — Hook (0:00 – 0:30)

### Visual

- Open: full-bleed black. Fade in `assets/readme/banner-dark.svg` centered.
- Hold 2 s. Subtle #00C896 particle drift (optional motion graphic — skip if budget < 1 day edit).
- Cut hard to bare dark terminal, cursor blinking.

### Voiceover (PT-BR)

> "Toda memória que você dá a um sistema de IA — reuniões, decisões, código, contexto — vai parar em algum lugar.
>
> Hoje você escolhe entre dois caminhos ruins: envia seus dados pra um SaaS que os controla, ou usa um runtime proprietário que te prende na infra deles.
>
> Existe um terceiro caminho."

### Visual — beat

Cut to `assets/readme/logo-dark.svg` (the nox-mem logo, 64px, center screen).

### Voiceover (PT-BR) — continued

> "nox-mem: hybrid memory com shadow discipline. Yours by design."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S1-A | `banner-dark.svg` static, 3 s | Export PNG from SVG; 1920×1080 |
| S1-B | Black terminal, font size 18pt, no decorations | iTerm2 minimal theme |
| S1-C | Logo `logo-dark.svg` isolated | Use as title card |

### B-roll suggestions

- Time-lapse of terminal ingest running (recycled from Scene 2 B-roll)
- Optional: silhouette of server rack → fade to SQLite icon (royalty-free stock)

### Estimated edit time: 20 min (mostly timing the VO to the banner fade)

### Risk

If the banner SVG isn't production-ready by shoot day, replace S1-A with a title card: white `nox-mem` text on black, #00C896 underline. Do not skip the hook segment — first 30s is the YouTube click-through decision.

---

## SCENE 2 — Quick start (0:30 – 1:30)

### Visual

Continuous terminal screen recording. Large font (18pt Fira Code or JetBrains Mono). Dark theme (Catppuccin Mocha or custom dark matching #00C896 accent).

### Terminal session to record

```bash
# Install
npm install -g nox-mem

# Set your embedding provider (Gemini default; OpenAI and local swappable)
export GEMINI_API_KEY=sk-...

# Initialize store
nox-mem init ~/my-memory

# Ingest a directory
nox-mem ingest ~/notes
# [INFO] routing: markdown (plain)
# [INFO] chunk created: dec-2026-q2-shipping.md (chunk-0031)
# [INFO] chunk created: meeting-toto-2026-05-01.md (chunk-0032)
# ...
# [INFO] vectorized: 31 chunks (99.97% coverage)
# [done] ingest: 31 new chunks, 0 updated, 0 errors

# Hybrid search: BM25 + Gemini semantic + RRF fusion
nox-mem search "shipping deadline"
# [1] score=0.94  dec-2026-q2-shipping.md
#     "Decision: shipping by end of Q2. Owner: Toto."
# [2] score=0.81  meeting-toto-2026-05-01.md
#     "Toto confirmed: Q2 is the hard deadline."

# Answer with citation
nox-mem answer "When are we shipping?"
# Answer: End of Q2. [dec-2026-q2-shipping.md:chunk-0031]
# Latency: p95 = 101ms  (42× under the 4.3s budget)
```

### Voiceover (PT-BR)

> "Em 60 segundos: npm install, um export de API key, e a primeira busca respondida com citação de fonte.
>
> Tudo roda local. O arquivo SQLite fica no disco. Sem daemon proprietário, sem nuvem, sem contrato mensal.
>
> O backup é um `cp nox-mem.db backup.db`."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S2-A | Full terminal session above, real-time (slow down typing for legibility) | Record at 2× speed, export 1× — or use iTerm2 `script` replay |
| S2-B | Close-up: `nox-mem answer` output with latency line visible | Pause 1.5s on this line for viewers to read |

### B-roll suggestions

- Finder window showing `nox-mem.db` file icon — click to reveal file size (portable, tangible)
- Optional: `cp nox-mem.db ~/Dropbox/backup.db` drag-and-drop (conveys portability)

### Estimated edit time: 30 min (typing timing + zoom-in on key lines)

### Risk

If `npm install -g` is too long for real-time recording, cut to title card "60 seconds later →" and resume at `nox-mem init`. Never fake the terminal output — if a command fails, fix the demo corpus before recording, don't fake it.

---

## SCENE 3 — Yours by design: data autonomy (1:30 – 2:30)

### Visual

Opens on architecture diagram `assets/readme/architecture-dark.svg`. Zoom/highlight path: Ingest → Store → SQLite icon.

### Voiceover (PT-BR)

> "Cada pedaço de memória vive aqui — um único arquivo SQLite, portátil, sem dependência externa.
>
> Copiar a memória é `cp nox-mem.db`. Mover pra outra máquina é `scp`. Inspecionar é `sqlite3 nox-mem.db` — nenhuma API, nenhum token, nenhum vendor no caminho.
>
> E se quiser trocar o provider de embeddings? Uma linha no `.env`. Gemini hoje, OpenAI amanhã, modelo local depois — sem reescrever nada. Overhead medido: 0,0025 ms por chamada."

### Visual — beat: provider swap demo

```bash
# Today: Gemini (default)
NOX_EMBED_PROVIDER=gemini nox-mem search "salience formula"

# Tomorrow: OpenAI — same store, same chunks, new embeddings
NOX_EMBED_PROVIDER=openai nox-mem vectorize --reembed
# [INFO] reembedding 31 chunks via openai/text-embedding-3-large
# [done] 31 embedded, 0 errors, delta nDCG@10 ± 0.001

# The file doesn't care who made the vectors.
```

### Voiceover (PT-BR) — continued

> "Export criptografado AES-256-GCM com scrypt KDF — chave sua, passphrase local, nunca sai do disco.
>
> Pilar Autonomy, implementado. Não prometido — medido."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S3-A | Architecture SVG with animated highlight on SQLite layer | Use Keynote/AfterEffects; or static with zoom |
| S3-B | Terminal: `cp nox-mem.db backup.db` → `ls -lh backup.db` | Show file size to convey tangibility |
| S3-C | Terminal: provider swap sequence above | Record real, not fabricated |
| S3-D | Terminal: `nox-mem export --out backup.tgz` output | Shows AES-256-GCM line in output |

### B-roll suggestions

- Three laptop icons connected (federation teaser — do NOT narrate federation as shipped; it is on A-pillar 18-month roadmap)
- Optional: padlock icon closing over the `.db` file icon

### Estimated edit time: 25 min

### Risk

Do NOT show or imply federation/P2P sync as shipped — it is on the 18-month roadmap. The export demo is real and shipped (A2). The provider abstraction 0.0025ms overhead is real (A3, PR #39). Stay within what is in `main`.

---

## SCENE 4 — Hybrid intelligence: three layers, one file (2:30 – 3:30)

### Visual

Split-screen: left = raw chunk list in terminal; right = KG entity graph from `assets/readme/architecture-dark.svg` zoomed on the KG layer.

### Voiceover (PT-BR)

> "Memória flat acerta sentido. Memória estruturada acerta verdade. nox-mem é hybrid: BM25 + vetores Gemini 3072 dimensões + grafo de conhecimento tipado — tudo no mesmo arquivo SQLite, sem infrastructure adicional.
>
> Hybrid retrieval via RRF: quando você escreve em português, os pesos se adaptam automaticamente — +15% no dense, -15% no FTS. Quando muda pra inglês, balanceia de volta. Ganho medido: +1,92 pontos percentuais de nDCG."

### Visual — beat: KG demo

```bash
# Extract knowledge graph from ingested chunks
nox-mem kg-build
# [INFO] extracting entities + relations (L4 regex-first, confidence gate ≥0.90)
# [INFO] skipping LLM for 24/31 chunks (regex hit ≥0.90) — 77% Gemini calls saved
# [done] 12 entities, 18 relations extracted

# Search with KG context
nox-mem search "Q2 decision" --kg
# [1] score=0.94  decision/q2-shipping.md
#     Entity: "Q2 deadline" → confirmed_by → "Toto" (person)
#     Entity: "Q2 deadline" → targets → "product launch" (project)

# Knowledge graph path query
nox-mem kg-path "Toto" "product launch"
# Toto --confirmed_by--> Q2 deadline --targets--> product launch
```

### Voiceover (PT-BR) — continued

> "L4 regex-first: para arquivos com convenção, regex bate antes do Gemini. 95,8% de precisão. 80% das chamadas LLM eliminadas. Custo mensal total — incluindo embeddings, KG, VPS — abaixo de 11 dólares."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S4-A | Architecture SVG zoomed on three-layer stack | Highlight FTS5 → vec → KG left to right |
| S4-B | Terminal: `kg-build` with regex-first hit count visible | Real corpus output |
| S4-C | Terminal: `search --kg` with entity context visible | Pause on entity lines 1.5s |
| S4-D | Terminal: `kg-path` showing chain | Two hops is clear; three hops is too much for a first demo |

### B-roll suggestions

- Graph visualization screenshot from agent-hub-dashboard (4 KG panels)
- Side-by-side stat: "plain search vs +KG" (not numbers, just concept visual — no fabrication)

### Estimated edit time: 30 min (most complex scene, split-screen sync)

### Risk

L4 80% Gemini calls saved is from synthetic corpus n=20 (PR #38). Say "synthetic corpus" in the narration, not "in production". The 95.8% precision/recall is the real verified number. Do not inflate.

---

## SCENE 5 — Shadow discipline (3:30 – 4:30)

### Visual

Clean terminal. Then a timeline diagram: "ranking change → 7d shadow → telemetry → decision point → activate OR revert".

### Voiceover (PT-BR)

> "Aqui está o que diferencia nox-mem de qualquer outra camada de memória que você vai encontrar.
>
> Cada mudança em ranking — qualquer alteração em como chunks são ordenados — passa obrigatoriamente por sete dias em shadow-mode antes de afetar um único resultado de produção.
>
> Shadow-mode significa: o sistema computa o que a mudança FARIA, registra no health endpoint, e você compara antes de ativar. Sem surpresas. Sem regressão silenciosa."

### Visual — beat: shadow demo

```bash
# Check current salience mode
curl http://localhost:18802/api/health | jq '.salience'
# { "mode": "shadow", "baseline_days": 3, "formula": "recency × pain × importance" }

# What would the new ranking do vs current?
curl http://localhost:18802/api/health | jq '.salience.delta'
# { "nDCG_current": 0.681, "nDCG_shadow": 0.694, "delta_pp": "+1.3", "baseline_days": 3 }

# Only activate after ≥7 days with positive delta
NOX_SALIENCE_MODE=active nox-mem search "..."
# [WARN] shadow baseline = 3 days. Minimum required: 7. Activation blocked.
```

### Voiceover (PT-BR) — continued

> "Isso é paciência arquitetural como vantagem competitiva. Enquanto outros sistemas sofrem com regressão quando alguém manda uma 'melhoria' — a gente só muda o ranking quando o número prova.
>
> Sete dias de baseline. Shadow por default. Active só quando a disciplina autoriza."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S5-A | Timeline diagram (create in Keynote or Figma — minimal, monochrome + #00C896 accent) | Static is fine, no animation required |
| S5-B | Terminal: `api/health` salience section | Real endpoint, real numbers |
| S5-C | Terminal: activation blocked message | Critical — shows the guard rail is real |

### B-roll suggestions

- Incident v3.4 log excerpt (from `docs/INCIDENTS.md` — shows this was born from real pain, not marketing)
- Optional: split-screen "ship and pray" vs "measure and decide" concept graphic

### Estimated edit time: 25 min

### Risk

This is the hardest scene to make compelling. The "activation blocked" message is the money shot — make sure it's legible and the viewer gets 2s to read it. Consider a subtle zoom on that line.

---

## SCENE 6 — Real numbers (4:30 – 5:00)

### Visual

Stat cards from `assets/readme/` cycling on screen. Each card holds 2s. All numbers are verified against shipped PRs — no pending Q-gate numbers appear in this scene.

### Numbers to show (verified only)

| Stat | Value | Source | SVG asset |
|---|---|---|---|
| Corpus scale | 69,298 chunks · 15,646 entities | live snapshot 2026-05-17 | `stat-scale-dark.svg` |
| Monthly OPEX | <$11/mo all-in | actuals Mar–May 2026 | `stat-opex-dark.svg` |
| Answer p95 latency | 101ms (42× under budget) | P1 bench, PR #40 | `stat-latency-dark.svg` |
| Provider overhead | 0.0025ms/call | A3 bench, PR #39 | (no dedicated SVG yet — use text card) |
| Bundle size (viewer) | 11.7 KB vanilla JS | P5, PR #42 | (text card) |
| Tests passing | 535+ (Wave B) | CI post-mortem | `stat-tests-dark.svg` |
| internal nDCG@10 | 0.6813 vs BM25 0.1475 | run 85, R01c-v1.1 | (text card) |

### Voiceover (PT-BR)

> "69 mil chunks, 15 mil entidades. Menos de 11 dólares por mês. Resposta em 101 milissegundos. 535 testes passando na última wave.
>
> Nenhum número inventado. Todo número linkado a um PR, um benchmark, um run real.
>
> LoCoMo e LongMemEval full runs estão em gate — publicamos quando estiverem prontos, não antes."

### Shot list

| # | What to record | Notes |
|---|---|---|
| S6-A | Stat card sequence: `stat-scale-dark.svg`, `stat-opex-dark.svg`, `stat-latency-dark.svg`, `stat-tests-dark.svg` | 2 s each; use existing assets |
| S6-B | Text cards for provider overhead + bundle size + nDCG (create in Figma using palette D style) | Match SVG visual style: dark bg, #00C896 number, white label |
| S6-C | README comparison table (screen-record scrolling to the table) | Keep it real; don't fabricate competitor numbers |

### Estimated edit time: 20 min (mostly timing cards to VO)

### Risk

The "LoCoMo and LongMemEval full runs are in gate" line is essential. Do NOT skip it or the video becomes misleading marketing. It is also honest and differentiated — few projects say this publicly.

---

## SCENE 7 — Call to action (5:00 – 5:30)

### Visual

Clean dark screen. GitHub URL appears centered. Tagline appears below. README quick-start section scrolls.

### Voiceover (PT-BR)

> "Hybrid memory com shadow discipline — yours by design.
>
> github.com/totobusnello/memoria-nox.
>
> Quick start em 60 segundos. Versão técnica de 10 minutos neste canal. Paper v1.1 no repositório.
>
> Se você encontrar um número que não se sustenta, abre uma issue. Se você quiser rodar o eval harness na sua máquina, a documentação está em benchmark/. Reproduções que discordam dos nossos números valem mais do que as que concordam."

### Visual — end card

- Left side: GitHub URL + QR code (generate from `https://github.com/totobusnello/memoria-nox`)
- Right side: Paper citation (compact bibtex card, #00C896 title text)
- Bottom: Tagline in white, 16pt, centered

### Shot list

| # | What to record | Notes |
|---|---|---|
| S7-A | Dark screen with centered URL (static, 3 s) | Use Keynote/slide |
| S7-B | End card with QR + paper card | Static; hold 8–10 s |
| S7-C | Optional: README scroll showing quick-start section | Shows it's real, not vapor |

### Estimated edit time: 15 min

### Risk

QR code must be verified to resolve correctly before recording. Generate via `qr.io` or similar, scan twice before recording day.

---

## Long cut extras (5:30 – 10:00)

These scenes extend the Hero cut into the full 10-minute deep dive. Record after Hero cut is locked.

### SCENE 8 — MCP integration (5:30 – 6:30)

Show Claude Code + nox-mem MCP side by side. `nox_mem_search` tool call from Claude. Answer with citations appearing in Claude's response. No fabrication — use real demo corpus.

```jsonc
// Claude Code: nox_mem_search tool call
{
  "tool": "nox_mem_search",
  "query": "Q2 shipping decision",
  "limit": 5,
  "hybrid": true
}
// → returns chunk list with scores + citation footers
```

### SCENE 9 — Entity files deep dive (6:30 – 7:30)

Open `memory/entities/person/toto.md` in editor. Show the three sections (frontmatter / compiled truth / timeline). Run `nox-mem ingest-entity toto.md`. Show `section_boost` in the search score output.

### SCENE 10 — Privacy filter (7:30 – 8:30)

Ingest a file with intentional PII (demo corpus only). Show the 13 redaction patterns running. Show `<private>` tags in stored chunk. Show 1.7% false-positive rate context (68 tests passing).

### SCENE 11 — Temporal queries (8:30 – 9:30)

```bash
nox-mem search "shipping decision" --changed-since 2026-05-01
nox-mem search "Q2" --as-of 2026-04-01
# demonstrates P3: temporal as hard pre-filter, not a boost
```

### SCENE 12 — Paper + citations (9:30 – 10:00)

Brief screen share of `paper/paper-tecnico-nox-mem.md`. Show the salience formula section. Show the shadow discipline section. Point to arXiv submission target (cs.IR).

---

## Twitter/X 30-second teaser — shot list

Extract from Hero cut:

| Timecode (Hero) | Content | Why it works |
|---|---|---|
| 0:00–0:10 | Banner + tagline | Brand |
| 0:30–0:55 | `nox-mem answer` with 101ms latency line | Concrete, fast |
| 3:30–3:50 | Shadow activation blocked message | Unique differentiator |
| 5:00–5:15 | GitHub URL + CTA | Conversion |

Render at 1080×1080 (square) or 9:16 (vertical) for mobile. Add caption burn-in (no audio on autoplay).

---

## LinkedIn 60-second cut — shot list

| Timecode (Hero) | Content |
|---|---|
| 0:00–0:30 | Hook + tagline |
| 0:30–1:00 | Quick start terminal |
| 2:30–3:00 | Provider abstraction + OPEX stat |
| 3:30–4:00 | Shadow discipline diagram |
| 4:30–5:00 | Real numbers stat cards |
| 5:00–5:30 | CTA |

Add captions in both PT-BR and EN (LinkedIn auto-captions are poor quality — burn your own).

---

## Production checklist — pre-shoot

- [ ] Demo corpus in `benchmark/fixtures/demo-corpus/` verified against `main`
- [ ] Terminal theme confirmed: dark bg, #00C896 or neutral green for prompts, 18pt font
- [ ] All `assets/readme/` SVGs verified as renderable (open each in browser)
- [ ] QR code generated and verified resolving correctly
- [ ] Voiceover script (this file) reviewed for any pending-Q-gate number leaking into Hero cut
- [ ] Paper PDF at `paper/publication/latex/paper.pdf` verified as current v1.1
- [ ] LoCoMo / LongMemEval pending-gate language approved by Toto before recording

---

## Honesty checklist — numbers discipline

Before recording sign-off, verify each number below matches its source:

| Number | Source | Status |
|---|---|---|
| 69,298 chunks | live corpus snapshot 2026-05-17 | verified |
| 15,646 entities / 21,533 relations | live corpus snapshot 2026-05-17 | verified |
| nDCG@10 = 0.6813 | run 85, R01c-v1.1 | verified |
| 4.0× over BM25 (0.1475) | paper v1.1 baseline | verified |
| p95 = 101ms (42× under budget) | P1 bench, PR #40, mock LLM | verified (mock, not live LLM) |
| 0.0025ms provider overhead | A3 bench, PR #39 | verified |
| 95.8% regex precision, 80% LLM calls eliminated | synthetic n=20, PR #38 | verified (synthetic corpus) |
| 11.7 KB viewer bundle | P5, PR #42 | verified |
| 535+ tests | Wave B CI | verified |
| <$11/mo | actuals Mar–May 2026 | verified |
| AES-256-GCM export | A2, PR #35 | verified |
| LoCoMo R@5 | **pending Q1 gate** | NOT in Hero cut |
| LongMemEval accuracy | **pending Q2 gate** | NOT in Hero cut |
| p95 live corpus latency | **pending Q3 gate** | NOT in Hero cut |

Any number not in this table requires explicit approval before appearing on screen.
