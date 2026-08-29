# Predição do §4.3.1 — registrada em 2026-08-28, antes do dia existir

## ❌ DESFECHO: REFUTADA (2026-08-29 09:02Z)

`exit 1`, veredito `REFUTADA`. O lote foi servido **108 vezes** em 29/08, com idade máxima
de **7,42** dias. Artefato: `BATCH-CYCLE-2026-08-29.json`.

O guarda do corte disparou junto — dois dias servindo com idade ≥ 7,0 (7,04 e 7,42) — e
**também esse alarme estava mal-endereçado**: `brief_log` não registra o canal, então
aquele guarda mediu a união do pool de cobertura com o pool principal, e o principal não
tem filtro de idade nenhum.

**Diagnóstico.** Há dois sub-pools de cobertura. O lote da retrodição (09–10/08) era
`sessions/boris/…` — sub-pool **por agente**, janela de 7 dias, e parou limpo aos 7,0. O
lote desta predição (21–22/08) é `entities/%` + `lessons.md` — sub-pool **global**, janela
de **30** dias. Apliquei a janela de um canal a um lote do outro. A retrodição continua
válida; a extrapolação não era.

**Cumprido o que este documento mandava fazer em caso de refutação:** o §4.3.1 foi
**substituído** antes de qualquer depósito. A explicação nova — pool elegível de 108
chunks (0,16% do corpus), esgotado 100% todo dia, com 12,4 slots por candidato — é mais
forte que a que caiu, e está medida em `POOL-ELEGIVEL-2026-08-29.json`.

⚠️ **O valor de ter registrado a predição antes está exatamente aqui.** Sem o registro,
"o lote continua sendo servido" seria um fato solto, fácil de acomodar. Com ele, foi uma
refutação com data, número e consequência declarada — e a consequência foi executada.

---


> **Precedência.** Este arquivo é escrito e commitado em **2026-08-28**, quando o dia
> 2026-08-29 ainda não produziu brief nenhum. O registro antecipado é o que impede que a
> predição seja ajustada depois de conhecido o resultado — a mesma disciplina dos
> `*-SEED-*.md` deste repo. Se este arquivo for editado depois de 29/08 09:00 UTC, o
> histórico do git mostra.

## O que se afirma

O §4.3.1 sustenta que o canal de cobertura é alimentado **em lotes** e que cada lote o
alimenta por sete dias, porque o sub-pool por agente exige `freshMaxAgeDays = 7`
(`brief-diversity.ts:61`). O mecanismo já está verificado por **retrodição** sobre o lote
de 09–10/08 (`BATCH-CYCLE-2026-08-28.json`): oito dias de serviço, idade máxima servida
nunca alcançando 7,00, encolhimento de 75 para 54 em 16/08 e zero a partir de 17/08, sem
retorno.

Esta predição é a **confirmação prospectiva** do mesmo mecanismo, não sua única perna.

## O lote

| | |
|---|---|
| janela de criação | 2026-08-21 22:51 → 2026-08-22 02:01 UTC |
| chunks criados na janela | 199 |
| chunks do lote que chegaram a ser servidos | **109** (108 no dia típico) |
| idade máxima servida em 28/08 | **6,53** dias |
| cruza 7,00 dias entre | **28/08 22:51** e **29/08 02:01** UTC |

## O que se prevê para 2026-08-29

1. **Os chunks do lote são servidos zero vezes.** É a asserção dura.
2. **O total de chunks distintos servidos no dia cai de 141 para ≈ 33** (141 − 108),
   salvo chegada de lote novo de ingestão.

A segunda é aproximada por construção e não é critério de falseamento sozinha — no ciclo
anterior a mesma conta previu 46 e observou 49, com 3 entradas novas. É a **primeira** que
decide.

## Como verificar — comando único, veredito por código de saída

```
python3 measurement/ciclo-do-lote.py \
  --db <nox-mem.db> --lote 2026-08-21:2026-08-23 --corte 7 \
  --esperar-zero-em 2026-08-29 --out BATCH-CYCLE-2026-08-29.json
```

`exit 0` ⇒ confirmada. `exit 1` ⇒ refutada **ou** não medida, e os dois casos são
distinguidos no texto e no campo `predicao.veredito`.

⚠️ **"Não medida" não conta como confirmação.** Se 29/08 não tiver brief nenhum — cron
parado, VPS fora, epoch pulado — o script diz `NAO MEDIDA` e sai 1. Um teste cujo silêncio
é indistinguível de sucesso não é teste; foi preciso escrever essa perna à mão porque a
ausência de linha do lote, sozinha, é ambígua.

As duas asserções foram verificadas por mutação em 28/08: prever zero para 28/08 (dia em
que o lote foi servido 108×) devolve `REFUTADA` + `exit 1`; prever zero para 29/08 hoje
devolve `NAO MEDIDA` + `exit 1`.

## O que acontece se for refutada

O §4.3.1 é reescrito **antes de qualquer depósito**. Refutação significa que o lote
continua sendo servido depois dos sete dias, e nesse caso o corte de idade não é o que
governa o canal — a explicação do congelamento entre lotes teria de ser outra. A
retrodição de 09–10/08 permaneceria válida como fato, mas deixaria de ser generalizável,
e o parágrafo teria de dizer isso.
