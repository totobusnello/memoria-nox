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

# ── T13: `--corpus` apontando para o fd de um DB APAGADO. Tres asserções, e a
#        (ii) é a que importa.
#
# 🔴 Medido 2026-09-09: `sqlite3.connect("/proc/PID/fd/N")` SEM o prefixo `file:`
# ABRE com sucesso e apresenta banco VAZIO (`sqlite_master` = 0 objetos) — logo
# uma consulta a `chunks` falha com `no such table`, e o veredito `corpus-ilegivel`
# sairia por ACIDENTE, não por desenho. Um probe escrito
# `SELECT count(*) FROM sqlite_master` passaria calado.
#
# 🔴 E o `connect()` SOZINHO — sem query, sem `INSERT`, sem `commit` — MATERIALIZA
# arquivo no disco, porque o modo padrão de abertura é read-write-CREATE. O nome
# é o texto do symlink, sufixo incluído: `orig.db (deleted)`, banco válido. Em
# produção isso nasceria dentro de `/var/lib/nox-mem/epochs/`, o diretório do
# ensaio, disparado por um guarda estritamente READ-ONLY.
#
# ⚠️ Correção de 2026-09-09, e as duas sessões erraram a mesma atribuição antes:
# escrevemos "é a escrita que cria". NÃO É. Isolado em três etapas contra o
# mesmo fd, com a listagem impressa DEPOIS DE CADA UMA e o diretório limpo entre
# elas: `file:…?mode=ro` → exceção, listagem `[]`; `connect(p)` sem query →
# nenhuma exceção, listagem `[orig.db (deleted)]`; `connect(p)` + SELECT → `no
# such table`, listagem igual. A atribuição anterior vinha de inferir causa da
# ORDEM da saída, sem listagem intermediária — medição que não discriminava.
#
# ⇒ (ii) exige que a recusa venha do MODO DE ABERTURA (`file:…?mode=ro` falha
#   ALTO, "unable to open database file") e não de tabela ausente.
# ⇒ (iii) e (iv) são asserções de EFEITO COLATERAL — as primeiras desta suíte.
#   Medido: sob `ro()` → `connect(p)` as TRÊS morrem (a listagem passa de `[]`
#   para `[ap.db (deleted)]`), não só a (ii).
python3 - "$T/epocas" <<'PYD' >/dev/null 2>&1 &
import os, sqlite3, sys, time
d = sys.argv[1]
p = os.path.join(d, "apagado.db")
c = sqlite3.connect(p); c.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
c.execute("INSERT INTO chunks VALUES (1)"); c.commit(); c.close()
f = open(p, "rb"); os.unlink(p)
time.sleep(90)
PYD
PIDD=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  ls -l "/proc/$PIDD/fd" 2>/dev/null | grep -q "apagado.db" && break
  sleep 0.3
done
FDD="$(ls -l "/proc/$PIDD/fd" 2>/dev/null | sed -nE 's#^.* ([0-9]+) -> .*apagado\.db( \(deleted\))?$#\1#p' | head -1)"
if [ -z "$FDD" ]; then
  falha "T13" "nao consegui montar fixture de fd apagado"
else
  ANTES="$(ls -la "$T/epocas" | tail -n +2)"
  L="$(roda "$G" --corpus "/proc/$PIDD/fd/$FDD" --vivo "$V_OK")"
  DEPOIS="$(ls -la "$T/epocas" | tail -n +2)"
  checa "T13 fd apagado como corpus" "$L" YELLOW corpus-ilegivel
  case "$L" in
    *"unable to open"*) ok "T13b recusa vem do MODO DE ABERTURA, nao de tabela ausente" ;;
    *"no such table"*) falha "T13b" "abriu banco VAZIO e culpou a tabela: $L" ;;
    *) falha "T13b" "detalhe inesperado: $L" ;;
  esac
  if [ "$ANTES" = "$DEPOIS" ]; then
    ok "T13c nenhum arquivo materializado no diretorio do fd"
  else
    falha "T13c" "EFEITO COLATERAL: a listagem mudou"
  fi
  if ls -1 "$T/epocas" | grep -qF "(deleted)"; then
    falha "T13d" "criou arquivo com sufixo (deleted) no nome"
  else
    ok "T13d sem arquivo de nome '(deleted)'"
  fi
fi
kill "$PIDD" 2>/dev/null

