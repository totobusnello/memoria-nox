#!/usr/bin/env python3
"""Judge-human agreement on the two labels that decide a number.

Every number of 2026-10-22 — KG fidelity 0.833, the nDCG interval
[0.24, 0.51], abstention 0.696/0.200 — was labelled by
`gemini-2.5-flash-lite`, whose agreement with a human has never been measured.
All three therefore carry an error of unknown size, and that is the single
largest obstacle to any of them being published.

Usage:
  ./2026-10-22-judge-agreement.py <human.json> <gabarito.json> [amostra-cega.json]

  human.json      {"<item id>": true|false}, exported from the judging page's
                  `judgments` collection (ArtifactData list -> {id: verdict}).
  gabarito.json   {"<item id>": true|false}, the judge's own labels, kept off
                  the page so they could not anchor the human.

Reported PER STRATUM, not pooled. The sample is 10 per (family x judge label)
cell, which is not the population's mix — KG faithfulness runs about 83%
positive and pooled relevance about 21%. A pooled accuracy over a balanced
sample is therefore not the accuracy on the real corpus, and averaging the
cells would hide the asymmetry that matters: a judge can be nearly perfect on
the positives and poor on the negatives, which is exactly the shape that
inflates a precision estimate.

What each cell gives you:
  judge=True  cell -> the judge's PRECISION within that family (of the items
                      it called good, how many are good)
  judge=False cell -> its false-negative rate

With both, the population estimate can be corrected:
    corrected = p * P(human=yes | judge=yes) + (1-p) * P(human=yes | judge=no)
where p is the judge's own positive rate on the full population (0.833 for the
KG sample of 150). Cohen's kappa is printed too, but on a sample stratified by
one rater's label kappa is not the headline — the per-cell rates are.

Ten per cell is a wide interval (a cell at 9/10 has a 95% Wilson interval of
roughly [0.60, 0.98]). It is enough to tell "the judge is roughly right" from
"the judge is wrong in one direction", which is the decision at hand; it is not
enough to publish a corrected figure to three digits.
"""
import json
import sys
from collections import defaultdict
from math import sqrt


def wilson(k, n, z=1.96):
    """95% Wilson interval — the normal approximation is useless at n=10."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    halfw = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - halfw) / d, (c + halfw) / d)


def kappa(pairs):
    """Cohen's kappa over (judge, human) boolean pairs."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    agree = sum(1 for a, b in pairs if a == b) / n
    pj = sum(1 for a, _ in pairs if a) / n
    ph = sum(1 for _, b in pairs if b) / n
    exp = pj * ph + (1 - pj) * (1 - ph)
    return float("nan") if exp == 1 else (agree - exp) / (1 - exp)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    human = json.load(open(sys.argv[1]))
    judge = json.load(open(sys.argv[2]))
    families = {}
    if len(sys.argv) > 3:
        families = {i["id"]: i["family"] for i in json.load(open(sys.argv[3]))["items"]}

    common = [k for k in judge if k in human]
    missing = [k for k in judge if k not in human]
    print(f"itens no gabarito: {len(judge)}   julgados pelo humano: {len(common)}")
    if missing:
        print(f"⚠️  {len(missing)} sem resposta humana — não entram em conta nenhuma")
        print(f"    {', '.join(sorted(missing)[:8])}{' …' if len(missing) > 8 else ''}")
    if not common:
        sys.exit("nada para comparar")

    cells = defaultdict(list)
    for k in common:
        fam = families.get(k, k.split("-")[0])
        cells[(fam, bool(judge[k]))].append((bool(judge[k]), bool(human[k])))

    print()
    for fam in sorted({f for f, _ in cells}):
        print(f"== {fam}")
        for jl in (True, False):
            rows = cells.get((fam, jl), [])
            if not rows:
                continue
            n = len(rows)
            agree = sum(1 for a, b in rows if a == b)
            lo, hi = wilson(agree, n)
            label = ("de tudo que o juiz chamou de BOM, humano concorda"
                     if jl else
                     "de tudo que o juiz REPROVOU, humano concorda")
            print(f"   juiz={str(jl):5s}  {agree}/{n} = {agree/n:.3f}  "
                  f"[{lo:.2f} · {hi:.2f}]   {label}")
        allrows = cells.get((fam, True), []) + cells.get((fam, False), [])
        print(f"   kappa (amostra BALANCEADA, não a população): {kappa(allrows):+.3f}")
        print()

    print("Correção da população, quando quiser aplicar:")
    print("  corrigido = p·P(humano=sim | juiz=sim) + (1−p)·P(humano=sim | juiz=não)")
    print("  p = taxa positiva do juiz na população inteira (KG: 0,833 em n=150)")
    print()
    print("⚠️  10 por célula. Serve para separar 'o juiz está mais ou menos certo'")
    print("    de 'o juiz erra para um lado'. Não serve para publicar 3 dígitos.")


if __name__ == "__main__":
    main()
