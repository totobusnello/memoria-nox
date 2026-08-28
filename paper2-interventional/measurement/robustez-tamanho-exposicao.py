#!/usr/bin/env python3
"""
robustez-tamanho-exposicao.py — o achado tamanho×exposição sobrevive a quê?

O §4.2 reporta `r = −0,728` entre `log₁₀(tamanho do tipo)` e `% exposto`, sobre 13
tipos. Uma revisão adversarial levantou três objeções, e as três são testáveis com os
dados que já existem:

1. **inferência ecológica** — a correlação é entre TIPOS, e a manchete fala como se
   fosse sobre chunks;
2. **confundidor idade** — tipos grandes podem ser grandes porque são antigos, e
   antigo pode ser menos exposto por outra razão;
3. **filtro não declarado** — `superficie-de-exposicao.py` usa `HAVING total >= 10`,
   o que exclui `pending` (n=6) e `procedure` (n=3). Ambos têm **0%** de exposição e
   são pequenos, logo a exclusão remove evidência CONTRA o padrão. Um filtro que só
   pode ajudar precisa ser declarado e medido.

⚠️ Um achado que este script torna explícito, e que muda a resposta à objeção 1:
**`log₁₀(tamanho)` é constante dentro do tipo.** Recalcular no nível do chunk não
acrescenta informação independente — só repondera pelos `n`. O problema ecológico
NÃO se resolve desagregando um preditor que é propriedade do grupo; o `n` efetivo
continua sendo o número de tipos. Reportar `r` de chunk como se fossem 67 mil
observações seria pior que reportar o de tipo.

Uso:
  robustez-tamanho-exposicao.py --dados tipos.csv
onde tipos.csv tem: tipo,n,expostos,idade_media,imp_media,tam_texto
"""
import argparse
import csv
import math


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else float("nan")


def spearman(xs, ys):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            m = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[o[k]] = m
            i = j + 1
        return r
    return pearson(rk(xs), rk(ys))


