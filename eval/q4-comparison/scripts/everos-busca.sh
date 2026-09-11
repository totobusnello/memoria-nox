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
# Uso (no host do benchmark do Q4; endereco fora do git, ver $NOX_Q4_HOST):
#     cd /root/q4-everos && bash scripts/everos-busca.sh
set -uo pipefail

RAIZ="${EVEROS_EVAL_ROOT:-/var/lib/everos-q4}"
QUERIES="${QUERIES:-cache/queries-rc4-all.jsonl}"
# ⚠️ `out/everos-busca`, nao `out/busca`: o vigia e o classificador observam
# este caminho. Artefato num caminho que ninguem observa le-se como AUSENTE.
SAIDA="${SAIDA:-out/everos-busca}"
K="${K:-10}"

# ⚠️ ORDEM: este guarda vem DEPOIS da credencial por acidente na 1a versao, e o
# teste no host do benchmark saiu `exit=2` na credencial sem NUNCA exercitar este guarda --
# terceira vez hoje que uma perna que decide primeiro esconde a de tras. Mas a
# ordem correta e' por DANO: credencial ausente e' inocua e o script apenas nao
# roda; migracao de schema sobre uma ingestao viva estraga horas de corrida paga.
# Logo o guarda de dano vem primeiro, e a credencial depois.
#
# guarda: a ingestao ainda corre?
#
# ⚠️ NAO usar `pgrep -f everos-corrida`. Medido 2026-09-10: o literal aparece na
# propria linha de comando de quem invoca o pgrep, logo ele casa consigo mesmo e a
# contagem nunca chega a zero -- o guarda ficaria PERMANENTEMENTE mordendo aqui, e
# no vigia a perna simetrica (detectar morte) nunca poderia disparar. Mesma classe
# da regra 9: predicado que nao alcanca o estado que devia detectar.
#
# Duas pernas que nao podem casar consigo: a sessao tmux, e o mtime do ledger
# (progresso pega tambem o caso "vivo mas travado", que o pgrep nao ve).
# ⚠️ `-t=NOME` com SINAL DE IGUAL, e a razao e' um defeito medido em 2026-09-10.
# `tmux has-session -t zep` casa POR PREFIXO e portanto casa a sessao `zep-busca`
# -- que e' a propria sessao que executa este guarda. Provado: uma sessao
# `alvo-teste-sufixo` faz `has-session -t alvo-teste` devolver verdadeiro, e
# `-t=alvo-teste` devolver falso; controle positivo com o nome exato passa.
#
# Isto e' o auto-casamento do `pgrep -f` outra vez, por outro mecanismo -- e eu
# troquei um pelo outro justamente por acreditar que este nao podia casar consigo.
# O predicado nao pode ser satisfeito pelo proprio observador.
if tmux has-session -t=everos 2>/dev/null; then
  echo "🔴 a ingestao AINDA CORRE (sessao tmux 'everos' viva). Abortando para nao"
  echo "   rodar migracao de schema por cima dela. Esperar o fecho."
  exit 3
fi
LEDGER=out/corrida/ledger-criados.txt
if [ -f "$LEDGER" ]; then
  IDADE=$(( $(date +%s) - $(stat -c %Y "$LEDGER" 2>/dev/null || echo 0) ))
  if [ "$IDADE" -lt 120 ]; then
    echo "🔴 o ledger foi escrito ha ${IDADE}s — a ingestao esta' ativa. Abortando."
    exit 3
  fi
fi

[ -f ~/.deepinfra.env ] || { echo "FALTA ~/.deepinfra.env (DEEPINFRA_API_KEY)"; exit 2; }
set -a; . ~/.deepinfra.env; [ -f ./.env ] && . ./.env; set +a
: "${GEMINI_API_KEY:?GEMINI_API_KEY ausente}"
: "${DEEPINFRA_API_KEY:?DEEPINFRA_API_KEY ausente}"

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
exec .venv/bin/python -u runner.py \
  --systems evermind \
  --queries-file "$QUERIES" \
  --skip-ingest \
  --k "$K" \
  --output "$SAIDA"
