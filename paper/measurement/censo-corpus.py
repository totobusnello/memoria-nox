#!/usr/bin/env python3
"""Censo do corpus do nox-mem, por POPULAÇÃO explícita, datado e reprodutível.

Por que este script existe
--------------------------
O `paper-tecnico-nox-mem.md` cita `~95k chunks` em três lugares e atribui o MESMO
número a duas populações incompatíveis:

  L178   "the **main store** has since grown to ~95k chunks — see Abstract"
  L1280  "~95k chunks **across 7 databases** ... as of 2026-06-04"
  L1328  "94,936 chunks (as of 2026-06-04)"   <- não diz qual população

As duas primeiras não podem ser ambas verdadeiras. E a terceira, que é a única com
data, não nomeia a população — logo não é conferível nem hoje nem depois. É a classe
"número certo carregado por frase errada": o erro não está no número, está na
atribuição, e por isso releitura não pega.

⚠️ E o defeito é auto-perpetuante: L178 manda "see Abstract", e o Abstract não tem
contagem de corpus nenhuma. Ponteiro para lugar sem o dado é pior que número solto,
porque parece ter lastro.

O que este censo estabelece
---------------------------
Duas populações, medidas na mesma corrida, nomeadas, com data e artefato:

  main_store  = o banco que a API serve (`/api/health.vectorCoverage.total`)
  soma_dos_7  = main + os 6 bancos por agente

⚠️ "7 bancos" precisa de definição operacional, porque `find` acha 13 arquivos
`nox-mem.db` na VPS. Seis não têm tabela `chunks` (legados, o mais antigo de
2026-04-01) e são excluídos POR MEDIÇÃO, não por lista: o script tenta contar e
registra a falha. Excluir por lista embutida seria a lista envelhecendo em silêncio.

READ-ONLY: `mode=ro` em todos os bancos.
"""
import argparse, json, os, sqlite3, subprocess, sys, datetime as dt

