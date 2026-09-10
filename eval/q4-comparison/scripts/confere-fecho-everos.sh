#!/bin/bash
# Ao fechar a ingestao do EverOS: retencao, falhas COM provenance, e a pergunta
# que decide se a falha entra como ressalva no paper -- algum documento que
# falhou e' GOLD de alguma query?
#
# ⚠️ `falhas: N` sozinho e' inacionavel: nao distingue 4 documentos que nenhuma
# query pede de 4 que sao a resposta de 4 queries. No segundo caso o nDCG cai
# por FALHA DE INGESTAO e sairia publicado como qualidade de retrieval -- mesma
# classe do fan-out degradado do Zep (2026-09-10).
set -uo pipefail
cd /root/q4-everos || exit 1
LEDGER=out/corrida/ledger-criados.txt
PROG=out/corrida/progresso.ndjson

echo "== 1. o fecho ja existe? =="
FECHO=$(grep -E '"evento": "(fecho|deadline)"' "$PROG" | tail -1)
[ -z "$FECHO" ] && { echo "AINDA_SEM_FECHO"; exit 0; }
python3 -c "
import json,sys
f=json.loads(sys.argv[1])
print('  evento     :', f.get('evento'))
print('  tentados   :', f.get('tentados'), '| ok:', f.get('ok'), '| falhas:', f.get('falhas'))
for e in f.get('primeiros_erros') or []:
    print('  FALHA:', e)
" "$FECHO"

echo "== 2. retencao: o que o INDICE tem (nao o que o corpus tinha) =="
python3 - <<'PY'
import json, subprocess
ledger = set()
for l in open("out/corrida/ledger-criados.txt"):
    l = l.strip()
    if l: ledger.add(l.split("\t")[0] if "\t" in l else l)
print(f"  ledger: {len(ledger)} doc_id distintos")
corpus = set()
for f in ("cache/locomo.jsonl", "cache/longmemeval.jsonl"):
    for l in open(f, encoding="utf-8"):
        l = l.strip()
        if l: corpus.add(json.loads(l).get("id") or json.loads(l).get("chunk_id"))
corpus.discard(None)
print(f"  corpus: {len(corpus)} id distintos (de 6.830 linhas)")
faltam = corpus - ledger
print(f"  ⇒ no corpus e NAO no ledger: {len(faltam)}")
if faltam and len(faltam) <= 20:
    print("   ", sorted(faltam))

# 3. algum dos que faltam e' GOLD de alguma query?
gold = {}
for l in open("cache/queries-rc4-all.jsonl", encoding="utf-8"):
    l = l.strip()
    if not l: continue
    r = json.loads(l)
    for g in r.get("gold_chunk_ids") or []:
        gold.setdefault(g, []).append(r.get("question_id"))
atingidas = {g: qs for g, qs in gold.items() if g in faltam}
print(f"== 3. documentos que faltam e sao GOLD: {len(atingidas)} ==")
for g, qs in list(atingidas.items())[:10]:
    print(f"  {g} <- queries {qs[:5]}")
if not atingidas:
    print("  nenhum ⇒ as falhas nao tocam nenhuma query; nao ha ressalva de nDCG")
PY
exit 0
