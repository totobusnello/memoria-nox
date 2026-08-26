# Designação do Paper 2 — declaração da seed de sorteio

> **Registrada antes de a rodada existir.** Este arquivo foi commitado e pushado ao
> repositório público em **2026-08-26T20:07:27Z** (commit `40d2462`), **antes** de a
> rodada do beacon nomeada abaixo ser emitida — ela sai às **20:25:00Z**. Folga
> real: **1.053 s = 17 min 33 s**, sobre um requisito de ≥ 300 s. Verificado no
> momento da escrita: `GET .../public/31657512` devolvia **HTTP 425** (rodada ainda
> não emitida). O histórico do repo é o selo de precedência — mesmo mecanismo de `CALIBRATION-SEED.md`,
> `EXTENSION-SEED-2026-08-11.md`, `EXTENSION-2-SEED-2026-08-14.md` e
> `LAMBDA-SEED-2026-08-21.md`.

## Para que serve

Escolher, dentro de cada grupo de assinatura de `p2_verdict`, **qual chunk** recebe
o boost de desfecho. Um por grupo.

A regra anterior está retratada. Três defeitos medidos, todos na
`AMENDMENT-v1.12.md` (retratações 3, 4, 13, 26, 27):

1. consumia `CUT_FRESH = 0,7342` como limiar, e o `pick` **não aplica limiar
   nenhum** — a emenda retrata o referente da constante;
2. o desempate registrado (`PREREG-DRAFT.md:535`) nomeava `created_at`, **coluna
   que não existe** em `p2_verdict` — não era não-implementado, era
   **não-implementável**;
3. `w_min` derivava de `salienceBase`, que inclui
   `0,20 · log1p(access_count)/log(1000)`. `access_count` é mutável por tráfego de
   busca exógeno ⇒ a designação **não era função só de dados congelados**. Empate
   exato em **4 dos 7** grupos multi-membro, e nesses o designado saía da ordem
   incidental de linhas do SQLite.

A substituição foi decidida em **2026-08-26T14:47Z** (`DECISION-designacao-2026-08-25.md`),
**antes** de qualquer linha de código da regra nova e **depois** de o custo estar
medido: **8,8%** de dose agregada. O que se compra com esses 8,8% é independência
da calibração de severidade de **uma** família do painel — `xai` responde por
**72,2%** do share de S2, e a regra alternativa (designar o de severidade máxima)
designaria S2 nos 5 grupos que diferem.

## Pré-condição verificada antes de declarar

Sobre `p2_verdict` na VPS, em 2026-08-26T19:4xZ:

| | |
|---|---|
| linhas totais | 280 |
| linhas com `chunk_id` | **55** — todas S1 ou S2 |
| linhas com `chunk_id IS NULL` | **225** — todas S0 |
| grupos (`sig_primary`) totais | 40 |
| grupos com pelo menos um chunk | **19** — os outros 21 existem só em S0 |
| grupos multi-membro | **7** (12 são singletons: não há escolha a fazer) |
| chunks em mais de um grupo | **0** |
| chunks com mais de uma severidade | **0** |
| `written_at` nulo | 0 |
| última adjudicação | 2026-08-21T02:43:22.139Z |
| `severity` distintas | S0, S1, S2 |

Dois fatos que a regra usa e que precisam estar no registro:

- **`S0 ⟺ chunk_id IS NULL`, exatamente.** As 225 linhas S0 não têm chunk, e
  nenhuma linha com chunk é S0. A implementação filtra pelos **dois** lados
  (`chunk_id IS NOT NULL AND severity IN ('S1','S2','S3','S4')`) porque a
  coincidência é fato do dado de hoje, não restrição de schema — se divergirem,
  as duas condições mordem.
- **Cada chunk pertence a exatamente um grupo.** É o que autoriza a chave a não
  mencionar `sig_primary` (ver abaixo).

## Desenho — travado antes do sorteio

```
designado(g) = argmin_{c ∈ g} SHA256( seed ‖ "|" ‖ chunk_id )
```

Com desempate explícito por `chunk_id` crescente caso duas chaves colidam — não
por ordem de iteração, que é precisamente o defeito que esta regra conserta.

**Escopo: global, não condicional ao pool.** A designação de um grupo não depende
de quem apareceu no brief corrente. Sob a regra anterior isso era invisível porque
cada fatia recomputava o argmin local, e `boostsParaCandidatos` é chamada **≥2
vezes por brief** com fatias diferentes de candidatos (`brief.ts:714`, `:753`,
`:843-851`), sem nenhum ponto onde os mapas fossem unificados.

**Grupo cujo designado não está no pool não recebe boost.** Ninguém é promovido em
seu lugar — promover o segundo colocado reintroduziria a dependência do pool.

