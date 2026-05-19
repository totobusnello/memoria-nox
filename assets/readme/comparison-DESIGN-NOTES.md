# comparison-chart — design notes

> Documentação de procedência e raciocínio para `comparison-chart-light.svg` +
> `comparison-chart-dark.svg`. Toda decisão visual e cada score do radar/grid
> referencia uma linha de `benchmark/COMPARISON.md` (snapshot 2026-05-18).
> Se essa referência mudar, o SVG precisa ser regerado e este documento
> atualizado.

---

## Intenção

Substituir (ou complementar) a tabela texto da seção 2 de `benchmark/COMPARISON.md`
por uma peça visual que:

1. Mostra **forma de cobertura** em um relance — o leitor vê a diferença
   entre nox-mem e a concorrência antes de ler qualquer rótulo.
2. Confirma **número exato** em um grid abaixo — sem mistério, sem leitura
   ambígua de polígono.
3. Mantém **honestidade**: claim de competidor não-verificado aparece como
   `vendor` / `paper` / `docs`, não como check verde.

Layout escolhido é a **Option C** sugerida pelo brief: radar (overview) + grid
(detalhe). Os dois compartilham os mesmos 7 eixos para evitar leitura cruzada
incoerente — o que está no radar está na linha do grid e vice-versa.

---

## Arquivos

| Arquivo | Dimensão | Tema |
|---|---|---|
| `comparison-chart-light.svg` | 1100×900 | Light (`#F5F5F7` ground) |
| `comparison-chart-dark.svg` | 1100×900 | Dark (`#0E0E10` ground) |

Ambos seguem o vocabulário visual de `architecture-light.svg` / `banner-dark.svg`:
JetBrains Mono, hairline grid 50px, section labels all-caps `letter-spacing: 2`,
accent `#00C896` para nox-mem.

Embed sugerido no README:

```md
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/comparison-chart-dark.svg">
  <img alt="nox-mem vs competitors — capability radar and coverage grid" src="assets/readme/comparison-chart-light.svg">
</picture>
```

---

## Eixos do radar (7)

Critério de escolha: dimensão é eixo do radar **se** distingue arquitetura ou
filosofia entre os sistemas. Métrica numérica volátil (ex: nDCG, latency p95) fica
fora do radar e mora nas stat cards (`stat-longmemeval-*.svg`, `stat-latency-*.svg`).
Radar é uma assinatura estrutural, não um placar.

| # | Eixo | Pergunta que responde | Procedência |
|---|---|---|---|
| 1 | Hybrid retrieval | BM25 + vector + RRF nativo? | COMPARISON.md §2 linha "Hybrid search" |
| 2 | Open-source license | Código auditável e fork-able? | COMPARISON.md §2 linha "Open source" + §6 |
| 3 | Self-hosted zero-daemon | Roda em VPS sem orquestração externa? | COMPARISON.md §2 linha "Zero-daemon (autonomous deploy)" + §6 |
| 4 | Provider autonomy (BYOK) | Posso trocar embedding/LLM provider sem reescrever? | COMPARISON.md §2 linha "Provider swap (BYO embeddings)" + A3 PR #39 |
| 5 | Production-verified numbers | Tem número de benchmark padronizado e reproduzível? | COMPARISON.md §1 +§4 + §5 Q1/Q2/Q3 |
| 6 | Shadow discipline | Métrica medida em paralelo ≥ 1 semana antes de aplicar? | CLAUDE.md "Shadow-mode" + Fase 1.7b-b + memory `feedback_shadow_mode_for_ranking_changes` |
| 7 | Pain weighting | Salience leva severidade em conta (recency × pain × importance)? | Schema v9 (CLAUDE.md "Schema (V7)") |

Eixos 6 e 7 são **paper novelty** — nenhum competidor mapeado oferece. É
intencional que eles fiquem no radar: a forma do polígono nox-mem é
imediatamente diferente, e o "porquê" está nesses dois eixos.

---

## Sistemas plotados (5 no radar, 6 no grid)

