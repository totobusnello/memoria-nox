#!/usr/bin/env python3
"""Estimador ITT por braço — H1 e H1a-c do estudo vivo (Paper 2).

NÃO REIMPLEMENTA REGRA NENHUMA. Importa de onde cada uma já vive:

  parse_ts, epoch_de, Episodio, carregar_episodios  <- pilot_replay.py
  carregar_verdicts (MAIORIA ESTRITA, empate=>not_failure)  <- pilot_replay.py
  span_por_sessao (horas de sessão, unidade da ANOVA)       <- pilot_replay.py
  sig_primary                                     <- extract_episodes.py (c0abe143)

Duas cópias da mesma regra escreveriam a população errada em silêncio — é o
defeito que `post_adjudicated.py` l.13-16 nomeia, e a razão de este ficheiro ser
composição e não implementação.

O QUE ESTE FICHEIRO ACRESCENTA, e só isto:
  (1) braço por DESIGNAÇÃO (ASSIGNMENT-SERVING.json, seed do beacon), nunca
      inferido dos dados — inferir é conditioning pós-randomização (§10.31);
  (2) restrição da ANÁLISE à janela do ensaio, mantendo o CORPUS INTEIRO para
      os `a_past`: cortar o corpus em 09-01 apagaria os a_past de agosto e
      apagaria as oportunidades do início da janela;
  (3) agregação por braço + bootstrap por EPOCH INTEIRO (o epoch é o cluster).

`Opportunity` = lock de 2026-07-29 (a AÇÃO), por decisão de 2026-09-21 — ver
§10.32. H1b é INAVALIÁVEL sob esse lock e não é computado aqui.
"""
from __future__ import annotations
import argparse, collections, json, random, sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_replay import (  # noqa: E402
    carregar_verdicts, carregar_episodios, span_por_sessao,
    EPOCH_H, WASHOUT_H, TAU,
)

JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"


