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
import glob
import hashlib
import json
import math
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


def episodios_instaveis(padroes: list[str]) -> set[str]:
    """Episodios cujo veredito de um MESMO painelista oscila entre replicas.

    Regra do STABILITY-TEST.md §9.2, adotada 2026-08-14. Censo dos 21 episodios
    de desempate (xai e zhipu em lados opostos de tau) com 5 replicas cada
    mostrou que **10 deles (47,6%) oscilam** — tres em 3F/3N exato. Nesses o
    painelista e voto de minerva por definicao, logo o desfecho consolidado
    sai da execucao, nao do episodio.

    CRITERIO AMPLO: qualquer oscilacao marca o episodio, tratando 5-1 igual a
    3-3. Um criterio graduado (so 4-2 e 3-3) e defensavel, mas NAO foi
    pre-especificado — escolhe-lo depois de ver a distribuicao seria escolher
    com os dados na mao. O amplo e o menos favoravel a nos, e por isso o menos
    suspeito. Revisar com dados quando houver replicas do corpus completo.

    Custo medido no corpus de 2026-08-14: 10 episodios, 0,69% bruto e 0,79%
    ponderado por Horvitz-Thompson (a amplificacao pelo peso 5,2 do estrato B
    ficou em 1,14x, nao nos 15x temidos).

    O episodio marcado NAO recebe veredito: `carregar_episodios` resolve para
    `unknown`, exatamente como "menos de 3 vereditos substantivos". Ou seja,
    instabilidade vira ausencia de evidencia, nao voto de moeda.
    """
    corte = NIVEIS.index(TAU)
    lados: dict[tuple[str, str], set[bool]] = collections.defaultdict(set)
    for padrao in padroes:
        for caminho in sorted(glob.glob(padrao)):
            for linha in Path(caminho).read_text().splitlines():
                if not linha.strip():
                    continue
                r = json.loads(linha)
                if r.get("status") != "ok" or r.get("verdict") == "abstain":
                    continue
                nivel = r.get("level")
                if nivel in NIVEIS:
                    lados[(r["episode_id"], r.get("panelist"))].add(
                        NIVEIS.index(nivel) >= corte)
    return {ep for (ep, _), s in lados.items() if len(s) > 1}


def carregar_verdicts(p: Path, instaveis: frozenset[str] = frozenset()) -> dict[str, str]:
    """episode_id -> 'failure' | 'not_failure', por MAIORIA ESTRITA.

    `instaveis` (de `episodios_instaveis`) sao omitidos do resultado e portanto
    resolvem para `unknown` — ver STABILITY-TEST.md §9.2.

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
        if ep in instaveis:
            continue  # oscila entre replicas -> `unknown` (STABILITY-TEST.md §9.2)
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


def _betainc(a: float, b: float, x: float) -> float:
    """Beta incompleta regularizada I_x(a,b) — fracao continuada de Lentz.

    Stdlib pura DE PROPOSITO. Este script e pre-registrado: um terceiro tem de
    poder rodar o replay sem instalar nada. `scipy` daria a mesma coisa em uma
    linha, e `tests/test_icc_ci.py` confronta as duas implementacoes — mas a
    dependencia fica no TESTE, nunca no caminho canonico.
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float, itmax: int = 300, eps: float = 3e-16) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _f_cdf(x: float, d1: float, d2: float) -> float:
    if x <= 0.0:
        return 0.0
    return _betainc(d1 / 2.0, d2 / 2.0, d1 * x / (d1 * x + d2))