| Sistema | No radar? | No grid? | Justificativa |
|---|---|---|---|
| **nox-mem** | sim (hero) | sim | foco do estudo |
| **mem0** | sim | sim | concorrente popular, ~53k stars, hybrid + optional graph |
| **Letta / MemGPT** | sim | sim | tração acadêmica, agent loop |
| **agentmemory** | sim | sim | claim LoCoMo R@5 95.2% — referência direta |
| **Memanto** | sim | sim | concorrente SaaS PT-BR alvo, claim LME 89.8% |
| **Zep** | não (radar) | sim | excluído do radar para legibilidade (5 polígonos cap); presente no grid |

Decisão de omitir Zep do radar é pura legibilidade: 6 polígonos sobrepostos
ficam ilegíveis no centro. O grid fecha o gap.

---

## Escala de score (0–3 ordinal)

| Score | Significado | Cor no grid |
|---|---|---|
| 3 | Verified / native / first-class | `#00A87A` (light) / `#00C896` (dark) — checkmark |
| 2 | Partial / optional / configurable | `#FFB800` — tilde `~` |
| 1 | Vendor-claimed / docs-only / weak | `#C18A45` (light) / `#D6A565` (dark) — palavra (`vendor`/`paper`/`docs`) |
| 0 | Absent / closed / vendor-controlled | `#FF4444` — cross `✗` ou desconhecido — `#888888` — `?` |

O símbolo `?` é deliberado e existe **só** quando COMPARISON.md marca a célula
como `❓` (vendor não publica). Não é "talvez sim" — é "não temos como
verificar". O grid distingue:

- `✗` (vermelho) — afirmação positiva: o sistema **não** tem a capacidade
- `?` (cinza)   — falta de evidência: o sistema **não publica**

---

## Matriz de scores (auditável linha-por-linha)

| Eixo | nox-mem | mem0 | Letta | agentmemory | Memanto | Zep |
|---|---:|---:|---:|---:|---:|---:|
| 1. Hybrid retrieval | 3 | 2 | 2 | ? | ? | 3 |
| 2. Open-source | 3 | 3 | 3 | 2 | 0 | 3 |
| 3. Self-hosted zero-daemon | 3 | 2 | 2 | 2 | 0 | 2 |
| 4. Provider autonomy (BYOK) | 3 | 3 | 3 | ? | 0 | 3 |
| 5. Production-verified | 3 | 1 (vendor) | 1 (paper) | 1 (vendor) | 1 (vendor) | 1 (docs) |
| 6. Shadow discipline | 3 | 0 | 0 | 0 | 0 | 0 |
| 7. Pain weighting | 3 | 0 | 0 | 0 | 0 | 0 |
| **Total / 21** | **21** | **10** | **9** | **6** | **2** | **12** |

> Zep aparece no grid mas não no radar; total Zep = 12/21 (não plotado no
> radar para legibilidade).

### Justificativa por cell (rastreável a COMPARISON.md)

**nox-mem — 21/21**
- Hybrid retrieval: COMPARISON.md §2 — "✅ BM25 + sqlite-vec + RRF (k=60)"
- Open-source: COMPARISON.md §2 — "✅ MIT"
- Self-hosted zero-daemon: COMPARISON.md §2 — "✅ A4 validated (PR #20)"
- Provider autonomy: COMPARISON.md §2 — "✅ A3 provider abstraction (merged PR #39)"
- Production-verified: COMPARISON.md §1 — "nDCG@10=0.3338 +18.8% vs FTS5 [verified 2026-05-18]" + p50=940ms
- Shadow discipline: CLAUDE.md "Salience formula (Fase 1.7b-b, shadow-mode)"
- Pain weighting: CLAUDE.md "Schema v10 — pain REAL DEFAULT 0.2"

**mem0 — 10/21**
- Hybrid retrieval = 2: COMPARISON.md §2 — "✅ (vector + optional graph)" — não é BM25+vec+RRF nativo
- Open-source = 3: COMPARISON.md §2 — "✅ Apache-2.0" + 53k+ stars
- Self-hosted zero-daemon = 2: COMPARISON.md §2 — "❌ Postgres + Qdrant" (não é zero-daemon mas é self-hostable)
- Provider autonomy = 3: COMPARISON.md §2 — "✅ OpenAI/Anthropic/etc."
- Production-verified = 1: COMPARISON.md §4 — "Publishes its own benchmark on docs site; numbers vary by version"
- Shadow discipline = 0: ausente da documentação pública
- Pain weighting = 0: ausente da documentação pública

