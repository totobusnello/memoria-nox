#!/usr/bin/env bash
# Barra blob NOVO e grande antes de entrar num repositorio PUBLICO.
#
# Por que existe: `eval/q4-comparison/output/.gitignore` diz `*.json` porque os
# outputs sao grandes -- e nove deles foram versionados a forca de todo modo. A
# regra de ignore protege ate alguem escrever `git add -f`. Um `git add -A` num
# diretorio de eval publicaria ~500 MB de lastro de benchmark, e o repositorio e
# publico: os bytes ficam no historico mesmo depois de um `git rm`.
#
# O que ele NAO faz: impedir que se atualize um arquivo grande que JA esta
# versionado. Barrar isso travaria os nove outputs que estao la de proposito, e o
# guarda seria desligado no primeiro dia. So o blob NOVO passa pelo crivo.
set -uo pipefail

LIMITE_MB="${LIMITE_MB:-5}"
limite=$((LIMITE_MB * 1024 * 1024))

# Arquivos grandes que ESTAO versionados de proposito ficam isentos por ja
# existirem -- nao por lista. A lista abaixo e para o caso de um arquivo novo
# que se decidiu, explicitamente, versionar apesar do tamanho.
ISENTOS=(
)

esta_isento() {
  local alvo="$1"
  for i in "${ISENTOS[@]:-}"; do [ "$i" = "$alvo" ] && return 0; done
  return 1
}

modo="${1:-staged}"
case "$modo" in
  staged) lista=$(git diff --cached --name-only --diff-filter=AM) ;;
  tudo)   lista=$(git ls-files) ;;
  *) echo "uso: $0 [staged|tudo]" >&2; exit 2 ;;
esac

# "Ja era versionado antes deste commit?" -- perguntado ao git por objeto, nao
# por busca de substring numa lista. Um `grep -qxF` sobre `git ls-tree` casava o
# caminho fora do laco de leitura e falhava dentro dele; a causa nao ficou
# estabelecida, e por isso mesmo o predicado passou a ser o idioma nativo, que
# nao depende de como a string atravessou o shell.
ja_versionado() { git cat-file -e "HEAD:$1" 2>/dev/null; }

violacoes=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  tam=$(wc -c < "$f" | tr -d ' ')
  [ "$tam" -le "$limite" ] && continue
  if ja_versionado "$f"; then
    printf '  ok (ja versionado, %.1f MB)  %s\n' "$(echo "$tam" | awk '{print $1/1048576}')" "$f"
    continue
  fi
  esta_isento "$f" && { echo "  ok (isento)  $f"; continue; }
  printf '🔴 BLOB NOVO DE %.1f MB  %s\n' "$(echo "$tam" | awk '{print $1/1048576}')" "$f" >&2
  violacoes=$((violacoes + 1))
done <<< "$lista"

if [ "$violacoes" -gt 0 ]; then
  cat >&2 <<MSG

$violacoes arquivo(s) novo(s) acima de ${LIMITE_MB} MB. Este repositorio e PUBLICO e o
historico do git nao esquece: um \`git rm\` posterior nao apaga os bytes.

Se for lastro de benchmark, o padrao do repo e NAO versionar os bytes e registrar
o sha256 no manifesto:

    python3 scripts/manifesto-lastro.py

Se for deliberado, acrescente o caminho a ISENTOS em scripts/guarda-blob-grande.sh,
no mesmo commit, com o motivo no corpo da mensagem.
MSG
  exit 1
fi
echo "guarda-blob-grande: nenhum blob novo acima de ${LIMITE_MB} MB"
