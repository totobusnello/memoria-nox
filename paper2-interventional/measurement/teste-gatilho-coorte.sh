#!/usr/bin/env bash
# Suíte do gatilho-coorte.sh — 11 casos + 5 mutações.
#
# ⚠️ Fixture com PROCESSO REAL, não `ls` stubado: um python que abre arquivos de
# verdade e, num caso, ABRE-E-APAGA para produzir um `(deleted)` autêntico em
# /proc/PID/fd. Stubar `ls` testaria o stub; o fd deletado é justamente o que a
# perna existe para enxergar (§10.10), e é onde um regex ancorado erra.
# Só o `systemctl` é stubado, porque não há como criar unidade em teste.
#
# ⚠️ `morre()` recusa contar morte se o mutante não IMPRIMIU status válido — é a
# lição de 09/09: mutante que não compila mata todo caso e não prova nada.
set -uo pipefail
cd "$(dirname "$0")"
G="$PWD/gatilho-coorte.sh"
T="$(mktemp -d /var/tmp/teste-coorte-XXXXXX)"
FALHAS=0
AGORA="2026-09-09T12:00:00Z"
trap 'pkill -P $$ 2>/dev/null; rm -rf "$T"' EXIT

mkdir -p "$T/bin" "$T/epocas"

# ─── fixtures de banco ──────────────────────────────────────────────────────
# corpus(nome, n_servidos, n_nunca, data_nunca)
corpus() {
  local f="$T/$1.db" ns="$2" nn="$3" dt="${4:-2026-09-07}"
  rm -f "$f"
  python3 - "$f" "$ns" "$nn" "$dt" <<'PY'
import sqlite3, sys
f, ns, nn, dt = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
c = sqlite3.connect(f)
c.execute("""CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT,
  importance REAL, pain REAL, source_date TEXT, created_at TEXT)""")
# servidos: ids 1..ns   nunca-servidos: ids 1001..1000+nn
for i in range(1, ns + 1):
    c.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)",
              (i, "memory/entities/lessons/a.md", 0.9, 0.5, None, "2026-08-21 22:51:23"))
for j in range(nn):
    c.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)",
              (1001 + j, "memory/lessons.md", 0.9, 0.4, None, dt))
c.commit()
PY
  printf '%s' "$f"
}
# vivo(nome, ids_servidos_csv, n_briefs)
vivo() {
  local f="$T/$1.db"
  rm -f "$f"
  python3 - "$f" "$2" "$3" <<'PY'
import sqlite3, sys
f, ids, nb = sys.argv[1], sys.argv[2], int(sys.argv[3])
c = sqlite3.connect(f)
c.execute("""CREATE TABLE brief_log (id INTEGER PRIMARY KEY AUTOINCREMENT,
  chunk_id INTEGER, scope TEXT, agent TEXT, served_at TEXT, brief_id TEXT)""")
for cid in [int(x) for x in ids.split(",") if x.strip()]:
    c.execute("INSERT INTO brief_log (chunk_id, served_at, brief_id) VALUES (?,?,?)",
              (cid, "2026-09-08 10:00:00", "b-antigo"))
# briefs DEPOIS da chegada da coorte, para a perna de orcamento
for k in range(nb):
    c.execute("INSERT INTO brief_log (chunk_id, served_at, brief_id) VALUES (?,?,?)",
              (1, "2026-09-08 12:00:00", f"b-{k}"))
c.commit()
PY
  printf '%s' "$f"
}

# ─── serving falso: processo REAL segurando fds reais ───────────────────────
# abre $T/epocas/<nomes>; se o nome comecar com "del:", abre e APAGA (deleted).
serving() {
  local lista="$1"
  python3 - "$T/epocas" "$lista" >/dev/null 2>&1 <<'PY' &
import os, sys, time
d, lista = sys.argv[1], sys.argv[2]
mantidos = []
for nome in lista.split(","):
    if not nome: continue
    apagar = nome.startswith("del:")
    if apagar: nome = nome[4:]
    p = os.path.join(d, nome)
    f = open(p, "rb")
    mantidos.append(f)
    if apagar: os.unlink(p)
time.sleep(120)
PY
  # ⚠️ stdout/stderr para /dev/null: sem isto o `$(serving …)` do chamador espera
  # o processo de fundo FECHAR stdout, e ele dorme 120 s -- a suite travava inteira.
  local pid=$!
  # espera os fds aparecerem
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    [ -d "/proc/$pid/fd" ] && ls -l "/proc/$pid/fd" 2>/dev/null | grep -q "$T/epocas" && break
    sleep 0.2
  done
  cat > "$T/bin/systemctl" <<EOF
#!/bin/sh
echo $pid
EOF
  chmod +x "$T/bin/systemctl"
  printf '%s' "$pid"
}
sem_serving() {
  cat > "$T/bin/systemctl" <<'EOF'
#!/bin/sh
echo 0
EOF
  chmod +x "$T/bin/systemctl"
}