def parcial(xs, ys, zs):
    """r(x,y | z) — correlação parcial pela fórmula de primeira ordem."""
    rxy, rxz, ryz = pearson(xs, ys), pearson(xs, zs), pearson(ys, zs)
    d = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (rxy - rxz * ryz) / d if d else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True)
    a = ap.parse_args()

    T = []
    with open(a.dados) as f:
        for r in csv.DictReader(f):
            T.append({"tipo": r["tipo"], "n": int(r["n"]), "exp": int(r["expostos"]),
                      "idade": float(r["idade_media"]), "imp": float(r["imp_media"]),
                      "texto": float(r["tam_texto"])})
    for t in T:
        t["pct"] = 100 * t["exp"] / t["n"]
        t["lx"] = math.log10(t["n"])

    def bloco(rot, sub):
        x = [t["lx"] for t in sub]
        y = [t["pct"] for t in sub]
        idade = [t["idade"] for t in sub]
        imp = [t["imp"] for t in sub]
        txt = [math.log10(max(t["texto"], 1)) for t in sub]
        print(f"\n── {rot} (n = {len(sub)} tipos) ──")
        print(f"   r(log n, %exposto)              = {pearson(x, y):+.3f}")
        print(f"   ρ Spearman                       = {spearman(x, y):+.3f}")
        print(f"   r parcial | idade                = {parcial(x, y, idade):+.3f}"
              f"      [r(log n, idade) = {pearson(x, idade):+.3f}]")
        print(f"   r parcial | importância          = {parcial(x, y, imp):+.3f}"
              f"      [r(log n, imp)   = {pearson(x, imp):+.3f}]")
        print(f"   r parcial | log(tam. do texto)   = {parcial(x, y, txt):+.3f}"
              f"      [r(log n, texto) = {pearson(x, txt):+.3f}]")

    bloco("PUBLICADO — filtro n ≥ 10", [t for t in T if t["n"] >= 10])
    bloco("SEM FILTRO — todos os tipos", T)
    velhos = [t for t in T if t["idade"] >= 70]
    bloco("SÓ TIPOS ANTIGOS (idade média ≥ 70 d) — idade quase constante", velhos)

    print("\n── nível do CHUNK ──")
    tot = sum(t["n"] for t in T)
    ex = sum(t["exp"] for t in T)
    # ponto-bisserial com preditor constante dentro do grupo: computável a partir
    # dos agregados, exatamente porque não há variação intra-tipo em `lx`.
    mx = sum(t["n"] * t["lx"] for t in T) / tot
    my = ex / tot
    sxy = sum(t["exp"] * (t["lx"] - mx) * (1 - my) +
              (t["n"] - t["exp"]) * (t["lx"] - mx) * (0 - my) for t in T)
    sxx = sum(t["n"] * (t["lx"] - mx) ** 2 for t in T)
    syy = ex * (1 - my) ** 2 + (tot - ex) * my ** 2
    rb = sxy / math.sqrt(sxx * syy)
    print(f"   r ponto-bisserial (67.187 chunks)= {rb:+.3f}")
    print(f"   ⚠️ NÃO é evidência independente: `log₁₀(tamanho)` é constante dentro do")
    print(f"      tipo, então este r só repondera os mesmos {len(T)} pontos pelos n.")
    print(f"      O n efetivo do teste segue sendo o número de TIPOS.")

    # ── A análise que dissolve a questão do filtro ────────────────────────────
    # Correlacionar PERCENTUAIS dá a um tipo de 3 chunks o mesmo peso de um com
    # 32.920, e é por isso que a inclusão de dois tipos minúsculos move `r` de
    # −0,73 para −0,33. O modelo binomial usa TODOS os tipos e pondera cada um pela
    # informação que ele carrega — o tipo de 3 chunks entra, e pesa o que vale.
    print("\n── regressão binomial (logit) — usa TODOS os tipos, pondera por n ──")

    def irls(sub):
        b0, b1 = 0.0, 0.0
        for _ in range(60):
            s00 = s01 = s11 = g0 = g1 = 0.0
            for t in sub:
                eta = b0 + b1 * t["lx"]
                p = 1 / (1 + math.exp(-max(-30, min(30, eta))))
                w = t["n"] * p * (1 - p)
                r_ = t["exp"] - t["n"] * p
                g0 += r_; g1 += r_ * t["lx"]
                s00 += w; s01 += w * t["lx"]; s11 += w * t["lx"] ** 2
            det = s00 * s11 - s01 * s01
            if abs(det) < 1e-12:
                break
            d0 = (s11 * g0 - s01 * g1) / det
            d1 = (s00 * g1 - s01 * g0) / det
            b0 += d0; b1 += d1
            if abs(d0) + abs(d1) < 1e-12:
                break
        ep = math.sqrt(s00 / det) if det > 0 else float("nan")
        return b0, b1, math.sqrt(s00 / det) if det > 0 else float("nan"), ep

    def jack(sub):
        """Erro-padrão por jackknife sobre TIPOS — a unidade de independência real."""
        _, b_full, _, _ = irls(sub)
        bs = []
        for i in range(len(sub)):
            fora = sub[:i] + sub[i + 1:]
            try:
                _, bi, _, _ = irls(fora)
                bs.append(bi)
            except Exception:
                pass
        k = len(bs)
        m = sum(bs) / k
        var = (k - 1) / k * sum((b - m) ** 2 for b in bs)
        return b_full, math.sqrt(var), min(bs), max(bs)

    for rot, sub in (("todos os 15 tipos", T),
                     ("só os 13 publicados", [t for t in T if t["n"] >= 10])):
        b0, b1, _, ep = irls(sub)
        bj, ej, lo, hi = jack(sub)
        print(f"   {rot:<22} β(log₁₀ n) = {b1:+.3f}  "
              f"⇒ ×{math.exp(b1):.2f} nas chances por década de tamanho")
        print(f"   {'':<22} EP do modelo = {ep:.3f} (z = {b1/ep:+.1f}) "
              f"⚠️ INVÁLIDO — supõe 67 mil observações independentes")
        print(f"   {'':<22} EP jackknife sobre tipos = {ej:.3f} "
              f"(z = {b1/ej:+.1f}) · β sem cada tipo ∈ [{lo:+.3f} ; {hi:+.3f}]")
    print("   ⚠️ Os dois tipos minúsculos quase não movem o coeficiente (9 chunks de")
    print("      informação contra 67.178) — é o que a correlação de percentuais não")
    print("      sabe fazer, e é por isso que ELA era sensível ao filtro.")
    print("   ⚠️ E o EP honesto é o jackknife: com 15 tipos, o n efetivo é 15, não 67 mil.")

    print("\n── os dois tipos que o filtro exclui ──")
    for t in T:
        if t["n"] < 10:
            print(f"   {t['tipo']:<12} n={t['n']:<4} expostos={t['exp']} "
                  f"({t['pct']:.0f}%) idade={t['idade']:.0f}d")
    print("   ⇒ ambos pequenos e com 0% exposto: são contraexemplos ao padrão")
    print("     'pequeno ⇒ muito exposto', e o filtro os remove.")


if __name__ == "__main__":
    main()
