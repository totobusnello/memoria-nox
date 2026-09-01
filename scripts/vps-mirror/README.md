# vps-mirror — Snapshots dos scripts rodando na VPS

Cópias **de consulta** dos scripts deployados em `/root/.openclaw/scripts/`. Servem
para ler e diffar a partir do Mac, com histórico em git.

> ⚠️ **Não editar aqui.** Estes arquivos **não** são deployados por commit. Editar
> este espelho não muda nada em produção e cria divergência silenciosa.

## ⚠️ Este espelho é a QUARTA cópia, e não é a fonte de deploy

Descoberto em 2026-09-01, ao corrigir o `semantic-canary.sh`:

| # | caminho | papel |
|---|---|---|
| 1 | `/root/.openclaw/scripts/<script>.sh` (VPS) | **o que executa** |
| 2 | `/root/repos/openclaw-vps/infra/scripts/…` (clone na VPS) | fonte de deploy |
| 3 | `Projetos/openclaw-vps/infra/scripts/…` (clone no Mac) | **de onde sai o commit** |
| 4 | `memoria-nox/scripts/vps-mirror/…` | este espelho, só leitura |

Corrigir (1) sem propagar para (2) e (3) faz o próximo deploy reverter a correção.
Corrigir (4) não faz nada em lugar nenhum.

⚠️ (2) e (3) são clones do mesmo remote em máquinas diferentes — um `find` rodado
só na VPS enxerga (1) e (2) e **não** vê (3).

Pelo roteamento do `Projetos/CLAUDE.md`, scripts de plataforma pertencem a
`openclaw-vps/infra/`. Este diretório nasceu antes desse repo existir e hoje é
redundante com (2)/(3) — **candidato a remoção**, pendente de decisão do Toto. Enquanto
existir, tem de ser sincronizado, senão vira documentação que mente.

## Fluxo correto de mudança

1. editar em (1) na VPS e testar lá
2. propagar para (2) e abrir PR no `openclaw-vps`
3. ressincronizar este espelho: `scp root@<vps>:/root/.openclaw/scripts/<script>.sh vps-mirror/`
4. commitar (3)

Se o script tiver linha no crontab, ver também
`openclaw-vps/infra/runbooks/crontab-canonical.md` — o horário vive em **quatro**
lugares que precisam bater.

## Scripts espelhados

| Arquivo | Função | Cron real |
|---|---|---|
| `health-probe.sh` | Probe de serviços (gateway, api, disco, SQLite) | `*/10` |
| `semantic-canary.sh` | Valida a camada semântica com query PT-BR natural | `16,46` |
| `morning-report.sh` | Resumo de saúde 24h para o Discord | `30 6 * * *` |
| `nightly-maintenance.sh` | reindex → consolidate → session-distill → vectorize → kg-build | `0 23 * * *` |

## Última sincronização

**2026-09-01** — os quatro espelhos estavam divergentes da VPS (o README anterior
datava de 2026-04-19 e listava três dos quatro crons errados: canary como
"06:00 diário", health-probe como `*/5`).

O `semantic-canary.sh` desta rodada traz duas mudanças de 01/09:

- `parse_summary` passa a contar `match_type: "hybrid"` como semântica **e** como
  fts. Sem isso, uma resposta em que todo resultado veio das duas listas era lida
  como `semantic=0` e disparava RED com a busca saudável — seis falsos alarmes num
  dia;
- **COVERAGE-GATE** antes do `vectorize` do self-heal: com `embedded == total` e
  `orphans == 0` não há o que vetorizar, e chamar o Gemini ali gasta a quota do
  mesmo provider que acabou de recusar.

Post-mortem completo em
`openclaw-vps/infra/lessons/2026-09-01-canary-hybrid-false-red.md`.

## Verificação rápida de drift

```bash
for f in health-probe.sh semantic-canary.sh morning-report.sh nightly-maintenance.sh; do
  L=$(shasum -a 256 "$f" | cut -c1-10)
  R=$(ssh root@<vps> "sha256sum /root/.openclaw/scripts/$f | cut -c1-10")
  printf "%-26s %s %s %s\n" "$f" "$L" "$R" "$([ "$L" = "$R" ] && echo ok || echo DIVERGE)"
done
```
