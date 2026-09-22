#!/usr/bin/env bash
# Cópia verificada do lastro do ensaio P2, com recibo datado.
#
# 🔑 O manifesto (`manifesto-lastro-p2.py`) prova que os bytes são os bytes.
#    NÃO prova que existe cópia. Este script é o remédio; aquele é o detector.
#
# 🔑 O hash é recalculado NO DESTINO. Recalcular na origem verifica a origem,
#    que não é a pergunta — a pergunta é se a cópia chegou inteira.
#
# ⚠️ Sem `NOX_LASTRO_HOST` no ambiente a perna remota é DECLARADA como não
#    verificada. Nunca omitida em silêncio: "não copiei" e "copiei e está bem"
#    não podem ter a mesma saída. O host nunca entra em ficheiro versionado —
#    este repositório é público.
#
# ⚠️ Sem `timeout(1)` aqui. No macOS ele vem do Homebrew e o PATH do launchd é
#    /usr/bin:/bin:/usr/sbin:/sbin — um agendamento perderia o binário e
#    reportaria "host inalcançável" onde o ssh funciona. O limite de tempo vem
#    das opções do próprio ssh.
set -uo pipefail

# ⚠️ COPIAR e VERIFICAR têm de ser separáveis, e a razão foi medida em
# 2026-09-21: com o `rsync` a correr antes da verificação, corromper um byte na
# cópia e correr o script dava ✅ — o rsync restaurava o ficheiro a partir da
# origem antes de alguém o olhar. «A cópia está íntegra» e «a cópia acabou de
# ser sobrescrita» produziam a mesma saída, que é a definição de um guarda que
# não vê. `--verificar` salta a cópia e olha para o que lá está.
SO_VERIFICAR=0
[ "${1:-}" = "--verificar" ] && SO_VERIFICAR=1

ORIG="$HOME/Backups/paper2-ensaio-2026-09-21"
VERD="$HOME/.paper2-verdicts"
MAN="$ORIG/MANIFESTO-LASTRO-P2.json"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RECIBOS="$ORIG/recibos"; mkdir -p "$RECIBOS"
REC="$RECIBOS/backup-$TS.txt"

[ -f "$MAN" ] || { echo "🔴 sem manifesto: rode scripts/manifesto-lastro-p2.py primeiro"; exit 2; }

{
  echo "recibo de cópia do lastro P2 — $TS"
  echo "manifesto: $(shasum -a 256 "$MAN" | cut -d' ' -f1)"
  echo
} | tee "$REC"

# ══ PERNA LOCAL ═══════════════════════════════════════════════════════════
# Segundo diretório no mesmo disco. Protege contra apagar por engano, NÃO
# contra falha de disco — e isso vai dito no recibo, para o recibo não afirmar
# mais do que a cópia vale.
DEST_L="$HOME/Backups/paper2-ensaio-2026-09-21-COPIA"
echo "── perna LOCAL → $DEST_L" | tee -a "$REC"
mkdir -p "$DEST_L"
if [ "$SO_VERIFICAR" -eq 1 ]; then
  echo "  (modo --verificar: NÃO copia; olha o que já está no destino)" | tee -a "$REC"
else
  rsync -a --delete "$ORIG/" "$DEST_L/artefatos/" 2>/dev/null
  rsync -a --delete "$VERD/" "$DEST_L/verdicts/"  2>/dev/null
fi

# verificação: recalcular NO DESTINO contra o manifesto
FALHAS=0; CONF=0
while IFS=$'\t' read -r nome caminho esperado tipo; do
  case "$caminho" in
    "$ORIG"*) rel="artefatos/${caminho#$ORIG/}" ;;
    "$VERD"*) rel="verdicts/${caminho#$VERD/}"  ;;
    *)        echo "  ⏭  $nome — fora das raízes copiadas (vive no repo, versionado)" | tee -a "$REC"; continue ;;
  esac
  alvo="$DEST_L/$rel"
  if [ "$tipo" = "diretorio" ]; then
    # UMA implementação: a do manifesto. Reimplementar aqui divergiu por uma
    # newline final na primeira versão deste script.
    obtido=$(python3 "$(dirname "$0")/manifesto-lastro-p2.py" --hash-dir "$alvo")
  else
    obtido=$(shasum -a 256 "$alvo" 2>/dev/null | cut -d' ' -f1)
  fi
  if [ "$obtido" = "$esperado" ]; then
    CONF=$((CONF+1)); echo "  ✅ $nome" | tee -a "$REC"
  else
    FALHAS=$((FALHAS+1))
    # ⚠️ AUSENTE e DIVERGENTE sao estados diferentes e pedem accoes diferentes:
    # o 1o e' «a copia nao tem», o 2o e' «a copia tem outra coisa». Um hash vazio
    # impresso como se fosse hash le-se como divergencia, e manda consertar o que
    # nao esta' partido.
    if [ -z "$obtido" ]; then
      echo "  🔴 $nome — AUSENTE da cópia (está no manifesto, não no destino)" | tee -a "$REC"
    else
      echo "  🔴 $nome — DIVERGE: esperado ${esperado:0:12}… obtido ${obtido:0:12}…" | tee -a "$REC"
    fi
  fi
