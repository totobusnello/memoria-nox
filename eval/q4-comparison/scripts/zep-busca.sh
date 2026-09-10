#!/bin/bash
# Fase de busca do Zep. Guardas ORDENADOS POR DANO, não por conveniência.
set -uo pipefail
cd /root/q4-everos

# ── 1) DANO MAIOR: índice incompleto ⇒ o nDCG mede o embedder, não o retrieval ──
# `fecho` da ingestão NÃO responde isto: o embedding é assíncrono e o recibo de
# 19:46 fechou com `indice_pronto: false` e 962 de 6.830 vetores.
CENSO=$(docker exec q4-postgres psql -U zep -d zep -tAc \
  "SELECT (SELECT count(*) FROM message)||' '||(SELECT count(*) FROM message_embedding);" 2>/dev/null)
MSG=${CENSO%% *}; EMB=${CENSO##* }
if [ -z "${MSG:-}" ] || [ "${MSG:-0}" -eq 0 ]; then
  echo "🔴 nao consegui medir o censo do Zep — NAO meço às cegas"; exit 3
fi
if [ "$EMB" -lt "$MSG" ]; then
  echo "🔴 indice INCOMPLETO: EMB=$EMB de MSG=$MSG. Buscar agora mede o embedder."; exit 3
fi
echo "✔ indice pronto: EMB=$EMB de MSG=$MSG"

# ── 2) a ingestão do Zep ainda corre? ──────────────────────────────────────────
# ⚠️ NAO usar `pgrep -f zep-corrida`: o literal aparece na própria linha de quem
# invoca o pgrep, logo ele casa consigo mesmo (medido 2026-09-10).
# ⚠️ `-t=NOME` com SINAL DE IGUAL, e a razao e' um defeito medido em 2026-09-10.
# `tmux has-session -t zep` casa POR PREFIXO e portanto casa a sessao `zep-busca`
# -- que e' a propria sessao que executa este guarda. Provado: uma sessao
# `alvo-teste-sufixo` faz `has-session -t alvo-teste` devolver verdadeiro, e
# `-t=alvo-teste` devolver falso; controle positivo com o nome exato passa.
#
# Isto e' o auto-casamento do `pgrep -f` outra vez, por outro mecanismo -- e eu
# troquei um pelo outro justamente por acreditar que este nao podia casar consigo.
# O predicado nao pode ser satisfeito pelo proprio observador.
if tmux has-session -t=zep 2>/dev/null; then
  echo "🔴 a ingestao do Zep ainda corre (tmux 'zep' vivo)"; exit 3
fi

# ── 3) credencial (inócua se faltar: nada roda) ────────────────────────────────
[ -f /root/q4-zep/.env ] || { echo "🔴 falta /root/q4-zep/.env"; exit 2; }
set -a; . /root/q4-zep/.env; set +a
[ -n "${OPENAI_API_KEY:-}" ] || { echo "🔴 OPENAI_API_KEY vazia"; exit 2; }

export ZEP_API_URL="http://127.0.0.1:8000"
# 96 workers: MEDIDO 2026-09-10 — 16→11,92s | 48→4,16s | 96→3,39s | 192→10,86s
# com "Bad file descriptor". Acima de ~96 o servidor degrada E perde sessões.
export NOX_ZEP_SEARCH_WORKERS=96
export ZEP_MAX_ERRO_SESSAO=0.01

K=${K:-10}
QUERIES=${QUERIES:-cache/queries-rc4-all.jsonl}
SAIDA=${SAIDA:-out/zep-busca}
mkdir -p "$SAIDA"
echo "→ 2.482 queries, k=$K, 96 workers, ~3,4 s/query ⇒ ~2,3 h"
exec .venv-zep/bin/python -u runner.py --systems zep --queries-file "$QUERIES" \
  --skip-ingest --k "$K" --output "$SAIDA"