**Letta / MemGPT — 9/21**
- Hybrid retrieval = 2: COMPARISON.md §2 — "✅ recall + archival"
- Open-source = 3: COMPARISON.md §2 — "✅ Apache-2.0"
- Self-hosted zero-daemon = 1: COMPARISON.md §2 — "❌ Docker + Postgres" (Docker stack pesado)
- Provider autonomy = 2: configurável mas defaulta OpenAI
- Production-verified = 1: COMPARISON.md §4 — "MemGPT paper (arXiv:2310.08560)... agent-loop, not retrieval-only" — não comparável direto
- Shadow discipline = 0
- Pain weighting = 0

**agentmemory — 6/21**
- Hybrid retrieval = ?: COMPARISON.md §2 — `❓` (não publicado)
- Open-source = 2: COMPARISON.md §2 — "✅ MIT (CLI) / ❌ iii-engine" (engine proprietário)
- Self-hosted zero-daemon = 1: COMPARISON.md §2 — "⚠️ iii-engine daemon required"
- Provider autonomy = ?: COMPARISON.md §2 — `❓`
- Production-verified = 1: COMPARISON.md §4 — "R@5 95.2% (vendor-reported, not independently verified)"
- Shadow discipline = 0
- Pain weighting = 0

(`?` no radar é plotado como score 1 para evitar colapso ao centro, mas o
grid mostra `?` honesto. Discrepância documentada.)

**Memanto — 2/21**
- Hybrid retrieval = ?: COMPARISON.md §2 — `❓`
- Open-source = 0: COMPARISON.md §2 — "depends (PyPI closed)"
- Self-hosted zero-daemon = 0: COMPARISON.md §2 — "❌ SaaS"
- Provider autonomy = 0: COMPARISON.md §2 — "❌ vendor-controlled"
- Production-verified = 1: COMPARISON.md §4 — "89.8% accuracy on LongMemEval (vendor-reported, not independently verified)"
- Shadow discipline = 0
- Pain weighting = 0

**Zep — 12/21** (no grid only)
- Hybrid retrieval = 3: COMPARISON.md §2 — "✅ BM25 + embedding"
- Open-source = 3: COMPARISON.md §2 — "✅ Apache-2.0 OSS"
- Self-hosted zero-daemon = 2: COMPARISON.md §2 — "Postgres self-host / SaaS Pro"
- Provider autonomy = 3: configurável
- Production-verified = 1: COMPARISON.md §4 — "publishes LongMemEval numbers on docs"
- Shadow discipline = 0
- Pain weighting = 0

---

## Convenções visuais

### Cores

| Token | Hex light | Hex dark | Uso |
|---|---|---|---|
| nox-mem hero | `#00A87A` stroke / `#00C896` fill | `#00C896` stroke + fill | polígono e check vencedor |
| mem0 | `#9C9CA0` | `#9C9CA0` | cinza neutro |
| Letta | `#A57BBB` | `#B591CC` | roxo dessaturado |
| agentmemory | `#7C8FA8` | `#7C9FC8` | azul-ardósia |
| Memanto | `#C0827D` | `#C0827D` | terracota dessaturada |
| score 2 (`~`) | `#FFB800` | `#FFB800` | âmbar |
| score 1 word | `#C18A45` | `#D6A565` | mostarda dessaturada |
| score 0 (`✗`) | `#FF4444` | `#FF4444` | vermelho |
| score `?` | `#888888` | `#888892` | cinza neutro (desconhecido ≠ ausente) |

### Tipografia
- `'JetBrains Mono', 'Courier New', monospace` em tudo (mesma fonte das outras SVGs)
- Section labels: `font-size: 9` `letter-spacing: 2` `font-weight: 500` — `#ABABAF` (light) / `#555558` (dark)
- Axis labels: `font-size: 11` `font-weight: 600` + sublabel `font-size: 8` `letter-spacing: 0.5`
- Grid headers: `font-size: 11` `font-weight: 500/700`
- Footer: `font-size: 9` `#888888` / `#666669`

