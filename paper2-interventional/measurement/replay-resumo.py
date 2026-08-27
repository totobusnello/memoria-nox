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


def tab_limiar(d):
    """w_min por estado a partir de um JSON em forma de `dose` com grid fino."""
    import collections
    por = collections.defaultdict(dict)
    erros = 0
    for x in d["dose"]["detalhe"]:
        if x.get("erro"):
            erros += 1
            continue
        por[x["ts"]][x["w"]] = x["churn"]
    ws = sorted({w for m in por.values() for w in m})
    naomono = 0
    wmins = []
    for m in por.values():
        seq = [m.get(w, 0) for w in ws]
        if any(seq[i] > seq[i + 1] for i in range(len(seq) - 1)):
            naomono += 1
        wm = next((w for w in ws if (m.get(w) or 0) > 0), None)
        wmins.append(wm)
    tem = sorted(w for w in wmins if w is not None)
    return {
        "estados": len(por),
        "erros": erros,
        "doses": len(ws),
        "grid_min": ws[0],
        "grid_max": ws[-1],
        "nao_monotonos": naomono,
        "sem_limiar_no_grid": sum(1 for w in wmins if w is None),
        "w_min_min": tem[0] if tem else None,
        "w_min_p50": tem[len(tem) // 2] if tem else None,
        "w_min_max": tem[-1] if tem else None,
    }


def tab_gaps(d):
    g = d["gaps"]
    return {
        "t_ref": g["t_ref"],
        "global_todos": {k: g["sub_pool_global"]["todos_os_pares"][k]
                         for k in ("pool", "estratos", "pares_no_estrato", "zeros",
                                   "positivos", "gap_max")},
        "global_so_estudo": {k: g["sub_pool_global"]["so_pares_com_chunk_do_estudo"][k]
                             for k in ("pool", "estratos", "pares_no_estrato", "zeros",
                                       "positivos", "gap_max")},
        "agentes_com_pool_vazio": [a for a, v in g["sub_pool_agente"].items()
                                   if v["todos_os_pares"]["pool"] == 0],
        "passo_adjacente_cota_a_distancia":
            g["calibracao_do_item_7"]["passo_adjacente_cota_a_distancia"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campo")
    ap.add_argument("--campo-estrito")
    ap.add_argument("--dose")
    ap.add_argument("--limiar")
    ap.add_argument("--gaps")
    ap.add_argument("--assert-json")
    a = ap.parse_args()

    out = {"campo": [], "dose": None, "limiar": None, "gaps": None}
    if a.campo:
        out["campo"].append(tab_campo(carrega(a.campo), "rowid"))
    if a.campo_estrito:
        out["campo"].append(tab_campo(carrega(a.campo_estrito), "estrito"))
    if a.dose:
        out["dose"] = tab_dose(carrega(a.dose))
    if a.limiar:
        out["limiar"] = tab_limiar(carrega(a.limiar))
    if a.gaps:
        out["gaps"] = tab_gaps(carrega(a.gaps))

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

        for sec in ("limiar", "gaps"):
            if esp.get(sec) is None:
                continue
            if out[sec] is None:
                falhas.append(f"{sec} ausente na rodada")
                continue
            def desce(caminho, e, o):
                if isinstance(e, dict):
                    for k, v in e.items():
                        desce(f"{caminho}.{k}", v, (o or {}).get(k))
                else:
                    confere(caminho, o, e)
            desce(sec, esp[sec], out[sec])

        if falhas:
            print("\n⛔ ASSERÇÃO FALHOU — a nota afirma número que a rodada não produz:",
                  file=sys.stderr)
            for f in falhas:
                print(f"   {f}", file=sys.stderr)
            sys.exit(1)
        print("\n✅ todos os números declarados batem com a rodada", file=sys.stderr)


if __name__ == "__main__":
    main()
