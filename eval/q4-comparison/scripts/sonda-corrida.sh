#!/bin/bash
# Sonda READ-ONLY do estado da corrida. Termina SEMPRE em exit 0 explicito:
# a versao anterior acabava em `[ -n "$E" ] && echo ...`, que devolve 1 quando
# nao ha linha EXIT= — o ssh saia 1 e o chamador lia "host inacessivel" para
# sempre. Ultimo comando de um script e' o veredito dele.
cd /root/q4-everos 2>/dev/null || { echo "ERRO=sem-dir"; exit 0; }
echo "LEDGER=$(wc -l < out/corrida/ledger-criados.txt 2>/dev/null || echo 0)"
if tmux has-session -t everos 2>/dev/null; then echo "TMUX=sim"; else echo "TMUX=nao"; fi
T=$(grep -E '"evento": "(fecho|deadline|sync_falhou)"' out/corrida/progresso.ndjson 2>/dev/null | tail -1)
[ -n "$T" ] && echo "TERM=$T"
P=$(grep '"evento": "progresso"' out/corrida/progresso.ndjson 2>/dev/null | tail -1)
[ -n "$P" ] && echo "PROG=$P"
E=$(grep -h "EXIT=" out/corrida/stdout.log 2>/dev/null | tail -1)
[ -n "$E" ] && echo "SAIDA=$E"
exit 0
