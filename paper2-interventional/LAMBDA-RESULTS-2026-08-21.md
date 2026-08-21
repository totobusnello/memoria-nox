# Rodada de λ — resultados

**Seed declarada em:** `LAMBDA-SEED-2026-08-21.md` (pushada 22:17:50Z, rodada
`31515871` emitida 22:22:57Z) · **Vereditos:**
`~/.paper2-verdicts/verdicts-lambda-2026-08-21.jsonl` (fora de repo público)

## A rodada

| | |
|---|---|
| `prompt_sha256` | `5b22f02c…` — **bate** com o travado no §4.1 e depositado |
| Chamadas | **870/870**, todas `ok` |
| Quota / missing | **0 / 0** nos três painelistas |
| Duração | **960,7 s** (16 min) |
| `randomness` | `ec04ba7c340e47e3375860177dee996f4e782944b0a872f1b8efa6827a1b7103` |
| `seed` | `7a7f212b80a6fb14751593b3b831f82ebbacae231ad8c397dbcc49fc1b1e04fe` |
| `sha256` da amostra | `cb64392272d5c7e6f562fc394f08b96c912690d14d8bb0015b861a7a6e06bf2e` |

⚠️ Eu havia estimado 6–13 min a partir de intervalos de `mtime` de rodadas
anteriores, chamando 1,27 chamadas/s de **piso**. O real foi **0,906/s**. O piso
estava errado, não apenas conservador: o intervalo entre dois arquivos limita a
duração do segundo **somente se** as duas rodadas tiverem o mesmo custo por
chamada, e eu não verifiquei isso.

## λ — e a correção do meu próprio enquadramento

| | |
|---|---|
| Estrato A (`is_error`, censo) | 46 adjudicados, **44 falhas** |
| Estrato B (amostra, peso HT 5,194215) | 234 adjudicados, **11 falhas** (4,70%) |
| Inadjudicáveis (abaixo do piso de 3) | **10** de 290 (3,45%) |
| Falhas estimadas na população (1.305) | **101,1** |
| **λ̂** | **0,077499** |
| SE · IC95 | 0,012023 · **[0,0539 ; 0,1011]** |

🔴 **Correção.** Eu anunciei isto como "4× menor que os ~30% que o desenho
assumia". **Errado, e é a terceira vez hoje que quase publico consequência a
partir de um referente não verificado.** O `~30%` do registro é *share das
falhas* (S2 e acima), não proporção de episódios. O parâmetro de dimensionamento
é `p̂0 = 0,111813`, a taxa de falha entre **oportunidades** — denominador mais
estreito que o meu, que é *todos os episódios*. Uma taxa menor num denominador
mais largo é o esperado. **λ̂ = 7,75% é consistente com o desenho; não o refuta.**

O `is_error` prediz forte mas não perfeito: 95,7% das falhas do estrato A, contra
4,70% no complemento. E há falhas **fora** do `is_error` — 11 na amostra, ~57 na
população. A estratificação está fazendo trabalho real.

## 🔴 O achado que importa: o estrato S2 depende de UM painelista

`W_OUTCOME = w · Δ_cut · severity`. A severidade **é** o portador da dose, e a
fronteira S1/S2 é o que separa os platôs. Medido:

| painelista | falhas | S2 | share de S2 nas falhas |
|---|---|---|---|
| moonshot | 66 | 16 | 24,2% |
| zhipu | 58 | 15 | 25,9% |
| **xai** | 54 | **39** | **72,2%** |

Os três **concordam sobre haver falha** (54–66 de ~285 cada) e discordam sobre
**quão grave**. Concordância par a par no nível: 87,9% / 88,8% / 89,4% — parecidas
entre si, o que descarta "xai é genericamente discordante". A discordância está
concentrada exatamente na fronteira S1/S2.

Consolidado com os três (mediana inferior, piso 3): **225 S0 · 33 S1 · 22 S2 ·
0 S3 · 0 S4**. E:

> **Todos os 22 S2 consolidados têm `xai = S2`. 100%.**
> Sem xai, sobreviveriam **5** (os episódios em que moonshot **e** zhipu marcam S2).

⚠️ **Não usei leave-one-family-out para afirmar isso**, porque ali o estimador
muda junto: com 3 painelistas a mediana inferior é o valor do meio, com 2 vira o
**mínimo**. O LOO indicava queda de 40% → 9,3% no share de S2, mas parte disso é
mecânico. A contagem acima não tem esse artefato — é episódio a episódio.

**Consequência para o desenho:** a §2 trata "S2 e acima" como a população
efetivamente tratada. Esse estrato, nos dados observados, **requer a calibração de
severidade de uma família**. Isso é achado de instrumento, e é precisamente o que
o leave-one-family-out está registrado para expor — só que o §9 o declarou sobre o
**veredito binário**, e este é sobre o **nível**, que é o eixo load-bearing.

## Zero S3 e zero S4 em 870 chamadas

Nenhum painelista atribuiu S3 ou S4 a nenhum episódio. Isso **confirma em dados
frescos** o baseline zero registrado no §3 — a cláusula (b) da regra de parada
segue reduzida a "≥1 incidente ≥ S3 na janela derruba", e o `abort-check` medirá
contra baseline zero.

## Abstenções: a fragilidade do §9 é real

12 abstenções (xai 7 · moonshot 4 · zhipu 1) ⇒ **10 episódios abaixo do piso de
3 vereditos (3,45%)**. Dentro do teto de 10%, mas **acima** dos 2,67% do conjunto
de calibração — e o §9 já havia declarado que com exatamente três painelistas uma
única abstenção derruba o episódio.

## O que isto destrava

**55 falhas consolidadas reais** (33 S1 + 22 S2). É a matéria-prima que faltava:
sem falha adjudicada o write path não tem linha, e sem linha o dual-compute não
tem o que deslocar. A medição de ativação em `shadow` deixa de estar bloqueada.
