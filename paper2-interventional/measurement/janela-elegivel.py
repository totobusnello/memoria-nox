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

⇒ Elegíveis INTEIROS: 2026-09-02 … 2026-09-19. Os dois parciais ficam registrados
separadamente em vez de arredondados para dentro ou para fora: um epoch de exposição
MISTA (alvo alcançável em parte dele) não é o mesmo objeto que um epoch de exposição
uniforme, e fundir os dois é a família do "número certo com população errada".
"""
import json
from datetime import datetime, timedelta, timezone

U = timezone.utc
ACTIVE_EM = datetime(2026, 9, 1, 10, 37, 1, 943000, tzinfo=U)   # 1a linha p2_outcome active
CRIADOS_EM = datetime(2026, 8, 21, 22, 51, 23, tzinfo=U)        # created_at dos 19, idêntico
JANELA_D = 30                                                    # freshGlobalMaxAgeDays
EXPIRA_EM = CRIADOS_EM + timedelta(days=JANELA_D)
FRONTEIRA_H = 9                                                  # epochs viram às 09:00Z


def epoch_de(dia: datetime) -> tuple[datetime, datetime]:
    ini = dia.replace(hour=FRONTEIRA_H, minute=0, second=0, microsecond=0)
    return ini, ini + timedelta(days=1)


def classifica(ini: datetime, fim: datetime) -> dict:
    """Fração do epoch em que a dose foi servida E o alvo era alcançável."""
    de = max(ini, ACTIVE_EM)
    ate = min(fim, EXPIRA_EM)
    exposto_s = max(0.0, (ate - de).total_seconds())
    total_s = (fim - ini).total_seconds()
    frac = exposto_s / total_s
    if frac == 0.0:
        classe = "fora"
    elif frac >= 1.0:
        classe = "inteiro"
    else:
        classe = "parcial"
    return {"fracao_exposta": round(frac, 6), "classe": classe,
            "exposto_h": round(exposto_s / 3600, 2)}


def main() -> None:
    primeiro = ACTIVE_EM.replace(hour=FRONTEIRA_H, minute=0, second=0, microsecond=0)
    if primeiro > ACTIVE_EM:
        primeiro -= timedelta(days=1)
    epochs, dia = [], primeiro
    while dia <= EXPIRA_EM:
        ini, fim = epoch_de(dia)
        c = classifica(ini, fim)
        epochs.append({"epoch": ini.date().isoformat(), "inicio": ini.isoformat(),
                       "fim": fim.isoformat(), **c})
        dia += timedelta(days=1)

    inteiros = [e for e in epochs if e["classe"] == "inteiro"]
    parciais = [e for e in epochs if e["classe"] == "parcial"]
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
        "janela_elegivel": {
            "inteiros_n": len(inteiros),
            "inteiros_de": inteiros[0]["epoch"] if inteiros else None,
            "inteiros_ate": inteiros[-1]["epoch"] if inteiros else None,
            "parciais": [{"epoch": e["epoch"], "fracao_exposta": e["fracao_exposta"],
                          "exposto_h": e["exposto_h"]} for e in parciais],
            "prereg_previa_epochs": 234,
        },
        "epochs": epochs,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
