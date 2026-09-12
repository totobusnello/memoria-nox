# ambiente-congelado — o que o `.venv` sabe, para que apagá-lo não perca nada

## Por que existe

A pergunta era «os 1,6 GB de ambiente, podemos apagar com certeza?». A resposta era
**não**, e foi este diretório que virou a condição para o sim.

`eval/q4-comparison/requirements.txt` tem **9 de 43** linhas com `==`. Ou seja,
`pip install -r requirements.txt` **não** reconstrói o ambiente que rodou as corridas —
reconstrói *um* ambiente, com as versões que o índice servir no dia. Para um harness de
benchmark isso não é detalhe: a versão da biblioteca **é parte do resultado**.

E não é hipotético. Ao procurar a certeza, o próprio `.venv` respondeu a uma pergunta que
o manuscrito declara **em aberto** no §6.3.2 — qual versão do Mem0 rodou o `rc4`. O
ambiente diz `mem0ai==2.0.10`, e a assinatura de `Memory.search` nele é keyword-only, sem
`user_id` nem `limit`. **Apagar o `.venv` antes de olhar teria destruído essa evidência.**

## O que está congelado

| arquivo | pacotes |
|---|---|
| `pip-freeze-venv-2026-09-12.txt` | 153 — inclui `mem0ai==2.0.10`, `chromadb==1.5.9`, `google-genai==2.10.0`, `openai==2.44.0` |
| `pip-freeze-venv-zep-2026-09-12.txt` | 17 |

⚠️ **É o estado de 2026-09-12, não o de nenhuma corrida passada.** O `.venv` foi mexido em
setembro (pacotes de outro projeto entraram). O que o congelamento garante é que as
versões de hoje ficam legíveis depois de o diretório sair do disco — não que o ambiente de
junho seja reconstruível.

## Reconstruir

```sh
python3 -m venv .venv && .venv/bin/python -m pip install -r \
  ambiente-congelado/pip-freeze-venv-2026-09-12.txt
```

Para os `node_modules`, o lockfile já basta e é melhor: `docs-site/package-lock.json`
(lockfileVersion 3, 540 pacotes) e
`experiments/a2-tier3-sqlcipher-spike/work/package-lock.json` (45 pacotes). **`npm ci`
reconstrói de forma determinística** — esses 303 MB são a única parte do peso que se
apaga sem congelar nada antes.
