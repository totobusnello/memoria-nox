# Extensão do painel — declaração da seed de amostragem (janela 30/07–11/08)

> **Registrado antes de o round existir.** Este arquivo é commitado e enviado
> ao repositório público em 2026-08-11, **antes** do round de beacon indicado
> abaixo ser emitido. O histórico do repositório é o carimbo de precedência —
> mesmo mecanismo de `CALIBRATION-SEED.md` e do `SEED_B` do §4 de
> `PILOT-PROJECTION.md`.

## Por que esta extensão existe

Completar o painel do moonshot (1.050/1.050, 11/08) e reconciliar o painel de
5 famílias no `pilot_replay.py` confirmou o mesmo número de epochs analisáveis
de 29/07: **12 epochs, 11 usáveis para ICC** — abaixo do piso de 30–50 que o
§9 exige. O corpus de ação (resgatado do bug de `CLAUDE_CONFIG_DIR` fixo,
10/08) contém **27 epochs distintos** no total, dos quais **8.826 episódios**
nunca foram adjudicados.

## Desenho — travado antes da amostra

| Campo | Valor |
|---|---|
| Estrato A (`is_error`, censo) | **632** episódios — todos, sem amostragem |
| Estrato B (complemento, amostra) | **1.576** de 8.194 — peso HT alvo **5,2×**, o mesmo regime já caracterizado na peça 3 (não introduz variância nova) |
| Painel | **3 famílias**: `zhipu` (GLM-5.2) · `xai` (Grok-4.5) · `moonshot` (K3) |
| Painel testado e descartado | `zhipu`/`xai`/`deepseek` — medido em 11/08 contra o calibration set de 300 (n=266 completos): **Fleiss' κ = 0,6464** (abaixo do piso 0,75), Krippendorff's α ordinal = 0,8250 (acima). Divergência não resolvida a favor do trio — optou-se pelo trio já validado nos dois coeficientes (`zhipu`/`xai`/`moonshot`, κ=0,8747/α=0,8557, medido em 29/07) |
| Total de episódios | 2.208 |
| Chamadas totais (3 painelistas) | 6.624 |

## Seed — parâmetros travados

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Período | 3 s · genesis `1692803367` |
| `T_declare` | **2026-08-11T21:48:59Z** |
| Regra de `R` | primeiro round com folga ≥ 5 min sobre `T_declare`, para o commit preceder o reveal com margem confortável, não apenas formalmente |
| **`R` (pré-computado)** | **31227290** — `ts(R)` = `2026-08-11T21:53:57Z` |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaços — mesma regra de encoding do `CALIBRATION-SEED.md` (ASCII, não bytes decodificados) |

## Verificação por terceiro

```bash
RAND=$(curl -s https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/31227290 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
# Estrato B (complemento): ordena por SHA256(seed || "|" || episode_id), amostra os 1576 primeiros
```

> ⚠️ **Correção 2026-08-14 — o separador `|` é obrigatório e faltava aqui.** A versão
> original desta seção dizia `SHA256(seed + episode_id)`, sem separador. A regra
> efetivamente usada — a que o `pilot_replay.py` implementa
> (`sha256(seed.encode("ascii") + b"|" + episode_id.encode())`) e que o
> `PILOT-PROJECTION.md` §4 já especificava — concatena com `|`.
>
> Verificado por reconstrução em 2026-08-14: com o separador, a ordenação reproduz
> **1.565 dos 1.576** episódios efetivamente adjudicados (99,3%; os 11 restantes são
> efeito de fronteira do universo — ver `SIZING-2026-08-14.md` §1). **Sem** o
> separador, reproduz **293**. Um terceiro que seguisse o comando publicado
> concluiria, erradamente, que a amostra não confere com a seed.
>
> A seed, o round e o desenho **não mudaram** — apenas a descrição da regra de
> ordenação, que estava incompleta. Isto é correção de documentação, não de método.

## Escopo — o que esta seed NÃO governa

- Não governa atribuição de braço do estudo vivo (isso segue sendo o §2).
- Não é resultado. Governa apenas quais 1.576 dos 8.194 episódios do
  complemento vão ao painel — o censo do estrato A não precisa de seed.
