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

recibo() {  # $1=estado $2=motivo $3...=campos medidos
  # ⚠️ `$3+` ENTRAM na linha. A primeira versao usava so `$2` e descartava
  # `outcome=`, `dropin-arquivado-em=` e o resumo da aposentadoria — o recibo saia
  # sem o que foi medido, que e' exatamente o defeito que o §10.17 inteiro tratou,
  # reaparecendo no script escrito depois dele. Achado pelo sandbox, nao pela leitura.
  local est="$1" mot="$2"; shift 2
  local l="$est p2-desliga-dose motivo=$mot ${*:+$* }ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$l"
  printf '%s\n' "$l" > "$STATUS"
  printf '{"ts":"%s","estado":"%s","motivo":"%s","campos":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$est" "$mot" "$*" >> "$NDJSON"
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

# ═══ APOSENTADORIA DOS GUARDAS ═══════════════════════════════════════════════
# Ordenado pelo Toto em 2026-09-09 14:46 BRT: **"aposenta os guardas junto no 21"**.
#
# ⚠️ POR QUE ISTO NÃO É SÓ TIRAR LINHAS DO CRON: o `morning-report.sh` chama
# `p2_gatilho <rotulo> <status> <idade_max_h>` para cada guarda, e essa função dá
# **YELLOW `sem status` / `gatilho parado?`** quando o arquivo falta ou envelhece.
# Parar os crons sem tocar no report trocaria **três REDs crônicos por seis YELLOWs
# crônicos** — ruído por ruído, com o propósito invertido. Medido: com o report
# editado a saída volta a `all green`.
#
# ⚠️ E POR QUE NÃO APAGAR AS CHAMADAS: silêncio sobre algo que era vigiado e deixou
# de ser é o defeito que custou seis dias no §10.10. As seis chamadas ficam
# **comentadas** com marca datada (preservando a calibragem dos tetos, que o bloco de
# regra logo acima referencia) e entra **uma** linha informativa `⚪` que não conta
# como RED nem YELLOW: a ausência aparece em vez de ser silêncio.
#
# ORDEM ESCOLHIDA POR QUAL FALHA É MENOS PIOR:
#   report primeiro, cron depois ⇒ falha deixa guardas rodando e o report AFIRMANDO
#     que foram aposentados. Silencioso e FALSO.
#   cron primeiro, report depois ⇒ falha deixa o report reclamando de guarda parado.
#     Ruidoso e HONESTO.
# Escolhido o segundo. E o arquivo novo é **pré-gerado e conferido hoje**, fora de
# `/var/tmp` (que some em 11 dias), de modo que o único passo restante é `install`.
REPORT=/root/.openclaw/scripts/morning-report.sh
REPORT_SHA_ESPERADO=20a5b63fda32c93b186a424d2b4444c03146dde7c86c38a451c2c981920f740f
REPORT_NOVO=/root/.openclaw/paper2/aposentadoria/morning-report.p2-aposentado.sh
REPORT_NOVO_SHA=d1da7f703295478991e970345e8312fb06de4706e3fef0c7531751a527d18b45

aposenta() {
  # Pré-condição do report ANTES de mexer no cron: se alguém editou o
  # `morning-report.sh` entre hoje e 21/09, instalar a minha versão apagaria a
  # edição dessa pessoa. Nesse caso a aposentadoria inteira é abortada e os guardas
  # ficam — ruidosos e honestos, que é o estado menos pior.
  local sha_r sha_n
  sha_r="$(sha256sum "$REPORT" 2>/dev/null | cut -d' ' -f1)"
  [ "$sha_r" = "$REPORT_SHA_ESPERADO" ] || {
    echo "APOSENTADORIA-ABORTADA report-divergiu sha=${sha_r:-vazio}"; return 1; }
  [ -f "$REPORT_NOVO" ] || { echo "APOSENTADORIA-ABORTADA report-novo-ausente"; return 1; }
  sha_n="$(sha256sum "$REPORT_NOVO" 2>/dev/null | cut -d' ' -f1)"
  [ "$sha_n" = "$REPORT_NOVO_SHA" ] || {
    echo "APOSENTADORIA-ABORTADA report-novo-divergente sha=${sha_n:-vazio}"; return 1; }
  bash -n "$REPORT_NOVO" 2>/dev/null || { echo "APOSENTADORIA-ABORTADA report-novo-sem-sintaxe"; return 1; }

  # ── cron: arquivo + `crontab <arquivo>`, NUNCA `crontab -l | ... | crontab -`.
  #    Esse pipe já zerou o crontab uma vez.
  local antes depois na nd np
  antes=/root/.openclaw/paper2/aposentadoria/crontab.antes-$(date -u +%Y%m%dT%H%M%SZ)
  depois="${antes}.depois"
  crontab -l > "$antes" 2>/dev/null || { echo "APOSENTADORIA-ABORTADA nao-li-o-crontab"; return 1; }
  np="$(grep -cE '# p2-' "$antes")"
  # ⚠️ ZERO linhas p2 NAO e' erro — e' a parte do cron ja feita, e o report pode
  #    continuar precisando de edicao. A primeira versao abortava aqui e dizia
  #    "guardas NAO aposentados" sobre guardas que ja nao existiam: veredito certo
  #    pelo motivo errado. Achado pelo sandbox (caso C).
  na="$(wc -l < "$antes")"
  if [ "$np" -gt 0 ]; then
    grep -vE '# p2-' "$antes" > "$depois"
    nd="$(wc -l < "$depois")"
    [ $((na - nd)) -eq "$np" ] || {
      echo "APOSENTADORIA-ABORTADA delta=$((na-nd))-esperava=$np"; return 1; }
    crontab "$depois" || { echo "APOSENTADORIA-ABORTADA crontab-recusou backup=$antes"; return 1; }
    [ "$(crontab -l | grep -cE '# p2-')" -eq 0 ] || {
      echo "APOSENTADORIA-PARCIAL cron-ainda-tem-p2 backup=$antes"; return 1; }
  else
    nd="$na"
  fi

  # ── report: `install` atômico, com backup do antigo ao lado do crontab antigo.
  cp -p "$REPORT" "/root/.openclaw/paper2/aposentadoria/morning-report.antes-$(date -u +%Y%m%dT%H%M%SZ).sh"
  install -m 0755 "$REPORT_NOVO" "$REPORT" || {
    echo "APOSENTADORIA-PARCIAL cron-limpo-mas-report-nao-instalou backup=$antes"; return 1; }

  echo "guardas=$np cron-linhas=$na->$nd report-instalado=$REPORT_NOVO_SHA backup=$antes"
  return 0
}

if APOS="$(aposenta)"; then
  recibo GREEN dose-desligada-e-guardas-aposentados outcome="$OUT_NOVO" \
    dropin-arquivado-em="$DESTINO" "$APOS"
else
  # A dose está desligada — isso é o que o Toto ordenou primeiro e já vale. A
  # aposentadoria falhou e os guardas seguem no ar: YELLOW, não RED, porque o
  # estado é ruidoso e honesto, não perigoso. O motivo vai na linha.
  recibo YELLOW dose-desligada-mas-guardas-NAO-aposentados outcome="$OUT_NOVO" \
    dropin-arquivado-em="$DESTINO" "${APOS:-aposenta-sem-saida}"
fi
