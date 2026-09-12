#!/usr/bin/env python3
"""Manifesto do lastro que o manuscrito cita e o git NAO versiona.

## O problema que este script existe para resolver

O `.gitignore` de `eval/q4-comparison/output/` diz `*.json`, com o comentario
"too large to commit". Na pratica, **nove** outputs foram versionados a forca --
exatamente os que o manuscrito cita. Os da corrida `rc4` ficaram fora, e o
§6.3.2 cita tres deles NOMINALMENTE como a fonte de numeros publicados. Eles
existem so no disco desta maquina, sem copia.

Nao da para versionar os bytes: sao ~520 MB, o repositorio e publico, e o proprio
manuscrito declara de proposito que os per-query outputs nao sao distribuidos.
A estrutura dos artefatos permite um recorte: cada `.json` e `{meta, queries}`,
onde `meta` tem 9 chaves e ~4 KB, e `queries` carrega os 2.482 per-query.

⇒ Este manifesto versiona o **meta**, o **sha256** e a **medicao que o paper cita**.
Os bytes grandes ficam fora. A integridade passa a ser verificavel sem publicar
per-query nem conteudo de corpus.

## O que o manifesto prova, e o que NAO prova

| prova | nao prova |
|---|---|
| que o arquivo no disco hoje e byte-a-byte o que foi medido | que ele existe em outro lugar -- manifesto **nao e backup** |
| que a medicao citada foi extraida deste artefato | que a corrida estava correta |
| **ausencia**: sai `!=0` quando um artefato citado desaparece | que o que sobrou nao mudou de significado |
| que a sonda de contagem nao alterou os bytes (hash reconferido depois) | que existe copia fora desta maquina |

Um manifesto e um detector de perda, nao um remedio. O backup e decisao do dono.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# caminho -> (secao que cita, o que o paper mede nele)
LASTRO = {
    "eval/q4-comparison/output/rc4/mem0.json": (
        "§6.3.2 confound (a)", "meta.version = 'mem0ai==0.1.114' (pin, nao leitura de runtime)"),
    "eval/q4-comparison/output/rc4/nox_mem.json": (
        "§6.3.2", "nDCG@10 = 0,5013 sobre n=2.482"),
    "eval/q4-comparison/output/rc4-ablation/mem0.json": (
        "§6.3.2 ablacao", "baseline Mem0 = 0,4337"),
    "eval/q4-comparison/output/rc4-ablation/nox_mem.json": (
        "§6.3.2 ablacao", "nDCG@10 generico = 0,4979 (-0,34 pp)"),
    "eval/q4-comparison/cache/rc4-nox-hybrid.db": (
        "§6.3.2 confound (e)", "eval_chunks = 6.822 (INSERT OR IGNORE colapsou 8 pares)"),
    "eval/q4-comparison/cache/rc4-nox-generic.db": (
        "§6.3.2 ablacao", "corpus da corrida de task-type generico"),
    "eval/q4-comparison/.mem0-chroma-rc4/chroma.sqlite3": (
        "§6.3.2 confound (e)", "embeddings = 6.830, com 6.822 chunk_id distintos"),
    # ⚠️ O sqlite do Chroma NAO e o vector store inteiro: os vetores vivem em
    # arquivos HNSW binarios num subdiretorio por colecao. Uma primeira versao
    # deste manifesto listava so o sqlite -- era manifesto de METADE do artefato,
    # e uma voz adversarial apontou a falta antes de a perda acontecer.
    "eval/q4-comparison/.mem0-chroma-rc4/"
    "5cf0506f-0f17-4dd4-8964-ea1faaaaa5c9/data_level0.bin": (
        "§6.3.2 confound (e)", "os vetores HNSW propriamente ditos (73 MB)"),
    "eval/q4-comparison/.mem0-chroma-rc4/"
    "5cf0506f-0f17-4dd4-8964-ea1faaaaa5c9/length.bin": (
        "§6.3.2 confound (e)", "comprimentos do indice HNSW"),
    "eval/q4-comparison/.mem0-chroma-rc4/"
    "5cf0506f-0f17-4dd4-8964-ea1faaaaa5c9/header.bin": (
        "§6.3.2 confound (e)", "cabecalho do indice HNSW"),
    "eval/q4-comparison/.mem0-chroma-rc4/"
    "5cf0506f-0f17-4dd4-8964-ea1faaaaa5c9/link_lists.bin": (
        "§6.3.2 confound (e)", "listas de ligacao do HNSW"),
    "eval/q4-comparison/.mem0-chroma-rc4/"
    "5cf0506f-0f17-4dd4-8964-ea1faaaaa5c9/index_metadata.pickle": (
        "§6.3.2 confound (e)", "metadados do indice HNSW"),
}

# Sidecars do SQLite. O hash do arquivo principal sozinho e de um estado que pode
# estar incompleto -- o que esta no `-wal` ainda nao foi aplicado. Entram no
# manifesto quando existem.
SIDECARS = ("-wal", "-shm")

# medicoes que o paper cita e que este script RECOMPUTA do artefato
def conta_sqlite(caminho, sql):
    """Conta numa COPIA em /var/tmp, nunca no artefato.

    Abrir um SQLite -- ainda que `mode=ro` -- pode disparar checkpoint do WAL e
    MUDAR os bytes, logo mudar o sha256 que este mesmo manifesto acabou de
    registrar. Sondar escreveria o estado que mede. A copia isola isso; e fica em
    /var/tmp e nao em /tmp de proposito.
    """
    tmp = tempfile.mkdtemp(prefix="manifesto-lastro-", dir="/var/tmp")
    try:
        copia = os.path.join(tmp, os.path.basename(caminho))
        shutil.copy2(caminho, copia)
        for suf in SIDECARS:
            if os.path.exists(caminho + suf):
                shutil.copy2(caminho + suf, copia + suf)
        con = sqlite3.connect(f"file:{copia}?mode=ro", uri=True)
        try:
            return con.execute(sql).fetchone()[0]
        finally:
            con.close()
    except (sqlite3.Error, OSError) as e:
        return f"erro: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

RECOMPUTA = {
    "eval/q4-comparison/cache/rc4-nox-hybrid.db":
        [("eval_chunks", "SELECT COUNT(*) FROM eval_chunks")],
    "eval/q4-comparison/.mem0-chroma-rc4/chroma.sqlite3": [
        ("embeddings", "SELECT COUNT(*) FROM embeddings"),
        # a segunda metade da afirmacao do §6.3.2: 6.830 linhas, 6.822 ids distintos
        ("chunk_id_distintos",
         "SELECT COUNT(DISTINCT string_value) FROM embedding_metadata "
         "WHERE key='chunk_id'"),
    ],
}


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main():
    ausentes, entradas = [], {}
    for rel, (secao, mede) in sorted(LASTRO.items()):
        abs_ = os.path.join(RAIZ, rel)
        if not os.path.exists(abs_):
            ausentes.append(rel)
            entradas[rel] = {"secao": secao, "mede": mede, "estado": "AUSENTE"}
            continue
        st = os.stat(abs_)
        e = {
            "secao": secao,
            "mede": mede,
            "estado": "presente",
            "bytes": st.st_size,
            "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256": sha256(abs_),
        }
        if rel.endswith(".json"):
            with open(abs_, encoding="utf-8") as fh:
                d = json.load(fh)
            e["meta"] = d.get("meta")
            e["n_queries_no_artefato"] = len(d.get("queries", []))
        for suf in SIDECARS:
            if os.path.exists(abs_ + suf):
                e.setdefault("sidecars", {})[suf] = {
                    "bytes": os.path.getsize(abs_ + suf),
                    "sha256": sha256(abs_ + suf),
                }
        for nome, sql in RECOMPUTA.get(rel, []):
            e.setdefault("recomputado", {})[nome] = conta_sqlite(abs_, sql)
        e["sha256_reconferido_apos_sonda"] = sha256(abs_)
        e["sonda_alterou_os_bytes"] = e["sha256_reconferido_apos_sonda"] != e["sha256"]
        entradas[rel] = e

    saida = {
        "_o_que_e": "manifesto do lastro citado pelo manuscrito e nao versionado; "
                    "prova integridade, NAO e backup",
        "_gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_gerado_por": "scripts/manifesto-lastro.py",
        "artefatos": entradas,
    }
    dest = os.path.join(RAIZ, "eval/q4-comparison/MANIFESTO-LASTRO.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    presentes = len(LASTRO) - len(ausentes)
    total_mb = sum(e.get("bytes", 0) for e in entradas.values()) / 1e6
    print(f"manifesto: {dest}")
    print(f"artefatos citados: {len(LASTRO)}  presentes: {presentes}  "
          f"ausentes: {len(ausentes)}  ({total_mb:.1f} MB fora do git)")
    for rel, e in sorted(entradas.items()):
        if e["estado"] == "presente":
            extra = ""
            if "recomputado" in e:
                extra = "  " + ", ".join(f"{k}={v}" for k, v in e["recomputado"].items())
            print(f"  ok       {e['sha256'][:16]}  {rel}{extra}")
    if ausentes:
        print("\n🔴 LASTRO PERDIDO — o manuscrito cita artefato que nao existe mais:",
              file=sys.stderr)
        for rel in ausentes:
            print(f"   {rel}  ({LASTRO[rel][0]}: {LASTRO[rel][1]})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