roda() {  # roda <script> <args...> -> imprime a linha de status
  local s="$1"; shift
  PATH="$T/bin:$PATH" "$s" --agora "$AGORA" --fd-prefix "$T/epocas/" "$@" 2>/dev/null | head -1
}
ok()   { echo "ok   $1"; }
falha(){ echo "FALHA $1"; echo "      $2"; FALHAS=$((FALHAS + 1)); }
checa(){ # checa <rotulo> <linha> <estado> <motivo>
  case "$2" in
    "$3 p2-coorte-nunca-servida motivo=$4"*) ok "$1" ;;
    *) falha "$1" "esperava '$3 … motivo=$4', veio: $2" ;;
  esac
}

echo "== casos =="
C_OK="$(corpus c_ok 5 0)"; V_OK="$(vivo v_ok 1,2,3,4,5 0)"
C_60="$(corpus c_60 5 60)"; V_60="$(vivo v_60 1,2,3,4,5 0)"
V_60G="$(vivo v_60g 1,2,3,4,5 400)"   # 400 briefs x 2 slots = 800 >= 60*10=600

cp "$C_60" "$T/epocas/e-com-coorte.db"
cp "$C_OK" "$T/epocas/e-sem-coorte.db"

# T1 corpus ilegivel
L="$(roda "$G" --corpus "$T/nao-existe.db" --vivo "$V_OK")"
checa "T1 corpus ilegivel" "$L" YELLOW corpus-ilegivel
# T2 vivo ilegivel
L="$(roda "$G" --corpus "$C_OK" --vivo "$T/nao-existe.db")"
checa "T2 vivo ilegivel" "$L" YELLOW vivo-ilegivel
# T3 pool vazio
C_VAZIO="$(corpus c_vazio 0 0)"
L="$(roda "$G" --corpus "$C_VAZIO" --vivo "$V_OK")"
checa "T3 pool vazio" "$L" YELLOW pool-vazio
# T4 canal alcancavel (0 nunca-servidos)
sem_serving
L="$(roda "$G" --corpus "$C_OK" --vivo "$V_OK")"
checa "T4 canal alcancavel" "$L" GREEN canal-alcancavel
case "$L" in *nunca_servidos=0*) : ;; *) falha "T4b" "sem nunca_servidos=0: $L";; esac
# T5 serving indeterminado NAO afirma inalcancabilidade
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60")"
checa "T5 serving indeterminado" "$L" YELLOW serving-indeterminado
case "$L" in *corpus_e_o_servido*) falha "T5b" "afirmou sobre o corpus servido sem dado: $L";; *) ok "T5b nao afirma sobre corpus servido sem dado";; esac
# T6 coorte NAO esta no corpus aberto
PID="$(serving "e-sem-coorte.db")"
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60")"
checa "T6 corpus nao e o servido" "$L" RED corpus-nao-e-o-servido
kill "$PID" 2>/dev/null
# T7 coorte alcancavel, orcamento NAO gasto -> transitorio
PID="$(serving "e-com-coorte.db")"
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60")"
checa "T7 bloqueio de reingestao" "$L" YELLOW bloqueio-de-reingestao
# T8 mesma coorte, orcamento GASTO -> estrutural
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60G")"
checa "T8 bloqueio estrutural" "$L" RED bloqueio-estrutural
kill "$PID" 2>/dev/null
# T9 fd DELETADO e reconhecido
cp "$C_60" "$T/epocas/e-del.db"
PID="$(serving "del:e-del.db")"
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60")"
checa "T9 fd deletado reconhecido" "$L" YELLOW bloqueio-de-reingestao
case "$L" in *corpus_e_o_servido=sim*) ok "T9b casou os bytes do inode DELETADO";; *) falha "T9b" "nao casou fd deletado: $L";; esac
kill "$PID" 2>/dev/null
# T10 DOIS fds, coorte no segundo -> nao depende de qual vem primeiro
PID="$(serving "e-sem-coorte.db,e-com-coorte.db")"
L="$(roda "$G" --corpus "$C_60" --vivo "$V_60")"
case "$L" in *fds_abertos=2*corpus_e_o_servido=sim*) ok "T10 dois fds: casa em qualquer um, nao so no primeiro";; *) falha "T10" "$L";; esac
kill "$PID" 2>/dev/null
# T11 status E ndjson em TODA saida, inclusive a de atalho (YELLOW)
sem_serving
rm -f "$T/st.txt" "$T/nd.ndjson"
roda "$G" --corpus "$T/nao-existe.db" --vivo "$V_OK" --status "$T/st.txt" --ndjson "$T/nd.ndjson" >/dev/null
if [ -s "$T/st.txt" ] && grep -q p2_gatilho_coorte "$T/nd.ndjson" 2>/dev/null; then
  ok "T11 atalho grava status E ndjson"
