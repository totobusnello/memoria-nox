#!/usr/bin/env python3
"""Delimita a janela elegível do ensaio do Paper 2 e emite JSON, não prosa.

Decisão do Toto em 2026-09-09 14:38 BRT, literal: **"encerra 20/09 mesmo, e desliga a
dose depois"**. Esta é a primeira instrução explícita sobre o desfecho — o registro
anterior (§10.14) fundava a reversão numa MEDIÇÃO e citava uma pergunta retórica
("prolonga ne? melhor nao acha?"), o que não é ordem. Agora é.

O que este script computa é a consequência ARITMÉTICA da decisão, não a decisão:

  * os epochs viram às 09:00Z (§2 do prereg);
  * o active começou a servir em 2026-09-01T10:37:01.943Z — 1h37m DEPOIS da
    fronteira, logo o primeiro epoch é PARCIAL;
  * os 19 designados têm `created_at` idêntico 2026-08-21 22:51:23 e a janela do
    sub-pool global é de 30 d pelo relógio de REQUEST ⇒ expiram em
    2026-09-20 22:51:23Z, que cai 13h51m DENTRO do epoch de 09-20, logo o último
    epoch também é PARCIAL.

Os parciais ficam registrados separadamente em vez de arredondados para dentro ou para
fora: um epoch de exposição MISTA não é o mesmo objeto que um de exposição uniforme, e
fundir os dois é a família do "número certo com população errada".

⚠️ **ERRATA 2026-09-10.** A versão anterior concluía *"Elegíveis INTEIROS: 2026-09-02 …
2026-09-19"* — **18 inteiros + 2 parciais** — e essa frase era falsa em dois epochs,
porque toda a classificação vinha de RELÓGIO e nenhuma de ENTREGA:

  * `2026-09-02` saía `inteiro, exposto_h 24.0` e serviu **0 briefs** (o epoch nunca
    abriu; lacuna de 32,5 h já registrada no `INCIDENT-2026-09-02-epoch-perdido.md`,
    isto é: o fato estava medido AO LADO e o artefato o contradizia);
  * `2026-09-03` saía `inteiro` e serviu **441 de 672**.

O defeito estava no nome: `fracao_exposta`/`exposto_h` leem-se como exposição ENTREGUE e
eram sobreposição de relógio, com um docstring que dizia "fração do epoch em que a dose
foi servida". Nome errado num artefato propaga-se a todo consumidor do JSON — pior que
frase errada em prosa, que ao menos ninguém importa.

Agora a classe é composta e as duas metades ficam visíveis: `classe_janela` (relógio) ×
`classe_entrega` (censo de serving, com procedência) ⇒ `unidade`. Sem censo o script
**aborta**; epoch ausente do censo é `vazio`, nunca `cheio` por omissão.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

U = timezone.utc
ACTIVE_EM = datetime(2026, 9, 1, 10, 37, 1, 943000, tzinfo=U)   # 1a linha p2_outcome active
CRIADOS_EM = datetime(2026, 8, 21, 22, 51, 23, tzinfo=U)        # created_at dos 19, idêntico
JANELA_D = 30                                                    # freshGlobalMaxAgeDays
EXPIRA_EM = CRIADOS_EM + timedelta(days=JANELA_D)
FRONTEIRA_H = 9                                                  # epochs viram às 09:00Z
ESPERADO_POR_EPOCH = 672     # 4 rajadas/h x 24 h x 7 briefs/rajada (6 agentes, nox 2x)
CENSO_PADRAO = "out/CENSO-SERVIDO-2026-09-10.json"


def carrega_censo(caminho: str | None = None) -> dict:
    """Lê o censo de entrega. ABORTA se faltar — nunca classifica sem o dado.

    Fail-closed porque o modo de falha que este script já teve foi exatamente o oposto:
    concluir `inteiro` na AUSÊNCIA de informação de entrega. Um default silencioso aqui
    reintroduz o defeito com outra roupa.
    """
    caminho = caminho or os.environ.get("P2_CENSO") or CENSO_PADRAO
    if not os.path.exists(caminho):
        raise SystemExit(
            f"RED censo-de-entrega-ausente caminho={caminho}\n"
            "  rode: python3 censo-servido-por-epoch.py > out/CENSO-SERVIDO-<data>.json")
    c = json.load(open(caminho))
    for k in ("por_campo_epoch", "por_epoch_e_modo", "host", "log_sha256", "linhas",
              "divergencia_campo_vs_ts", "sem_modo", "semantica"):
        if k not in c:
            raise SystemExit(f"RED censo-sem-campo-{k} caminho={caminho}")
    if c["sem_modo"] != 0:
        raise SystemExit("RED censo-com-registro-sem-modo "
                         f"n={c['sem_modo']} (impede separar active de shadow)")
    if c["divergencia_campo_vs_ts"] != 0:
        raise SystemExit("RED censo-com-chave-de-epoch-divergente "
                         f"n={c['divergencia_campo_vs_ts']}")
    return c


def epoch_de(dia: datetime) -> tuple[datetime, datetime]:
    ini = dia.replace(hour=FRONTEIRA_H, minute=0, second=0, microsecond=0)
    return ini, ini + timedelta(days=1)


def classifica_janela(ini: datetime, fim: datetime) -> dict:
    """Fração do epoch DENTRO DA JANELA: active já no ar E designados ainda frescos.

    ⚠️ É RELÓGIO, não entrega. Esta função não lê o log de serving e por isso NÃO pode
    dizer que a dose foi servida — a versão anterior prometia isso no docstring, chamava
    a saída de `fracao_exposta`/`exposto_h`, e classificou `2026-09-02` como
    `inteiro, 24.0 h` num epoch que serviu **0 briefs**. Os nomes agora dizem relógio.
    A entrega entra por `classifica_entrega()`, com dado medido.
    """
    de = max(ini, ACTIVE_EM)
    ate = min(fim, EXPIRA_EM)
    dentro_s = max(0.0, (ate - de).total_seconds())
    total_s = (fim - ini).total_seconds()
    frac = dentro_s / total_s
    if frac == 0.0:
        classe = "fora"
    elif frac >= 1.0:
        classe = "inteiro"
    else:
        classe = "parcial"
    return {"fracao_da_janela": round(frac, 6), "classe_janela": classe,
            "horas_na_janela": round(dentro_s / 3600, 2)}


def classifica_entrega(epoch: str, por_modo: dict, hoje: str,
                       fim: datetime | None = None,
                       agora: datetime | None = None) -> dict:
    """Classe de ENTREGA do epoch, do censo de serving. Fail-closed por construção.

    `por_modo` é `por_epoch_e_modo` do `censo-servido-por-epoch.py`. Epoch AUSENTE do
    censo é `vazio` (0 servidos) — nunca `cheio` por omissão, que é a regra 9 do
    CLAUDE.md: guarda cujo predicado exige o dado que falta não cobre a falta do dado.

    ⚠️ **Conta só o `active`.** A primeira versão usava o TOTAL e para `2026-09-01`
    declarava `cheio` com 672, quando 630 foram sob a dose designada (w=4,0) e 42 em
    `shadow` (w=2,0). O veredito do epoch continuava `parcial`, mas chegava pela perna do
    **relógio** — logo a perna de entrega errava exactamente no único epoch capaz de a
    testar (medido: 09-01 é o único de modo misto da janela). Perna correta encoberta por
    outra perna correta não tem teste que a alcance, e por isso `classe_entrega` de 09-01
    é asserção própria na suíte, separada de `unidade`.
    """
    if epoch > hoje:
        return {"servidos": None, "classe_entrega": "futuro"}
    modos = por_modo.get(epoch, {})
    n = int(modos.get("active", 0))
    total = int(sum(modos.values()))
    extra = {"servidos_total": total, "por_modo": modos,
             "modo_misto": len([m for m, v in modos.items() if v > 0]) > 1}
    if fim is not None and agora is not None and fim > agora:
        return {"servidos": n, "esperado": ESPERADO_POR_EPOCH,
                "classe_entrega": "em_curso", **extra}
    if n == 0:
        c = "vazio"
    elif n >= ESPERADO_POR_EPOCH:
        c = "cheio"
    else:
        c = "parcial"
    return {"servidos": n, "esperado": ESPERADO_POR_EPOCH, "classe_entrega": c, **extra}


def main() -> None:
    primeiro = ACTIVE_EM.replace(hour=FRONTEIRA_H, minute=0, second=0, microsecond=0)
    if primeiro > ACTIVE_EM:
        primeiro -= timedelta(days=1)
    censo = carrega_censo()
    por_modo = censo["por_epoch_e_modo"]
    agora = datetime.now(U)
    hoje = agora.date().isoformat()

    epochs, dia = [], primeiro
    while dia <= EXPIRA_EM:
        ini, fim = epoch_de(dia)
        ep = ini.date().isoformat()
        j = classifica_janela(ini, fim)
        e = classifica_entrega(ep, por_modo, hoje, fim=fim, agora=agora)
        # A unidade de análise só é INTEIRA se o relógio E a entrega o forem. Uma delas
        # sozinha já classificou errado em produção.
        if j["classe_janela"] == "fora":
            unidade = "fora"
        elif e["classe_entrega"] == "futuro":
            unidade = "futuro"
        elif e["classe_entrega"] == "em_curso":
            unidade = "em_curso"
        elif e["classe_entrega"] == "vazio":
            unidade = "vazia"
        elif j["classe_janela"] == "inteiro" and e["classe_entrega"] == "cheio":
            unidade = "inteira"
        else:
            unidade = "parcial"
        motivos = [m for m, cond in (
            ("relogio", j["classe_janela"] == "parcial"),
            ("volume", e["classe_entrega"] == "parcial"),
            ("vazio", e["classe_entrega"] == "vazio"),
        ) if cond]
        epochs.append({"epoch": ep, "inicio": ini.isoformat(), "fim": fim.isoformat(),
                       **j, **e, "unidade": unidade, "motivos": motivos})
        dia += timedelta(days=1)

    inteiros = [e for e in epochs if e["unidade"] == "inteira"]
    parciais = [e for e in epochs if e["unidade"] == "parcial"]
    vazias = [e for e in epochs if e["unidade"] == "vazia"]
    futuras = [e for e in epochs if e["unidade"] == "futuro"]
    out = {
        "decisao": {
            "data": "2026-09-09T14:38-03:00",
            "literal": "encerra 20/09 mesmo, e desliga a dose depois",
            "fonte": "instrução direta do Toto; primeira explícita sobre o desfecho",
        },
        "premissas_medidas": {
            "active_primeira_linha_servida": ACTIVE_EM.isoformat(),
            "designados_created_at": CRIADOS_EM.isoformat(),
            "designados_n": 19,
            "fresh_global_max_age_days": JANELA_D,
            "expira_em": EXPIRA_EM.isoformat(),
            "fronteira_de_epoch_utc": f"{FRONTEIRA_H:02d}:00Z",
            "corpus_de_referencia": "servido-e20260903T060001Z.db",
            "corpus_sha256": "23378a9ea83cd27d0360cfe148207167aee30a376f29ef89d4bcfae415d04131",
        },
        "censo_de_entrega": {
            "host": censo["host"], "log": censo["log"],
            "log_sha256": censo["log_sha256"], "linhas": censo["linhas"],
            "divergencia_campo_vs_ts": censo["divergencia_campo_vs_ts"],
            "semantica": censo["semantica"],
        },
        "unidades_de_analise": {
            "semantica": ("INTEIRA exige relogio inteiro E entrega cheia; as duas classes "
                          "ficam separadas no vetor `epochs`"),
            "inteiras_n": len(inteiros),
            "inteiras_de": inteiros[0]["epoch"] if inteiros else None,
            "inteiras_ate": inteiros[-1]["epoch"] if inteiros else None,
            "parciais": [{"epoch": e["epoch"],
                "motivos": ([m for m, cond in (
                    ("relogio", e["classe_janela"] == "parcial"),
                    ("volume", e["classe_entrega"] == "parcial")) if cond]),
                "fracao_da_janela": e["fracao_da_janela"],
                "horas_na_janela": e["horas_na_janela"],
                "servidos_active": e["servidos"], "servidos_total": e.get("servidos_total"),
                "esperado": e.get("esperado"), "modo_misto": e.get("modo_misto")}
                for e in parciais],
            "vazias": [{"epoch": e["epoch"], "servidos": e["servidos"]} for e in vazias],
            "modo_misto": [{"epoch": e["epoch"], "por_modo": e.get("por_modo")}
                           for e in epochs if e.get("modo_misto")],
            "futuras_n": len(futuras),
            "em_curso": [{"epoch": e["epoch"], "servidos": e["servidos"]}
                         for e in epochs if e["unidade"] == "em_curso"],
            "prereg_previa_epochs": 234,
        },
        "epochs": epochs,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
