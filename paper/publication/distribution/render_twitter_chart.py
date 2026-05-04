"""
render_twitter_chart.py
=======================
Gera twitter-chart-hero.png (1200×675 px, DPI 100) para o Tweet 6 do thread
"The Pain Diary and Shadow Discipline".

3 bars:
  • FTS5 vanilla    — ghost dashed rose  (#E11D48, 8 % opacity fill)
  • BM25 Pyserini   — slate solid        (#475569)
  • nox-mem hybrid  — indigo solid       (#4F46E5, outline + check marker)

Uso:
    python render_twitter_chart.py

Deps: matplotlib (stdlib numpy incluída no pacote)
"""

from __future__ import annotations

import pathlib
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np

matplotlib.use("Agg")  # headless — sem display necessário

# ---------------------------------------------------------------------------
# Paleta canônica (adaptada do spec original para fundo branco)
# ---------------------------------------------------------------------------
BG            = "#FFFFFF"
TITLE_COLOR   = "#0F172A"   # quase-preto para texto sobre branco
SUBTITLE_CLR  = "#475569"   # slate médio
GRID_COLOR    = "#E2E8F0"   # slate-200, sutil sobre branco

ROSE_EDGE     = "#E11D48"   # borda dashed FTS5
ROSE_FILL     = "#FFF1F2"   # rose-50 ~ 8 % opacity sobre branco
ROSE_LABEL    = "#BE123C"   # legível sobre branco

SLATE_BAR     = "#475569"   # BM25 Pyserini
SLATE_LABEL   = "#1E293B"

INDIGO_BAR    = "#4F46E5"   # nox-mem hybrid
INDIGO_DARK   = "#3730A3"   # outline mais escuro
INDIGO_LABEL  = "#4338CA"   # valor no topo

EMERALD_CHECK = "#059669"   # ✓ marker
FOOTER_URL    = "#4F46E5"   # indigo para URL
FOOTER_PAPER  = "#64748B"   # slate para paper title

ANNOTATION    = "#94A3B8"   # seta/texto annotation FTS5

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
NDCG_FTS5   = 0.0123
NDCG_BM25   = 0.1475
NDCG_HYBRID = 0.5213

Y_MAX = 0.70   # cap acima de 0.5213, escala honest


