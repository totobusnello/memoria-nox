#!/bin/bash
# Desliga a dose do ensaio do Paper 2 depois do fim da janela elegível. READ-MOSTLY:
# a única mutação é MOVER o drop-in que arma o `active` e reiniciar o unit.
#
# Decisão do Toto em 2026-09-09 14:38 BRT, literal: **"encerra 20/09 mesmo, e desliga
# a dose depois"**. Primeira instrução explícita sobre o desfecho — o §10.14 fundava a
# reversão numa medição e citava pergunta retórica, o que não era ordem.
#
# ⚠️ O PROCEDIMENTO NÃO É INVENÇÃO MINHA: está escrito no próprio
# `zz-p2-active.conf`, seção `Rollback` — *"rm this file, systemctl daemon-reload,
# restart nox-mem-api. Effect: NOX_P2_OUTCOME falls back to shadow
# (p2s2-shadow.conf), no brief gets treatment, and everything already served stays on
# the record."* Duas diferenças deliberadas: MOVE em vez de `rm` (o arquivo é o
# registro do que foi armado — apagá-lo apaga a prova) e pré-condições com recibo.
#
# ⚠️ POR QUE 09:23Z E NÃO MEIA-NOITE: o mesmo drop-in avisa que a fronteira de epoch é
# 09:00 UTC e que reiniciar antes dela resolve o epoch do dia ANTERIOR. O epoch de
# 09-20 corre até 09-21 09:00Z; desligar depois disso não trunca epoch elegível
# nenhum. A VPS roda em UTC (`timedatectl` = Etc/UTC), medido — não presumido.
set -uo pipefail

STATUS=/var/lib/nox-mem/p2/status-desliga-dose.txt
NDJSON=/var/lib/nox-mem/p2/desliga-dose.ndjson
DROPIN=/etc/systemd/system/nox-mem-api.service.d/zz-p2-active.conf
ARQUIVO_MORTO=/root/.openclaw/paper2/desarmado
CORPUS_PRESERVADO=/var/backups/nox-mem/p2-corpus-servido/servido-e20260903T060001Z.db
CORPUS_SHA_ESPERADO=23378a9ea83cd27d0360cfe148207167aee30a376f29ef89d4bcfae415d04131
FIM_DA_JANELA=2026-09-21T09:00:00Z   # o epoch de 09-20 fecha aqui

mkdir -p "$(dirname "$STATUS")" 2>/dev/null

recibo() {  # $1=estado $2=motivo  — TODO caminho passa por aqui, inclusive os abortos
  local l="$1 p2-desliga-dose motivo=$2 ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$l"
  printf '%s\n' "$l" > "$STATUS"
  printf '{"ts":"%s","estado":"%s","motivo":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$NDJSON"
  exit 0
}

# ── (1) A janela já fechou? Um desligamento antecipado TRUNCA epoch elegível, que é
#        dano irreversível ao ensaio — pior que um desligamento atrasado.
AGORA_S=$(date -u +%s)
FIM_S=$(date -u -d "$FIM_DA_JANELA" +%s 2>/dev/null) || recibo RED nao-parseei-o-fim-da-janela
[ "$AGORA_S" -ge "$FIM_S" ] || recibo YELLOW janela-ainda-aberta-faltam-$(( (FIM_S - AGORA_S) / 3600 ))h

# ── (2) Já está desligado? Idempotência: o cron é one-shot mas dispara todo 21/09.
[ -f "$DROPIN" ] || recibo GREEN ja-desligado-dropin-ausente
OUT_ATUAL="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_OUTCOME=//p' | tail -1)"
[ "$OUT_ATUAL" = active ] || recibo GREEN ja-desligado-outcome="${OUT_ATUAL:-vazio}"

# ── (3) O corpus servido está preservado? O restart DERRUBA o fd, e até 09/09 15:25Z
#        esse fd era a ÚNICA cópia dos bytes sobre os quais todo o ensaio foi computado
#        (§10.21). Reiniciar sem a cópia conferida destrói a evidência primária.
[ -f "$CORPUS_PRESERVADO" ] || recibo RED corpus-servido-sem-copia-ABORTANDO-restart
SHA_ATUAL="$(sha256sum "$CORPUS_PRESERVADO" 2>/dev/null | cut -d' ' -f1)"
[ "$SHA_ATUAL" = "$CORPUS_SHA_ESPERADO" ] || \
  recibo RED copia-do-corpus-divergente-ABORTANDO sha="${SHA_ATUAL:-vazio}"

# ── (4) Desarma: MOVE, não apaga. O drop-in é o registro do que foi servido.
mkdir -p "$ARQUIVO_MORTO"
DESTINO="$ARQUIVO_MORTO/zz-p2-active.conf.desarmado-$(date -u +%Y%m%dT%H%M%SZ)"
mv "$DROPIN" "$DESTINO" || recibo RED nao-movi-o-dropin
systemctl daemon-reload || recibo RED daemon-reload-falhou-dropin-em="$DESTINO"
systemctl restart nox-mem-api || recibo RED restart-falhou-dropin-em="$DESTINO"

# ── (5) Conferir o efeito, não presumi-lo. `systemctl is-active` dizendo `active` já
#        conviveu com drop-in silenciosamente desabilitado (lição de 19/08 no próprio
#        drop-in), então o que se lê é o ENV do processo e a saúde da API.
sleep 5
OUT_NOVO="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_OUTCOME=//p' | tail -1)"
[ "$OUT_NOVO" = shadow ] || recibo RED outcome-nao-caiu-para-shadow="${OUT_NOVO:-vazio}"
PORTA="${NOX_API_PORT:-18802}"
curl -fsS --max-time 20 "http://127.0.0.1:$PORTA/api/health" >/dev/null 2>&1 \
  || recibo RED api-nao-responde-apos-restart outcome="$OUT_NOVO"

recibo GREEN dose-desligada outcome="$OUT_NOVO" dropin-arquivado-em="$DESTINO"
