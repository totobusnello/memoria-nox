#!/usr/bin/env bash
# re-embed-orphans.sh — Re-embeds chunks que estão sem mapeamento em vec_chunk_map
#
# ⚠️  NÃO RODAR EM PRODUÇÃO SEM APROVAÇÃO EXPLÍCITA DO USUÁRIO ⚠️
#
# Contexto: incident 2026-05-18 — 57 chunks sem embedding por expiração da Gemini API key.
# Docs: docs/incidents/2026-05-18-orphan-embeddings.md
#
# Uso:
#   bash scripts/re-embed-orphans.sh [--dry-run] [--force] [--verbose] [--limit N]
#
# Flags:
#   --dry-run   Lista orphans + estima custo, sem chamar Gemini nem modificar DB
#   --force     Re-embeds mesmo chunks que já têm mapeamento (não recomendado)
#   --verbose   Mostra progresso chunk a chunk
#   --limit N   Processa no máximo N chunks (útil para testar)
#
# Pré-requisitos no VPS:
#   set -a; source /root/.openclaw/.env; set +a
#   (GEMINI_API_KEY deve estar válida — verificar antes de rodar)
#
# Idempotente: chunks que já têm mapeamento em vec_chunk_map são skipped por padrão.
# Seguro para re-run: não modifica chunks existentes.

set -euo pipefail

# ─── Configuração ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Caminho do DB — usa OPENCLAW_WORKSPACE ou default VPS
DB_PATH="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}/tools/nox-mem/nox-mem.db"

# Gemini embedding endpoint
GEMINI_EMBED_MODEL="${NOX_EMBED_MODEL:-gemini-embedding-001}"
GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_EMBED_MODEL}:embedContent"
EMBED_DIMENSIONS=3072
TASK_TYPE="RETRIEVAL_DOCUMENT"

# Custo estimado por chunk (USD, approximado)
COST_PER_CHUNK=0.00005

# ─── Flags ─────────────────────────────────────────────────────────────────────
DRY_RUN=false
FORCE=false
VERBOSE=false
LIMIT=0  # 0 = sem limite

for arg in "$@"; do
  case $arg in
    --dry-run)  DRY_RUN=true ;;
    --force)    FORCE=true ;;
    --verbose)  VERBOSE=true ;;
    --limit=*)  LIMIT="${arg#*=}" ;;
    --limit)    shift; LIMIT="$1" ;;
  esac
done