else
  falha "T11" "status=$( [ -s "$T/st.txt" ] && echo sim || echo NAO) ndjson=$(grep -c . "$T/nd.ndjson" 2>/dev/null || echo 0)"
fi

echo
echo "== mutacoes =="
# morre(): so conta morte se o mutante IMPRIMIU status valido (GREEN|YELLOW|RED)
morre() { # morre <rotulo> <sed-expr> <caso-cmd...>
  local rot="$1" expr="$2"; shift 2
  local M="$T/mut.sh"
  sed -E "$expr" "$G" > "$M"; chmod +x "$M"
  if ! bash -n "$M" 2>/dev/null; then falha "$rot" "mutante nao compila"; return; fi
  if cmp -s "$G" "$M"; then falha "$rot" "mutacao NAO aplicada (arquivo identico)"; return; fi
  local out; out="$("$@" 2>/dev/null)"
  case "$out" in
    GREEN*|YELLOW*|RED*) : ;;
    *) falha "$rot" "mutante nao imprimiu status valido: '${out:0:80}'"; return ;;
  esac
  printf '%s' "$out"
}
# M1: perna 4 (serving indeterminado) desativada -> T5 deve virar RED
sem_serving
O="$(morre "M1" 's/^if \[ -n "\$SERV_ERRO" \]; then$/if false \&\& [ -n "$SERV_ERRO" ]; then/' \
      env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "$C_60" --vivo "$V_60")"
case "$O" in RED*corpus-nao-e-o-servido*) ok "M1 mata T5 (sem a perna, afirma divergencia sem dado)";; *) falha "M1" "nao matou: ${O:0:90}";; esac
# M2: `<` viram `<=` no limiar dos slots -> T4 deixa de ser GREEN? (0 < 2 e 0 <= 2 iguais)
#     Caso desenhado: coorte de EXATAMENTE freshSlots. 2 < 2 falso; 2 <= 2 verdadeiro.
C_2="$(corpus c_2 5 2)"; V_2="$(vivo v_2 1,2,3,4,5 0)"
L="$(roda "$G" --corpus "$C_2" --vivo "$V_2")"
case "$L" in YELLOW*serving-indeterminado*) ok "T12 coorte == freshSlots ja bloqueia (nao e GREEN)";; *) falha "T12" "$L";; esac
O="$(morre "M2" 's/if len\(nunca\) < fslots:/if len(nunca) <= fslots:/' \
      env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "$C_2" --vivo "$V_2")"
case "$O" in GREEN*) ok "M2 mata T12 (limiar frouxo declara alcancavel com coorte == slots)";; *) falha "M2" "nao matou: ${O:0:90}";; esac
# M3: ancorar o regex sem ` (deleted)` -> T9 morre
cp "$C_60" "$T/epocas/e-del2.db"
PID="$(serving "del:e-del2.db")"
O="$(morre "M3" 's/\( \\\(deleted\\\)\)\?//' \
      env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "$C_60" --vivo "$V_60")"
case "$O" in YELLOW*serving-indeterminado*|*corpus_e_o_servido=nao*) ok "M3 mata T9 (sem ( deleted) opcional o fd deletado nao casa)";; *) falha "M3" "nao matou: ${O:0:90}";; esac
kill "$PID" 2>/dev/null
# M4: pegar so o primeiro fd -> T10 morre (coorte esta no segundo)
PID="$(serving "e-sem-coorte.db,e-com-coorte.db")"
O="$(morre "M4" 's/\| sort -n -u\)"$/| sort -n -u | head -1)"/' \
      env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "$C_60" --vivo "$V_60")"
case "$O" in *corpus_e_o_servido=nao*) ok "M4 mata T10 (head -1 perde o fd que casa)";; *) falha "M4" "nao matou: ${O:0:90}";; esac
kill "$PID" 2>/dev/null
# M5: orcamento medido por briefs SEM multiplicar por slots -> T8 vira transitorio
PID="$(serving "e-com-coorte.db")"
O="$(morre "M5" 's/out\["oportunidades"\] = briefs \* fslots/out["oportunidades"] = briefs/' \
      env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "$C_60" --vivo "$V_60G")"
case "$O" in YELLOW*bloqueio-de-reingestao*) ok "M5 mata T8 (oportunidade != brief; 400 briefs = 800 slots)";; *) falha "M5" "nao matou: ${O:0:90}";; esac
kill "$PID" 2>/dev/null

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS FALHA(S)"
exit "$FALHAS"
