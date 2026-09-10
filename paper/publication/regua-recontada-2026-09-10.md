# Régua recontada — 2026-09-10

> **Por que este documento existe.** O `diagnostico-arxiv-2026-09-09.md` mediu a régua
> **antes** dos PRs #491, #492, #494 e do `5885acc`, que executaram os itens 1, 3 e 4 do
> plano dele. Eu quase refiz o item 1 sobre os números de ontem — e teria proposto
> **criar** apêndices, quando o achado era **cortá-los** e o corte já havia acontecido.
> Número medido envelhece; recontar é mais barato que desfazer.

## O que mudou em 24 h

| | 09/09 | **10/09** | aceitos (MemMachine · MERIT · Human-Insp · Theoria) |
|---|---:|---:|---|
| referências | 7 | **30** | 21 · 16 · 11 · 51 |
| refs / 1.000 palavras | 0,31 | **1,25** | 1,96 · 2,40 · 1,90 · 2,69 |
| arXiv IDs distintos citados | 2 | **23** | 12 · 17 · 1 · 42 |
| apêndices | 7 | **2** (A, B) | 0 · 0 · — · — |
| palavras de prosa | 22.255 | **24.005** | 10.724 · 6.662 · 5.787 · 18.956 |

Método: blocos de código cercados e linhas de tabela removidos, como no diagnóstico. As
definições de footnote contam 985 palavras; excluí-las move a razão de 1,25 para 1,30, o
que não muda conclusão nenhuma — registro porque o método original não diz o que fez com
elas.

**Contagem e IDs entraram na faixa dos aceitos. A razão não.** E o motivo é contraintuitivo:
a prosa **cresceu** de 22.255 para 24.005 enquanto as referências cresciam. Cortar cinco
apêndices não encurtou o paper, porque o §1.5 Related Work (#492) entrou no mesmo passe.

## A alavanca deixou de ser bibliografia e passou a ser comprimento

Com 30 referências fixas, a razão é função só do tamanho:

| palavras | refs/mil com 30 refs | posição vs aceitos |
|---:|---:|---|
| 24.005 (hoje) | 1,25 | **1,27× mais longo** que o mais longo aceito |
| 18.850 | 1,59 | sob a Theoria (18.956) |
| 15.789 | **1,90** | dentro da faixa |
| 12.500 | 2,40 | mediana da faixa |

## Onde está o comprimento, medido

| seção | palavras | % do paper |
|---|---:|---:|
| **§5 Empirical Evaluation** | **9.830** | **40,9%** |
| §6 Q4 COMPARISON | 4.527 | 18,9% |
| §3 Memory Pipeline | 2.204 | 9,2% |
| §7 Limitations | 1.900 | 7,9% |
| References and Footnotes | 1.645 | 6,9% |
| §1 Introduction | 1.522 | 6,3% |
| §2 System Architecture | 751 | 3,1% |
| Apêndices A + B | 481 | 2,0% |

§5 sozinha é quase o MemMachine inteiro (10.724). §5 + §6 = **60%** do paper. Dentro de §5:

| bloco | palavras | % de §5 |
|---|---:|---:|
| **§5.1 EverMemBench + Wave A ablation series** | **2.768** | 28,2% |
| **§5.5 Q3 orchestration — IterC/IterB** | **2.391** | 24,3% |
| §5.8 Methodology, 5-batch protocol, caveats | 1.250 | 12,7% |
| §5.2 Classical multi-hop QA | 833 | 8,5% |
| §5.4 EverMemBench F_MH paradox | 545 | 5,5% |
| §5.7 Operational characteristics | 504 | 5,1% |
| §5.3 LoCoMo cross-bench | 378 | 3,8% |
| §5.6 Cross-bench LongMemEval | 185 | 1,9% |

§5.1 e §5.5 somam **5.159 palavras — 21% do paper** — e são **histórico de ablação**
(Wave A/B/C, D48, IterB/IterC), não o resultado que o leitor precisa. É o mesmo gênero dos
apêndices C-G, que já saíram por #494: processo interno, não material experimental.

## O alvo — e a retratação da minha própria aritmética

> 🔴 **A projeção abaixo, publicada por mim mais cedo hoje, estava ERRADA.** Ela dizia:
> *"§5.1 + §5.5 → suplemento: −5.159 palavras ⇒ 18.846 e razão 1,59"*. **§5.1 não pode
> sair.** §5.1.2 (salience aditiva) e §5.1.3 (`section_boost`) são a evidência do **próprio
> título** do paper, e §5.1.9/§5.1.10 são citadas **12** e **17** vezes como premissa do
> resto do texto. Eu tratei "5.159 palavras" como se fossem fungíveis; metade delas é
> carga estrutural. O erro é de espécie, não de conta.

**O que de fato saiu** (PR #508): §5.1.11–§5.1.12 (433 palavras, **zero** citações) e
§5.5.4–§5.5.8 (1.534 palavras, o bloco Wave 2), verbatim, para
`supplement-wave2-and-cross-backbone.md`, com **stub por anchor** carregando o
número-manchete — 31 anchors §5.x citados, todos resolvem, zero pendurados.

| | antes | **depois (medido)** | aceitos |
|---|---:|---:|---|
| palavras de prosa | 24.005 | **22.469** | 5.787–18.956 |
| refs / 1.000 palavras | 1,25 | **1,34** | 1,90–2,69 |
| × o mais longo aceito | 1,27 | **1,19** | 1,00 |
| §5.5 | 2.391 | **1.219** (−49%) | — |

⚠️ A mensagem do commit mergeado no #508 diz **22.487** palavras e razão **1,33** — foi
contada antes do ajuste final de um stub, e a emenda não chegou ao remoto antes do merge.
O valor medido é **22.469 / 1,34**; o corpo do PR já carrega a errata, e este documento é
a referência.

**O que resta para entrar na faixa**, agora com números reais:

| alavanca | efeito |
|---|---|
| chegar a 18.956 (deixar de ser o mais longo) | faltam **3.513** palavras |
| chegar a 1,90 refs/mil com 30 refs | faltam **6.680** palavras (alvo 15.789) |
| chegar a 1,90 refs/mil a 22.469 palavras | faltam **13 referências** (alvo 43) |
| combinação plausível | cortar ~3.500 fora de §5.1/§5.5 **e** somar ~7 refs ⇒ 37 refs a 18.969 = **1,95** |

Os candidatos de corte fora de §5.1/§5.5, medidos: §6 (4.527), §7 Limitations (1.900),
§5.8 metodologia (1.250). A corrida do EverOS (item 6) traz citação própria e reforça §6,
o que empurra na direção oposta em palavras — é trade-off a decidir com o número na mão,
não antes.

## O que a bibliografia ainda tem de defeito, e é pequeno

| footnote | defeito |
|---|---|
| `[^mem0]`, `[^zep]` | citam **só** o repo GitHub, e os dois **têm paper** |
| `[^everos]` | só repo — o paper, se existir, entra com a corrida do item 6 |
| `[^memo]` | escreve `arXiv 2605.15156v2` sem o `arXiv:`, então varredura por localizador não o acha |
| `[^sqlitevec]` | só repo — **correto**, é software sem paper |

⚠️ O `[^hipporag2]`, que o diagnóstico apontou como **sem localizador nenhum**, já foi
corrigido e hoje carrega `arXiv:2502.14802` e ICML 2025.
