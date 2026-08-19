# Proveniência das shares de severidade — recuperada, e a unidade está errada

> Fecha o item (i) da revisão adversarial de 2026-08-19 (Kimi K2). Insumo da emenda.

## A proveniência existe e está no código, não em prosa

`{S1 69,73% · S2 29,62% · S3 0,58% · S4 0,08%}` estava hard-coded em 6 arquivos e
sem artefato JSON. A fonte está declarada em **`dose_reach.mjs:74-77`**:

> *"a severidade de fato observada nas **3.812 duplas únicas (episódio, painelista)**
> com veredito `failure` do corpus-piloto congelado … que o corpus alcança em
> **3 vereditos de 3.812**."*

**Reproduzido** (`shares_provenance.py`): a distribuição de `level` sobre duplas
únicas `(episode_id, panelist)` com `status == "ok"` e `verdict == "failure"`, sobre
`peca3-pass1.jsonl + verdicts-combinado-v2.jsonl` mais alguns
`moonshot-cycle-*.jsonl`, dá

```
n = 3.746   S1 0,6973   S2 0,2963   S3 0,0056   S4 0,0008   (3 vereditos S4)
alvo        S1 0,6973   S2 0,2962   S3 0,0058   S4 0,0008
```

S1 e S4 batem em **4 casas decimais**, e os **3 vereditos S4** batem com a nota do
próprio código. O conjunto exato de arquivos não foi isolado — `n` fica em 3.746
contra os 3.812 documentados, e há 74 arquivos com vereditos `failure` — mas a
**definição** está recuperada e é reprodutível. A soma de 100,01% é
arredondamento de quatro casas, não erro.

## O defeito real não é falta de proveniência — é a unidade

As shares são **por veredito**, e o §2 as usa como *"share of failures"* para
ponderar **alcance**, que é definido sobre **oportunidades/episódios**. Não é a
mesma população: um episódio com 5 painelistas contribui 5 vezes.

Sobre exatamente o mesmo corpus, consolidando por episódio (mediana inferior do
painel, a regra que o §5 registra):

| unidade | S1 | S2 | S3 | S4 | n |
|---|---|---|---|---|---|
| **(episódio, painelista)** — o que o §2 usa | 69,73% | 29,62% | 0,58% | **0,08%** | ~3.746 |
| **episódio consolidado** — o que o alcance mede | **78,93%** | **21,07%** | **0,00%** | **0,00%** | 707 |
| idem, `peca3-pass1` | 78,11% | 21,60% | 0,30% (1) | 0,00% | 338 |

**Depois da consolidação, S3 e S4 essencialmente não existem.** Um painelista
sozinho dizendo S4 entre cinco não sobrevive a uma mediana. Em 707 episódios
consolidados: **zero** S3 e **zero** S4.

## O que isso explica, e o que derruba

**Explica o 0,00% medido de `w = 2.0`** por uma razão mais forte do que a que eu
tinha registrado. Eu havia escrito que S3/S4 *"são raros demais para alguma vez
serem o match mais fácil de alcançar"*. Não é raridade: **não existe episódio S3 ou
S4 no corpus consolidado**. O braço baixo admite um conjunto vazio, não um conjunto
pequeno.

**Derruba minha estimativa de 0,66%** na raiz. Eu a computei somando as shares de
S3 (0,58%) e S4 (0,08%) — **shares por veredito, de classes com zero episódios**.
O número era um artefato de misturar duas unidades, e já estava marcado morto por
outro caminho.

**Derruba a leitura dose-resposta de quatro degraus.** A escada útil tem **dois**
níveis, S1 e S2, porque só esses dois existem depois da consolidação — o que é
consistente com `distribuicao_severidade_do_a_past` nos três JSONs de
reachability, todos com apenas S1 e S2.

## Para a emenda

1. **A definição das shares entra registrada**, com a unidade explícita: *"sobre
   duplas (episódio, painelista) com veredito `failure`"*. Sem isso o número é
   irreproduzível — foi o que a revisão apanhou.
2. **Onde o alcance é ponderado, a unidade tem de ser o episódio consolidado.**
   `{S1 78,93% · S2 21,07%}`, e a declaração explícita de que S3/S4 têm **zero**
   episódios no corpus-piloto.
3. **A mistura de severidade S3/S4 não pode aparecer em nenhum cálculo de alcance**
   — nem como plateau da banda, nem como população do braço baixo.
4. ⚠️ **Consequência que ainda não foi medida:** `SEVERITY_PAIN` do write path
   (`#42`) mapeia S0–S4, e o `CHECK` da tabela aceita os cinco. Isso está certo —
   o painel adjudica cinco níveis. Mas nenhum episódio S3/S4 deve ser esperado, e
   se aparecerem depois do deploy, é sinal de que a regra de consolidação em
   produção difere da do piloto. Vale como sonda.
