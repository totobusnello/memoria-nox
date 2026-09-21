#!/usr/bin/env python3
"""Teste do nulo agudo por RE-RANDOMIZAÇÃO — a inferência registada (PREREG §5).

    "Sharp-null test: epoch-level permutation test (re-randomize epoch→arm under
     the same balancing constraints, 10,000 (LOCKED 2026-07-29) permutations) on
     the trend-residualized outcome (outcome regressed on study-day, residuals
     permuted). Declared scope: this tests the sharp null of zero total effect
     (direct + carry-over); rejection alone does not attribute magnitude."

Existe porque o manuscrito reportava apenas cluster bootstrap e **não declarava
a substituição**. Uma revisão adversarial apanhou-o. O bootstrap assume sorteio
iid de epochs; a randomização real é estratificada com controlled rounding, logo
a distribuição de referência do bootstrap **não é a que o desenho gera**.

⚠️ A armadilha que a `SPEC-ANALISE §4` pré-compromete contra, e que este ficheiro
respeita: **permutar os braços entre os 20 não reproduz a distribuição**. Os 20
caem todos na primeira metade de calendário, onde a estratificação colapsa. Cada
réplica REDESENHA os 234 com semente nova e restringe à janela.

`assign_arms.assign` é importado, nunca reimplementado — a distribuição de
referência tem de ser a do desenho, e a única forma de o garantir é correr o
mesmo código que atribuiu.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, sys
from datetime import timedelta, date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assign_arms as AA                                          # noqa: E402
from pilot_replay import (                                        # noqa: E402
    carregar_verdicts, carregar_episodios, span_por_sessao, EPOCH_H, WASHOUT_H,
)

JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"


def por_epoch(episodios: Path, verdicts: Path, b_ids: set[str]):
    """Quantidades por epoch. NÃO dependem do braço — é isso que torna a
    re-randomização barata e, mais importante, é a premissa do nulo agudo:
    sob H0 o desfecho de cada epoch é o que é, qualquer que fosse o braço."""
    verd = carregar_verdicts(verdicts)
    eps = carregar_episodios(episodios, verd)
    resto = [e for e in eps if not e.err]
    peso_b = len(resto) / len(b_ids) if b_ids else 1.0

    primeiro: dict[str, object] = {}
    for e in eps:
        if e.estado == "failure" and e.sig not in primeiro:
            primeiro[e.sig] = e.epoch
    limiar = timedelta(hours=EPOCH_H)

    oport = collections.defaultdict(float); repet = collections.defaultdict(float)
    horas = collections.defaultdict(float)
    for (ep, _s), h in span_por_sessao(eps).items():
        horas[ep] += h
    for e in eps:
        if e.offset_h < WASHOUT_H:
            continue
        t0 = primeiro.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue
        if e.err:
            w = 1.0
        elif e.id in b_ids:
            w = peso_b
        else:
            continue
        oport[e.epoch] += w
        if e.estado == "failure":
            repet[e.epoch] += w

    dentro = sorted(ep for ep in set(oport) | set(horas)
                    if JANELA_INI <= ep.strftime("%Y-%m-%d") <= JANELA_FIM)
    return {ep.strftime("%Y-%m-%d"): dict(oport=oport[ep], repet=repet[ep],
                                          horas=horas[ep]) for ep in dentro}, peso_b


def residualiza(chaves: list[str], y: list[float]) -> list[float]:
    """Regride em study-day e devolve resíduos — mínimos quadrados a olho nu,
    porque uma reta em 20 pontos não justifica uma dependência."""
    # study-day = dias desde o inicio do estudo, NAO a posicao na lista: se um
    # epoch faltasse, a posicao mentiria sobre a distancia temporal.
    d0 = _date.fromisoformat(chaves[0])
    x = [float((_date.fromisoformat(k) - d0).days) for k in chaves]
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx if sxx else 0.0
    a0 = my - b * mx
    return [c - (a0 + b * a) for a, c in zip(x, y)]


def main() -> int:
    ap = argparse.ArgumentParser(description="nulo agudo por re-randomização (PREREG §5)")
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--assignment", default=str(Path(__file__).parent / "ASSIGNMENT-SERVING.json"))
    ap.add_argument("--replicas", type=int, default=10000)
    ap.add_argument("--seed-prefix", required=True, help="prefixo declarado das sementes")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    b_ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    dados, peso_b = por_epoch(Path(a.episodes), Path(a.verdicts), b_ids)
    real = {e["epoch_inicio"]: e["arm"]
            for e in json.loads(Path(a.assignment).read_text())["epochs"]}

    # desfechos por epoch. H1c só existe onde há oportunidade; declarado.
    chaves = sorted(dados)
    sem_oport = [k for k in chaves if dados[k]["oport"] <= 0]
    usaveis = [k for k in chaves if dados[k]["oport"] > 0]

    desfechos = {
        "H1c_prop":  [dados[k]["repet"] / dados[k]["oport"] for k in usaveis],
        "H1_dens":   [dados[k]["repet"] / dados[k]["horas"] if dados[k]["horas"] else 0.0
                      for k in usaveis],
        "H1a_taxa":  [dados[k]["oport"] / dados[k]["horas"] if dados[k]["horas"] else 0.0
                      for k in usaveis],
    }

    def estatistica(y_res: list[float], bracos: list[str]) -> float | None:
        t = [v for v, b in zip(y_res, bracos) if b == "treatment"]
        c = [v for v, b in zip(y_res, bracos) if b == "control"]
        if not t or not c:
            return None
        return sum(t) / len(t) - sum(c) / len(c)

    EP234 = AA.build_epochs("2026-09-01", 234)
    resultados = {}
    padroes = set()
    for nome, y in desfechos.items():
        y_res = residualiza(usaveis, y)
        obs = estatistica(y_res, [real[k] for k in usaveis])
        mais_extremos = 0; validas = 0; nulo = []
        for i in range(a.replicas):
            seed = hashlib.sha256(f"{a.seed_prefix}|{i}".encode()).hexdigest()
            m = AA.assign(EP234, seed)
            br = [("treatment" if m[k] != AA.CONTROL else "control") for k in usaveis]
            if nome == "H1c_prop":
                padroes.add("".join("T" if x == "treatment" else "C" for x in br))
            s = estatistica(y_res, br)
            if s is None:
                continue
            validas += 1; nulo.append(s)
            if abs(s) >= abs(obs) - 1e-12:
                mais_extremos += 1
        nulo.sort()
        resultados[nome] = dict(
            observado=round(obs, 6),
            p_bilateral=round(mais_extremos / validas, 5) if validas else None,
            replicas_validas=validas,
            nulo_p025=round(nulo[int(.025 * len(nulo))], 6),
            nulo_p975=round(nulo[int(.975 * len(nulo))], 6),
            rejeita_nulo_agudo_a_5pct=(mais_extremos / validas) < 0.05 if validas else None,
        )

    out = dict(
        teste="nulo agudo, PREREG §5 — re-randomizacao redesenhando os 234",
        escopo_declarado="testa o nulo agudo de efeito TOTAL zero (direto + carry-over); "
                         "rejeicao sozinha nao atribui magnitude",
        armadilha_evitada="permutar entre os 20 NAO reproduz a distribuicao: os 20 caem "
                          "todos na 1a metade de calendario, onde a estratificacao colapsa",
        desfecho="residualizado por tendencia (regressao em study-day), conforme PREREG §5",
        replicas=a.replicas, seed_prefix=a.seed_prefix,
        padroes_distintos_de_braco=len(padroes),
        epochs_usaveis=len(usaveis), epochs_sem_oportunidade=sem_oport,
        peso_estrato_b=round(peso_b, 4),
        resultados=resultados,
    )
    Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