### Layout
- 1100×900 viewBox para fit em README sem scroll horizontal em 1280px+ displays
- Radar center cx=375, cy=340, r=180 (left half)
- Legend column x=700–1060 (right of radar)
- Coverage grid full-width abaixo do divider y=625
- Vertical stripe `fill="#00C896" opacity 0.06-0.08"` em x=345–415 do grid sinaliza coluna nox-mem sem precisar de outline forte

### Hairlines
- Section dividers `stroke-width: 0.5`
- Row separators `stroke-width: 0.5` cor `#EFEFF2` (light) / `#1E1E22` (dark)
- Radar rings stroke gradient `#E5E5E8 → #C8C8CC` (light) / `#26262A → #3A3A40` (dark) com peso crescente para fora

---

## Geometria do radar (referência)

7 eixos partindo do topo (`-π/2`), sentido horário, separação `2π/7`:

| k | θ (rad) | cos θ | sin θ | Outer vertex (r=180, cx=375, cy=340) |
|---|---:|---:|---:|---|
| 0 | -1.5708 |  0.0000 | -1.0000 | (375.00, 140.00) |
| 1 | -0.6981 |  0.7660 | -0.6428 | (512.88, 204.30) |
| 2 |  0.2244 |  0.9749 |  0.2225 | (550.48, 360.05) |
| 3 |  1.1468 |  0.4339 |  0.9009 | (453.10, 482.16) |
| 4 |  2.0691 | -0.4339 |  0.9009 | (296.90, 482.16) |
| 5 |  2.9915 | -0.9749 |  0.2225 | (199.52, 360.05) |
| 6 |  3.9138 | -0.7660 | -0.6428 | (237.12, 204.30) |

Para qualquer sistema, vértice k = `(cx + r·(score/3)·cos θ_k, cy + r·(score/3)·sin θ_k)`.

---

## Honestidade / caveats

- Score 5 (Production-verified) para nox-mem é o único com **verificação
  independente** — Q1 Python reimpl 2026-05-18 n=100 + Q3 prod /api/search
  n=95. Score 1 para competidores reflete que números deles foram
  **vendor-reported, não medidos pelo nosso harness**. Esta diferença é
  semantically signaled no grid (palavra `vendor`/`paper`/`docs` em vez de
  check verde) — não é greenwash.
- Pain weighting (eixo 7) e Shadow discipline (eixo 6) são exclusivos nox-mem
  por design e por construção. Não é unfair — é a tese do paper. Se um
  competidor adotar mesmo padrão, score sobe e o SVG é regerado.
- Memanto Hybrid retrieval = `?` (não plotado no radar como 0). No grid também
  é `?`. Honest representation: nós não sabemos.
- Zep tem o score grid de 12/21 — segundo maior depois do nox-mem. Não é
  plotado no radar **apenas por legibilidade**, não por motivo competitivo.
  Toto pode optar por incluir Zep e excluir Memanto numa próxima versão.

---

## Atualização / regeneração

Quando regerar:

1. Mudança em `benchmark/COMPARISON.md` §1, §2, §4, ou §6 que altere
   qualquer cell relevante.
2. Quando A3 provider abstraction shipped em prod (atualmente `merged PR #39`
   — score 3 já refletido).
3. Quando Q2 LongMemEval landar — refletir em Production-verified row;
   mover Memanto/agentmemory de "vendor" para número medido (ou descartar se
   blocker B3 não destravar).
4. Se algum competidor publicar uma feature listada como 0 atualmente.

Não automatizado ainda. Edição manual dos dois SVGs + esta tabela. Considerar
generator script se mudanças >2x/mês.

---

## Referência rápida

- Dados: `benchmark/COMPARISON.md` (2026-05-18 Wave B snapshot)
- Visual sibling files: `assets/readme/architecture-{light,dark}.svg`,
  `assets/readme/banner-{light,dark}.svg`, `assets/readme/stat-*.svg`
- Paper que motivou eixos 6+7: `paper/paper-tecnico-nox-mem.md` (Six Gaps)
- Pivot que justificou tagline e Q/A/P pillars: memory
  `project_qap_pillars_strategic_decision`
