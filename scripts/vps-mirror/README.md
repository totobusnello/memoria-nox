# vps-mirror — Snapshots dos scripts rodando na VPS

Estes arquivos são **cópias de consulta** dos scripts deployados em `/root/.openclaw/scripts/` na VPS (root@100.87.8.44). Ficam fora do git do workspace da VPS por convenção operacional, então espelhamos aqui pra ter backup + histórico no git do Mac/GitHub.

**Não editar estes arquivos diretamente** — eles NÃO são deployados por commit. Fluxo correto:

1. Editar na VPS (`ssh root@100.87.8.44 'vim /root/.openclaw/scripts/<script>.sh'`) ou via scp local + upload
2. Testar na VPS
3. Atualizar o espelho aqui: `scp root@100.87.8.44:/root/.openclaw/scripts/<script>.sh vps-mirror/`
4. Commitar a cópia

## Scripts espelhados

| Arquivo | Função | Cron |
|---|---|---|
| `health-probe.sh` | Probe de serviços (gateway, api, disco, SQLite) | */5 min |
| `semantic-canary.sh` | Valida Layer 2 semantic com query natural | 06:00 diário |
| `morning-report.sh` | Resumo de saúde 24h pra Discord `#nox-chief-of-staff` | 06:30 diário |
| `nightly-maintenance.sh` | Reindex → consolidate → session-distill → vectorize → kg-build | 23:00 diário |

## Última sincronização

2026-04-19 07:25 — após fixes de ordem no nightly e threshold inteligente em morning-report.
