# Extensão 2 do painel — declaração da seed de amostragem (epochs 12–14/08)

> **Registrado antes de o round existir.** Este arquivo é commitado e enviado ao
> repositório público em **2026-08-14T18:10Z**, **antes** de o round de beacon
> indicado abaixo ser emitido (ele sai às 18:20:27Z). O histórico do repositório
> é o carimbo de precedência — mesmo mecanismo de `CALIBRATION-SEED.md`,
> `EXTENSION-SEED-2026-08-11.md` e do `SEED_B` do §4 de `PILOT-PROJECTION.md`.

## Por que esta extensão existe

O `SIZING-2026-08-14.md` fechou o corpus da extensão 1 e produziu **27 epochs
analisáveis (24 usáveis para ICC)** — ainda abaixo do piso de **30–50** que o §9
exige para estimar ICC de forma confiável. A largura do IC resultante
([0,0554 ; 0,1786]) sozinha move o estudo de 172 para 456 dias, o que impede
qualquer decisão informada sobre MDE ou duração.

Diagnóstico do corpus de ação: ele contém **30 epochs**, dos quais **25** têm ao
menos um episódio adjudicado. Os cinco sem adjudicação são 16/07 e 17/07
(2 e 1 episódios — não geram sessões utilizáveis) e **12, 13 e 14/08**
(233, 223 e 244 episódios). Adjudicar estes três leva de 27 para **30 epochs**.

**30 é o teto do corpus atual, e é exatamente o piso do §9.** Não há folga: se
algum dos três não render sessões analisáveis, ficamos abaixo de novo.

## Desenho — travado antes da amostra

| Campo | Valor |
|---|---|
| Universo (epochs 12–14/08, boundary 09:00 UTC) | **700** episódios |
| Estrato A (`is_error`, censo) | **65** — todos, sem amostragem |
| Estrato B (complemento, amostra) | **122** de 635 |
| Taxa do estrato B | **19,235%** — idêntica à da extensão 1 (1.576/8.194) |
| Painel | **3 famílias**: `zhipu` (GLM-5.2) · `xai` (Grok-4.5) · `moonshot` (K3) |
| Total a adjudicar | 187 episódios · **561 chamadas** |
| Sessões distintas nos 3 epochs | 47 |

**Por que a mesma taxa, e não censo.** O `pilot_replay.py` aplica um peso
Horvitz-Thompson único, `len(resto)/len(estrato_b)`, a todo o estrato B. Fazer
censo dos epochs novos lhes daria peso 1,0 contra 5,2 dos antigos, misturados no
mesmo estimador — o código não suporta peso por época, e alterá-lo **depois de
ver os resultados do sizing** seria mexer no estimador com os dados à vista. A
taxa idêntica mantém o estimador válido sem tocar em uma linha dele.

## Seed — parâmetros travados

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Período | 3 s · genesis `1692803367` |
| `T_declare` | **2026-08-14T18:10:27Z** |
| Regra de `R` | primeiro round com folga ≥ 5 min sobre `T_declare` |
| **`R` (pré-computado)** | **31309420** — `ts(R)` = **2026-08-14T18:20:27Z** (folga 10 min) |
| Round observado ao declarar | 31309220 |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaços |
| **Ordenação** | `chave(e) = SHA256( ascii(seed) \|\| "\|" \|\| e.episode_id )` — **o separador `\|` é obrigatório** |

## Verificação por terceiro

```bash
CHAIN=52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
RAND=$(curl -s https://api.drand.sh/$CHAIN/public/31309420 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
# Estrato B: ordena por SHA256(SEED || "|" || episode_id), amostra os 122 primeiros
```

> O separador `|` está explícito aqui **porque sua ausência no
> `EXTENSION-SEED-2026-08-11.md` era um defeito de reprodutibilidade**: quem
> seguisse aquele comando reproduzia 293 dos 1.576 em vez de 1.565. Corrigido
> naquele arquivo em 2026-08-14.

## Escopo — o que esta seed NÃO governa

- Não governa atribuição de braço do estudo vivo (isso segue sendo o §2 do pré-registro).
- Não é resultado. Governa apenas quais **122 dos 635** episódios do complemento
  vão ao painel; o censo do estrato A não precisa de seed.
- Não altera τ, nem o painel, nem a regra de desfecho, nem a regra de
  instabilidade (`STABILITY-TEST.md` §9.2).

## Verificação da extração (2026-08-14, pós-declaração)

O universo foi regenerado do `action-archive` da VPS e **bate exatamente com o
desenho declarado acima**: 700 episódios, 65 no estrato A, 47 sessões distintas.
Sorteio dos 122 pelo round 31309420 (`randomness` `6a9b71b4…f0b57`,
`seed = SHA256(randomness)` = `fd9b4027…aa85`) fecha em **19,213%** — o 19,235%
declarado é a fração exata `1.576/8.194`; 122 é seu arredondamento para inteiro.

### ⚠️ Censura à direita no último epoch de toda extração

A mesma extração mostrou o epoch **11/08 com 316 episódios**, contra os **264**
congelados no `universo-extensao.jsonl` da extensão 1 — porque aquela extração
rodou *durante* o 11/08 e capturou 83,5% do epoch. **Todo último epoch de uma
extração é parcial**, e isso não estava registrado em lugar nenhum.

Consequências, nesta ordem:

1. **O epoch 11/08 da extensão 1 fica como está.** Completá-lo agora seria mexer
   no corpus depois de ver o resultado do sizing — exatamente o que o desenho
   proíbe. Ele entra como cluster menor, o que o ICC comporta.
2. **O epoch 14/08 desta extensão também é parcial** (244 episódios, extraído às
   ~23:00 UTC de um epoch que só fecha às 09:00 UTC de 15/08). Entra parcial, e
   isto está declarado *antes* da adjudicação, não depois.
3. Para extrações futuras: **descartar o epoch corrente** ou esperar sua
   fronteira. Um cluster truncado não enviesa o ICC por si só, mas reduz m̄ de
   forma não-aleatória — e m̄ é o termo que domina o design effect.

## O que esta extensão não resolve

Mesmo com sucesso total, chegamos a **30 epochs — o piso, não uma folga**. O
intervalo do ICC continuará largo; 30 clusters estreitam-no, não o fecham. E o
corpus não tem mais epochs a oferecer: qualquer ganho além disso exige **esperar
mais dias de tráfego**, não mais adjudicação.