# ── T14: o RECIBO carrega o corpus como CAMPO, no caminho comum (GREEN) ──
# O sha nascia na perna de alcançabilidade, então todo veredito anterior — incluindo
# o GREEN `canal-alcancavel`, que é o caminho comum — saía com o corpus identificado
# só por `basename` dentro de um blob de texto. Basename nomeia caminho; sha
# identifica bytes, e bytes é o que distingue os dois corpora deste ensaio.
# Este caso existe porque a suíte ficava VERDE com e sem a correção: nenhum caso
# olhava o NDJSON, só a linha de status.
sem_serving
ND="$T/recibo.ndjson"; : > "$ND"
L="$(roda "$G" --corpus "$C_OK" --vivo "$V_OK" --ndjson "$ND")"
checa "T14 recibo no caminho comum" "$L" GREEN canal-alcancavel
SHA_ESPERADO="$(sha256sum "$C_OK" | cut -d' ' -f1)"
R="$(python3 -c "
import json
r=json.loads(open('$ND').read().strip().splitlines()[-1])
falta=[k for k in ('corpus_path','corpus_sha256','pool_global','nunca_servidos') if k not in r]
print('FALTAM=' + ','.join(falta) if falta else 'CAMPOS=ok')
print('SHA=' + r.get('corpus_sha256',''))
print('PATH=' + r.get('corpus_path',''))
" 2>/dev/null)"
case "$R" in
  *CAMPOS=ok*) ok "T14a corpus_path/corpus_sha256/pool_global/nunca_servidos sao CAMPOS" ;;
  *) falha "T14a" "recibo sem campos: $(printf '%s' "$R" | tr '\n' ' ')" ;;
esac
case "$R" in
  *"SHA=$SHA_ESPERADO"*) ok "T14b corpus_sha256 e o sha REAL do argumento" ;;
  *) falha "T14b" "sha divergente; esperava $SHA_ESPERADO em: $(printf '%s' "$R" | tr '\n' ' ')" ;;
esac
case "$R" in
  *"PATH=$C_OK"*) ok "T14c corpus_path e o argumento, nao o basename" ;;
  *) falha "T14c" "corpus_path errado: $(printf '%s' "$R" | tr '\n' ' ')" ;;
esac

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

# M6: `ro()` deixa de usar a forma URI `file:…?mode=ro` e passa a `connect()`
#     simples. Sob ele o fd apagado ABRE (banco vazio) e o veredito ainda sai
#     `corpus-ilegivel` — por `no such table`, não por recusa. Nenhum dos outros
#     12 casos morre; só T13b, que asserta a ORIGEM da recusa. Mutante proposto
#     pela sessão par, e ele mira o que este script IA fazer antes da medição do
#     `/proc` obrigar a reformular.
python3 - "$T/epocas" <<'PYE' >/dev/null 2>&1 &
import os, sqlite3, sys, time
d = sys.argv[1]; p = os.path.join(d, "apagado2.db")
c = sqlite3.connect(p); c.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
c.commit(); c.close()
f = open(p, "rb"); os.unlink(p); time.sleep(60)
PYE
PIDE=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  ls -l "/proc/$PIDE/fd" 2>/dev/null | grep -q "apagado2.db" && break
  sleep 0.3
done
FDE="$(ls -l "/proc/$PIDE/fd" 2>/dev/null | sed -nE 's#^.* ([0-9]+) -> .*apagado2\.db( \(deleted\))?$#\1#p' | head -1)"
if [ -z "$FDE" ]; then
  falha "M6" "nao consegui montar fixture"
else
  O="$(morre "M6" 's#return sqlite3.connect\(f"file:\{p\}\?mode=ro", uri=True\)#return sqlite3.connect(p)#' \
        env PATH="$T/bin:$PATH" "$T/mut.sh" --agora "$AGORA" --fd-prefix "$T/epocas/" --corpus "/proc/$PIDE/fd/$FDE" --vivo "$V_OK")"
  case "$O" in
    *"no such table"*) ok "M6 mata T13b (connect simples abre banco vazio; recusa vira acidente)" ;;
    *) falha "M6" "nao matou: ${O:0:110}" ;;
  esac
fi
kill "$PIDE" 2>/dev/null

# M7: os campos do recibo voltam a ser blob de texto -> T14a tem de morrer.
# Mutação SEMÂNTICA (troca de expressão), nunca `d` de faixa: apagar linhas aqui
# cairia DENTRO do heredoc PYND, o mutante morreria de syntax error e "mataria"
# todo caso — evidência sobre perna nenhuma (a variante (c) da lição de mutação).
M7="$T/mut7.sh"
sed -E 's/^        if k not in rec:/        if False and k not in rec:/' "$G" > "$M7"
chmod +x "$M7"
if cmp -s "$G" "$M7"; then
  falha "M7" "mutacao NAO aplicada"
elif ! bash -n "$M7" 2>/dev/null; then
  falha "M7" "mutante nao compila"
else
  sem_serving; ND7="$T/recibo7.ndjson"; : > "$ND7"
  O7="$(roda "$M7" --corpus "$C_OK" --vivo "$V_OK" --ndjson "$ND7")"
  case "$O7" in
    GREEN*|YELLOW*|RED*)
      R7="$(python3 -c "
import json
r=json.loads(open('$ND7').read().strip().splitlines()[-1])
print('TEM' if 'pool_global' in r else 'SEM')
" 2>/dev/null)"
      case "$R7" in
        SEM) ok "M7 mata T14a (sem os campos, o recibo volta a ser texto)" ;;
        *)   falha "M7" "nao matou: pool_global segue campo" ;;
      esac ;;
    *) falha "M7" "mutante nao imprimiu status valido: '${O7:0:80}'" ;;
  esac
fi

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS FALHA(S)"
exit "$FALHAS"
