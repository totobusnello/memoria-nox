# implantacao/ — os wrappers que o cron chama, versionados

Estes arquivos vivem em `/root/.openclaw/scripts/p2/` na VPS. **Estão aqui porque a
cópia implantada não pode ser a única.** O `PROCEDENCIA.md` que acompanha a implantação
diz que a fonte é o repo; se os wrappers existissem só lá, essa frase seria falsa e a
configuração real do monitoramento — quais caminhos, qual corpus, qual teto de tempo —
não estaria em nenhum histórico.

| arquivo | papel |
|---|---|
| `run-composicao.sh` | wrapper horário do 7(b); carrega `.env` |
| `run-saturacao.sh` | wrapper diário do 7(a); lê a configuração do **unit do systemd**, com `timeout 1500` |
| `PROCEDENCIA.md` | o aviso que fica ao lado da cópia implantada |

## Cron instalado (2026-08-27, crontab 40 → 42 linhas)

```
9 * * * * /root/.openclaw/scripts/p2/run-composicao.sh >> /var/log/nox-p2-gatilhos.log 2>&1 # p2-composicao
41 5 * * * flock -n /tmp/nox-p2-saturacao.lock /root/.openclaw/scripts/p2/run-saturacao.sh >> /var/log/nox-p2-gatilhos.log 2>&1 # p2-saturacao
```

Backup do crontab anterior em `/root/.openclaw/crontab.bak-20260827T175704Z`. Instalado
via arquivo com conferência de contagem — **nunca** `crontab -l | ... | crontab -`, que
já zerou este crontab uma vez.

## Por que o (a) lê o systemd e não o `.env`

`NOX_P2_DESIGNATION`, `NOX_P2_DESIGNATION_SHA256`, `NOX_P2_OUTCOME` e
`NOX_P2_SHADOW_W` são declarados no **drop-in do serviço**, não no `.env`. É de lá que a
produção lê. Um gatilho que lesse de outro lugar vigiaria uma configuração que ninguém
está usando — o defeito exato que o item 7 original tinha.
