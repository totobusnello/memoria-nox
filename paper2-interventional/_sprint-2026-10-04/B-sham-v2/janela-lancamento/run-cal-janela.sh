#!/usr/bin/env bash
# $1=tsfile $2=out-prefix ; REAL designation, doses 4 and 100000, served corpus, rowid cut
# Copia de cal/run-cal.sh do job-v2b, so com D trocado para o diretorio da janela.
set -u
D=/var/tmp/sprint-sham-v2-janela-w
SHA=$(sha256sum $D/in/DESIGNATION-2026-08-26.json | cut -d" " -f1)
/usr/bin/time -v -o $2.time nice -n 10 node $D/raiz/replay-oportunidade.mjs --modo dose --raiz $D/raiz \
  --corpus $D/db/corpus-SERVING-REAL-e20260903-recuperado.db --vivo $D/db/vivo-v2.db --corte rowid \
  --t-ref 2026-09-01T00:00:00Z --excluir-briefs $D/in/excluir-vazio.txt --log-campo $D/in/p2-serving.ndjson \
  --so-ts-file $1 --w 4 --w 100000 --designacao $D/in/DESIGNATION-2026-08-26.json --designacao-sha256 $SHA \
  --tmp-base $D/tmp --sem-assert --out $2.json > $2.stdout 2> $2.stderr
echo "exit=$?" > $2.exit