def bracos(p: Path) -> dict[str, tuple[str, float]]:
    d = json.loads(p.read_text())
    return {e["epoch_inicio"]: (e["arm"], float(e["w"])) for e in d["epochs"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="ITT por braço — H1/H1a/H1c")
    ap.add_argument("--episodes", required=True, help="corpus INTEIRO (a_past vêm de antes da janela)")
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--assignment", default=str(Path(__file__).parent / "ASSIGNMENT-SERVING.json"))
    ap.add_argument("--estrato-b-ids", required=True, help="os ids amostrados do estrato B")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, required=True, help="seed do bootstrap — declarar")
    ap.add_argument("--excluir", default="", help="epochs YYYY-MM-DD separados por virgula: perna de SENSIBILIDADE")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    verd = carregar_verdicts(Path(a.verdicts))
    eps = carregar_episodios(Path(a.episodes), verd)
    arm = bracos(Path(a.assignment))
    b_ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}

    # ── peso Horvitz-Thompson do estrato B, calculado sobre o CORPUS INTEIRO ──
    # O `pilot_replay` avisa que o peso só vale se a TAXA for única. Aqui há uma
    # só extração (800 de N_B deste corpus), logo uma só taxa — mas o número é
    # impresso para o leitor conferir, nunca assumido.
    resto = [e for e in eps if not e.err]
    peso_b = len(resto) / len(b_ids) if b_ids else 1.0

    # ── condição (i): primeiro a_past de FALHA por assinatura, sobre o corpus ──
    primeiro_failure: dict[str, object] = {}
    for e in eps:
        if e.estado == "failure" and e.sig not in primeiro_failure:
            primeiro_failure[e.sig] = e.epoch

    limiar = timedelta(hours=EPOCH_H)
    horas = span_por_sessao(eps)

    oport = collections.defaultdict(float)   # epoch -> oportunidades (ponderadas)
    repet = collections.defaultdict(float)   # epoch -> repeats
    unk   = collections.defaultdict(int)
    h_ep  = collections.defaultdict(float)   # epoch -> horas de sessão analisadas
    for (ep, _s), h in horas.items():
        h_ep[ep] += h

    for e in eps:
        if e.offset_h < WASHOUT_H:
            continue
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue                                   # (i) não satisfeita
        if e.err:
            w = 1.0                                    # estrato A: censo
        elif e.id in b_ids:
            w = peso_b                                 # estrato B: amostrado
        else:
            continue                                   # não sorteado ⇒ não observado
        oport[e.epoch] += w
        if e.estado == "failure":
            repet[e.epoch] += w
        elif e.estado == "unknown":
            unk[e.epoch] += 1                          # denominador sim, numerador não (§5)

    # ── restrição da ANÁLISE à janela (o corpus inteiro já foi usado acima) ──
    dentro = [ep for ep in sorted(set(oport) | set(h_ep))
              if JANELA_INI <= ep.strftime("%Y-%m-%d") <= JANELA_FIM]
    excl = {s.strip() for s in a.excluir.split(",") if s.strip()}

    def montar(excluidos: set[str]):
        d = collections.defaultdict(list)
        for ep in dentro:
            k = ep.strftime("%Y-%m-%d")
            if k not in arm or k in excluidos:
                continue
            d[arm[k][0]].append(ep)
        return d

    por_braco = montar(set())

    def agrega(lista):
        o = sum(oport[e] for e in lista); r = sum(repet[e] for e in lista)
        h = sum(h_ep[e] for e in lista)
        return dict(n_epochs=len(lista), oportunidades=round(o, 2), repeats=round(r, 2),
                    horas_sessao=round(h, 2),
                    H1_densidade=round(r / h, 6) if h else None,      # repeats / hora
                    H1a_taxa_oport=round(o / h, 6) if h else None,    # oport / hora
                    H1c_prop=round(r / o, 6) if o else None,          # repeats / oport
                    unknown_no_denominador=sum(unk[e] for e in lista))

    res = {b: agrega(v) for b, v in sorted(por_braco.items())}

    # ── bootstrap por EPOCH INTEIRO (o epoch é o cluster; §3 do PREREG) ──
    rng = random.Random(a.seed)
    def ic(metrica, pb=None):
        difs = []
        pb = pb if pb is not None else por_braco
        t, c = pb.get("treatment", []), pb.get("control", [])
        if not t or not c:
            return None
        for _ in range(a.boot):
            at = [t[rng.randrange(len(t))] for _ in t]
            ac = [c[rng.randrange(len(c))] for _ in c]
            vt, vc = agrega(at)[metrica], agrega(ac)[metrica]
            if vt is not None and vc is not None:
                difs.append(vt - vc)
        if not difs:
            return None
        difs.sort()
        return dict(dif_pontual=round((agrega(t)[metrica] or 0) - (agrega(c)[metrica] or 0), 6),
                    ic95=[round(difs[int(.025 * len(difs))], 6), round(difs[int(.975 * len(difs))], 6)],
                    n_replicas=len(difs))

    saida = dict(
        estimando="Opportunity = ACAO (lock 2026-07-29); ver DEVIATIONS 10.32",
        tau=TAU, washout_h=WASHOUT_H, epoch_h=EPOCH_H,
        janela=[JANELA_INI, JANELA_FIM],
        braco_de="ASSIGNMENT-SERVING.json (designacao; nao inferido dos dados)",
        peso_estrato_b=round(peso_b, 4), n_estrato_b_amostrado=len(b_ids),
        n_resto_no_corpus=len(resto),
        epochs_na_janela=len(dentro),
        primario=dict(
            nota="definicao TRAVADA: todos os epochs da janela, denominador = span por sessao",
            por_braco=res,
            H1_diferenca=ic("H1_densidade"),
            H1a_diferenca=ic("H1a_taxa_oport"),
            H1c_diferenca=ic("H1c_prop"),
        ),
        sensibilidade=(dict(
            nota="perna declarada: remove " + a.excluir + " — reportada AO LADO, nunca adjudicada em favor de uma (SPEC-ANALISE 2)",
            epochs_removidos=sorted(excl),
            por_braco={b: agrega(v) for b, v in sorted(montar(excl).items())},
            H1_diferenca=ic("H1_densidade", montar(excl)),
            H1a_diferenca=ic("H1a_taxa_oport", montar(excl)),
            H1c_diferenca=ic("H1c_prop", montar(excl)),
        ) if excl else None),
        H1b="INAVALIAVEL — colisao de locks, ver DEVIATIONS 10.32",
        bootstrap=dict(replicas=a.boot, seed=a.seed, unidade="epoch inteiro"),
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, sort_keys=True, ensure_ascii=False))
    print(json.dumps(saida, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
