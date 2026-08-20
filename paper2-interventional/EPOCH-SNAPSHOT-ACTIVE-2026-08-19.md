# `NOX_EPOCH_SNAPSHOT`: shadow → active

> O estimando registrado (§0/§2) exige que o brief seja servido a partir do
> **snapshot de epoch**, não do live. Virado 2026-08-19, autorizado pelo Toto.

## A evidência — e por que NÃO é a do ShadowTracker

O plano dizia "virar com soak". O soak que eu imaginava não existia:

**`ShadowTracker` é ring buffer em memória** (`Map<feature, Map<hour_ts, bucket>>`,
`lib/shadow-tracker.ts:198-202`). Os 17 comparativos que eu li não eram 24 h de
dados — eram **25 minutos**, desde um restart que eu mesmo havia feito. E o flip
**exige** restart, então a evidência que o justificaria é apagada pelo próprio ato
de flipar. Um soak que não sobrevive a restart não é soak.

A evidência durável estava em outro lugar: os **snapshots de epoch em disco**
(`/var/lib/nox-mem/epochs/`, com manifesto e integridade). Medido diretamente —
brief construído do snapshot vs brief construído do live, mesma `CFG`, mesmos
agentes:

| agente | itens que mudariam |
|---|---|
| nox · atlas · boris · cipher · forge · lex | **0/10 cada** |
| **total** | **0/60 — 0,0%** |

**O flip é no-op hoje**, e é reproduzível (`diverg.mjs`), não uma leitura de buffer
volátil.

⚠️ **E o soak não testa o mecanismo sob carga.** O corpus está estático desde que a
autoria de entity files parou (**2026-07-10**). A primeira divergência real virá
das escritas do próprio estudo. Dizer "soakado" sem esta ressalva seria alegar
evidência que não existe.

## Estado depois do flip

| | |
|---|---|
| modo | `active` |
| snapshot servido | `e20260820T090001Z` (rotacionou durante a noite **em modo active**, sem quebrar) |
| `degraded` | `false` |
| briefs | idênticos ao baseline pré-deploy nos 3 agentes com baseline |
| erros no log | 0 |

A rotação noturna sob `active` é o primeiro ponto de soak real: **uma fronteira de
epoch sobreviveu ao novo modo**.

## ⚠️ O erro no caminho: drop-in sem `[Service]` cai para `off`, em silêncio

A primeira escrita do drop-in saiu **sem o cabeçalho `[Service]`**. O systemd
ignorou a linha `Environment=` sem reclamar, e o modo foi para **`off`** — não
`active`, e **não** de volta para `shadow`: **desligado**.

Duas lições, e a segunda é a que importa:

1. **`systemctl is-active` não confirma que a configuração pegou.** O serviço subiu
   `active` (o *serviço*) com a variável ausente. A confirmação é o estado
   observável: `/api/health.servingSnapshot.mode`.
2. **O modo de falha é silencioso e cai para o lado errado.** `parseMode()` devolve
   `"off"` para qualquer coisa que não seja `shadow`/`active` — então um drop-in
   malformado **desliga o mecanismo** em vez de errar alto ou degradar para o modo
   anterior. Se eu não tivesse conferido o health, teria declarado o flip feito com
   o snapshot desativado.

Conserto: `[Service]` inserido, `daemon-reload`, restart, confirmado no health.

## Reversão

```sh
D=/etc/systemd/system/nox-mem-api.service.d
rm "$D/p2s1-active.conf"
mv "$D/p2s1-shadow.conf.retired-20260819-065446" "$D/p2s1-shadow.conf"
systemctl daemon-reload && systemctl restart nox-mem-api.service
# conferir: curl -s .../api/health | jq .servingSnapshot.mode  == "shadow"
```
