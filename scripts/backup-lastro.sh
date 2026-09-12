#!/usr/bin/env bash
# Copia o lastro declarado no MANIFESTO-LASTRO.json para fora do repositorio, e
# VERIFICA A COPIA -- nao a origem.
#
# Por que a distincao importa: um manifesto gerado na origem e copiado junto com
# os arquivos nao prova nada sobre a copia. O sha256 tem de ser recalculado no
# destino e comparado com o declarado. Feito de outro modo, "backup verificado"
# quer dizer "origem verificada, destino esperancoso".
#
# ⚠️ O que este script NAO resolve: destino no mesmo disco fisico e o mesmo ponto
# de falha da origem. Ele imprime um aviso quando detecta isso. Copia off-machine
# de verdade (disco externo, iCloud/Drive, deposito restrito) e escolha do dono.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFESTO="$REPO/eval/q4-comparison/MANIFESTO-LASTRO.json"
DEST="${1:-}"

[ -z "$DEST" ] && { echo "uso: $0 <diretorio-de-destino>" >&2; exit 2; }
[ -f "$MANIFESTO" ] && : || { echo "manifesto ausente: $MANIFESTO" >&2; exit 2; }

mkdir -p "$DEST" || exit 2

# mesmo dispositivo que a origem? entao nao e backup contra falha de disco
dev_o=$(stat -f %d "$REPO" 2>/dev/null || echo o)
dev_d=$(stat -f %d "$DEST" 2>/dev/null || echo d)
mesmo_disco=0
[ "$dev_o" = "$dev_d" ] && mesmo_disco=1

python3 - "$REPO" "$MANIFESTO" "$DEST" <<'PY'
import hashlib, json, os, shutil, sys

repo, manifesto, dest = sys.argv[1:4]
with open(manifesto, encoding="utf-8") as fh:
    arte = json.load(fh)["artefatos"]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

copiados = divergentes = ausentes = 0
total = 0
recibo = {}
for rel, e in sorted(arte.items()):
    if e.get("estado") != "presente":
        print(f"  pula (nao presente na origem)  {rel}")
        continue
    orig = os.path.join(repo, rel)
    if not os.path.exists(orig):
        print(f"🔴 origem desapareceu  {rel}", file=sys.stderr); ausentes += 1; continue
    alvo = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    shutil.copy2(orig, alvo)
    # sidecars do SQLite viajam junto, senao a copia e de um estado incompleto
    for suf in ("-wal", "-shm"):
        if os.path.exists(orig + suf):
            shutil.copy2(orig + suf, alvo + suf)
    # o hash e recalculado NO DESTINO e comparado com o DECLARADO
    obtido = sha(alvo)
    esperado = e.get("sha256")
    if obtido != esperado:
        print(f"🔴 COPIA DIVERGE  {rel}\n   declarado {esperado}\n   na copia  {obtido}",
              file=sys.stderr)
        divergentes += 1
        continue
    copiados += 1
    total += e.get("bytes", 0)
    recibo[rel] = {"sha256_verificado_no_destino": obtido, "bytes": e.get("bytes")}
    print(f"  ok  {obtido[:16]}  {rel}")

with open(os.path.join(dest, "RECIBO-VERIFICACAO.json"), "w", encoding="utf-8") as fh:
    json.dump({"copiados": copiados, "divergentes": divergentes,
               "ausentes_na_origem": ausentes, "bytes": total,
               "artefatos": recibo}, fh, indent=2, ensure_ascii=False)

print(f"\ncopiados e VERIFICADOS na copia: {copiados}  ({total/1e6:.1f} MB)")
print(f"divergentes: {divergentes}   ausentes na origem: {ausentes}")
sys.exit(1 if (divergentes or ausentes) else 0)
PY
ec=$?

if [ "$mesmo_disco" = "1" ]; then
  cat >&2 <<MSG

⚠️ O destino esta no MESMO dispositivo que a origem. Isto protege contra
   \`rm\`/\`git clean\` dentro do repo, e NAO contra falha do disco. Para copia
   off-machine, repita com destino em disco externo, iCloud/Drive, ou deposito
   restrito com DOI.
MSG
fi
exit $ec
