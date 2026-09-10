# Corrida 2026-09-10 — diretório próprio, de propósito

Não misturada em `output/` por duas razões medidas, não por estética:

1. **`output/zep.json` é citado nominalmente pelo manuscrito** (linhas 1161 e 1184
   de `paper/paper-tecnico-nox-mem.md`): o smoke de 2026-05-25, n=20, divulgado
   deliberadamente para que um leitor que abra `output/` não leia contradição.
   Escrever a corrida de hoje por cima apagaria a prova do que está publicado.
   (Eu movi esse arquivo por engano ao preparar isto, e desfiz — o `git mv`
   quebra a citação tão bem como o sobrescrever.)

2. **`aggregate.py` deriva o nome do sistema de `meta.system`**, e o glob é
   `*.json` não-recursivo. Dois artefatos de `system: "zep"` no mesmo diretório
   dariam duas linhas rotuladas "zep", sem o leitor distinguir n=20 (25/05) de
   n=2482 (10/09) — o mesmo defeito da tabela de retenção que juntava duas
   populações sem nomear a corrida.

Agregar com: `python3 aggregate.py --output-dir output-2026-09-10 --k 10`

⚠️ `output/evermind.json` (stub de 2026-05-23: `n_queries=5, n_errors=5`, 5
entradas em `queries`) **não está sob controle de versão** — o `git mv` recusou.
É estado local, não artefato versionado, e o manuscrito não o cita por caminho.