# ─── Helpers ───────────────────────────────────────────────────────────────────
log()     { echo "[$(date '+%H:%M:%S')] $*"; }
log_ok()  { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
log_err() { echo "[$(date '+%H:%M:%S')] ✗ $*" >&2; }
log_v()   { $VERBOSE && echo "[$(date '+%H:%M:%S')]   $*" || true; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { log_err "Comando '$1' não encontrado. Abortando."; exit 1; }
}

# ─── Validações pré-execução ───────────────────────────────────────────────────
require_cmd sqlite3
require_cmd curl
require_cmd python3
require_cmd jq

if [[ ! -f "$DB_PATH" ]]; then
  log_err "DB não encontrado em: $DB_PATH"
  log_err "Defina OPENCLAW_WORKSPACE ou verifique o path."
  exit 1
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  log_err "GEMINI_API_KEY não definida no ambiente."
  log_err "Execute: set -a; source /root/.openclaw/.env; set +a"
  exit 1
fi

# ─── Consultar orphans ─────────────────────────────────────────────────────────
log "Consultando orphan chunks em: $DB_PATH"

LIMIT_CLAUSE=""
if [[ $LIMIT -gt 0 ]]; then
  LIMIT_CLAUSE="LIMIT $LIMIT"
fi

ORPHANS=$(sqlite3 "$DB_PATH" "
  SELECT c.id, c.chunk_type, c.source_file
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL
  $LIMIT_CLAUSE;
" 2>&1) || {
  log_err "Falha ao consultar DB: $ORPHANS"
  exit 1
}

ORPHAN_COUNT=$(echo "$ORPHANS" | grep -c '|' || echo 0)

if [[ $ORPHAN_COUNT -eq 0 ]]; then
  log_ok "Nenhum orphan encontrado. Cobertura de embeddings está completa."
  exit 0
fi

ESTIMATED_COST=$(python3 -c "print(f'\${${ORPHAN_COUNT} * ${COST_PER_CHUNK}:.4f}')" 2>/dev/null || echo "~\$0.00")

log "Orphans encontrados: $ORPHAN_COUNT chunks"
log "Custo estimado Gemini: $ESTIMATED_COST"

if $DRY_RUN; then
  log ""
  log "── DRY-RUN — nenhuma modificação será feita ──"
  log ""
  log "Chunks que seriam re-embedded (id | chunk_type | source_file):"
  echo "$ORPHANS" | while IFS='|' read -r id ctype srcfile; do
    log "  ID=$id  type=$ctype  file=$srcfile"
  done
  log ""
  log "Para executar: bash $0 --verbose"
  exit 0
fi

# ─── Confirmar execução em produção ────────────────────────────────────────────
if [[ "${NOX_NONINTERACTIVE:-}" != "1" ]]; then
  echo ""
  echo "⚠️  ATENÇÃO: Este script modifica o banco de produção ($DB_PATH)"
  echo "   Orphans a processar: $ORPHAN_COUNT"
  echo "   Custo estimado: $ESTIMATED_COST"
  echo ""
  read -r -p "Confirmar? (yes/no): " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    log "Abortado pelo usuário."
    exit 0
  fi
fi

# ─── Loop de re-embedding ──────────────────────────────────────────────────────
SUCCESS=0
SKIPPED=0
ERRORS=0
ERRORS_DETAIL=""

log "Iniciando re-embedding de $ORPHAN_COUNT chunks..."
log ""

while IFS='|' read -r CHUNK_ID CHUNK_TYPE SOURCE_FILE; do
  [[ -z "$CHUNK_ID" ]] && continue

  log_v "Processando chunk ID=$CHUNK_ID (type=$CHUNK_TYPE, file=$SOURCE_FILE)"

  # Idempotência: verificar se já foi mapeado (pode ter sido adicionado concurrentemente)
  if ! $FORCE; then
    ALREADY_MAPPED=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM vec_chunk_map WHERE chunk_id=$CHUNK_ID;")
    if [[ "$ALREADY_MAPPED" -gt 0 ]]; then
      log_v "ID=$CHUNK_ID já mapeado — skip"
      SKIPPED=$((SKIPPED + 1))
      continue
    fi
  fi

  # Buscar texto do chunk
  CHUNK_TEXT=$(sqlite3 "$DB_PATH" "SELECT chunk_text FROM chunks WHERE id=$CHUNK_ID;" 2>/dev/null)

  if [[ -z "$CHUNK_TEXT" ]]; then
    log_err "ID=$CHUNK_ID — chunk_text vazio ou chunk não encontrado. Skip."
    ERRORS=$((ERRORS + 1))
    ERRORS_DETAIL="${ERRORS_DETAIL}\n  ID=$CHUNK_ID: chunk_text vazio"
    continue
  fi

  # Chamar Gemini Embeddings API
  REQUEST_JSON=$(python3 -c "
import json, sys
text = sys.stdin.read()
payload = {
  'model': 'models/${GEMINI_EMBED_MODEL}',
  'content': {'parts': [{'text': text}]},
  'taskType': '${TASK_TYPE}',
  'outputDimensionality': ${EMBED_DIMENSIONS}
}
print(json.dumps(payload))
" <<< "$CHUNK_TEXT")

  HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Content-Type: application/json" \
    -H "x-goog-api-key: ${GEMINI_API_KEY}" \
    -d "$REQUEST_JSON" \
    "$GEMINI_BASE_URL" 2>/dev/null)

  HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n -1)
  HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n 1)

  if [[ "$HTTP_CODE" != "200" ]]; then
    ERROR_MSG=$(echo "$HTTP_BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',{}).get('message','unknown'))" 2>/dev/null || echo "HTTP $HTTP_CODE")
    log_err "ID=$CHUNK_ID — Gemini API falhou: $ERROR_MSG"
    ERRORS=$((ERRORS + 1))
    ERRORS_DETAIL="${ERRORS_DETAIL}\n  ID=$CHUNK_ID: $ERROR_MSG"
    continue
  fi

  # Extrair vetor da resposta
  EMBEDDING_JSON=$(echo "$HTTP_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
values = d.get('embedding', {}).get('values', [])
if not values:
    print('ERROR: empty embedding')
    sys.exit(1)
print(json.dumps(values))
" 2>/dev/null)

  if [[ $? -ne 0 ]] || [[ "$EMBEDDING_JSON" == "ERROR"* ]]; then
    log_err "ID=$CHUNK_ID — embedding vazio na resposta"
    ERRORS=$((ERRORS + 1))
    ERRORS_DETAIL="${ERRORS_DETAIL}\n  ID=$CHUNK_ID: embedding vazio"
    continue
  fi

  # Inserir no vec_chunks (sqlite-vec) e vec_chunk_map
  # sqlite-vec espera blob serializado como float32 little-endian
  INSERT_RESULT=$(python3 - "$DB_PATH" "$CHUNK_ID" "$EMBED_DIMENSIONS" <<PYEOF
import sys, struct, sqlite3
db_path = sys.argv[1]
chunk_id = int(sys.argv[2])
dims = int(sys.argv[3])
import json
raw = sys.stdin.read().strip()
values = json.loads(raw)
if len(values) != dims:
    print(f"ERROR: expected {dims} dims, got {len(values)}")
    sys.exit(1)
vec_blob = struct.pack(f'{dims}f', *values)
conn = sqlite3.connect(db_path)
conn.enable_load_extension(True)
try:
    conn.load_extension('vec0')
    conn.enable_load_extension(False)
    # Insert into virtual table
    conn.execute("INSERT OR REPLACE INTO vec_chunks(rowid, embedding) VALUES (?, ?)",
                 (chunk_id, vec_blob))
    # Insert mapping
    conn.execute("INSERT OR IGNORE INTO vec_chunk_map(vec_rowid, chunk_id) VALUES (?, ?)",
                 (chunk_id, chunk_id))
    conn.commit()
    print("OK")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    conn.close()
PYEOF
<<< "$EMBEDDING_JSON")

  if [[ "$INSERT_RESULT" != "OK" ]]; then
    log_err "ID=$CHUNK_ID — falha ao inserir no DB: $INSERT_RESULT"
    ERRORS=$((ERRORS + 1))
    ERRORS_DETAIL="${ERRORS_DETAIL}\n  ID=$CHUNK_ID: $INSERT_RESULT"
    continue
  fi

  log_ok "ID=$CHUNK_ID embedded e mapeado"
  SUCCESS=$((SUCCESS + 1))

  # Rate limiting gentil (evitar estouro de quota Gemini)
  sleep 0.1

done <<< "$ORPHANS"

# ─── Relatório final ────────────────────────────────────────────────────────────
log ""
log "══════════════════════════════════════"
log "Re-embedding concluído"
log "  Sucesso:  $SUCCESS"
log "  Skipped:  $SKIPPED (já mapeados)"
log "  Erros:    $ERRORS"
log "══════════════════════════════════════"

if [[ $ERRORS -gt 0 ]]; then
  log ""
  log_err "Detalhes dos erros:"
  printf "%b\n" "$ERRORS_DETAIL"
fi

# Verificação pós-execução
log ""
log "Verificação pós-execução:"
REMAINING=$(sqlite3 "$DB_PATH" "
  SELECT count(*)
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL;
")
log "  Orphans restantes: $REMAINING"

if [[ "$REMAINING" -eq 0 ]]; then
  log_ok "Cobertura de embeddings: 100%"
elif [[ "$REMAINING" -le 5 ]]; then
  log "  Residual mínimo ($REMAINING). Pode ser orphan pré-existente."
else
  log_err "  $REMAINING orphans ainda sem embedding. Revisar erros acima."
fi

log ""
log "Validar via API: curl http://127.0.0.1:18802/api/health | jq .vectorCoverage"