done < <(python3 -c '
import json,sys
m=json.load(open(sys.argv[1]))
for a in m["artefatos"]:
    print("\t".join([a["nome"],a["caminho"],a["sha256"],a["tipo"]]))' "$MAN")

{
  echo "  local: $CONF conferem, $FALHAS divergem"
  echo "  ⚠️ mesma máquina e mesmo disco da origem — protege contra apagar, não contra perder o disco"
  echo
} | tee -a "$REC"

# ══ PERNA OFF-MACHINE ═════════════════════════════════════════════════════
echo "── perna OFF-MACHINE" | tee -a "$REC"
if [ -z "${NOX_LASTRO_HOST:-}" ]; then
  {
    echo "  🔴 NÃO VERIFICADA — \$NOX_LASTRO_HOST ausente do ambiente."
    echo "     O lastro existe hoje em UMA máquina. Isto é uma declaração, não um erro"
    echo "     do script: sem a variável não há destino, e omitir a perna faria"
    echo "     'não copiei' parecer 'copiei e está bem'."
  } | tee -a "$REC"
  REMOTO=2
else
  DEST_R="/var/backups/nox-mem/paper2-lastro-ensaio"
  if [ "$SO_VERIFICAR" -eq 1 ]; then true; else
  ssh -o ConnectTimeout=15 -o BatchMode=yes "$NOX_LASTRO_HOST" "mkdir -p $DEST_R" 2>>"$REC" \
    && rsync -a -e "ssh -o ConnectTimeout=15" "$ORIG/" "$NOX_LASTRO_HOST:$DEST_R/artefatos/" 2>>"$REC" \
    && rsync -a -e "ssh -o ConnectTimeout=15" "$VERD/" "$NOX_LASTRO_HOST:$DEST_R/verdicts/"  2>>"$REC"    \
    && rsync -a -e "ssh -o ConnectTimeout=15" "$(dirname "$0")/manifesto-lastro-p2.py" "$NOX_LASTRO_HOST:$DEST_R/" 2>>"$REC"
  fi
  if [ "$SO_VERIFICAR" -eq 0 ] && [ $? -ne 0 ]; then
    echo "  🔴 cópia remota FALHOU — ver erro acima" | tee -a "$REC"; REMOTO=1
  else
    # recalcular NO DESTINO REMOTO
    RF=0; RC=0
    while IFS=$'\t' read -r nome caminho esperado tipo; do
      case "$caminho" in
        "$ORIG"*) rel="artefatos/${caminho#$ORIG/}" ;;
        "$VERD"*) rel="verdicts/${caminho#$VERD/}"  ;;
        *) continue ;;
      esac
      if [ "$tipo" = "diretorio" ]; then
        # o MESMO script corre no destino (copiado acima) — nunca uma 2ª regra
        obtido=$(ssh -n -o ConnectTimeout=15 "$NOX_LASTRO_HOST" \
          "python3 $DEST_R/manifesto-lastro-p2.py --hash-dir $DEST_R/$rel" 2>/dev/null)
      else
        obtido=$(ssh -n -o ConnectTimeout=15 "$NOX_LASTRO_HOST" \
          "sha256sum $DEST_R/$rel 2>/dev/null | cut -d' ' -f1")
      fi
      if [ "$obtido" = "$esperado" ]; then RC=$((RC+1)); else RF=$((RF+1)); echo "  🔴 remoto $nome" | tee -a "$REC"; fi
    done < <(python3 -c '
import json,sys
m=json.load(open(sys.argv[1]))
for a in m["artefatos"]:
    print("\t".join([a["nome"],a["caminho"],a["sha256"],a["tipo"]]))' "$MAN")
    echo "  remoto: $RC conferem, $RF divergem (de $CONF que a perna local viu)" | tee -a "$REC"
    # ⚠️ INVARIANTE: a perna remota tem de examinar o MESMO número de artefatos que
    # a local. Sem isto, «1 confere, 0 divergem» lê-se como sucesso quando são 11
    # não examinados — foi o que aconteceu em 2026-09-22T01:47Z, porque o `ssh`
    # dentro do `while read` consumia o stdin do loop e engolia as linhas. O `-n`
    # corrige a causa; este teste é a rede para a próxima variante dela.
    if [ "$((RC+RF))" -ne "$CONF" ]; then
      echo "  🔴 a perna remota examinou $((RC+RF)) de $CONF — NÃO é um veredito sobre a cópia" | tee -a "$REC"
      REMOTO=1
    else
      REMOTO=$([ "$RF" -eq 0 ] && echo 0 || echo 1)
    fi
  fi
fi

echo | tee -a "$REC"
echo "recibo: $REC" | tee -a "$REC"
# exit 0 só se a local confere E a remota confere. 3 = local ok, remota ausente.
if [ "$FALHAS" -gt 0 ]; then exit 1
elif [ "${REMOTO:-2}" -eq 2 ]; then exit 3
elif [ "${REMOTO}" -ne 0 ]; then exit 1
else exit 0; fi