**Congelamento.** O conjunto designado é publicado como arquivo e preso por
`sha256`, no mesmo par de env vars que o `ASSIGNMENT.json` usa
(`NOX_P2_DESIGNATION` + `NOX_P2_DESIGNATION_SHA256`). Divergência de hash ⇒ recusa
servir tratamento. **Não é recomputado a cada brief**, e a razão é operacional:
`p2_verdict` é tabela viva (`write-path.ts:189` insere), então recomputar faria o
conjunto mudar se uma adjudicação nova entrasse — o oposto de congelado. O código
recomputa **uma vez por processo** apenas como guarda de drift, e grita
`p2_designation_drift` se o derivável divergir do congelado; o arquivo continua
sendo a autoridade.

### Por que `sig_primary` NÃO entra na chave

O layout aprovado em 14:47Z era `SHA256(seed ‖ "|" ‖ sig_primary ‖ "|" ‖ chunk_id)`.
Foi corrigido às 19:40Z, **antes** desta declaração, e o registro está em
`DECISION-designacao-2026-08-25.md` §B.

**Todos** os 19 valores de `sig_primary` contêm `|` — o próprio separador
(`Bash|shell:outro`, `Read|arquivo:doc`). O layout portanto **não era injetivo**, e
a colisão é concreta: `seed ‖ "Bash|shell:outro" ‖ 308226` e
`seed ‖ "Bash" ‖ "shell:outro|308226"` são a **mesma sequência de bytes**. Não é
explorável — `sig_primary` vem de `p2_verdict`, conjunto de valores fechado e
publicado, não de entrada livre — mas registrar "colisão conhecida e aceita" é
posição pior do que não ter a colisão.

A correção foi **remover o campo**, não trocar o separador, porque cada chunk
pertence a exatamente um grupo (0 de 55 em mais de um): pertencimento já é função
de `chunk_id`, logo `sig_primary` na chave não carregava informação. A propriedade
estatística é idêntica — uniforme dentro de cada grupo, grupos disjuntos, sorteios
independentes. E há um ganho: a chave passa a depender **só de ids congelados**, de
modo que renomear um `sig_primary` não move designado nenhum. É a mesma classe de
mutabilidade que invalidou a regra anterior via `access_count`.

**Não foi argumento:** medi os dois layouts sob a seed de teste `ab`×32 (3 dos 19
designados diferem; soma de severidade 6,5000 contra 6,7500). Esses números não
entraram na decisão. Escolher layout pelo resultado sob uma seed já disponível é
pescaria de seed — o mesmo vício que fez esta declaração usar rodada nova em vez de
sub-seed rotulada.

### Por que rodada nova e não sub-seed rotulada

O repo tem os dois precedentes. `assign_arms.py:465-495` (`cmd_permute`, `SEED_B`)
deriva sub-seed de uma seed-pai por rótulo, sem rodada nova. **Não serve aqui.** A
`randomness` do pai já é pública, então seria possível computar offline o resultado
para vários rótulos e escolher o favorável — pescaria de rótulo é
discricionariedade com aparência de derivação. Com rodada nova, a rodada **não
existe** quando a declaração é pushada, e a pescaria é impossível.

O precedente da sub-seed existe para **amostragem** (quais episódios medir). Esta
seed escolhe **quem recebe tratamento**, e merece a garantia mais forte. O custo são
cinco minutos de espera.

## Beacon

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| `chain` | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| `genesis_time` | 1692803367 |
| Período | 3 s |
| **Rodada `R`** | **31657512** |
| Emissão de `R` | **2026-08-26T20:25:00Z** |
| Estado de `R` na escrita | **HTTP 425** — não emitida |
| Regra para `R` | ≥ 5 min de folga sobre `T_declare`. `T_declare` = **20:07:27Z**, folga real **1.053 s** (limite era 20:20:00Z) |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** (o v2 **não** devolve `randomness`) |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaço |
| **Ordenação** | `key(c) = SHA256( ascii(seed) \|\| "\|" \|\| c.chunk_id )` — o separador `\|` é **obrigatório** |

## Verificação por terceiro

```bash
CHAIN=52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
RAND=$(curl -s https://api.drand.sh/$CHAIN/public/31657512 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)

# O conjunto designado, recomputado do zero:
python3 designation_verify.py --round 31657512 \
        --verdicts p2-verdict-frame-2026-08-26.csv
```

O frame está **depositado neste repositório** —
`p2-verdict-frame-2026-08-26.csv`, 55 linhas, `sha256`
`9d0d80d68ffc61733426b0850d2c0f920b4b0b7a3052bd9865d6930ba3f5178a` — e foi
commitado às **20:08:55Z**, também **antes** de `R` existir. Isso importa: com o
frame publicado antes do sorteio, não há como ajustar a população depois de ver o
resultado. É o resultado exato de