def build_chart(output_path: pathlib.Path) -> None:
    """Renderiza o chart hero e salva em *output_path*.

    Args:
        output_path: Caminho absoluto para o arquivo PNG de saída.
    """
    # bbox_inches="tight" encolhe ~5-7 % — compensar com figsize maior.
    # Alvo final: 1200×675 px @ 100 dpi. Fator empírico: ~1.07-1.09.
    fig_w_in = 12.83  # → 1200 px após tight crop
    fig_h_in = 7.36   # → 675 px após tight crop

    fig = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor=BG, dpi=100)

    # Área do plot — deixa margem para header (topo) e footer (base)
    # [left, bottom, width, height] em fração da figura
    ax = fig.add_axes([0.08, 0.22, 0.84, 0.55])
    ax.set_facecolor(BG)

    # ------------------------------------------------------------------
    # Posições e largura dos bars (espaço X normalizado 0–1)
    # ------------------------------------------------------------------
    bar_w   = 0.14
    x_fts5  = 0.22
    x_bm25  = 0.50
    x_hyb   = 0.78

    # ------------------------------------------------------------------
    # Grid Y
    # ------------------------------------------------------------------
    for y in np.arange(0.0, Y_MAX + 0.01, 0.1):
        lw   = 1.2 if abs(y % 0.2) < 1e-9 else 0.5
        ls   = "-"
        ax.axhline(y=y, color=GRID_COLOR, linewidth=lw, linestyle=ls, zorder=1)

    # Linha pontilhada no topo da escala
    ax.axhline(y=Y_MAX, color=GRID_COLOR, linewidth=0.8,
               linestyle="--", alpha=0.7, zorder=1)

    # ------------------------------------------------------------------
    # Bar 1 — FTS5 ghost (dashed border, fill 8 % opacity)
    # ------------------------------------------------------------------
    ghost_h = 0.018   # altura mínima visual para ghost bar
    ghost_rect = mpatches.FancyBboxPatch(
        (x_fts5 - bar_w / 2, 0),
        bar_w,
        ghost_h,
        boxstyle="square,pad=0",
        linewidth=1.8,
        linestyle=(0, (4, 3)),   # dashed manual
        edgecolor=ROSE_EDGE,
        facecolor=ROSE_FILL,
        zorder=3,
    )
    ax.add_patch(ghost_rect)

    # ------------------------------------------------------------------
    # Bar 2 — BM25 Pyserini (slate sólido)
    # ------------------------------------------------------------------
    ax.bar(
        x_bm25, NDCG_BM25,
        width=bar_w,
        color=SLATE_BAR,
        alpha=0.9,
        zorder=3,
        linewidth=0,
    )

    # ------------------------------------------------------------------
    # Bar 3 — nox-mem hybrid (indigo sólido, outline escuro)
    # ------------------------------------------------------------------
    ax.bar(
        x_hyb, NDCG_HYBRID,
        width=bar_w,
        color=INDIGO_BAR,
        alpha=1.0,
        zorder=3,
        linewidth=2.0,
        edgecolor=INDIGO_DARK,
    )

    # ------------------------------------------------------------------
    # Labels de valor acima dos bars
    # ------------------------------------------------------------------
    # FTS5
    ax.annotate(
        "",
        xy=(x_fts5, ghost_h + 0.005),
        xytext=(x_fts5, ghost_h + 0.045),
        arrowprops=dict(
            arrowstyle="-|>",
            color=ROSE_EDGE,
            lw=1.2,
            mutation_scale=10,
        ),
        zorder=4,
    )
    ax.text(
        x_fts5, ghost_h + 0.052,
        "0.0123",
        ha="center", va="bottom",
        fontsize=16, fontweight="bold",
        color=ROSE_LABEL, fontfamily="DejaVu Sans",
        zorder=5,
    )
    ax.text(
        x_fts5, ghost_h + 0.112,
        "structural near-zero",
        ha="center", va="bottom",
        fontsize=8, color=ANNOTATION,
        fontstyle="italic", fontfamily="DejaVu Sans",
        zorder=5,
    )

    # BM25
    ax.text(
        x_bm25, NDCG_BM25 + 0.018,
        "0.1475",
        ha="center", va="bottom",
        fontsize=17, fontweight="bold",
        color=SLATE_LABEL, fontfamily="DejaVu Sans",
        zorder=5,
    )

    # nox-mem hybrid — valor principal
    ax.text(
        x_hyb, NDCG_HYBRID + 0.022,
        "0.5213",
        ha="center", va="bottom",
        fontsize=26, fontweight="bold",
        color=INDIGO_LABEL, fontfamily="DejaVu Sans",
        zorder=5,
        path_effects=[
            pe.withStroke(linewidth=3, foreground=BG),
        ],
    )
    # Check marker ✓
    ax.text(
        x_hyb + bar_w / 2 + 0.025, NDCG_HYBRID - 0.035,
        "✓",
        ha="left", va="center",
        fontsize=20, color=EMERALD_CHECK,
        fontfamily="DejaVu Sans",
        fontweight="bold",
        zorder=5,
    )

    # ------------------------------------------------------------------
    # Sub-labels dos bars (abaixo do eixo X)
    # ------------------------------------------------------------------
    sub_labels = [
        (x_fts5,  "FTS5 VANILLA\n(BM25-ONLY)"),
        (x_bm25,  "BM25 PYSERINI\n(BASELINE)"),
        (x_hyb,   "NOX-MEM HYBRID\n(FTS5 + GEMINI + RRF)"),
    ]
    for xi, lbl in sub_labels:
        ax.text(
            xi, -0.068,
            lbl,
            ha="center", va="top",
            fontsize=8.5, color=SUBTITLE_CLR,
            fontfamily="DejaVu Sans",
            linespacing=1.5,
            transform=ax.transData,
        )

    # ------------------------------------------------------------------
    # Eixo e spines
    # ------------------------------------------------------------------
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, Y_MAX)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Linha de base (x-axis)
    ax.axhline(y=0, color="#CBD5E1", linewidth=1.2, zorder=2)

    # ------------------------------------------------------------------
    # Tick labels Y à esquerda (apenas 0.0, 0.2, 0.4, 0.6)
    # ------------------------------------------------------------------
    for y in [0.0, 0.2, 0.4, 0.6]:
        ax.text(
            -0.005, y,
            f"{y:.1f}",
            ha="right", va="center",
            fontsize=8, color=GRID_COLOR[:-1] if GRID_COLOR != "#E2E8F0" else "#94A3B8",
            fontfamily="DejaVu Sans",
            transform=ax.transData,
        )

    # ------------------------------------------------------------------
    # Header — título e subtítulo (acima do plot)
    # ------------------------------------------------------------------
    fig.text(
        0.08, 0.935,
        "FTS5 vs BM25 vs nox-mem hybrid  (n=60 queries)",
        fontsize=17, fontweight="bold",
        color=TITLE_COLOR, fontfamily="DejaVu Sans",
        ha="left", va="top",
    )
    fig.text(
        0.08, 0.895,
        "nDCG@10  —  3-run mean  (Hybrid 0.5213 ± 0.0004)",
        fontsize=11, color=SUBTITLE_CLR,
        fontfamily="DejaVu Sans",
        ha="left", va="top",
    )

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    # Linha separadora
    line_y = 0.115
    fig.add_artist(
        plt.Line2D(
            [0.04, 0.96], [line_y, line_y],
            transform=fig.transFigure,
            color="#E2E8F0", linewidth=0.8,
        )
    )

    # Footer esquerdo — insight
    fig.text(
        0.08, 0.105,
        "FTS5 alone contributes ~0 % to hybrid score on full-sentence NL queries\n"
        "Structural constraint — not tunable",
        fontsize=9.5, color="#64748B",
        fontfamily="DejaVu Sans",
        ha="left", va="top",
        linespacing=1.6,
    )

    # Footer direito — paper + URL
    fig.text(
        0.92, 0.105,
        "The Pain Diary and Shadow Discipline",
        fontsize=9, color=FOOTER_PAPER,
        fontfamily="DejaVu Sans",
        ha="right", va="top",
    )
    fig.text(
        0.92, 0.062,
        "github.com/totobusnello/memoria-nox",
        fontsize=9, color=FOOTER_URL,
        fontfamily="DejaVu Sans",
        ha="right", va="top",
        fontweight="bold",
    )

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output_path,
        dpi=100,
        bbox_inches="tight",
        facecolor=BG,
        edgecolor="none",
        format="png",
        metadata={"Author": "render_twitter_chart.py"},
    )
    plt.close(fig)

    size_kb = output_path.stat().st_size / 1024
    print(
        f"Saved: {output_path}  "
        f"({output_path.stat().st_size // 1024} KB)"
        f"  — {'OK < 1 MB' if size_kb < 1024 else 'WARN > 1 MB'}"
    )


def main() -> None:
    """Entry point: renderiza o chart hero para o diretório corrente."""
    script_dir = pathlib.Path(__file__).resolve().parent
    output = script_dir / "twitter-chart-hero.png"
    build_chart(output)


if __name__ == "__main__":
    main()
