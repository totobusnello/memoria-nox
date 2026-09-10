#!/bin/bash
# Fase de BUSCA do EverOS — roda DEPOIS da ingestao fechar.
#
# ⚠️ PAGA em dois provedores: embedding da query (Gemini) + rerank (DeepInfra,
# `Qwen/Qwen3-Reranker-4B`). A ingestao NAO e' refeita: `--skip-ingest` obriga
# o runner a reusar o indice ja' construido.
#
# ESCOLHA DE CONFIGURACAO, decidida pelo Toto em 2026-09-10 (opcao A do spike):
# reranker de FABRICA do EverOS, na DeepInfra. Mede o EverOS como ele e' entregue,
# que e' o principio ja' escrito neste harness ("each system uses native
# defaults"). Sob defaults nativos o EverOS tem rerank e o nox-mem NAO tem (o
# cross-encoder dele e' opt-in e os numeros canonicos sao sem ele) -- a assimetria
# e' diferenca de pipeline A DECLARAR, nao a esconder.
#
# ⚠️ NAO rodar isto enquanto a ingestao corre. O `setup()` do adapter chama
# `ensure_business_indexes()`, que e' MIGRACAO DE SCHEMA, e o upstream avisa que
# mexer no conjunto de tabelas e' invisivel para handles em cache (ha' um OME
# lock). Um segundo processo sobre a mesma raiz pode estragar a corrida paga.
#
# Uso (na kvm8):
#     cd /root/q4-everos && bash scripts/everos-busca.sh
set -uo pipefail

RAIZ="${EVEROS_EVAL_ROOT:-/var/lib/everos-q4}"
QUERIES="${QUERIES:-cache/queries-rc4-all.jsonl}"
SAIDA="${SAIDA:-out/busca}"
K="${K:-10}"

[ -f ~/.deepinfra.env ] || { echo "FALTA ~/.deepinfra.env (DEEPINFRA_API_KEY)"; exit 2; }
set -a; . ~/.deepinfra.env; [ -f ./.env ] && . ./.env; set +a
: "${GEMINI_API_KEY:?GEMINI_API_KEY ausente}"
: "${DEEPINFRA_API_KEY:?DEEPINFRA_API_KEY ausente}"

# guarda: a ingestao ainda corre?
if pgrep -f everos-corrida >/dev/null 2>&1; then
  echo "🔴 a ingestao AINDA CORRE (everos-corrida vivo). Abortando para nao"
  echo "   rodar migracao de schema por cima dela. Esperar o fecho."
  exit 3
fi

BASE=https://generativelanguage.googleapis.com/v1beta/openai/
export EVEROS_ROOT="$RAIZ" EVEROS_EVAL_ROOT="$RAIZ"
export EVEROS_LLM__MODEL="${EVEROS_LLM__MODEL:-gemini-2.5-flash-lite}"
export EVEROS_LLM__API_KEY="$GEMINI_API_KEY" EVEROS_LLM__BASE_URL="$BASE"
export EVEROS_EMBEDDING__MODEL=gemini-embedding-001
export EVEROS_EMBEDDING__API_KEY="$GEMINI_API_KEY" EVEROS_EMBEDDING__BASE_URL="$BASE"
export EVEROS_EMBEDDING__DIMENSIONS=3072
export EVEROS_RERANK__PROVIDER=deepinfra
export EVEROS_RERANK__MODEL="Qwen/Qwen3-Reranker-4B"
export EVEROS_RERANK__BASE_URL="https://api.deepinfra.com/v1/inference"
export EVEROS_RERANK__API_KEY="$DEEPINFRA_API_KEY"

echo "raiz=$RAIZ  queries=$QUERIES  k=$K  saida=$SAIDA"
echo "documentos no indice: $(sqlite3 -readonly "$RAIZ/.index/sqlite/system.db" \
  'SELECT COUNT(*) FROM knowledge_documents;' 2>/dev/null || echo '?')"

mkdir -p "$SAIDA"
exec .venv/bin/python runner.py \
  --systems evermind \
  --queries-file "$QUERIES" \
  --skip-ingest \
  --k "$K" \
  --output "$SAIDA"
