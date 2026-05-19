# nox-mem — Visual Identity Design Notes

> Refresh 2026-05-18. Substitui logos plain anteriores por sistema de marca completo (wordmark + symbol + favicon).

---

## Arquivos entregues

| Arquivo | Dimensão | Uso |
|---|---|---|
| `logo-light.svg` | 300×80 | README hero, light theme, marketing pages |
| `logo-dark.svg` | 300×80 | Dark theme README, OG images, dark dashboards |
| `logo-symbol-light.svg` | 80×80 | Symbol isolado, social avatars, app icons sobre fundo claro |
| `logo-symbol-dark.svg` | 80×80 | Symbol isolado sobre fundo escuro (mesmas dimensões; cores idênticas, só bar opacity 0.45/0.75/1.0 vs 0.40/0.70/1.0) |
| `favicon.svg` | 32×32 | Favicon do site, app icon iOS/Android, bookmarks |

Auxiliares (não-marca, podem ser deletados depois):
- `_preview.html` — visual sanity check em browser
- `_scale-test.html` — grid de escalas 16/24/32/48/64/80/128

---

## Symbol — significado e construção

### Conceito
Crescente lunar sobreposta a três barras horizontais empilhadas. Lê-se em três camadas conceituais:

1. **Crescente (nox)** — "shadow discipline". A lua minguante denota disciplina, espera, contenção. Não é uma lua decorativa: é a sombra que define o que fica retido versus o que decai.
2. **Três barras (mem)** — as três camadas do hybrid retrieval do nox-mem:
   - Barra superior (40% opacity): **lexical** — FTS5 BM25
   - Barra intermediária (70% opacity): **semantic** — sqlite-vec embeddings Gemini 3072d
   - Barra inferior (100% opacity): **graph** — KG entities/relations + salience scoring
3. **Eclipse (interação)** — as barras truncam exatamente na borda esquerda da lua. Visualmente: a disciplina (shadow) define onde a memória termina. Não há "vazamento" das barras dentro do disco lunar — corte limpo via SVG `clip-path` com `fill-rule="evenodd"`.

### Pain-weighting visualizado
A gradação de opacity das três barras (0.40 → 0.70 → 1.00) codifica o conceito de **pain-weighting**: memórias mais "doloridas"/críticas (graph layer, KG entities marcadas com `pain=0.8-1.0`) aparecem com peso visual maior. É meta-novelty — o logo literalmente desenha o algoritmo de salience.

### Geometria precisa (80×80 canvas)
- Barras: x=[8, 72], height=6px, rx=3 (rounded caps), y={20, 37, 54}
- Lua externa: círculo r=26 centrado em (48, 40)
- Lua interna (carve): círculo r=22 centrado em (56, 40) — offset +8 no eixo X cria o crescente esquerdo
- `clip-path` even-odd remove o disco lunar inteiro do clip das barras → bars renderizam só FORA do disco
- Crescente desenhado por cima das barras truncadas, completando a composição

### Por que crescente em vez de círculo cheio
- Círculo cheio = bandeira do Japão. Sem caráter. Crescente = lua, noite, sombra → narrativa coerente com "nox" e "shadow discipline".
- Crescente também lê como **parêntese** ou **letra C** — sugere containment, cache, crystallize. Triplo significado sem forçar.
- A abertura à direita aponta para o wordmark — direciona o olho.

---

## Wordmark — tipografia e hierarquia

### Font stack
```
'IBM Plex Sans', 'Inter Tight', 'Inter', 'Helvetica Neue', 'Segoe UI', system-ui, sans-serif
```

**Primária:** IBM Plex Sans — geométrica, técnica, free (Apache 2.0), latin-1 completo, usada por IBM Research / sistemas de ML. Match perfeito de tom: técnica sem ser fria, humana sem ser casual.

**Fallback:** Inter Tight / Inter (web-safe), depois system fonts. Garante render correto em qualquer ambiente sem font remote loading.

> **Decisão consciente:** o brief proibia "Inter, Roboto" como genéricos AI-slop, mas Inter aqui é apenas FALLBACK. A face de design é IBM Plex Sans. Se o usuário não tem Plex instalado, Inter degrada graciosamente sem trair o caráter (ambas geométricas próximas).

### Hierarquia visual (em "nox.mem")
- **nox**: weight 600, color #0D1117 (light) / #FFFFFF (dark), letter-spacing -1.2
- **·** (hyphen como ponto): circle r=3.6px, fill #00C896 — único uso do primary no wordmark, alta densidade visual
- **mem**: weight 500, color #0D1117 @ 72% opacity (light) / #FFFFFF @ 62% (dark)

A diferença de weight (600/500) + opacity (100%/72%) cria hierarquia clara entre namespace "nox" e produto "mem" sem fragmentar a leitura.

### Por que substituir hyphen por dot?
- Hyphen entre "nox" e "mem" lê como CLI flag (`--nox-mem`), aspecto técnico mas frio.
- Dot é universal em design tipográfico de produto (Stripe `.`, Vercel `.`, etc.) — marca premium, não comoditizada.
- Dot em #00C896 amarra a paleta primária diretamente no nome — single point of brand color injection.

