#!/usr/bin/env python3
"""Cobertura por braço (§4.5) e correlação braço×cobertura (§4.6, M10).

Existe porque a primeira versão destes números foi computada por script ad-hoc
e **não foi salva**: o manuscrito prometia que todo número é rastreável a um
artefacto e dois dos seus não eram. Uma revisão adversarial apanhou a promessa;
o buraco era maior do que ela viu.

⚠️ `boost_by_id` NÃO é cobertura. Ele regista o boost **calculado** para todo
candidato, uniformemente — lê-lo como cobertura dá 139 650, que é o número de
candidatos avaliados, não de chunks designados servidos. A cobertura sai de
cruzar `ids_tratado`/`ids_controle` (conforme `servido`) com a designação.

⚠️ O denominador aqui é **19** epochs, não os 20 da análise ITT: cobertura
define-se sobre briefs servidos e `09-02` não serviu nenhum. A quantidade não
existe lá, o que não é o mesmo que ser zero.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, json, math, random
from pathlib import Path

JANELA = ("2026-09-01", "2026-09-20")
EPOCH_OFFSET_H = 9


def pearson(x, y):
    m = len(x)
    if m < 2:
        return None
    mx, my = sum(x) / m, sum(y) / m
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serving", required=True)
    ap.add_argument("--designation", required=True)
    ap.add_argument("--assignment", default=str(Path(__file__).parent / "ASSIGNMENT-SERVING.json"))
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    des = json.loads(Path(a.designation).read_text())
    dset = set(des["designados"].values())
    arm = {e["epoch_inicio"]: (e["arm"], float(e["w"]))
           for e in json.loads(Path(a.assignment).read_text())["epochs"]}

    n_br = collections.Counter()      # epoch -> briefs
    c_br = collections.Counter()      # epoch -> briefs com >=1 designado
    por_arm_n = collections.Counter(); por_arm_c = collections.Counter()
    sig_hits = collections.Counter()  # chunk designado -> ocorrencias servidas
    ocorrencias = 0

    for linha in Path(a.serving).open():
        o = json.loads(linha)
        d = dt.datetime.fromisoformat(o["ts"].replace("Z", "+00:00"))
        ep = (d - dt.timedelta(hours=EPOCH_OFFSET_H)).strftime("%Y-%m-%d")
        if not (JANELA[0] <= ep <= JANELA[1]) or ep not in arm:
            continue
        # o braço SERVIDO decide qual lista de ids foi de facto entregue
        ids = o.get("ids_tratado") if o.get("servido") == "tratado" else o.get("ids_controle")
        if ids is None:
            continue
        br = arm[ep][0]
        n_br[ep] += 1; por_arm_n[br] += 1
        batidos = [i for i in ids if i in dset]
        if batidos:
            c_br[ep] += 1; por_arm_c[br] += 1
        for i in batidos:
            sig_hits[i] += 1; ocorrencias += 1

    eps = sorted(n_br)
    cob = {e: c_br[e] / n_br[e] for e in eps}

    def leg(excl: set[str]):
        sel = [e for e in eps if e not in excl]
        x = [1.0 if arm[e][0] == "treatment" else 0.0 for e in sel]
        y = [cob[e] for e in sel]
        r = pearson(x, y)
        rng = random.Random(a.seed); b = []
        for _ in range(a.boot):
            idx = [rng.randrange(len(sel)) for _ in sel]
            v = pearson([x[i] for i in idx], [y[i] for i in idx])
            if v is not None:
                b.append(v)
        b.sort()
        return dict(epochs=len(sel), excluidos=sorted(excl), r=round(r, 4),
                    ic95=[round(b[int(.025 * len(b))], 4), round(b[int(.975 * len(b))], 4)],
                    contem_zero=b[int(.025 * len(b))] <= 0 <= b[int(.975 * len(b))])

    x_dose = [arm[e][1] for e in eps]
    out = dict(
        gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(),
        janela=list(JANELA),
        nota_denominador="19 epochs: cobertura define-se sobre briefs SERVIDOS; 09-02 nao "
                         "serviu nenhum. A analise ITT usa 20 — populacoes diferentes.",
        nota_boost="boost_by_id NAO e' cobertura: regista boost calculado para todo "
                   "candidato (uniforme). Le-lo como cobertura da' 139650.",
        cobertura_por_braco={
            b: dict(briefs=por_arm_n[b], com_designado=por_arm_c[b],
                    proporcao=round(por_arm_c[b] / por_arm_n[b], 4) if por_arm_n[b] else None)
            for b in sorted(por_arm_n)},
        ocorrencias_designado_servido=ocorrencias,
        assinaturas_servidas=len(sig_hits),
        assinaturas_designadas=len(dset),
        share_por_assinatura={k: round(v / ocorrencias, 4) for k, v in sorted(sig_hits.items())},
        cobertura_por_epoch={e: dict(braco=arm[e][0], w=arm[e][1], briefs=n_br[e],
                                     com_designado=c_br[e], proporcao=round(cob[e], 4))
                             for e in eps},
        M10=dict(
            nota="TOST do PREREG 5 exige K>=30; nao avaliavel. Reporta-se r + IC, "
                 "incondicionalmente, com as pernas declaradas.",
            primaria=leg(set()),
            sem_09_20=leg({"2026-09-20"}),
            sem_os_dois_parciais=leg({"2026-09-20", "2026-09-03"}),
            sem_09_14=leg({"2026-09-14"}),
            r_com_dose=round(pearson(x_dose, [cob[e] for e in eps]), 4),
        ),
        bootstrap=dict(replicas=a.boot, seed=a.seed, unidade="epoch"),
    )
    Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out["cobertura_por_braco"], indent=2))
    print(f"ocorrencias={ocorrencias}  assinaturas={len(sig_hits)}/{len(dset)}")
    for k in ("primaria", "sem_09_20", "sem_os_dois_parciais", "sem_09_14"):
        v = out["M10"][k]
        print(f"  {k:22} K={v['epochs']:2} r={v['r']:+.4f} IC{v['ic95']} "
              f"{'contem zero' if v['contem_zero'] else 'EXCLUI'}")
    print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