def conta(caminho):
    """(n, erro). Não distingue 'vazio' de 'sem tabela' pelo nome — pergunta ao banco."""
    try:
        db = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
        n = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        db.close()
        return n, None
    except Exception as e:
        return None, str(e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default="/root/.openclaw")
    ap.add_argument("--main", default="/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
    ap.add_argument("--api", default="http://127.0.0.1:18802/api/health")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rec = {
        "instrumento": "censo-corpus", "versao": 1,
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raiz": a.raiz, "main_path": a.main,
    }

    # ── varredura: TODO nox-mem.db fora de backups, contado ou recusado com o motivo ──
    achados = []
    for base, _dirs, arqs in os.walk(a.raiz):
        if "/backups/" in base + "/":
            continue
        if "nox-mem.db" in arqs:
            p = os.path.join(base, "nox-mem.db")
            n, err = conta(p)
            achados.append({"path": p, "chunks": n, "erro": err,
                            "mtime": dt.datetime.fromtimestamp(os.path.getmtime(p), dt.timezone.utc)
                                       .strftime("%Y-%m-%dT%H:%M:%SZ")})
    achados.sort(key=lambda x: (-(x["chunks"] or -1), x["path"]))
    rec["arquivos_examinados"] = len(achados)          # <- contador: sem ele, "0 achados" é ambíguo
    rec["com_tabela_chunks"] = sum(1 for x in achados if x["chunks"] is not None)
    rec["sem_tabela_chunks"] = sum(1 for x in achados if x["chunks"] is None)
    rec["arquivos"] = achados

    vivos = [x for x in achados if x["chunks"] is not None]
    mains = [x for x in vivos if os.path.realpath(x["path"]) == os.path.realpath(a.main)]
    if len(mains) != 1:
        rec.update(veredito="RED", motivo=f"main-store-nao-identificado (casou {len(mains)})")
        return emitir(rec, a.out)

    rec["main_store"] = mains[0]["chunks"]
    agentes = [x for x in vivos if x is not mains[0]]
    rec["agentes"] = {os.path.basename(os.path.dirname(os.path.dirname(
                        os.path.dirname(x["path"])))): x["chunks"] for x in agentes}
    rec["n_agentes"] = len(agentes)
    rec["soma_dos_7"] = rec["main_store"] + sum(x["chunks"] for x in agentes)
    rec["bancos_somados"] = 1 + len(agentes)

    # ── entity files: DUAS populações outra vez, e a razão medida, não modelada ──
    # O paper dizia "769 entity files x 3 sections ~ 2.307 boost-bearing chunks" e, 63
    # linhas antes, "184 of 184 eligible entity files" — contradição INTERNA. E "entity
    # file" tem duas populações: o que existe no disco e o que está representado no
    # banco. Elas divergem porque arquivo apagado do disco deixa os chunks no store.
    # A razão seções/arquivo também é medida: o formato sugere 3 (frontmatter +
    # compiled + timeline), mas timeline é 1..N, então a média real não é 3.
    try:
        db = sqlite3.connect(f"file:{a.main}?mode=ro", uri=True)
        secs = dict(db.execute(
            "SELECT COALESCE(section,'(NULL)'), COUNT(*) FROM chunks GROUP BY 1").fetchall())
        arqs_db = db.execute(
            "SELECT COUNT(DISTINCT source_file) FROM chunks WHERE section IS NOT NULL"
        ).fetchone()[0]
        db.close()
        com_section = sum(v for k, v in secs.items() if k != "(NULL)")
        rec["entity"] = {
            "por_section": secs,
            "chunks_com_section": com_section,
            "arquivos_no_banco": arqs_db,
            "secoes_por_arquivo": round(com_section / arqs_db, 2) if arqs_db else None,
        }
        d = os.path.join(a.raiz, "workspace/memory/entities")
        no_disco = sum(len([x for x in arqs if x.endswith(".md")])
                       for _b, _d, arqs in os.walk(d)) if os.path.isdir(d) else None
        rec["entity"]["arquivos_no_disco"] = no_disco
        rec["entity"]["divergencia_disco_banco"] = (
            None if no_disco is None else arqs_db - no_disco)
    except Exception as e:
        rec["entity"] = {"erro": str(e)}

    # ── controle positivo: a API tem de concordar com o main store ──
    # Sem isto, "main_store" é só a contagem de um arquivo que EU escolhi. A API é a
    # segunda via, e é ela que define o que a produção serve.
    try:
        out = subprocess.run(["curl", "-s", "--max-time", "10", a.api],
                             capture_output=True, text=True, timeout=15).stdout
        vc = json.loads(out).get("vectorCoverage", {})
        rec["api_total"] = vc.get("total")
        rec["api_embedded"] = vc.get("embedded")
    except Exception as e:
        rec["api_total"] = None
        rec["api_erro"] = str(e)

    rec["api_concorda_com_main"] = (rec.get("api_total") == rec["main_store"])

    if rec["bancos_somados"] != 7:
        rec.update(veredito="YELLOW",
                   motivo=f"bancos-com-chunks={rec['bancos_somados']}-nao-7")
    elif not rec["api_concorda_com_main"]:
        rec.update(veredito="YELLOW", motivo="api-divergiu-do-main-store")
    else:
        rec.update(veredito="GREEN", motivo="duas-populacoes-medidas-e-nomeadas")
    return emitir(rec, a.out)

def emitir(rec, out):
    print(f'{rec["veredito"]} paper1-censo-corpus motivo={rec["motivo"]} '
          f'main_store={rec.get("main_store")} soma_dos_7={rec.get("soma_dos_7")} '
          f'bancos={rec.get("bancos_somados")} '
          f'entity_chunks={rec.get("entity",{}).get("chunks_com_section")} '
          f'entity_arq_banco={rec.get("entity",{}).get("arquivos_no_banco")} '
          f'entity_arq_disco={rec.get("entity",{}).get("arquivos_no_disco")} '
          f'examinados={rec["arquivos_examinados"]} '
          f'sem_tabela={rec["sem_tabela_chunks"]} api={rec.get("api_total")} ts={rec["ts"]}')
    if out:
        with open(out, "w") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        print(f"artefato={out}")
    print("FIM examinados=%d somados=%d" % (rec["arquivos_examinados"], rec.get("bancos_somados", 0)))

if __name__ == "__main__":
    main()
