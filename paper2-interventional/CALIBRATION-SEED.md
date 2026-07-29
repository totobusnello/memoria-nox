# Calibration set — declaração da seed de amostragem

> **Registrado antes de a seed existir.** Este arquivo foi commitado e enviado ao
> repositório público em 2026-07-28, **antes** do instante `T_calib` definido
> abaixo. O round de beacon indicado não existia no momento do commit, e o
> histórico do repositório é o carimbo de precedência.

---

## Por que existe uma seed separada da do §2

O §2 do pré-registro deriva a seed de **atribuição de braço** de um round de
`drand` cujo `T_seed` é, por construção, **estritamente posterior ao registro no
OSF**. O corte numérico de severidade que a calibração produz é um item
`[TO LOCK]` — precisa estar preenchido **no** registro.

Logo a calibração precede o registro, e o registro precede `T_seed`. **A
calibração não pode usar a seed do §2: a ordem torna isso impossível.**

O §4.1 diz *"The production seed will be derived from the beacon (§2), not
chosen."* A parte que vale é **"derived from the beacon, not chosen"** — a
propriedade exigida é ausência de discricionariedade do autor, não a identidade
do round. Esta declaração satisfaz a exigência com um round próprio, anterior ao
registro e igualmente fora de controle do autor.

**Correção pendente no §4.1:** a frase deve distinguir `T_seed_calib` (aqui) de
`T_seed_assign` (§2). Sem isso, um leitor lê a linha 148 como promessa quebrada.

## Parâmetros — travados

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Período | 3 s · genesis `1692803367` |
| `T_calib` | **2026-07-29T01:20:00Z** (22:20 BRT de 2026-07-28) |
| Regra de `R` | primeiro round com `timestamp ≥ T_calib`, i.e. `R = floor((T_calib − genesis)/3) + 1` |
| **`R` (pré-computado)** | **30828212** — `ts(R)` = `2026-07-29T01:20:00Z` exato |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaços |

### Dois pontos de precisão — verificados, não presumidos

1. **Encoding é ASCII, não bytes.** Para o round 30800000, `SHA256` sobre a
   string hex dá `1ae88fbf27fe83bc…`; sobre os bytes decodificados dá
   `0e6824e682b9d776…`. São seeds diferentes. Fica travado: **a string hex**.
2. **A API v2 não devolve `randomness`** — só `round` e `signature`. O campo
   `randomness` existe apenas no endpoint v1. Uma regra que não fixa o endpoint
   não é reproduzível. **Ambos valem também para o §2**, que hoje escreve
   `SHA256(randomness_hex(R))` sem fixar nenhum dos dois.

**Fallback** (beacon inalcançável em `T_calib`): `seed = SHA256(block_hash(H))`,
`H` = primeiro bloco Bitcoin minerado em ou após `T_calib`. Uso do fallback é
registrado no changelog de desvios.

## Verificação por terceiro

```bash
RAND=$(curl -s https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/30828212 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
python extract_episodes.py --sample 300 --seed "$SEED"
```

A amostra resultante é byte-determinística: `extract_episodes.py` ordena por
`SHA256(seed + episode_id)`, sem `random` sem seed e sem timestamp de execução.

## Escopo — o que esta seed NÃO governa

- **Não** governa atribuição de braço (isso é o §2, round distinto, posterior ao registro).
- **Não** é um resultado. Governa apenas *quais* 300 episódios dos 4.560 vão ao painel.
- A estratificação por assinatura primária é independente da seed e já verificada:
  um sorteio de 300 cobre as **72** assinaturas primárias.

## Preenchido após `T_calib`

| Campo | Valor |
|---|---|
| `randomness(R)` | _(a preencher)_ |
| `seed` derivada | _(a preencher)_ |
| SHA-256 do `episodes.jsonl` amostrado | _(a preencher)_ |
