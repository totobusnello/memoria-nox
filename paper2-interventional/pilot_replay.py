#!/usr/bin/env python3
"""
§9 item 7 — harness de replay do piloto.

Produz EXATAMENTE tres numeros — `r_hat`, `p0_hat`, `icc` — mais as duas
quantidades de exposicao que `sizing.py` consome (`hours_per_epoch`,
`session_hours_per_epoch`). Nada alem disso: quem escolhe `mde` e o
pre-registro, quem calcula `N_epochs` e `sizing.py`, e ele roda uma vez so.

DEFINICOES (travadas em PREREG-DRAFT.md §3, "Pilot metric definitions")
----------------------------------------------------------------------
Epoch      24h, boundary 06:00 BRT = 09:00 UTC.
Washout    primeiras 2h de cada epoch, excluidas da analise.
Failure    MAIORIA ESTRITA do painel em `failure` (>50% dos vereditos
           substantivos). Corrigido 2026-07-29 — ver a nota abaixo.
Oportunidade
           acao `a` executada pos-washout tal que existe failure episode
           `a_past` com sig_primary(a_past) == sig_primary(a) escrito
           >= 1 epoch length ANTES do inicio do epoch de `a`.
           Depende so da condicao (i) — NAO olha como `a` terminou.
Repeat     oportunidade cujo proprio desfecho e failure (condicao (ii)).
r_hat      oportunidades / horas-sessao analisadas.
p0_hat     repeats / oportunidades  (no replay todo epoch e controle).
icc        ANOVA de efeitos aleatorios, epoch como fator; negativo -> 0.

A CIRCULARIDADE, E COMO ELA E TRATADA
-------------------------------------
Marcar oportunidade exige saber quais episodios PASSADOS sao failure, e
medir `p0_hat` exige saber se o episodio ATUAL e failure. Ambos vem do
painel. Como a adjudicacao e cara, este script nao assume cobertura total:
cada episodio entra como `failure`, `not_failure` ou `unknown`, e o
relatorio informa quanta massa esta em `unknown`. Um `p0_hat` calculado
sobre cobertura parcial e reportado com a cobertura ao lado, nunca sozinho.

APROXIMACAO DECLARADA
---------------------
A condicao (i) pergunta o que o snapshot CONTINHA. `pruneEpochs(keep=3)`
apaga os .db historicos de proposito, entao a pertinencia e reconstruida
por timestamp (`ts < boundary`). Divergencia conhecida: 0,144%/epoch (T7).
Ver a nota de sensibilidade no pre-registro.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

BOUNDARY_UTC_H = 9      # 06:00 BRT
EPOCH_H = 24.0
WASHOUT_H = 2.0
PISO_SESSAO_H = 1 / 60  # sessao de uma acao so conta 1 minuto, nao zero
TAU = "S1"
NIVEIS = ["S0", "S1", "S2", "S3", "S4"]


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def epoch_de(t: datetime) -> tuple[datetime, float]:
    """Devolve (inicio_do_epoch, horas_desde_o_inicio)."""
    e = t.replace(hour=BOUNDARY_UTC_H, minute=0, second=0, microsecond=0)
    if t < e:
        e -= timedelta(days=1)
    return e, (t - e).total_seconds() / 3600


def carregar_verdicts(p: Path) -> dict[str, str]:
    """episode_id -> 'failure' | 'not_failure', por MAIORIA ESTRITA.

    CORRECAO 2026-07-29 — a versao anterior usava `v[len(v)//2]`, a mediana
    SUPERIOR, para as duas condicoes. Duas coisas estavam erradas nisso.

    1. O §4.1 do pre-registro trava, literalmente: *"condition (ii) is the
       binary verdict. Severity governs condition (i) only."* Severidade
       decide quais episodios PASSADOS semeiam um repeat; o desfecho do
       episodio corrente e o veredito binario por **maioria simples**.
    2. Com contagem PAR a mediana superior nao e a maioria. Para 4 vereditos
       ordenados v0<=v1<=v2<=v3, `v[2] >= tau` significa 2 de 4 acima do
       corte — um EMPATE resolvido a favor de `failure`. Maioria simples
       exige 3 de 4. A mediana INFERIOR (`v[1]`) e que coincide com ela.

    Por que isso nao e detalhe: 987 dos 1.140 episodios da peca 3 tem
    exatamente 4 vereditos substantivos (moonshot parou em 88/1.140 por
    cota). Contagem par e a REGRA, nao a excecao — e o pre-registro so
    afirma ausencia de empate por assumir painel impar ("odd panel => no
    binary tie"), premissa que abstencao e falha de cota derrubam.
    Medido: as duas leituras fieis (maioria estrita; empate => inadjudicavel)
    dao K = 64; a mediana superior da 53. Swing de 20% num parametro que o
    pre-registro nunca especificou.

    Empate exato (n/2 falhas, so possivel com n par) resolve para
    `not_failure` — um empate nao e maioria. Conservador: subestima falhas,
    logo subestima lambda_0, logo INFLA K. Erra para estudo mais longo.

    Abstencao conta como ausente (§4.1); < 3 vereditos substantivos vira
    `unknown`.
    """
    # Dedupe por (episode_id, panelist) — nao por episode_id sozinho.
    #
    # Motivo (incident 2026-08-13, docs/INCIDENTS.md): dois processos
    # adjudicaram a mesma fila em paralelo e 40 episodios receberam DOIS
    # vereditos do mesmo painelista. Agregando so por episode_id, o segundo
    # entra como voto extra: 39 episodios viraram painel PAR (4 votos), e a
    # maioria estrita abaixo resolve empate 2-2 silenciosamente para
    # `not_failure`. Naquele caso o impacto medido foi ZERO (os pares
    # concordavam), mas a premissa de painel impar — "sem empate por
    # construcao" — tinha sido violada sem ninguem notar.
    #
    # Regra: mantem o PRIMEIRO registro de cada (episodio, painelista) na
    # ordem do arquivo de entrada. Quando o arquivo e montado concatenando as
    # rodadas em ordem de geracao, "primeiro no arquivo" == cronologicamente
    # anterior, que e a regra declarada em STABILITY-TEST.md §6. Se o chamador
    # concatenar fora de ordem, a regra degrada para "primeiro visto" — ainda
    # deterministica e independente do conteudo do veredito, que e a
    # propriedade que importa para nao escolher resultado.
    por_ep: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for linha in p.read_text().splitlines():
        if not linha.strip():
            continue
        r = json.loads(linha)
        if r.get("status") != "ok" or r.get("verdict") == "abstain":
            continue
        nivel = r.get("level")
        if nivel in NIVEIS:
            por_ep[r["episode_id"]].setdefault(r.get("panelist"), NIVEIS.index(nivel))

    out: dict[str, str] = {}
    corte = NIVEIS.index(TAU)
    for ep, por_painelista in por_ep.items():
        v = list(por_painelista.values())
        if len(v) < 3:
            continue
        n_falha = sum(1 for x in v if x >= corte)
        out[ep] = "failure" if n_falha * 2 > len(v) else "not_failure"
    return out


@dataclass
class Episodio:
    id: str
    ts: datetime
    sessao: str
    sig: str
    epoch: datetime
    offset_h: float
    estado: str  # failure | not_failure | unknown
    err: bool    # is_error — estratificador do desenho (§4 de PILOT-PROJECTION.md)


def carregar_episodios(p: Path, verdicts: dict[str, str]) -> list[Episodio]:
    eps: list[Episodio] = []
    for linha in p.read_text().splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        if not d.get("ts") or not d.get("session"):
            continue
        t = parse_ts(d["ts"])
        e, off = epoch_de(t)
        eps.append(Episodio(
            id=d["episode_id"], ts=t, sessao=d["session"],
            sig=d["sig_primary"], epoch=e, offset_h=off,
            estado=verdicts.get(d["episode_id"], "unknown"),
            err=bool(d.get("is_error")),
        ))
    eps.sort(key=lambda x: x.ts)
    return eps


def span_por_sessao(eps: list[Episodio]) -> dict[tuple[datetime, str], float]:
    """Horas de cada sessao, chaveado por (epoch, sessao).

    A SESSAO e a unidade de analise do ANOVA — o epoch e o cluster. Por isso
    o span fica por sessao em vez de ja somado: com uma observacao por epoch
    nao ha variancia within, e o ICC sai identicamente 0 por construcao.
    """
    ts_por_sessao: dict[tuple[datetime, str], list[datetime]] = collections.defaultdict(list)
    for e in eps:
        ts_por_sessao[(e.epoch, e.sessao)].append(e.ts)
    return {
        k: max((max(v) - min(v)).total_seconds() / 3600, PISO_SESSAO_H)
        for k, v in ts_por_sessao.items()
    }


def icc_anova(por_epoch: dict[datetime, list[float]]) -> float:
    """ICC de efeitos aleatorios (one-way). Negativo -> 0 (conservador)."""
    grupos = [v for v in por_epoch.values() if v]
    if len(grupos) < 2:
        return 0.0
    todos = [x for g in grupos for x in g]
    n = len(todos)
    k = len(grupos)
    if n <= k:
        return 0.0
    media = statistics.fmean(todos)
    ms_between = sum(len(g) * (statistics.fmean(g) - media) ** 2 for g in grupos) / (k - 1)
    ms_within = sum((x - statistics.fmean(g)) ** 2 for g in grupos for x in g) / (n - k)
    m_bar = n / k
    denom = ms_between + (m_bar - 1) * ms_within
    if denom <= 0:
        return 0.0
    return max(0.0, (ms_between - ms_within) / denom)


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay do piloto — produz r_hat, p0_hat, icc")
    ap.add_argument("--episodes", required=True, help="JSONL do extract_episodes")
    ap.add_argument("--verdicts", required=True, help="JSONL do run_panel")
    ap.add_argument("--min-epochs", type=int, default=0,
                    help="recusa rodar com menos epochs analisaveis que isto (gate do §3)")
    ap.add_argument("--seed-b", default="",
                    help="SEED_B do desenho estratificado (§4 de PILOT-PROJECTION.md); "
                         "sem ela o script roda em modo censo, sem pesos")
    ap.add_argument("--n-b", type=int, default=800,
                    help="tamanho da amostra do estrato nao-is_error (default 800)")
    ap.add_argument("--json", action="store_true", help="saida so em JSON")
    a = ap.parse_args()

    verdicts = carregar_verdicts(Path(a.verdicts))
    eps = carregar_episodios(Path(a.episodes), verdicts)
    if not eps:
        print("ERRO: nenhum episodio com ts+session", file=sys.stderr)
        return 2

    spans = span_por_sessao(eps)
    horas: dict[datetime, float] = collections.defaultdict(float)
    sessoes_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    for (ep, _), h in spans.items():
        horas[ep] += h
        sessoes_por_epoch[ep] += 1

    # failure episodes conhecidos, por assinatura, com o timestamp mais antigo
    primeiro_failure: dict[str, datetime] = {}
    for e in eps:
        if e.estado == "failure" and (e.sig not in primeiro_failure or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts

    limiar = timedelta(hours=EPOCH_H)
    oport_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    repeat_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    repeat_por_sessao: dict[tuple[datetime, str], int] = collections.defaultdict(int)
    oport_unknown = 0
    analisaveis = [e for e in eps if e.offset_h >= WASHOUT_H]

    # ── Desenho amostral ────────────────────────────────────────────────────
    # Sem `--seed-b`, o script assume CENSO: todo episodio pesa 1 e episodios
    # de desfecho desconhecido entram como oportunidade — o que faz de
    # `p0_hat` um PISO, e o aviso no fim diz isso.
    #
    # Com `--seed-b`, ele reproduz o desenho estratificado declarado no §4 de
    # PILOT-PROJECTION.md (censo do estrato is_error + amostra uniforme de
    # `--n-b` do complemento, ordenada por hash) e aplica pesos de
    # Horvitz-Thompson. Sem esses pesos o estimador subconta os repeats do
    # estrato amostrado por um fator N_B/n_B — aqui, 5.2x — e `lambda_0` sai
    # deflacionado. Nao e conservador nem otimista por acaso: e simplesmente
    # o estimador errado para o desenho.
    if a.seed_b:
        estrato_a = [e for e in analisaveis if e.err]
        resto = [e for e in analisaveis if not e.err]
        chave = lambda e: hashlib.sha256(
            a.seed_b.encode("ascii") + b"|" + e.id.encode()).hexdigest()
        estrato_b = sorted(resto, key=chave)[: a.n_b]
        peso = {e.id: 1.0 for e in estrato_a}
        peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
        analisaveis = estrato_a + estrato_b
    else:
        peso = {e.id: 1.0 for e in analisaveis}

    for e in analisaveis:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue                      # condicao (i) nao satisfeita
        if a.seed_b and e.estado == "unknown":
            oport_unknown += 1            # fora do estimador: peso nao definido
            continue
        oport_por_epoch[e.epoch] += peso[e.id]
        if e.estado == "failure":
            repeat_por_epoch[e.epoch] += peso[e.id]
            repeat_por_sessao[(e.epoch, e.sessao)] += peso[e.id]
        elif e.estado == "unknown":
            oport_unknown += 1            # desfecho nao adjudicado (modo censo)

    epochs = sorted(ep for ep in horas if horas[ep] > 0)
    if a.min_epochs and len(epochs) < a.min_epochs:
        print(f"ERRO: {len(epochs)} epochs analisaveis, minimo exigido {a.min_epochs}", file=sys.stderr)
        return 3

    tot_oport = sum(oport_por_epoch.values())
    tot_repeat = sum(repeat_por_epoch.values())
    tot_horas = sum(horas[ep] for ep in epochs)

    # ANOVA: uma observacao por SESSAO (unidade), agrupada por epoch (cluster).
    # Epochs com < 2 sessoes nao contribuem variancia within e sao excluidos
    # do ICC — reportados a parte para nao sumirem em silencio.
    dens: dict[datetime, list[float]] = collections.defaultdict(list)
    for (ep, s), h in spans.items():
        if ep in epochs and sessoes_por_epoch[ep] >= 2:
            dens[ep].append(repeat_por_sessao.get((ep, s), 0) / h)
    epochs_degenerados = [ep for ep in epochs if sessoes_por_epoch[ep] < 2]

    saida = {
        "r_hat": round(tot_oport / tot_horas, 6) if tot_horas else None,
        "p0_hat": round(tot_repeat / tot_oport, 6) if tot_oport else None,
        "icc": round(icc_anova(dict(dens)), 6),
        "hours_per_epoch": round(tot_horas / len(epochs), 4) if epochs else None,
        "session_hours_per_epoch": round(
            sum(sessoes_por_epoch[ep] for ep in epochs) / len(epochs), 4) if epochs else None,
        "epochs_analisaveis": len(epochs),
        "epochs_fora_do_icc": len(epochs_degenerados),
        "oportunidades": tot_oport,
        "repeats": tot_repeat,
        "cobertura_adjudicacao": {
            "episodios_total": len(eps),
            "com_veredito": sum(1 for e in eps if e.estado != "unknown"),
            "pct": round(100 * sum(1 for e in eps if e.estado != "unknown") / len(eps), 2),
            "oportunidades_com_desfecho_unknown": oport_unknown,
        },
        "assinaturas_com_failure_conhecido": len(primeiro_failure),
        "desenho": "estratificado-HT" if a.seed_b else "censo",
        "regra_desfecho": "maioria estrita (>50%); empate => not_failure",
        "tau": TAU,
    }

    if a.json:
        print(json.dumps(saida, indent=2, sort_keys=True, default=str))
        return 0

    print(json.dumps(saida, indent=2, sort_keys=True, default=str))
    cob = saida["cobertura_adjudicacao"]
    if cob["pct"] < 100:
        print(f"\n⚠️  cobertura de adjudicacao {cob['pct']}% — "
              f"{cob['oportunidades_com_desfecho_unknown']} oportunidades sem desfecho adjudicado.\n"
              f"    p0_hat acima e um PISO: os unknown so podem aumenta-lo.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
