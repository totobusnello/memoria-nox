#!/usr/bin/env bash
# teste-controle-negativo.sh — as quatro pernas do controle-negativo-intra-braco.py.
#
# Fixtures por SUBTRACAO do log real (nunca construidas do zero): a licao de 2026-09-10
# e que stub construido do zero embute a suposicao que estava em teste.
#
# Uso: bash teste-controle-negativo.sh [caminho-do-log]
set -uo pipefail
LOG="${1:-/root/.openclaw/logs/p2-serving.ndjson}"
CN="$(dirname "$0")/controle-negativo-intra-braco.py"
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
ok=0; falhou=0

diz() { # $1=rotulo $2=exit-esperado $3=exit-obtido
  if [ "$2" = "$3" ]; then printf "  ok    %-46s exit=%s\n" "$1" "$3"; ok=$((ok+1))
  else printf "  FALHA %-46s exit=%s esperado=%s\n" "$1" "$3" "$2"; falhou=$((falhou+1)); fi
}

[ -r "$LOG" ] || { echo "log ilegivel: $LOG — teste NAO avaliavel"; exit 2; }

python3 - "$D" "$LOG" <<'PY'
import json, sys
D, L = sys.argv[1], sys.argv[2]
a = open(D+"/semdesig.ndjson","w"); c = open(D+"/viola.ndjson","w"); injetou=False
for ln in open(L, encoding="utf-8", errors="replace"):
    ln = ln.strip()
    if not ln: continue
    d = json.loads(ln)
    d2 = dict(d); d2.pop("designated_ids", None); a.write(json.dumps(d2)+"\n")
    ci, t, dg = d.get("ids_controle"), d.get("ids_tratado"), d.get("designated_ids")
    if (not injetou and d.get("modo") == "active" and ci is not None and t is not None
            and dg is not None and str(d.get("epoch"))[:10] >= "2026-09-01"
            and not (set(dg) & (set(ci) | set(t)))):
        d = dict(d); d["ids_tratado"] = list(t) + ["ZZZ-INJETADO"]; injetou = True
    c.write(json.dumps(d)+"\n")
a.close(); c.close()
if not injetou:
    print("  FALHA fixture: nenhum brief sem alcance para injetar — teste C nao avaliavel")
    sys.exit(3)
PY
[ $? -eq 0 ] || { echo "  fixtures nao construidas"; exit 3; }

python3 "$CN" --log "$LOG"                  --out "$D/real.json" >/dev/null 2>&1; diz "real: passa"                    0 $?
python3 "$CN" --log "$D/semdesig.ndjson"    --out "$D/a.json"    >/dev/null 2>&1; diz "sem designated_ids: indeterminavel" 2 $?
python3 "$CN" --log "$LOG" --desde 2027-01-01 --out "$D/b.json"  >/dev/null 2>&1; diz "janela vazia: nao avaliavel"     2 $?
python3 "$CN" --log "$D/viola.ndjson"       --out "$D/c.json"    >/dev/null 2>&1; diz "violacao injetada"               1 $?
python3 "$CN" --log "$D/nao-existe.ndjson"                       >/dev/null 2>&1; diz "log inexistente"                 2 $?

# A perna CONTRATUAL: exit code carrega o veredito, artefato carrega a evidencia.
# Sem ela, um guarda que retorna antes do --out passa nos quatro casos acima.
if [ -f "$D/c.json" ] && python3 -c "
import json,sys
d=json.load(open('$D/c.json'))
sys.exit(0 if (d['controle_negativo']['passa'] is False and d['controle_negativo']['violacoes']==1) else 1)"; then
  printf "  ok    %-46s\n" "artefato existe E acusa, apesar do exit 1"; ok=$((ok+1))
else
  printf "  FALHA %-46s\n" "artefato ausente ou mudo na falha"; falhou=$((falhou+1))
fi

echo "  --- $ok ok, $falhou falhas ---"
[ "$falhou" -eq 0 ]
