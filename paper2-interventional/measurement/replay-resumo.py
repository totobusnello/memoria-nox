#!/usr/bin/env python3
"""
replay-resumo.py — emite as tabelas de REPLAY-OPORTUNIDADE-2026-08-27.md a
partir dos JSON do `replay-oportunidade.mjs`.

Existe pela mesma razão que os outros emissores desta linha: prosa que afirma um
resultado CALCULADO é cache sem invalidação. Nenhum número da nota é digitado —
todos saem daqui, e `--assert-json` trava os que a nota cita.

Uso:
  ./replay-resumo.py --campo c-350-v3.json --campo-estrito c-350.json \\
                     --dose dose-350.json [--assert-json esperado.json]
"""
import argparse
import json
import sys


def carrega(p):
    with open(p) as f:
        return json.load(f)


def tab_campo(d, rotulo):
    c = d["campo"]
    det = c["detalhe"]
    ok = [x for x in det if not x.get("erro")]
    inventado = [x for x in ok if (x.get("churn") or 0) > 0 and x["producao"]["churn"] == 0]
    perdido = [x for x in ok if (x.get("churn") or 0) == 0 and x["producao"]["churn"] > 0]
    prod_churn = sum(x["producao"]["churn"] for x in ok)
    rep_churn = sum(x.get("churn") or 0 for x in ok)
    return {
        "rotulo": rotulo,
        "corte": d["procedencia"].get("corte_serve_state"),
        "briefs_no_log": c["briefs_no_log"],
        "replayados": len(ok),
        "nao_localizados": c["erros"],
        "bate_controle": c.get("bate_controle"),
        "bate_churn": c["bate_churn"],
        "bate_entra": c["bate_entra"],
        "churn_producao": prod_churn,
        "churn_replay": rep_churn,
        "inventado": len(inventado),
        "perdido": len(perdido),
    }


def tab_dose(d):
    t = d["dose"]["tabela"]
    return {
        "estados": d["dose"]["estados"],
        "linhas": [
            {
                "w": r["w"],
                "estados": r["estados"],
                "mexeu": r["mexeu"],
                "churn_total": r["churn_total"],
                "boosts": r["boosts"],
            }
            for r in t
        ],
        "controle_positivo": d["dose"]["controle_positivo"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campo")
    ap.add_argument("--campo-estrito")
    ap.add_argument("--dose")
    ap.add_argument("--assert-json")
    a = ap.parse_args()

    out = {"campo": [], "dose": None}
    if a.campo:
        out["campo"].append(tab_campo(carrega(a.campo), "rowid"))
    if a.campo_estrito:
        out["campo"].append(tab_campo(carrega(a.campo_estrito), "estrito"))
    if a.dose:
        out["dose"] = tab_dose(carrega(a.dose))

    print(json.dumps(out, indent=2, ensure_ascii=False))

    if a.assert_json:
        esp = carrega(a.assert_json)
        falhas = []

        def confere(caminho, obtido, esperado):
            if obtido != esperado:
                falhas.append(f"{caminho}: obtido {obtido!r} != declarado {esperado!r}")

        for e in esp.get("campo", []):
            obs = next((x for x in out["campo"] if x["rotulo"] == e["rotulo"]), None)
            if obs is None:
                falhas.append(f"campo[{e['rotulo']}] ausente na rodada")
                continue
            for k, v in e.items():
                if k != "rotulo":
                    confere(f"campo[{e['rotulo']}].{k}", obs.get(k), v)
        if "dose" in esp and esp["dose"] is not None:
            if out["dose"] is None:
                falhas.append("dose ausente na rodada")
            else:
                for k, v in esp["dose"].items():
                    if k == "linhas":
                        obs = {r["w"]: r for r in out["dose"]["linhas"]}
                        for lin in v:
                            o = obs.get(lin["w"])
                            if o is None:
                                falhas.append(f"dose w={lin['w']} ausente")
                                continue
                            for kk, vv in lin.items():
                                confere(f"dose[w={lin['w']}].{kk}", o.get(kk), vv)
                    else:
                        confere(f"dose.{k}", out["dose"].get(k), v)

        if falhas:
            print("\n⛔ ASSERÇÃO FALHOU — a nota afirma número que a rodada não produz:",
                  file=sys.stderr)
            for f in falhas:
                print(f"   {f}", file=sys.stderr)
            sys.exit(1)
        print("\n✅ todos os números declarados batem com a rodada", file=sys.stderr)


if __name__ == "__main__":
    main()
