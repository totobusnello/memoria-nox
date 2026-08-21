# Rodada de λ — declaração da seed de amostragem (epochs 2026-08-15 → 08-20)

> **Registrada antes de a rodada existir.** Este arquivo é commitado e pushado ao
> repositório público em **2026-08-21T22:17Z**, **antes** de a rodada do beacon
> nomeada abaixo ser emitida (ela sai às **22:22:57Z**). O histórico do repo é o
> selo de precedência — mesmo mecanismo de `CALIBRATION-SEED.md`,
> `EXTENSION-SEED-2026-08-11.md` e `EXTENSION-2-SEED-2026-08-14.md`.

## Para que serve

Duas coisas que a decisão de desenho precisa e que nenhuma aritmética entregou:

1. **λ** — a proporção de episódios adjudicados como falha. É o que decide banda e
   `N`, e a análise de 21/08 mostrou que sem ele não há como afirmar se existe
   contraste (`AMENDMENT-v1.12-DRAFT.md` §2-quater).
2. **Os primeiros chunks reais do estudo.** Sem falha adjudicada o write path não
   tem linha, e sem linha o dual-compute não tem o que deslocar — a medição de
   ativação em `shadow` fica bloqueada.

## Pré-condição verificada antes de declarar

O harness estava **quebrado** desde 2026-08-16 (`d11afee` traduziu o marcador que
delimita o corpo do prompt; `carregar_prompt` levantava `IndexError`). Corrigido em
`d09b3cb`, e o corpo confere com o hash travado:

| | |
|---|---|
| `prompt_sha256` do corpo | `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e` |
| confere com o depositado | ✅ (`CORPUS-FREEZE.md`, `DEPOSIT-README.md`) |
| guarda | o runner agora **recusa rodar** se divergir, em vez de só anotar |

## Desenho — travado antes da amostra

| Campo | Valor |
|---|---|
| Universo: epochs **08-15 → 08-20**, fronteira 09:00 UTC | **1.305** episódios |
| Epochs | 6, todos **completos** |
| Sessões distintas | 109 |
| Estrato A (`is_error`, **censo**) | **48** — todos, sem amostragem |
| Estrato B (complemento, amostrado) | **242** de 1.257 |
| Taxa do estrato B | **19,235%** — idêntica à das extensões 1 e 2 |
| Painel | **3 famílias**: `zhipu` (GLM-5.2) · `xai` (Grok-4.5) · `moonshot` (K3) |
| Total a adjudicar | **290** episódios · **870** chamadas |
| `sha256` do universo extraído (completo, 12.274 linhas) | `c9325d86c078cb72a18f371c1ad489c797efe3f1de7986a6184a21e3bc5dfa4f` |

**Por que 08-21 fica fora.** O epoch de 08-21 estava **incompleto** no momento da
declaração (fronteira 09:00 UTC, declaração às 22:17Z): 101 episódios contra
157–320 dos completos. Incluí-lo enviesaria λ para baixo por truncamento de
exposição, não por comportamento da frota.

**⚠️ `is_error` caiu.** Nesta janela é **3,68%** (48/1.305), contra **9,29%**
(65/700) da extensão 2. Registro antes de ver os vereditos, porque depois seria
racionalização. Não sei a causa e não vou inferir daqui.

## Beacon

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| `chain` | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Período | 3 s |
| **Rodada `R`** | **31515871** |
| Emissão de `R` | **2026-08-21T22:22:57Z** |
| Regra para `R` | primeira rodada com ≥ 5 min de folga sobre `T_declare` (folga real: 354 s) |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaço |
| **Ordenação** | `key(e) = SHA256( ascii(seed) \|\| "\|" \|\| e.episode_id )` — o separador `\|` é **obrigatório** |

## Verificação por terceiro

```bash
CHAIN=52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
RAND=$(curl -s https://api.drand.sh/$CHAIN/public/31515871 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
# Estrato B: ordenar por SHA256(SEED || "|" || episode_id) e tomar os 242 primeiros
```

O separador `|` está explícito porque **sua ausência em
`EXTENSION-SEED-2026-08-11.md` foi um defeito de reprodutibilidade**.

## O que esta rodada NÃO decide

- Não sorteia braço. `T_seed_assign` continua aberto e vem **depois** de congelar
  o mecanismo emendado (decisão do Toto, 17/08).
- Não mede ativação. Isso exige `NOX_P2_OUTCOME=shadow` **depois** de os chunks
  existirem, e é passo separado.
- Não altera a emenda. Os vereditos alimentam a decisão de banda/`N`; a emenda
  declara mecanismo, estimando e regras — não níveis.