```sql
SELECT DISTINCT sig_primary, severity, chunk_id FROM p2_verdict
 WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')
 ORDER BY sig_primary, chunk_id;
```

e a verificação por terceiro não depende de acesso ao banco.

`designation_verify.py --self-test` trava o layout de bytes sem tocar a rede: seis
checagens, entre elas o **teste negativo do separador** (sem o `|` a chave muda) e
a distinção entre `seed` como string hex e como 32 bytes decodificados.

O separador está explícito porque **sua ausência é um defeito vivo neste repo**:
`extract_episodes.py:226` faz `sha256(seed + episode_id)` sem ele, é o script que
`CALIBRATION-SEED.md` manda um terceiro rodar, e
`EXTENSION-SEED-2026-08-11.md:49-64` registra o estrago (reproduziu 293 de 1.576
episódios em vez de 1.565). Havia **três** implementações inline da derivação e
nenhuma compartilhada; `designation_verify.py` é a quarta e a primeira com vetor de
teste, e importa `seed_from_randomness_hex` de `assign_arms.py` em vez de
reimplementar.

### Vetor de teste cruzado, congelado

Com `seed = "0"×64` e os grupos abaixo — nomes contendo `|` de propósito, porque é
o dado real:

| grupo | membros | designado |
|---|---|---|
| `grupo\|um` | 10 (S1), 11 (S1), 12 (S2) | **11** |
| `grupo\|dois` | 20 (S2) | **20** |
| `grupo\|tres` | 30 (S1), 31 (S1) | **30** |

`sha256` do conjunto: `a599d19de17400a870f474828aba6bdc263550fd843412a17e591fda1305b4f8`

Chaves individuais:

```
10  c5135da1044e3e823bfa94d61ea0986129d54688683691ed11024f535f020faa
11  3bf1f31ad408d7ecac870c2ac2129aee13662d8443e850dd015c0f56ae70f972
30  011b80e08a7c7f4dc4020689c12d77529e02ee349b4216704380b8ba3df921f6
```

Note que em `grupo|um` o designado é um **S1** havendo um **S2** disponível: a
regra sorteia e **não olha severidade**. É o ponto da opção B.

Este vetor é asserção em **duas** implementações — `designation_verify.py`
(`--self-test`) e `src/__tests__/p2-outcome.test.ts`. Cinco mutações do fonte TS
foram confirmadas fazendo os testes falharem: separador removido (3 falhas), seed
como bytes (3), sha1 no lugar de sha256 (2), filtro de S0/`chunk_id NULL` removido
(1), desempate entregue à ordem de linha (1). Asserção que não morde não é
asserção.

## Resultado — a preencher DEPOIS de `R` ser emitida

| Campo | Valor |
|---|---|
| `randomness` de `R` | _(preencher)_ |
| `seed` derivada | _(preencher)_ |
| conjunto designado (19 ids) | _(preencher)_ |
| `sha256` do conjunto | _(preencher)_ |
| TS × Python concordam | _(preencher)_ |

## O que esta seed NÃO decide

- **Não é o `T_seed_assign`.** São dois sorteios distintos: esta escolhe **qual
  chunk** recebe o boost dentro do grupo; o `T_seed_assign` sorteia **qual braço**
  cada epoch recebe. Nomes distintos, declarações separadas, e confundi-los
  permitiria a quem conhece uma inferir a outra. O `T_seed_assign` continua aberto
  e vem depois — nunca foi declarado no OSF `yf7d2`, por decisão de 17/08, para só
  existir depois de o mecanismo estar congelado.
- **Não fixa a dose.** `w` e `Δ_cut` são dose, não designação. O item 3 do §5.3 da
  emenda (`Δ_cut`) fica para a própria rodada, com medição antes da decisão — a
  disciplina que funcionou aqui.
- **Não inicia o Epoch 1.** A ordem é: esta seed → `ASSIGNMENT.json`
  (= `T_seed_assign`) → `NOX_P2_OUTCOME=active` → Epoch 1.
- **Não altera a emenda.** A v1.12 está depositada e imutável
  (`10.5281/zenodo.22110203`, 2026-08-26). Esta declaração é o cumprimento dos
  itens 1, 2 e 4 do §5.3 dela, não uma revisão.

---

*Proveniência: `DECISION-designacao-2026-08-25.md` (decisão 14:47Z, layout
corrigido 19:40Z, consequência do restart declarada 20:05Z) ·
`AMENDMENT-v1.12.md` §5.2, §5.2-bis, §5.3 · `LAMBDA-SEED-2026-08-21.md:55-80`
(maquinaria de beacon) · `designation_verify.py` · `src/paper2/brief-outcome.ts` e
`src/api/brief.ts` na VPS (compilados e testados 2026-08-26T19:5xZ, 379 passes / 0
falhas na suíte de 380).*
