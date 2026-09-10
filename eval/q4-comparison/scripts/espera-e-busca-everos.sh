#!/bin/bash
# Espera a INGESTAO do EverOS fechar e so entao dispara a busca.
#
# ⚠️ A busca NAO pode arrancar durante a ingestao: `setup()` chama
# `ensure_business_indexes()`, que e' MIGRACAO DE SCHEMA, e o upstream avisa que
# mudar o conjunto de tabelas e' invisivel para handles em cache. O
# `everos-busca.sh` tem o guarda; este script so evita que alguem (eu) tenha de
# ficar a sondar para o lançar na hora.
#
# Liveness por PROGRESSO, nao por processo: `pgrep -f` casaria a propria linha
# deste script.
set -uo pipefail
cd /root/q4-everos
CONSOLE=out/everos-busca-console.log
LIMITE=$(( $(date +%s) + 6*3600 ))   # prazo de parede: nao esperar para sempre
while [ "$(date +%s)" -lt "$LIMITE" ]; do
  # ⚠️ `-t=` EXATO: este script roda na sessao `everos-busca`, e `-t everos`
  # casaria por PREFIXO a propria sessao que o executa ⇒ esperaria para sempre.
  if ! tmux has-session -t=everos 2>/dev/null; then
    IDADE=$(( $(date +%s) - $(stat -c %Y out/corrida/ledger-criados.txt 2>/dev/null || echo 0) ))
    if [ "$IDADE" -ge 150 ]; then
      # 🔴 PERNA QUE FALTAVA: sessao morta + ledger quieto e' compativel com
      # "fechou normalmente" E com "morreu a meio". Buscar sobre um indice
      # PARCIAL produz nDCG que se le como qualidade do sistema -- a mesma
      # classe do artefato de 100 queries que passou por corrida completa hoje,
      # e do fan-out degradado do Zep. O `fecho` e' o unico registro que
      # distingue termino de morte, e `deadline` diz explicitamente que sobrou
      # corpus. Exigir `fecho`, e recusar `deadline`.
      FIM=$(grep -E '"evento": "(fecho|deadline)"' out/corrida/progresso.ndjson 2>/dev/null | tail -1)
      if [ -z "$FIM" ]; then
        echo "[espera] 🔴 sessao morta e ledger quieto ha ${IDADE}s, mas NAO HA evento de fecho"
        echo "         => a ingestao morreu a meio. NAO disparo busca paga sobre indice parcial."
        echo "         Retomavel com o mesmo --out (o ledger e' a rede)."
        exit 4
      fi
      case "$FIM" in
        *'"deadline"'*)
          echo "[espera] 🔴 a ingestao parou por DEADLINE, nao por fecho: $FIM"
          echo "         => sobrou corpus. NAO disparo busca sobre indice incompleto."
          exit 4;;
      esac
      echo "[espera] ingestao FECHOU e ledger quieto ha ${IDADE}s — disparando a busca"
      echo "[espera] fecho: $FIM"
      # sem `exec`: preciso do pipe para o console que o vigia classifica, e
      # `exec cmd | tee` substituiria o shell antes de montar o pipe.
      bash scripts/everos-busca.sh 2>&1 | tee -a "$CONSOLE"
      exit "${PIPESTATUS[0]}"
    fi
    echo "[espera] sessao morta mas ledger escrito ha ${IDADE}s — aguardando 150s de quietude"
  fi
  sleep 60
done
echo "[espera] 🔴 prazo de 6h esgotado sem a ingestao fechar — NAO disparei a busca"
exit 3
