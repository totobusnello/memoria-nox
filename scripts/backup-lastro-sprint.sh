#!/usr/bin/env bash
# Perna off-machine do lastro do sprint 2026-10-04, com recibo datado.
#
# Por que existe (2026-10-18): uma varredura de `~/Backups` mediu 600 MB — 40% da
# pasta, o maior item dela — numa máquina só. Os dois lastros que têm script
# (`backup-lastro.sh` do paper 1, `backup-lastro-p2.sh` do paper 2) já tinham duas
# pernas conferidas todo dia; este saiu do repo à mão (ver `MOVED-PATHS.txt`) e
# ficou sem nenhuma. São 121 artefatos: os `runs` dos três jobs de sham, os ZIPs e
# o PDF do depósito do paper B, e os quatro drafts de metodologia.
#
# 🔑 O hash é recalculado NO DESTINO. Recalcular na origem verifica a origem, que
#    não é a pergunta — a pergunta é se a cópia chegou inteira.
#
# ⚠️ COPIAR e VERIFICAR têm de ser separáveis, e a razão foi medida em 2026-09-21
#    no lastro do P2: com o `rsync` a correr antes da verificação, corromper um byte
#    na cópia e rodar o script dava ✅, porque o rsync restaurava o ficheiro a partir
#    da origem antes de alguém o olhar. «A cópia está íntegra» e «a cópia acabou de
#    ser sobrescrita» produziam a mesma saída. `--verificar` salta a cópia.
#
# ⚠️ Sem `NOX_LASTRO_HOST` no ambiente a perna é DECLARADA como não verificada.
#    Nunca omitida em silêncio: "não copiei" e "copiei e está bem" não podem ter a
#    mesma saída. O host nunca entra em ficheiro versionado — este repo é público.
#
# ⚠️ Sem `timeout(1)`: no macOS ele vem do Homebrew e o PATH do launchd é
#    /usr/bin:/bin:/usr/sbin:/sbin. O limite de tempo vem das opções do próprio ssh.
set -uo pipefail

SO_VERIFICAR=0
[ "${1:-}" = "--verificar" ] && SO_VERIFICAR=1

ORIG="$HOME/Backups/memoria-nox-sprint-2026-10-04"
SUMS="$ORIG/SHA256SUMS"
DEST_R="/var/backups/nox-mem/paper2-sprint-2026-10-04"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RECIBOS="$ORIG/recibos"; mkdir -p "$RECIBOS"
REC="$RECIBOS/off-machine-$TS.txt"

[ -f "$SUMS" ] || { echo "🔴 sem SHA256SUMS em $ORIG"; exit 2; }
ESPERADOS=$(grep -c . "$SUMS")

{
  echo "recibo da perna off-machine do lastro do sprint — $TS"
  echo "origem:    $ORIG"
  echo "esperados: $ESPERADOS artefatos"
  echo
} | tee "$REC"

if [ -z "${NOX_LASTRO_HOST:-}" ]; then
  {
    echo "🔴 NÃO VERIFICADA — \$NOX_LASTRO_HOST ausente do ambiente."
    echo "   Isto é uma declaração, não um erro: o lastro pode estar numa máquina só"
    echo "   e este script não tem como saber. O host vive no EnvironmentVariables de"
    echo "   ~/Library/LaunchAgents/com.toto.nox-mem.verifica-lastro.plist."
  } | tee -a "$REC"
  exit 1
fi

# ── CÓPIA ────────────────────────────────────────────────────────────────────
# Aditiva de propósito: sem --delete. Este lastro é append-only; um --delete aqui
# faria uma origem truncada apagar a cópia boa, que é a falha que o backup existe
# para impedir.
#
# ⚠️ `--checksum`, e não o default. Medido em 2026-10-18: corrompendo UM byte de
# METHODOLOGY-v4.md no destino, preservando tamanho e mtime, o `--verificar` acusa
# (120/121) e uma corrida de cópia com `rsync -a` NÃO repara — ele compara
# tamanho+mtime e conclui «igual» onde o sha256 conclui «diferente». As duas metades
# do script passavam a discordar sobre o que é o mesmo ficheiro, e quem visse o
# FAILED e rodasse a cópia esperando conserto teria o mesmo FAILED e culparia a
# origem. Custa ler os dois lados; a alternativa é um reparo que não repara.
if [ "$SO_VERIFICAR" -eq 1 ]; then
  echo "── modo --verificar: NÃO copia; olha o que já está no destino" | tee -a "$REC"
else
  echo "── cópia → \$NOX_LASTRO_HOST:$DEST_R" | tee -a "$REC"
  ssh -o ConnectTimeout=15 -o BatchMode=yes -n "$NOX_LASTRO_HOST" "mkdir -p $DEST_R" 2>>"$REC" \
    && rsync -a --checksum -e "ssh -o ConnectTimeout=15 -o BatchMode=yes" \
         "$ORIG/" "$NOX_LASTRO_HOST:$DEST_R/" --exclude 'recibos/' 2>>"$REC"
  if [ $? -ne 0 ]; then
    echo "🔴 cópia FALHOU — ver erro acima" | tee -a "$REC"; exit 1
  fi
fi

# ── VERIFICAÇÃO NO DESTINO ───────────────────────────────────────────────────
echo "── verificação (sha256 recalculado no destino)" | tee -a "$REC"
SAIDA=$(ssh -o ConnectTimeout=15 -o BatchMode=yes -n "$NOX_LASTRO_HOST" \
          "cd $DEST_R && sha256sum -c SHA256SUMS 2>&1" )
RC_SSH=$?

OK=$(printf '%s\n' "$SAIDA" | grep -c ': OK$')
FALHAS=$(printf '%s\n' "$SAIDA" | grep -c ': FAILED')
printf '%s\n' "$SAIDA" | grep ': FAILED' | sed 's/^/  🔴 /' | tee -a "$REC"

# ⚠️ INVARIANTE: a perna remota tem de examinar o MESMO número de artefatos que o
# SHA256SUMS declara. Sem isto, um ssh que morre no meio devolve "0 falhas" sobre
# os poucos que chegou a olhar, e 0/121 lê-se igual a 121/121. Foi o que aconteceu
# com o lastro do P2 em 2026-09-22T01:47Z.
if [ "$((OK+FALHAS))" -ne "$ESPERADOS" ]; then
  {
    echo "  🔴 examinou $((OK+FALHAS)) de $ESPERADOS — NÃO é um veredito sobre a cópia"
    echo "     (ssh rc=$RC_SSH)"
  } | tee -a "$REC"
  exit 1
fi

{
  echo "  remoto: $OK conferem, $FALHAS divergem (de $ESPERADOS declarados)"
  echo
  echo "recibo: $REC"
} | tee -a "$REC"

[ "$FALHAS" -eq 0 ] || exit 1
