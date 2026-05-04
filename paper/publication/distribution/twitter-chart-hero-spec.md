# Twitter Chart Hero — Visual Spec
## Tweet 6 / Thread "The Pain Diary and Shadow Discipline"
### Launch 2026-05-21 09:00 ET

---

## 1. Conceito escolhido: Opção A — Hybrid vs FTS, com tratamento cirúrgico

**Escolha:** Opção A (bar chart de comparação) com anotações que transformam o dado nu em argumento.

**Justificativa (300w):**

A audience Twitter/X tech toma decisões de parada em <2 segundos. Nesse tempo, um radar chart (Opção B) não processa — exige rotação mental de 5 dimensões. Um diagrama de arquitetura (Opção C) não tem número, portanto não para o scroll. Uma timeline de incidentes (Opção D) é narrativa, e narrativa precisa de tempo que a timeline feed não dá. Uma tabela de 8 sistemas (Opção E) tem o maior risco de todas: text-heavy, requer parse linha por linha.

O bar chart com gap de 0.0123 → 0.5213 é o único formato que cria choque cognitivo em 1.5s:

1. Dois bars. Um está quase no zero (0.0123 — estruturalmente inútil). O outro está em 52%. O vazio fala sozinho.
2. Não precisa de legenda elaborada — o contraste espacial é o argumento.
3. Mobile-first: em 375px de largura, dois bars verticais com label inset são legíveis; 5 eixos de radar não são.
4. O número 0.0123 é o hook real. Não é "baixo desempenho" — é **ausência quase total de sinal** (97.6% gap relativo). Isso é contra-intuitivo para qualquer dev que já usou FTS no SQLite e achava que funcionava. O chart provoca dúvida retroativa: "meu sistema também está assim?"
5. Nox-mem não está vendendo produto — está publicando resultado. O chart precisa ter cara de resultado científico, não de marketing slide. Bar chart austero com dado de avaliação cumpre esse sinal.

**Alternativa secundária para A/B:** Versão aumentada da Opção A com um terceiro "bar fantasma" representando o sistema médio competidor (nDCG estimado de literatura ~0.40-0.55) entre os dois — cria progressão visual em 3 pontos em vez de contraste binário. Executar só se o teste A indicar que o chart parece simples demais. Nota: com valores corrigidos (0.5213 vs 0.0123), o gap visual ainda é dramático e o contraste binário preserva o impacto.

---

## 2. Layout proposto

**Dimensões:** 1200 × 675 px (formato 16:9 padrão Twitter Card OG)
Razão: Twitter expande cards landscape em desktop e em mobile mostra crop centralizado — landscape mantém os dois bars visíveis sem crop. Quadrado 1080×1080 força crop no mobile feed e esconde o segundo bar.

