#!/usr/bin/env bash
# =============================================================================
# Teste de mutação do gate de anonimato do build --tmlr.
#
# O build reporta "0 vazamento(s)". Sem este teste, esse zero é indistinguível
# de um gate que não sabe olhar: um gate que nunca reprova é decoração.
#
# A mutação é o erro real que se quer impossível — alguém troca
# `\usepackage{tmlr}` por `\usepackage[accepted]{tmlr}` (a linha que o
# camera-ready pede) e esquece que a submissão é cega. Com `[accepted]` o
# `tmlr.sty` imprime o `\author{}`, e o nome do autor aparece no PDF.
#
# Esperado: `build-paper.sh --tmlr` sai 4 e nomeia os sítios.
#
# ⚠️ O teste mexe em paper/preamble-tmlr.tex e reverte num trap EXIT. Se for
# interrompido de outra forma, conferir com `git diff paper/preamble-tmlr.tex`.
# =============================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PREAMBULO="${RAIZ}/paper/preamble-tmlr.tex"
BACKUP="$(mktemp)"

cp "$PREAMBULO" "$BACKUP"
reverter() { cp "$BACKUP" "$PREAMBULO"; rm -f "$BACKUP"; }
trap reverter EXIT

# --- perna 1: sem mutação, o build TEM de passar -------------------------
echo "[1/2] controle: build limpo tem de sair 0"
if ! "${RAIZ}/scripts/build-paper.sh" --tmlr > /tmp/gate-limpo.$$.log 2>&1; then
  echo "🔴 o build limpo FALHOU (exit $?) — o teste da mutação não diria nada" >&2
  tail -20 /tmp/gate-limpo.$$.log >&2
  rm -f /tmp/gate-limpo.$$.log
  exit 1
fi
grep -q '0 vazamento' /tmp/gate-limpo.$$.log \
  || { echo "🔴 build limpo não reportou 0 vazamentos" >&2; exit 1; }
rm -f /tmp/gate-limpo.$$.log
echo "      ✅ build limpo passa com 0 vazamentos"

# --- perna 2: com [accepted], o gate TEM de morder -----------------------
echo "[2/2] mutação: \\usepackage[accepted]{tmlr} de-anonimiza"
python3 - "$PREAMBULO" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
alvo = "\n\\usepackage{tmlr}\n"
if s.count(alvo) != 1:
    sys.exit(f"a mutação não acha o alvo: '\\usepackage{{tmlr}}' aparece {s.count(alvo)}x")
p.write_text(s.replace(alvo, "\n\\usepackage[accepted]{tmlr}\n"
                             "\\def\\month{09}\\def\\year{2026}\\def\\openreview{x}\n"), encoding="utf-8")
PY

set +e
"${RAIZ}/scripts/build-paper.sh" --tmlr > /tmp/gate-mut.$$.log 2>&1
rc=$?
set -e
if [[ "$rc" -ne 4 ]]; then
  echo "🔴 a mutação NÃO foi mordida: exit $rc, esperado 4" >&2
  tail -20 /tmp/gate-mut.$$.log >&2
  rm -f /tmp/gate-mut.$$.log
  exit 1
fi
if ! grep -q 'nome do autor' /tmp/gate-mut.$$.log; then
  echo "🔴 saiu 4 mas sem nomear o sítio — marcador errado" >&2
  tail -20 /tmp/gate-mut.$$.log >&2
  rm -f /tmp/gate-mut.$$.log
  exit 1
fi
echo "      ✅ mordeu: exit 4, sítios nomeados ($(grep -c 'nome do autor\|email:' /tmp/gate-mut.$$.log))"
rm -f /tmp/gate-mut.$$.log

echo
echo "ok — gate de anonimato do --tmlr: passa limpo, morde a de-anonimização"
