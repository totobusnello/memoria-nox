#!/usr/bin/env bash
# vps-healthcheck.sh — Detecta IP swaps ou outages na VPS nox-mem cedo
#
# Contexto: incident 2026-05-20 — Hostinger floating-IP rebalance moveu VPS
# de 45.43.85.86 → 187.77.234.79 silenciosamente; recovery levou ~30min.
# Este script roda periodicamente (cron) e alerta se a VPS ficar inacessível.
#
# Cron sugerido (a cada 15 min, alerta visual no Mac):
#   */15 * * * * /Users/lab/Claude/Projetos/memoria-nox/scripts/vps-healthcheck.sh --quiet || /usr/bin/osascript -e 'display notification "VPS unreachable" with title "nox-mem"'
#
# Uso:
#   ./vps-healthcheck.sh [--ip <IP>] [--quiet] [--alert-cmd <CMD>] [--help]
#
# Exit codes:
#   0 — todos os checks passaram
#   1 — ping falhou
#   2 — SSH falhou
#   3 — HTTP API falhou
#
# Dependências: ping, ssh, curl, jq (todos presentes em Mac + Linux por padrão)
#
# PATH normalization: cron environment vem com PATH=/usr/bin:/bin (sem /sbin),
# o que faz `ping` não ser encontrado (Mac: /sbin/ping). Garantimos PATH
# completo aqui pra script funcionar idêntico em terminal e cron.

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

set -euo pipefail

# --------------------------------------------------------------------------- #
# Cores (somente quando TTY)
# --------------------------------------------------------------------------- #
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  RESET='\033[0m'
else
  RED='' GREEN='' YELLOW='' CYAN='' BOLD='' RESET=''
fi

# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
IP_FILE="$REPO_ROOT/.vps-current-ip"

VPS_IP=""
QUIET=0
ALERT_CMD=""

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
log()  { printf "%b\n" "$*"; }
ok()   { log "${GREEN}[OK]${RESET}  $*"; }
warn() { log "${YELLOW}[WARN]${RESET} $*"; }
fail() { log "${RED}[FAIL]${RESET} $*"; }
info() { log "${CYAN}[INFO]${RESET} $*"; }

usage() {
  cat <<EOF
${BOLD}vps-healthcheck.sh${RESET} — detecta IP swaps ou outages na VPS nox-mem

${BOLD}Uso:${RESET}
  $0 [--ip <IP>] [--quiet] [--alert-cmd <CMD>] [--help]

${BOLD}Opções:${RESET}
  --ip <IP>          IP da VPS (padrão: arquivo .vps-current-ip ou env VPS_IP)
  --quiet            Silencioso — output somente em falha (ideal para cron)
  --alert-cmd <CMD>  Comando executado em caso de falha (ex: osascript webhook)
  --help             Exibe esta mensagem

${BOLD}Checks realizados:${RESET}
  1. Ping       — 3 pacotes, timeout 2s por pacote
  2. SSH        — conecta como root e executa 'hostname'
  3. HTTP API   — GET http://<IP>:18802/api/health, valida .vectorCoverage

${BOLD}Exit codes:${RESET}
  0 — sucesso
  1 — ping falhou
  2 — SSH falhou
  3 — API HTTP falhou

${BOLD}Exemplos:${RESET}
  # Teste manual:
  $0 --ip 187.77.234.79

  # Cron a cada 15 min com alerta macOS:
  */15 * * * * $0 --quiet || /usr/bin/osascript -e 'display notification "VPS unreachable" with title "nox-mem"'

  # Com webhook Slack:
  $0 --quiet --alert-cmd 'curl -s -X POST https://hooks.slack.com/... -d "{\"text\":\"VPS down\"}"'
EOF
}

# --------------------------------------------------------------------------- #
# Parse args
# --------------------------------------------------------------------------- #
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip)
      VPS_IP="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    --alert-cmd)
      ALERT_CMD="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      log "${RED}Opção desconhecida: $1${RESET}"
      usage >&2
      exit 1
      ;;
  esac
done

# --------------------------------------------------------------------------- #
# Resolve IP: --ip arg > env VPS_IP > arquivo .vps-current-ip
# --------------------------------------------------------------------------- #
if [[ -z "$VPS_IP" ]]; then
  # printenv lê a env var sem ser afetado pela variável local de mesmo nome
  _env_ip="$(printenv VPS_IP 2>/dev/null || true)"
  if [[ -n "$_env_ip" ]]; then
    VPS_IP="$_env_ip"
  elif [[ -f "$IP_FILE" ]]; then
    VPS_IP="$(tr -d '[:space:]' < "$IP_FILE")"
  fi
fi

if [[ -z "$VPS_IP" ]]; then
  log "${RED}[ERROR]${RESET} IP não encontrado. Use --ip <IP>, env VPS_IP, ou crie $IP_FILE"
  exit 1
fi