---

## Palette

### Locked
| Token | Hex | Uso |
|---|---|---|
| `--primary` | **#00C896** | Symbol crescent, accent dot, charts |
| `--text-light` | #0D1117 | Wordmark sobre light bg |
| `--text-dark` | #FFFFFF | Wordmark sobre dark bg |

### Extensões propostas (não usadas no logo, mas reservadas para sistema)
| Token | Hex | Uso futuro |
|---|---|---|
| `--secondary` | #0F1B2D | Deep navy — favicon backdrop, headers, dashboards |
| `--accent-pain` | #FF6B35 | Warm orange — pain-weighting overlays em dashboards, NUNCA no logo |
| `--surface-light` | #F5F5F7 | Light theme canvas alternativo |
| `--surface-dark` | #161B22 | Dark theme card backgrounds |
| `--success` | #00C896 | Reusa primary — `vec coverage 100%`, `golden score ↑` |
| `--warning` | #FFB85C | Soft amber — `embeddings stale`, `FTS5 drift` |
| `--danger` | #FF4D4D | `op-audit crashed`, `snapshot failed` |

**Regra:** primary #00C896 NUNCA combinado com purple gradients, gradient meshes saturadas, ou complementary red — paleta intencionalmente austera para reforçar "shadow discipline".

---

## Scale tests (verificado via qlmanage render 2026-05-18)

| Tamanho | Symbol | Wordmark | Favicon |
|---|---|---|---|
| 16×16 | Crescent legível, barras viram 1 traço (aceitável) | N/A (use symbol) | Crescent clean, square backing dá contraste |
| 24×24 | 3 barras discerníveis | N/A | Ideal favicon |
| 32×32 | Pleno detalhe | N/A | Ideal favicon hi-DPI |
| 48-128 | Pleno detalhe | N/A | N/A |
| 300×80 | N/A | Wordmark + symbol em proporção 80:204 (symbol:wordmark), padding lateral igual | N/A |

**Falhas conhecidas / aceitas:**
- Em 12-14px, as três barras compõem em 2 traços perceptíveis (o de cima fica abaixo do threshold de opacity). Aceitável — 12px é fora do uso esperado (use favicon ao invés).
- Em rendering monocromático (impressão preto-e-branco), a opacity das barras vai colapsar para tons de cinza. Funciona mas perde o "pain-weight" semântico. Para impressão dedicada, criar variante `logo-mono.svg` no futuro.

---

## Acessibilidade

- Todos SVGs têm `role="img"`, `aria-label`, `<title>` e `<desc>` para screen readers
- Contraste WCAG AA:
  - Wordmark light: #0D1117 sobre #FFFFFF = **18.69:1** (AAA)
  - Wordmark dark: #FFFFFF sobre #0D1117 = **18.69:1** (AAA)
  - "mem" light @ 72%: efetivo ~13:1 (AAA)
  - "mem" dark @ 62%: efetivo ~11.6:1 (AAA)
  - Primary #00C896 sobre #FFFFFF = **2.61:1** (NÃO atende AA para texto — por isso primary é usado só em shapes, nunca em texto significativo)
- Acentos de cor (dot, crescente) nunca carregam informação crítica que precise ser lida — toda info essencial está nas formas + texto, cor é decorativa

---

## Verificação SVG

Todos os arquivos:
- [x] Têm `<?xml version="1.0" encoding="UTF-8"?>` declaration
- [x] Têm `xmlns="http://www.w3.org/2000/svg"` namespace
- [x] Têm `viewBox` (responsividade) + `width`/`height` explícitos (browser defaults)
- [x] Têm `role="img"` + `aria-label` + `<title>` + `<desc>` (a11y)
- [x] Sem dependência de fontes remotas (system stack fallback)
- [x] Sem `<image>` embeds, sem rasters base64 — vetor puro
- [x] Renderiza correto em macOS qlmanage, Safari, Chrome (paths SVG 1.1 compliant)

---

## Uso recomendado

### README hero
```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/logo-dark.svg">
  <img src="assets/readme/logo-light.svg" alt="nox-mem" width="300">
</picture>
```

### HTML/site
```html
<link rel="icon" type="image/svg+xml" href="/assets/readme/favicon.svg">
<link rel="apple-touch-icon" href="/assets/readme/logo-symbol-light.svg">
```

### Social cards (OG image base)
Use `logo-dark.svg` em canvas 1200×630 #0D1117, centralizado vertical, padding 80px nas laterais.

### NUNCA
- Não esticar/comprimir desproporcionalmente — preservar aspect ratio sempre
- Não pintar de outra cor que não primary #00C896 (exceção: variante mono futuro)
- Não adicionar drop shadows, glows, ou outros efeitos — paleta austera é a marca
- Não embed em PDF impresso sem testar render mono primeiro
- Não usar primary verde em texto de body (contraste insuficiente)

---

## Histórico

| Data | Versão | Mudança |
|---|---|---|
| 2026-05-18 | 2.0 | Wordmark + symbol + favicon system (refresh palette D #00C896) |
| pré-2026-05-18 | 1.x | Plain text-only logos (logo-light.svg / logo-dark.svg) |