def _f_ppf(p: float, d1: float, d2: float) -> float:
    """Quantil da F por bissecao sobre a CDF. Monotona, logo a bissecao basta."""
    lo, hi = 1e-12, 1.0
    while _f_cdf(hi, d1, d2) < p and hi < 1e12:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _f_cdf(mid, d1, d2) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def icc_anova(por_epoch: dict[datetime, list[float]],
              alfa: float = 0.05) -> dict[str, float | int | None]:
    """ICC de efeitos aleatorios (one-way) com IC exato de Searle.

    Devolve os QUADRADOS MEDIOS junto com o ponto e o intervalo. Antes esta
    funcao devolvia so o `float`, e o SIZING-2026-08-14 teve de estimar a
    largura do IC RECONSTRUINDO a ANOVA num script separado — que deu 0,0964
    contra os 0,1175 do canonico e obrigou o documento a dizer "isto indica a
    largura, nao e o intervalo oficial". Com os MS expostos o IC sai do mesmo
    codigo que produz o ponto, e a divergencia deixa de existir.

    IC (Searle 1971, one-way): com F = MSb/MSw e g.l. (k-1, n-k),
        F_L = F / F_{1-alfa/2},  F_U = F / F_{alfa/2}
        ICC_bound = (F_bound - 1) / (F_bound + m_bar - 1)

    ⚠️ APROXIMACAO DECLARADA: `m_bar = n/k` é a media aritmetica dos tamanhos de
    cluster. O IC exato de Searle assume clusters BALANCEADOS, e os nossos nao
    sao (30 epochs, tamanhos de 1 a ~100, dois deles parciais por censura a
    direita). Para desbalanceamento moderado o intervalo e conhecido por ser
    levemente ANTICONSERVADOR — estreito demais. Ele serve para decidir se a
    incerteza e da ordem de dezenas ou de centenas de dias; nao serve como
    intervalo publicavel sem uma nota. Um IC por bootstrap de cluster resolve,
    custa mais, e nao foi pre-especificado.

    `icc` negativo -> 0 (conservador), e o limite inferior tambem.
    """
    grupos = [v for v in por_epoch.values() if v]
    vazio = {"icc": 0.0, "ms_between": None, "ms_within": None, "f": None,
             "gl_between": None, "gl_within": None, "m_bar": None,
             "ic_low": None, "ic_high": None, "ic_alfa": alfa}
    if len(grupos) < 2:
        return vazio
    todos = [x for g in grupos for x in g]
    n, k = len(todos), len(grupos)
    if n <= k:
        return vazio
    media = statistics.fmean(todos)
    ms_between = sum(len(g) * (statistics.fmean(g) - media) ** 2 for g in grupos) / (k - 1)
    ms_within = sum((x - statistics.fmean(g)) ** 2 for g in grupos for x in g) / (n - k)
    m_bar = n / k
    denom = ms_between + (m_bar - 1) * ms_within
    if denom <= 0:
        return vazio
    icc = max(0.0, (ms_between - ms_within) / denom)

    out: dict[str, float | int | None] = {
        "icc": round(icc, 6),
        "ms_between": round(ms_between, 8),
        "ms_within": round(ms_within, 8),
        "gl_between": k - 1,
        "gl_within": n - k,
        "m_bar": round(m_bar, 4),
        "ic_alfa": alfa,
        "f": None, "ic_low": None, "ic_high": None,
    }
    if ms_within > 0:
        f = ms_between / ms_within
        d1, d2 = float(k - 1), float(n - k)
        fl = f / _f_ppf(1.0 - alfa / 2.0, d1, d2)
        fu = f / _f_ppf(alfa / 2.0, d1, d2)
        lim = lambda fb: (fb - 1.0) / (fb + m_bar - 1.0)
        # Clamp em [0,1] nos DOIS limites. O superior tambem pode sair negativo:
        # quando F < F_{alfa/2}, os dados sao compativeis com ausencia total de
        # efeito de cluster e a formula devolve um numero abaixo de zero. Como
        # o ICC nao e definido fora de [0,1], o intervalo colapsa em [0, 0] —
        # que se le como "nao ha evidencia de estrutura de cluster", nao como
        # "o ICC vale exatamente zero".
        out["f"] = round(f, 6)
        out["ic_low"] = round(min(1.0, max(0.0, lim(fl))), 6)
        out["ic_high"] = round(min(1.0, max(0.0, lim(fu))), 6)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay do piloto — produz r_hat, p0_hat, icc")
    ap.add_argument("--episodes", required=True, help="JSONL do extract_episodes")
    ap.add_argument("--verdicts", required=True, help="JSONL do run_panel")
    ap.add_argument("--min-epochs", type=int, default=0,
                    help="recusa rodar com menos epochs analisaveis que isto (gate do §3)")
    ap.add_argument("--seed-b", default="",
                    help="SEED_B do desenho estratificado (§4 de PILOT-PROJECTION.md); "
                         "sem ela o script roda em modo censo, sem pesos")
    ap.add_argument("--estrato-b-ids", default="",
                    help="arquivo com um episode_id por linha: a amostra ja sorteada "
                         "do estrato B. Use quando o corpus une universos de seeds "
                         "diferentes (ver comentario no corpo). Tem precedencia sobre "
                         "--seed-b/--n-b; exige mesma TAXA de amostragem entre eles.")
    ap.add_argument("--n-b", type=int, default=800,
                    help="tamanho da amostra do estrato nao-is_error (default 800)")
    ap.add_argument("--json", action="store_true", help="saida so em JSON")
    ap.add_argument("--replicas", nargs="*", default=[],
                    help="globs de JSONL com replicas do painel (ex: "
                         "'~/.paper2-verdicts/tiebreak-rep*.jsonl'). Episodios cujo "
                         "veredito oscila entre replicas viram `unknown` — "
                         "STABILITY-TEST.md §9.2. Sem isto, o script roda sem a regra.")
    a = ap.parse_args()

    instaveis = frozenset()
    if a.replicas:
        padroes = [str(Path(x).expanduser()) for x in a.replicas]
        instaveis = frozenset(episodios_instaveis(padroes))
        print(f"regra de instabilidade ativa: {len(instaveis)} episodios -> unknown",
              file=sys.stderr)

    verdicts = carregar_verdicts(Path(a.verdicts), instaveis)
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
    # ── Corpus com MAIS DE UMA seed (extensao 2, 2026-08-14) ────────────────
    # O sorteio acima ordena TODO o `resto` por uma unica seed. Isso deixa de
    # funcionar quando o corpus e a uniao de dois universos amostrados por
    # seeds diferentes, cada uma declarada antes do seu proprio round:
    # re-sortear a uniao produziria uma TERCEIRA amostra, que nenhuma das duas
    # declaracoes cobre.
    #
    # `--estrato-b-ids` resolve isso pela unica via honesta: le a lista de
    # sorteados de um arquivo, em vez de re-derivar. Cada ID da lista continua
    # sendo derivavel da sua seed publica aplicada ao seu proprio universo —
    # a auditoria por terceiro nao perde nada, so passa a ter dois passos.
    #
    # ⚠️ O ESTIMADOR NAO MUDA. O peso segue `len(resto)/len(estrato_b)`, e ele
    # so permanece valido porque as duas extensoes usam a MESMA TAXA (19,2%):
    # 1.576/8.194 = 5,199 e 122/635 = 5,205, uniao 1.698/8.829 = 5,200. Se uma
    # extensao futura usar taxa diferente, este caminho passa a estar ERRADO e
    # o codigo precisa de peso por estrato — nao de mais um arquivo de IDs.
    estratificado = bool(a.estrato_b_ids or a.seed_b)
    if a.estrato_b_ids:
        ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
        estrato_a = [e for e in analisaveis if e.err]
        resto = [e for e in analisaveis if not e.err]
        estrato_b = [e for e in resto if e.id in ids]
        faltando = len(ids) - len(estrato_b)
        if faltando:
            print(f"aviso: {faltando} ids da amostra nao estao no universo/pos-washout",
                  file=sys.stderr)
        peso = {e.id: 1.0 for e in estrato_a}
        peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
        analisaveis = estrato_a + estrato_b
    elif a.seed_b:
        # CORRECAO 2026-08-14 — o sorteio roda sobre `eps` (universo BRUTO), nao
        # sobre `analisaveis` (pos-washout). A versao anterior sorteava os `n_b`
        # do complemento JA filtrado por washout, e isso estava errado por dois
        # motivos que se somavam:
        #
        # 1. CONJUNTO ERRADO. O desenho declarado em EXTENSION-SEED-2026-08-11
        #    §"Desenho" e "1.576 de 8.194" — 8.194 e o complemento no bruto, e e
        #    sobre ele que a amostra foi de fato sorteada e adjudicada (99,3% de
        #    reproducao). Sorteando pos-washout (6.675) o script escolhia OUTRO
        #    conjunto de 1.576: apenas 1.259 deles tinham veredito, e os 317
        #    restantes entravam como `unknown`. Medido: `unknown` cai de 232
        #    para 44 com a correcao.
        # 2. PESO ERRADO. `len(resto_pw)/n_b` = 6.675/1.576 = 4,235, contra o
        #    peso HT de 5,2x que o proprio desenho declara como alvo. O estrato
        #    B saia subcontado em ~20%.
        #
        # Efeito nos tres numeros do piloto (corpus da extensao 1):
        #   r_hat  22,78 -> 27,86 | p0_hat 0,1310 -> 0,1159 | icc 0,1169 -> 0,1016
        estrato_a = [e for e in analisaveis if e.err]
        resto = [e for e in analisaveis if not e.err]
        chave = lambda e: hashlib.sha256(
            a.seed_b.encode("ascii") + b"|" + e.id.encode()).hexdigest()
        sorteados = {e.id for e in sorted(
            [e for e in eps if not e.err], key=chave)[: a.n_b]}
        estrato_b = [e for e in resto if e.id in sorteados]
        peso = {e.id: 1.0 for e in estrato_a}
        peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
        analisaveis = estrato_a + estrato_b
    else:
        peso = {e.id: 1.0 for e in analisaveis}

    for e in analisaveis:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue                      # condicao (i) nao satisfeita
        if estratificado and e.estado == "unknown":
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

    icc_out = icc_anova(dict(dens))

    saida = {
        "r_hat": round(tot_oport / tot_horas, 6) if tot_horas else None,
        "p0_hat": round(tot_repeat / tot_oport, 6) if tot_oport else None,
        "icc": icc_out["icc"],
        "icc_anova": icc_out,
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
        "desenho": "estratificado-HT" if estratificado else "censo",
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
