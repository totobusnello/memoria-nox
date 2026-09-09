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
| `run-designados.sh` | wrapper horário da integridade dos 19 designados; lê o unit |
| `run-corpus-alinhado.sh` | wrapper horário do §10.10 — de qual **inode** o serving lê |
| `run-heartbeat.sh` | wrapper horário do "o serving parou" + "a unidade que fechou está inteira" |
| `restart-realinha-corpus.sh` | ação one-shot, 5 pré-condições que abortam |
| `PROCEDENCIA.md` | o aviso que fica ao lado da cópia implantada |

⚠️ As quatro linhas do meio entraram nesta tabela em 2026-09-09. Os arquivos existiam
no diretório desde 08/09 (`run-designados`, `run-corpus-alinhado`, `restart-realinha`) e
a tabela listava só dois — ou seja, o documento que existe para que *"a cópia implantada
não seja a única"* estava omitindo metade dos wrappers implantados. Ao acrescentar
wrapper, acrescentar a linha: uma tabela incompleta é pior que tabela ausente, porque
parece completa.

## Cron instalado (2026-08-27, crontab 40 → 42 linhas)

```
9 * * * * /root/.openclaw/scripts/p2/run-composicao.sh >> /var/log/nox-p2-gatilhos.log 2>&1 # p2-composicao
41 5 * * * flock -n /tmp/nox-p2-saturacao.lock /root/.openclaw/scripts/p2/run-saturacao.sh >> /var/log/nox-p2-gatilhos.log 2>&1 # p2-saturacao
```

⚠️ O horário do `p2-saturacao` mudou para `12 9 * * *` em 2026-08-28 (o de 05:41Z
deixava o `morning-report` cego por um dia inteiro a uma rodada pulada). O bloco acima
é o histórico da instalação; o crontab vivo é o de baixo.

## Cron acrescentado (2026-09-09, crontab 61 → 62 linhas)

```
54 * * * * /root/.openclaw/scripts/p2/run-heartbeat.sh >> /var/log/nox-p2-gatilhos.log 2>&1 # p2-heartbeat
```

Backup em `/root/.openclaw/crontab.bak-20260909T100533Z`, contagem conferida antes e
depois (61 → 62), com restauração automática se a pós-instalação divergisse.

Minuto **:54** para não colidir com nenhum outro gatilho (:9 composição, :24 designados,
:39 corpus-alinhado) nem com o `brief-refresh` (:7, :22, :37, :52) — o guarda mede a
idade do último registro, e medi-la no mesmo minuto em que a rajada escreve daria uma
leitura sistematicamente otimista.

Ligado ao `morning-report.sh` na mesma sessão, com teto de idade **3 h** (idade normal
0,6 h; 3 rodadas puladas = 3,6 h ⇒ dispara). Sem essa linha o guarda escreveria num
arquivo que ninguém lê.

🔴 **Divergência pré-existente, não consertada aqui:** a cópia do `morning-report.sh` em
`/root/repos/openclaw-vps/infra/scripts/` está de 04/09 e **já divergia** da viva antes
desta edição (`md5` diferente). O canônico dele é o repo `openclaw-vps/infra`, não este
— a linha do heartbeat foi acrescentada na cópia **viva**, e a reconciliação das duas é
trabalho daquele repo.

Backup do crontab anterior em `/root/.openclaw/crontab.bak-20260827T175704Z`. Instalado
via arquivo com conferência de contagem — **nunca** `crontab -l | ... | crontab -`, que
já zerou este crontab uma vez.

## Por que o (a) lê o systemd e não o `.env`

`NOX_P2_DESIGNATION`, `NOX_P2_DESIGNATION_SHA256`, `NOX_P2_OUTCOME` e
`NOX_P2_SHADOW_W` são declarados no **drop-in do serviço**, não no `.env`. É de lá que a
produção lê. Um gatilho que lesse de outro lugar vigiaria uma configuração que ninguém
está usando — o defeito exato que o item 7 original tinha.