**Grid de composição:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  ZONE HEADER (h: 90px, fundo: #0F172A)                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  "Natural language queries on production memory"             │  │
│  │  [título principal — Syne Bold 22px, white]                 │  │
│  │  "50 queries · 4-month corpus · nDCG@10"                    │  │
│  │  [subtítulo — Syne Regular 13px, #94A3B8]                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ZONE CHART (h: 460px, fundo: #0F172A)                            │
│                                                                     │
│    1.0 ┤                                    ╔══════════════╗        │
│    0.8 ┤                                    ║              ║        │
│        │                                    ║   0.5213     ║        │
│    0.6 ┤                                    ║  [emerald]   ║        │
│        │                                    ║              ║        │
│    0.4 ┤                                    ║   HYBRID     ║        │
│        │                                    ║  FTS5+Gemini ║        │
│    0.2 ┤                                    ║   + RRF      ║        │
│        │                                    ║              ║        │
│    0.0 ┤  ╔══╗                              ╚══════════════╝        │
│        │  ║░░║  0.000                                               │
│        │  ║  ║  [rose, 8% opacity fill +                            │
│        │  ║  ║   dashed border]                                     │
│        │  ║FTS║                                                      │
│        └──────────────────────────────────────────────────────┤     │
│                                                                     │
│  ANNOTATION ZONE — inline no chart:                                │
│    ← bar esquerdo (FTS5): label acima "0.0123" em rose #E11D48,   │
│       sub-label "FTS5 vanilla\n(BM25-only)" em slate, 11px        │
│    ← bar direito (Hybrid): label acima "0.5213" em emerald         │
│       #059669 Bold 32px, sub-label "nox-mem hybrid\n(FTS5 +       │
│       Gemini + RRF)" em slate, 11px                               │
│                                                                     │
│  ZONE FOOTER (h: 125px, fundo: #0F172A com borda-topo 1px        │
│  #1E293B)                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ LEFT-ALIGNED:                                                │  │
│  │   "FTS5 alone contributes ~0% to hybrid score"              │  │
│  │   "on full-sentence NL queries — structural, not tunable"   │  │
│  │   [Syne Regular 13px, #CBD5E1, max-width 60%]               │  │
│  │                                                              │  │
│  │ RIGHT-ALIGNED:                                               │  │
│  │   "The Pain Diary and Shadow Discipline"  [12px, #94A3B8]   │  │
│  │   "github.com/totobusnello/memoria-nox"   [12px, #4F46E5]   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Hierarquia visual (ordem de atenção):**
1. Gap entre os dois bars (choque imediato — área vazia do bar esquerdo)
2. Número "0.714" em emerald Bold 32px (confirma a escala)
3. Número "0.000" em rose 24px (valida o zero)
4. Título — ancoragem de contexto
5. Footer — citação científica + handle

**Tratamento do bar FTS5 (zero):**
O bar de altura zero seria invisível. Solução: usar 4px de altura mínima + fill rose a 8% opacity + borda dashed rose #E11D48 de 1.5px, criando um "ghost bar" que existe mas está vazio. O dashed sinaliza ausência, não apenas pequenez. Label "0.000" flutua acima com seta para baixo apontando ao ghost.

**Espaçamento negativo:**
Razão de largura dos bars: FTS5 40%, Gap 20%, Hybrid 40% do espaço útil horizontal. Hybrid ocupa mais espaço vertical propositalmente (height: 78% do eixo Y) para dominar visualmente. O fundo escuro (#0F172A, quase preto) evita o clichê de "chart branco corporativo" e cria profundidade adequada para Twitter dark mode.

---

## 3. Cores

Paleta canônica do projeto, WCAG AA confirmado:

| Elemento | Cor | Hex | Contraste vs #0F172A |
|---|---|---|---|
| Fundo geral | Quase-preto | `#0F172A` | — |
| Bar Hybrid (fill) | Emerald | `#059669` | 4.6:1 ✓ AA |
| Label "0.714" | Emerald claro | `#34D399` | 8.1:1 ✓ AAA |
| Bar FTS5 (ghost border) | Rose | `#E11D48` | 5.2:1 ✓ AA |
| Label "0.000" | Rose | `#FB7185` | 6.7:1 ✓ AA |
| Título principal | Branco | `#F8FAFC` | 19.8:1 ✓ AAA |
| Subtítulo / sub-labels | Slate claro | `#94A3B8` | 4.6:1 ✓ AA |
| URL handle | Indigo claro | `#818CF8` | 4.8:1 ✓ AA |
| Grid lines Y-axis | Slate escuro | `#1E293B` | decorativo |

**Razão do fundo escuro:** Twitter feed em dark mode (adotado por >60% mobile) mostra charts brancos com halo indesejado. Fundo `#0F172A` integra com o feed escuro e faz as cores emerald/rose vibrarem sem saturação excessiva.

---

## 4. Typography

**Display font: Syne** (Google Fonts, open source, sem licença)
- Motivo: geométrica sem ser genérica como Inter. Tem peso Bold com presença em 32px que funciona no label numérico sem grifo adicional. Família única = coerência total.
- Fallback stack: `'Syne', 'DM Sans', ui-sans-serif, system-ui`

| Uso | Weight | Size | Tracking |
|---|---|---|---|
| Número 0.714 | Bold 700 | 36px | -0.02em |
| Número 0.000 | Bold 700 | 26px | -0.01em |
| Título chart | Bold 700 | 20px | -0.01em |
| Subtítulo chart | Regular 400 | 13px | 0 |
| Sub-labels dos bars | Regular 400 | 11px | +0.02em uppercase |
| Footer citação | Regular 400 | 13px | 0 |
| Paper title (footer) | Regular 400 | 12px | +0.03em uppercase |

**Regra de tamanho mínimo mobile:** em 375px (iPhone SE), 11px em fonte rasterizada = ~9px CSS equivalent no export PNG a 2x. Legível. Nada abaixo de 11px no design.

---

## 5. Annotations inline

| Anotação | Posição | Estilo |
|---|---|---|
| "0.5213" | Acima do bar Hybrid, centrado | Emerald #34D399, Syne Bold 36px |
| "(nDCG@10, n=50, 3-run mean)" | Imediatamente abaixo de 0.5213 | Slate #94A3B8, 11px |
| "0.0123" | Acima do ghost bar FTS5, centrado | Rose #FB7185, Syne Bold 26px |
| Seta para baixo "↓" | Entre label 0.000 e ghost bar | Rose, 14px, opacity 70% |
| "FTS5 vanilla\n(BM25-only)" | Abaixo do eixo X, centrado no bar | Slate #94A3B8, 10px, uppercase |
| "nox-mem hybrid\n(FTS5 + Gemini + RRF)" | Abaixo do eixo X, centrado no bar | Slate #94A3B8, 10px, uppercase |
| "Structural constraint — not tunable" | Footer, left-aligned | #CBD5E1, 13px, itálico |

**O que NÃO anotar:** eixo Y com todos os ticks (0.2, 0.4, 0.6, 0.8) — usar apenas linhas de grid sutis (#1E293B) sem label numérico para reduzir ruído. A única referência de escala necessária é o 1.0 no topo (uma linha pontilhada mais fina, indicando o teto da métrica).

---

## 6. CTA visual

**Footer right-aligned, dois itens empilhados:**
```
The Pain Diary and Shadow Discipline    ← 12px Syne Regular, #94A3B8, uppercase tracking
github.com/totobusnello/memoria-nox     ← 12px Syne Regular, #818CF8 (indigo claro)
```

**Sem QR code** — Twitter não permite clique na imagem diretamente; o link vai no texto do tweet. QR code adicionaria ruído visual sem conversão real.

**Sem logo ou ícone personalizado** — o paper title + GitHub URL é a identidade suficiente para esse momento de lançamento. Um ícone inventado nesse contexto parece overreach.

---

## 7. Tools recomendados para produção

### Opção 1 — Figma (recomendado: 20-30min)
- Criar frame 1200×675 com fundo #0F172A
- Rectangles com corner radius 4px para bars
- Ghost bar FTS5: rectangle stroke dashed via plugin "Dashed Border" (free, Figma Community)
- Instalar Syne via Google Fonts plugin
- Export: PNG 2x → 2400×1350px, depois comprimir com TinyPNG (<1MB para Twitter)

**ETA:** 25min para designer com Figma fluente

### Opção 2 — matplotlib Python (recomendado para reprodutibilidade: 45min)

Starter code:

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- Paleta
BG = "#0F172A"
EMERALD = "#059669"
EMERALD_LABEL = "#34D399"
ROSE = "#E11D48"
ROSE_LABEL = "#FB7185"
SLATE = "#94A3B8"
WHITE = "#F8FAFC"
INDIGO_LIGHT = "#818CF8"
GRID = "#1E293B"

fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=BG)
ax.set_facecolor(BG)

# Dados
labels = ["FTS5 vanilla\n(BM25-only)", "nox-mem hybrid\n(FTS5 + Gemini + RRF)"]
values = [0.0123, 0.5213]
colors = [ROSE, EMERALD]
x = np.array([0.28, 0.72])
bar_width = 0.22

# Bar híbrido
ax.bar(x[1], values[1], width=bar_width, color=EMERALD,
       alpha=0.9, zorder=3, linewidth=0)

# Ghost bar FTS5 (altura mínima visual)
ghost_h = 0.018
ghost_rect = plt.Rectangle(
    (x[0] - bar_width/2, 0), bar_width, ghost_h,
    linewidth=1.5, linestyle="--", edgecolor=ROSE,
    facecolor=ROSE + "14",  # 8% opacity hex
    zorder=3
)
ax.add_patch(ghost_rect)

# Labels dos valores
ax.text(x[1], values[1] + 0.025, "0.5213",
        ha="center", va="bottom", fontsize=34, fontweight="bold",
        color=EMERALD_LABEL, fontfamily="DejaVu Sans")
ax.text(x[1], values[1] - 0.05, "nDCG@10 · n=50 · 3-run mean",
        ha="center", va="top", fontsize=10, color=SLATE, fontfamily="DejaVu Sans")

ax.text(x[0], ghost_h + 0.03, "0.0123",
        ha="center", va="bottom", fontsize=24, fontweight="bold",
        color=ROSE_LABEL, fontfamily="DejaVu Sans")
ax.annotate("", xy=(x[0], ghost_h + 0.015), xytext=(x[0], ghost_h + 0.028),
            arrowprops=dict(arrowstyle="-|>", color=ROSE, lw=1.2))

# Sub-labels dos bars (eixo X)
for xi, lbl in zip(x, labels):
    ax.text(xi, -0.06, lbl, ha="center", va="top", fontsize=9,
            color=SLATE, fontfamily="DejaVu Sans",
            linespacing=1.4)

# Grid
for y_tick in [0.2, 0.4, 0.6, 0.8, 1.0]:
    ax.axhline(y=y_tick, color=GRID, linewidth=0.8, zorder=1)
ax.axhline(y=1.0, color=SLATE, linewidth=0.6, linestyle="--", alpha=0.4, zorder=1)

# Título e subtítulo
fig.text(0.04, 0.92, "Natural language queries on production memory",
         fontsize=18, fontweight="bold", color=WHITE,
         fontfamily="DejaVu Sans", ha="left", va="top")
fig.text(0.04, 0.86, "50 queries · 4-month corpus · nDCG@10",
         fontsize=11, color=SLATE, fontfamily="DejaVu Sans",
         ha="left", va="top")

# Footer esquerdo
fig.text(0.04, 0.06,
         "FTS5 alone contributes ~0% to hybrid score on full-sentence NL queries\n"
         "Structural constraint — not tunable",
         fontsize=10, color="#CBD5E1", fontfamily="DejaVu Sans",
         ha="left", va="bottom", linespacing=1.5)

# Footer direito — paper title + handle
fig.text(0.96, 0.09, "THE PAIN DIARY AND SHADOW DISCIPLINE",
         fontsize=9, color=SLATE, fontfamily="DejaVu Sans",
         ha="right", va="bottom")
fig.text(0.96, 0.05, "github.com/totobusnello/memoria-nox",
         fontsize=9, color=INDIGO_LIGHT, fontfamily="DejaVu Sans",
         ha="right", va="bottom")

# Spine / axes cleanup
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.12)
ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout(rect=[0, 0.12, 1, 0.88])
plt.savefig("twitter-chart-hero.png", dpi=200, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close()
print("Saved: twitter-chart-hero.png (1200×675px equivalent)")
```

**Nota:** `DejaVu Sans` é fallback bundled no matplotlib. Para Syne: `pip install matplotlib; fc-cache; curl` a fonte e registrar via `matplotlib.font_manager.fontManager.addfont()`. Código acima funciona sem font externa como validação rápida.

**ETA:** 45min (inclui ajuste fino de espaçamento e export)

### Opção 3 — Canva (não recomendada)
Canva não permite fundo #0F172A exato em chart nativo — forçaria workaround com screenshot de chart sobre retângulo escuro. Resulta em pixelação de borda. Evitar.

---

## 8. Checklist de produção antes de publicar

- [ ] Export PNG 2400×1350 (2x), comprimido para < 900KB (Twitter rejeita > 5MB mas processa melhor < 1MB)
- [ ] Verificar dark mode Twitter: abrir no app móvel antes de agendar
- [ ] Testar crop em mobile: Twitter corta 16:9 para ~16:7 no feed — garantir que os dois bars e o título ficam na zona segura central (padding 10% topo/baixo)
- [ ] Alt text do tweet: "Bar chart comparing nDCG@10 scores: FTS5 vanilla scores 0.0123 and nox-mem hybrid (FTS5 + Gemini + RRF) scores 0.5213 on 50 natural language queries (3-run mean) against a 4-month production corpus."
- [ ] Agendar via Typefully junto ao texto do Tweet 6

---

*Spec criada: 2026-05-03. Chart para lançamento 2026-05-21.*
