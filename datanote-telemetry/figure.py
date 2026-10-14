#!/usr/bin/env python3
"""Figure 1: estimated cost per UTC day, one panel per phase.

    python3 figure.py --dir <dataset folder> [--out figure1.pdf]

Reads daily_phase_summary.csv from the published dataset (10.5281/zenodo.23130191).
Days with no row for a phase are absent from that file and are drawn as zero.
Each panel has its own y-scale; the panel title names the phase and its 32-day total.
"""
import argparse
import csv
import os
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PHASES = [("construction", "#2a78d6"), ("query", "#eb6834"), ("maintenance", "#1baf7a")]
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#e4e3de", "#fcfcfb"
START = date(2026, 8, 7)
DAYS = [START + timedelta(d) for d in range(32)]
SILENT = (date(2026, 8, 25), date(2026, 9, 6))  # D11, inclusive
MIGRATION = date(2026, 8, 23)  # D10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="figure1.pdf")
    a = ap.parse_args()
    cost = {p: {d: 0.0 for d in DAYS} for p, _ in PHASES}
    for r in csv.DictReader(open(os.path.join(a.dir, "daily_phase_summary.csv"), newline="")):
        cost[r["phase"]][date.fromisoformat(r["date_utc"])] = float(r["cost_estimate_usd"])

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                         "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED})
    fig, axes = plt.subplots(3, 1, figsize=(6.3, 4.6), sharex=True, facecolor=SURFACE)
    x = list(range(32))
    for ax, (phase, color) in zip(axes, PHASES):
        y = [cost[phase][d] * 1000 for d in DAYS]  # milli-USD
        ax.set_facecolor(SURFACE)
        lo, hi = DAYS.index(SILENT[0]), DAYS.index(SILENT[1])
        ax.axvspan(lo - 0.5, hi + 0.5, color=GRID, alpha=0.55, lw=0, zorder=0)
        mi = DAYS.index(MIGRATION)
        ax.axvline(mi, color=MUTED, lw=0.8, ls=(0, (2, 2)), zorder=1)
        ax.bar(x, y, width=0.78, color=color, edgecolor=SURFACE, linewidth=1.0, zorder=2)
        total = sum(cost[phase].values())
        ax.set_title(f"{phase}  (32-day total USD {total:.4f})", loc="left",
                     fontsize=8.5, color=INK, pad=3)
        ax.set_ylabel("milli-USD / day", fontsize=7.5)
        ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
        ax.set_ylim(0, max(y) * 1.12)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    top = axes[0]
    ymax = top.get_ylim()[1]
    top.text((lo + hi) / 2, ymax * 0.93, "no construction or maintenance rows (13 days)",
             ha="center", va="top", fontsize=7, color=MUTED)
    top.text(mi - 0.3, ymax * 0.93, "host migration", ha="right", va="top",
             fontsize=7, color=MUTED)
    ticks = [i for i, d in enumerate(DAYS) if d.day in (7, 14, 21, 28) or d.day == 4]
    axes[-1].set_xticks(ticks, [DAYS[i].strftime("%b %-d") for i in ticks])
    axes[-1].set_xlim(-0.7, 31.7)
    fig.tight_layout(h_pad=0.6)
    fig.savefig(a.out, facecolor=SURFACE)
    fig.savefig(os.path.splitext(a.out)[0] + ".png", dpi=200, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
