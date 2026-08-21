# Os três braços são distinguíveis — e o canal não é o registrado

**Data:** 2026-08-21 · **Depende de:** `BAR-RETRACTION-2026-08-20.md`
**Não depende de λ.**

## O que mudou desde ontem

O estoque de nunca-servidos **zerou em um dia**, não em três: 52 primeiros-serves
em 20/08 contra os 38 elegíveis que eu havia contado. Estoque agora: **0**. O
regime estacionário é o de hoje, não o de daqui a três dias.

## Terceira constante velha: o cut dos slots principais

Eu vinha usando `0,8524`, medido no regime de pool vazio. Medido agora, ao vivo,
separando cobertura de principal via `diff.fresh_added`:

| agente | cut do slot **principal** | picks de cobertura |
|---|---|---|
| lex | **0,6100** | 0,7344 / 0,7344 |
| nox | 0,6851 | 0,7344 / 0,7344 |
| boris | 0,6925 | 0,7344 / 0,7344 |
| forge | 0,7051 | 0,7344 / 0,7344 |
| atlas | 0,7613 | 0,7344 / 0,7344 |
| cipher | **0,7922** | 0,7344 / 0,7344 |

Dois fatos estruturais que nenhum documento registrou:

1. **O cut principal é agente-heterogêneo** (0,610 → 0,792, span de 0,18). Não é
   uma constante do sistema; é uma propriedade de cada agente.
2. **A cobertura hoje supera o principal em 4 dos 6 agentes.** ⚠️ *(corrigido de "5" em 21/08 após revisão do Grok — erro aritmético: 0,7344 não supera atlas 0,7613 nem cipher 0,7922.)* Os picks de
   cobertura estão a 0,7344 — acima do cut de lex, nox, boris e forge — **4 de 6**, não 5 (erro aritmético corrigido 21/08 após revisão do Grok): não supera atlas (0,7613) nem cipher (0,7922). A hierarquia
   "cobertura é o caminho fraco, principal é o forte" **está invertida**.

## Severidade domina idade — a dose não pode reordenar

Dentro da janela de 30 dias:

```
vantagem máxima de idade (0 d vs 30 d) : 0,016365
menor degrau de severidade    a w = 0  : 0,025000
```

O degrau de severidade é **maior** que todo o span de recência disponível. Logo a
ordenação entre nunca-servidos é **estritamente por severidade**, com idade só
desempatando dentro da mesma severidade. E `W_OUTCOME = w·Δ_cut·severity` **escala
com a severidade**, então qualquer `w > 0` só aumenta essa dominância.

**Consequência:** a dose não pode alterar *qual* severidade ocupa os 2 slots de
cobertura. Esse canal é inerte por construção da fórmula, em todo braço.

## O canal que existe: mais de 2 itens do estudo no brief

Os 2 primeiros chunks do estudo entram pela cobertura sem competir (nunca-servidos).
O 3º em diante precisa **vencer o cut principal**. É aí que a dose age.

Com as severidades que de fato ocorrem — consolidadas por episódio, S1 78,93% /
S2 21,07% / **S3 0,00% / S4 0,00% em 707 episódios**:

| braço | agentes alcançados por S1 | por S2 | total | Δ vs controle |
|---|---|---|---|---|
| controle (w=0) | 1/6 (lex) | 3/6 (bor, lex, nox) | 4 | — |
| **w = 2,0** | 2/6 (lex, nox) | 4/6 (+for) | 6 | **+2** |
| **w = 4,0** | 4/6 (+bor, for) | 5/6 (+atl) | 9 | **+5** |
| **w = 7,5** | 4/6 | 6/6 (+cip) | 10 | **+6** |

**Os três braços são distinguíveis, com dose-resposta monótona (+2, +5, +6).**

Isso derruba duas coisas que eu mesmo afirmei nos últimos dias:

- ❌ "`w = 2,0` é quase-inerte / candidato a controle negativo" — move 2 dos 6
  cruzamentos disponíveis. Não é inerte.
- ❌ "`w = 4,0` só age via S4, que nunca ocorre" — a conta usava o cut velho de
  0,8524. Contra o cut real, `w = 4,0` age via **S1 e S2**, que são 100% da massa.

⚠️ E revela uma **saturação entre 4,0 e 7,5** (+5 → +6): o topo da banda compra
um agente a mais que o meio. A dose-resposta é monótona mas achata no topo.

## O que é depositável e o que não é

**Depositável (mecanismo, não nível):**
- o cut principal é agente-heterogêneo — a análise tem de ser por agente ou
  estratificada, nunca contra uma constante única;
- severidade domina idade na janela de 30 d ⇒ a dose não reordena severidades;
- o canal do tratamento é o **excedente** além dos 2 slots de cobertura;
- os braços são distinguíveis com dose-resposta monótona e saturante.

**Não depositável:** todo número desta página. É a **quarta** medição de "o cut"
em quatro dias (0,8524 → 0,7342 → 0,744495 → 0,7345 → agora 0,610–0,792), e a
razão é sempre a mesma: o corpus servido é estado, não parâmetro. Qualquer nível
publicado tem de vir com a data e com o estoque de nunca-servidos daquele
instante.

## Gate Stanford — série completa

`provider_telemetry`: **2.064 rows, 14 dias, 2026-08-07 → 2026-08-20**. Fechada.
