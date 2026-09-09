#!/bin/bash
# Cadência horária. READ-ONLY (só le o ndjson do serving e o relógio).
# Vigia a perna que faltava: "o serving parou" e "a unidade que fechou está
# inteira" — as duas coisas que nenhum outro gatilho deste ensaio pode ver,
# porque todos leem O ÚLTIMO EPOCH e ficam calados quando não há epoch nenhum.
#
# ⚠️ A configuração vem do UNIT DO SYSTEMD, não do `.env`: o caminho do log é o
# que a produção realmente escreve. Mesma disciplina do run-saturacao.sh.
#
# ⚠️ TETO = 3600 s, calibrado por medição em 2026-09-09 sobre 11.396 registros:
# maior intervalo normal 936 s (0,26 h, a cadência do brief-refresh), e só 2
# intervalos acima de 1 h em 19 dias — os dois incidentes conhecidos. Folga de
# 3,85x. Se a cadência do brief-refresh mudar, este teto tem de ser remedido:
# ele é 4x o intervalo entre rajadas, não um número redondo.
#
# ⚠️ ESPERADO = 672 registros por epoch = 4 rajadas/h x 24 h x 7 agentes.
# Vale na era `active` e valeu em todo epoch completo medido (08-29 a 09-01,
# 09-05 a 09-08). O `677` de 27/08 é pré-active, de outro regime.
#
# ⚠️ MINUTO :54, escolhido para não colidir com os outros gatilhos (:9 composição,
# :24 designados, :39 corpus-alinhado) nem com o brief-refresh (:7,:22,:37,:52).
set -uo pipefail
exec /root/.openclaw/scripts/p2/gatilho-heartbeat.sh \
  --teto-s 3600 \
  --esperado 672 \
  --status /var/lib/nox-mem/p2/status-heartbeat.txt \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
