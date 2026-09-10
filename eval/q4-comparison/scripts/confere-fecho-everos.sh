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

echo "== 2. retencao: TRES contadores, e so um e' o que a busca ve =="
# 🔴 Medido 2026-09-10 a meio da corrida: ledger 6.654 | dirs 6.652 | sqlite 6.500.
# Tres numeros para "quanto foi ingerido", e divergem por desenho:
#   ledger        = o meu registro de ESCRITA, apos create_document() retornar
#   dirs no disco = os markdown que o extractor escreveu (fica atras do ledger
#                   pelo que esta em voo)
#   sqlite        = o INDICE PESQUISAVEL, atualizado so por sincroniza()
# ⇒ A retencao publicavel e' a do sqlite APOS o sync final. Ler antes dele
# subdeclara -- aqui, por 154 documentos.
SQL=/var/lib/everos-q4/.index/sqlite/system.db
echo "  sqlite knowledge_documents: $(sqlite3 -readonly "$SQL" 'SELECT COUNT(*) FROM knowledge_documents;' 2>/dev/null || echo '?')"
echo "  sqlite knowledge_topics   : $(sqlite3 -readonly "$SQL" 'SELECT COUNT(*) FROM knowledge_topics;' 2>/dev/null || echo '?')"
echo "  dirs de documento no disco: $(find /var/lib/everos-q4/q4eval/default_project/knowledge -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)"
ULT_SYNC=$(grep '"evento": "sync"' "$PROG" 2>/dev/null | tail -1)
echo "  ultimo sync: ${ULT_SYNC:-nenhum}"
case "$ULT_SYNC" in
  *'"final"'*) echo "  ✔ sync FINAL feito — a contagem do sqlite e' a publicavel";;
  *) echo "  🔴 o ultimo sync NAO e' o final: a contagem do sqlite esta ATRASADA e nao e' reportavel";;
esac
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