# --------------------------------------------------------------------------- #
# Timestamp
# --------------------------------------------------------------------------- #
TS="$(date '+%Y-%m-%dT%H:%M:%S%z')"

# --------------------------------------------------------------------------- #
# Função: executa checks e retorna resultado
# --------------------------------------------------------------------------- #
FAILED_CHECK=""
FAILURE_DETAIL=""
SSH_HOSTNAME=""
SSH_UPTIME_DAYS=""

run_checks() {
  # --- Check 1: Ping ---
  if [[ "$QUIET" -eq 0 ]]; then
    info "Verificando ping para $VPS_IP..."
  fi

  if ! ping -c 3 -W 2 "$VPS_IP" > /dev/null 2>&1; then
    FAILED_CHECK="ping"
    FAILURE_DETAIL="Ping falhou para $VPS_IP (3 packets, 2s timeout cada)"
    return 1
  fi

  # --- Check 2: SSH ---
  if [[ "$QUIET" -eq 0 ]]; then
    info "Verificando SSH root@$VPS_IP..."
  fi

  SSH_OUTPUT="$(ssh \
    -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=no \
    -o BatchMode=yes \
    -o LogLevel=ERROR \
    "root@$VPS_IP" \
    'printf "%s uptime_days=%s" "$(hostname)" "$(awk '"'"'{print int($1/86400)}'"'"' /proc/uptime 2>/dev/null || echo "?")"' \
    2>&1)" || {
    FAILED_CHECK="ssh"
    FAILURE_DETAIL="SSH falhou para root@$VPS_IP: $SSH_OUTPUT"
    return 2
  }

  SSH_HOSTNAME="$(echo "$SSH_OUTPUT" | awk '{print $1}')"
  SSH_UPTIME_DAYS="$(echo "$SSH_OUTPUT" | grep -oE 'uptime_days=[^ ]+' | cut -d= -f2)"

  # --- Check 3: HTTP API ---
  # Porta 18802 só escuta em 127.0.0.1 na VPS (não exposed externamente
  # por design). Por isso curl externo daqui falha. Solução: tunelar via
  # SSH executando curl DENTRO da VPS contra 127.0.0.1:18802.
  if [[ "$QUIET" -eq 0 ]]; then
    info "Verificando API http://127.0.0.1:18802/api/health via SSH ($VPS_IP)..."
  fi

  API_RESPONSE="$(ssh -o ConnectTimeout=5 -o BatchMode=yes \
                      "root@$VPS_IP" \
                      'curl -s -m 5 http://127.0.0.1:18802/api/health' 2>&1)" || {
    FAILED_CHECK="api"
    FAILURE_DETAIL="curl via SSH falhou: $API_RESPONSE"
    return 3
  }

  if ! echo "$API_RESPONSE" | jq -e '.vectorCoverage' > /dev/null 2>&1; then
    FAILED_CHECK="api"
    FAILURE_DETAIL="API respondeu mas .vectorCoverage ausente. Resposta: $(echo "$API_RESPONSE" | head -c 200)"
    return 3
  fi

  return 0
}

# --------------------------------------------------------------------------- #
# Executa checks
# --------------------------------------------------------------------------- #
EXIT_CODE=0
run_checks || EXIT_CODE=$?

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
case $EXIT_CODE in
  0)
    if [[ "$QUIET" -eq 0 ]]; then
      ok "${BOLD}OK${RESET} ${TS}  host=${SSH_HOSTNAME}  uptime=${SSH_UPTIME_DAYS}d  ip=${VPS_IP}"
    fi
    ;;
  1)
    fail "${BOLD}FALHA [ping]${RESET} ${TS}  ip=${VPS_IP}"
    fail "${FAILURE_DETAIL}"
    warn "Ação sugerida: verificar painel Hostinger → VPS → Network → se IP mudou, atualizar $IP_FILE"
    if [[ -n "$ALERT_CMD" ]]; then
      eval "$ALERT_CMD" 2>/dev/null || true
    fi
    ;;
  2)
    fail "${BOLD}FALHA [ssh]${RESET} ${TS}  ip=${VPS_IP}"
    fail "${FAILURE_DETAIL}"
    warn "Ação sugerida: ping OK mas SSH inacessível — verificar sshd na VPS ou firewall Hostinger"
    if [[ -n "$ALERT_CMD" ]]; then
      eval "$ALERT_CMD" 2>/dev/null || true
    fi
    ;;
  3)
    fail "${BOLD}FALHA [api]${RESET} ${TS}  ip=${VPS_IP}  host=${SSH_HOSTNAME}"
    fail "${FAILURE_DETAIL}"
    warn "Ação sugerida: SSH OK mas API down — verificar 'systemctl status openclaw-api' na VPS"
    if [[ -n "$ALERT_CMD" ]]; then
      eval "$ALERT_CMD" 2>/dev/null || true
    fi
    ;;
esac

exit $EXIT_CODE
