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

## Preenchido após `T_calib` — 2026-07-29T01:20:00Z

| Campo | Valor |
|---|---|
| `randomness(R)` | `da5c9bde5b640648a70466bb98a106613afcee13a2bee3c22130d97f89900421` |
| **`seed` derivada** | **`f61f4c463dc86251e0f6620c37c5cece202b36b3c183e13f0ec5e98f488f4319`** |
| SHA-256 da amostra de 300 | `8e95d70ee20533eab4129641fe968dd9afb86c3bc8672571e9f712fd44df2eff` |
| SHA-256 do **corpus completo** no momento da amostragem | `34dc3fd13e8e8c73774578457a70f7eab32f091ebdb4b0fd937fb63432ef3d76` |

⚠️ O hash da amostra é calculado sobre o corpo **sem** a quebra de linha final;
`shasum` do arquivo em disco dá `b0862afc…` e a diferença é exatamente esse byte.
Não é corrupção — mas quem verificar precisa saber qual dos dois está reproduzindo.

### Estado do corpus na amostragem — e por que isto tem que ser congelado

| | pré-registro (2026-07-26) | amostragem (2026-07-29) |
|---|---|---|
| episódios | 4.560 | **5.547** |
| `is_error` | 434 (9,5%) | **514 (9,3%)** |
| coarse / primary / fine | 14 / 72 / 162 | 14 / **74** / **168** |

A amostra de 300 cobre **74 de 74** assinaturas primary — a *propriedade* afirmada
no §4.1 (cobertura total) se manteve; o *número* mudou. Distribuição: 20,0% de
`is_error` na amostra contra 9,3% no corpus, efeito esperado da estratificação,
que sobre-amostra assinaturas raras.

**O que isto expõe:** a taxonomia do `sig()` é derivada dos dados, e o corpus
cresce ~330 episódios/dia. Sem congelar, qualquer número publicado fica obsoleto
entre a escrita e a submissão — foi o que aconteceu com "72" em três dias.
Declarar a seed **não basta** para reprodutibilidade: a seed ordena um conjunto,
e o conjunto se move. O hash do corpus acima congela o conjunto desta amostragem,
mas reproduzir de fato exige um snapshot do `action-archive` na data, não só o
hash. **Item aberto, não resolvido aqui.**
