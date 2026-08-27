# /root/.openclaw/scripts/p2 — implantação, não fonte

A **fonte de verdade** destes arquivos é o repo `memoria-nox`, em
`paper2-interventional/measurement/`. Esta pasta é uma cópia implantada; editar aqui
faz o repo e a produção divergirem em silêncio, que é exatamente o defeito que o
item 8 do protocolo existe para evitar.

| arquivo | item do protocolo | cadência |
|---|---|---|
| `replay-oportunidade.mjs` | 1 — a harness canônica | sob demanda + chamada por (a) |
| `gatilho-composicao.mjs`  | 7(b) — composição do canal | horária |
| `gatilho-saturacao.sh`    | 7(a) — saturação da dose | diária |

Status em `/var/lib/nox-mem/p2/`, lido pelo `morning-report.sh` às 06:30Z.
`node_modules` é symlink para o do nox-mem — os gatilhos não têm deps próprias.
