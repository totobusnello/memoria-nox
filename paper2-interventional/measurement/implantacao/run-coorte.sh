#!/bin/bash
# Cadência horária. READ-ONLY. Vigia a perna que faltava: o canal por onde a dose
# alcança os designados — os `freshSlots` do pool global — pode estar ENTUPIDO por
# uma coorte de nunca-servidos, e nesse estado o zero da dose é ESTRATO, não
# ausência de efeito. Nenhum outro gatilho deste ensaio vê isso.
#
# ⚠️ O CORPUS É O SERVIDO, NÃO O `current.db`. A pergunta operacional é sobre o que
# a produção realmente serve, e o que ela serve desde 03/09 17:30 é o inode que o
# `fd 26` do pid 546151 mantém vivo — preservado em cópia byte-idêntica abaixo. O
# `current.db` responderia "estaria alcançável SE o serving pegasse o corpus de
# hoje", e hoje isso sai RED toda hora: alarme cronicamente vermelho é o que ensina
# a ignorar alarme.
#
# ⚠️ O wrapper NÃO envelhece em silêncio. Se o serving reiniciar, ele passa a servir
# outro corpus e a perna `corpus_e_o_servido` do próprio guarda vira `nao` — o
# recibo denuncia que esta referência ficou velha. É por isso que a escolha do
# corpus servido é segura: ela se auto-invalida.
#
# ⚠️ SHA PINADO. Cópia substituída, truncada ou regravada viraria referência
# silenciosa do ensaio inteiro. O sha abaixo foi medido em 2026-09-09 contra três
# fontes independentes que concordaram: o `fd 26` vivo, a cópia de 08/09 15:01 em
# /var/lib/nox-mem/p2/, e o backup 0400 de 09/09 15:25. Divergindo, este script
# escreve RED e NÃO roda o guarda.
#
# ⚠️ MINUTO :44, livre de todos os outros: :9 composição, :24 designados,
# :39 corpus-alinhado, :54 heartbeat, `12 9` saturação, e o brief-refresh em
# :7,:22,:37,:52.
set -uo pipefail
CORPUS=/var/backups/nox-mem/p2-corpus-servido/servido-e20260903T060001Z.db
CORPUS_SHA_ESPERADO=23378a9ea83cd27d0360cfe148207167aee30a376f29ef89d4bcfae415d04131
STATUS=/var/lib/nox-mem/p2/status-coorte.txt
NDJSON=/var/lib/nox-mem/p2/gatilhos.ndjson

morre() { local l="$1 p2-coorte-alcancavel motivo=$2 ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          echo "$l"; printf '%s\n' "$l" > "$STATUS"
          printf '{"tag":"p2_gatilho_coorte","ts":"%s","veredito":"%s","motivo":"%s"}\n' \
                 "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$NDJSON"
          exit 0; }

# ── A dose ainda está ligada? Sem dose, a pergunta deste guarda é VAZIA: ele mede
#    se o canal permite a dose MORDER, e o `desliga-dose-p2.sh` a desarma em 21/09
#    09:43Z. A partir do restart o serving passa a servir outro corpus, e sem esta
#    perna a referência pinada acima faria o guarda sair `corpus-nao-e-o-servido`
#    RED a cada hora, para sempre — alarme cronicamente vermelho, que é exatamente o
#    que ensina a ignorar alarme. GREEN aqui não é "está tudo bem com o canal": é
#    "a pergunta não se aplica mais", e o motivo diz isso.
OUT="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_OUTCOME=//p' | tail -1)"
[ "$OUT" = active ] || morre GREEN ensaio-encerrado-dose-desligada-outcome="${OUT:-vazio}"

[ -f "$CORPUS" ] || morre RED corpus-servido-ausente
SHA="$(sha256sum "$CORPUS" 2>/dev/null | cut -d' ' -f1)"
[ -n "$SHA" ] || morre RED corpus-servido-ilegivel
[ "$SHA" = "$CORPUS_SHA_ESPERADO" ] || morre RED corpus-servido-sha-divergente

exec timeout 180 /root/.openclaw/scripts/p2/gatilho-coorte.sh \
  --corpus "$CORPUS" \
  --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  --status "$STATUS" \
  --ndjson "$NDJSON"
