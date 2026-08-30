# `T_seed_assign` — declaração da seed de atribuição de braços

> **Precedência.** Este documento é escrito e empurrado **antes** de a rodada `R` existir.
> No instante da escrita, `GET /public/31774052` devolve **HTTP 425** e a rodada mais
> recente da chain é **31773754** — 298 rodadas antes. Quem duvidar da ordem pode conferir
> o horário do commit contra o `emission time` da rodada: eles são fatos independentes,
> um do Git e outro do beacon, e nenhum dos dois está sob nosso controle.

## Para que serve

Esta seed fixa **qual braço cada epoch recebe** no ensaio intervencional do Paper 2. Ela
é o `T_seed_assign` que o pré-registro (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`)
deixou como `[TO LOCK]`, e é o **último** desses.

⚠️ **Esta é a segunda seed do estudo, e a distinção é substantiva.** A seed de 2026-08-26
(`DESIGNATION-SEED-2026-08-26.md`, rodada 31657512) escolhe **qual chunk** de cada grupo
de assinatura recebe o bônus. Esta escolhe **qual braço** cada epoch recebe. Reutilizar a
primeira para esta seria pescaria de rótulo com aparência de derivação: a `randomness`
daquela rodada **já é pública**, então qualquer atribuição derivada dela seria computável
offline antes de ser declarada. Por isso, rodada nova.

## Pré-condições verificadas antes de declarar

| # | condição | estado na escrita |
|---|---|---|
| 1 | a concentração está medida e publicada | ✅ `out/CONCENTRATION-2026-08-30.json` |
| 2 | o estimando prospectivo está registrado, com o desfecho primário nomeado | ✅ `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis: **H1c primária** |
| 3 | a designação está congelada e recomputável por terceiro | ✅ `sha256_do_conjunto` `e549420907cd…`, TS × Python concordando |
| 4 | a designação está viva em produção, com o pino batendo | ✅ `sha256` idêntico em repositório, VPS e drop-in |
| 5 | nenhum epoch randomizado existe | ✅ `ASSIGNMENT.json` não existe; `NOX_P2_OUTCOME=shadow` |
| 6 | o mecanismo opera e a sua taxa está medida | ✅ **3,74%** de churn na janela fechada (`out/SHADOW-CHURN-2026-08-30.json`) |

⚠️ **A pré-condição 6 é nova e corrige o registro.** O texto anterior supunha que o
mecanismo estava inerte e que ligar a seed o faria sair de zero. Ele **já opera**: em
2026-08-30 mediu-se `designated_ids` não-vazio em 1.344 de 1.344 decisões e churn de
**151 em 4.037** briefs. O que esta seed muda é a atribuição de braços, não a existência
do efeito.

## Desenho — travado antes do sorteio

**Unidade de randomização:** o *epoch*. **N = 234** epochs, alocação **117 / 39 / 39 / 39**
(controle / três braços de tratamento), como registrado. O aninhamento
`H1c ⊆ H1b ⊆ H1a` permanece.

**A regra, e ela é total:**

```
seed = SHA256( ascii_hex(randomness_de_R) )
key(e) = SHA256( ascii(seed) || "|" || ascii(epoch_index) )
```

Os 234 epochs são ordenados por `key(e)` crescente; os primeiros 117 recebem
**controle**, os 39 seguintes o braço **1**, os 39 seguintes o **2**, os últimos 39 o
**3**. Não há desempate porque não pode haver: `key` é um SHA-256 de 234 entradas
distintas, e uma colisão teria probabilidade da ordem de 2⁻²⁴⁴.

⚠️ **O separador `|` é obrigatório e é a terceira vez que este repositório o declara.**
`extract_episodes.py:226` faz `sha256(seed + episode_id)` **sem** o separador, e
`EXTENSION-SEED-2026-08-11.md` registra o estrago: 293 episódios reproduzidos em vez de
1.565. Sem separador, `seed="ab"+id="1"` e `seed="a"+id="b1"` colidem. Com ele, o layout
é injetivo porque a seed é hex e o índice é decimal, e nenhum dos dois contém `|`.

## Beacon

| Campo | Valor |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| `chain` | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| `genesis_time` | 1692803367 |
| Período | 3 s |
| **Rodada `R`** | **31774052** |
| Emissão de `R` | **2026-08-30T21:32:00Z** |
| Estado de `R` na escrita | **HTTP 425** — não emitida (mais recente: 31773754) |
| `T_declare` | **2026-08-30T21:16:59Z** — folga real **901 s**, limite era 21:21:59Z |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** (o v2 **não** devolve `randomness`) |
| Derivação | `seed = SHA256( ascii_hex(randomness) )`, hex minúsculo, sem `0x`, sem espaço |

## Verificação por terceiro

Sem acesso a este repositório e sem confiar em nada aqui:

```bash
CHAIN=52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
R=31774052
RAND=$(curl -s "https://api.drand.sh/$CHAIN/public/$R" | python3 -c 'import json,sys;print(json.load(sys.stdin)["randomness"])')
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d" " -f1)
python3 - "$SEED" <<'PY'
import hashlib, sys
seed = sys.argv[1]
ordem = sorted(range(1, 235),
               key=lambda e: hashlib.sha256(f"{seed}|{e}".encode()).hexdigest())
bracos = {}
for i, e in enumerate(ordem):
    bracos[e] = "controle" if i < 117 else f"tratamento_{(i - 117)//39 + 1}"
seq = ",".join(f"{e}:{bracos[e]}" for e in range(1, 235))
print("sha256_da_atribuicao:", hashlib.sha256(seq.encode()).hexdigest())
PY
```

O `sha256_da_atribuicao` que isso imprime tem de ser idêntico ao registrado em
`ASSIGNMENT.json` depois da emissão. Se divergir, **esta declaração falhou** e o estudo
não começa — não há versão desta seed que possa ser "corrigida" depois de emitida.

### Vetor de teste, congelado antes da emissão

Para que a implementação seja verificável **antes** de `R` existir, com uma seed que não
é a de produção:

| seed de teste | primeiros 5 epochs por `key` crescente |
|---|---|
| `0000000000000000000000000000000000000000000000000000000000000000` | conferir com o bloco acima trocando `$SEED` |

⚠️ O vetor existe para travar o **layout da chave** (`seed`, `|`, índice decimal), que é
onde o defeito de 2026-08-11 morava. Ele não valida a seed de produção, que ainda não
existe.

## O que esta seed **não** decide

- **Não** decide qual chunk recebe o bônus — isso é a seed de 2026-08-26, e as duas são
  independentes por construção.
- **Não** decide a dose `w`, que é parâmetro de desenho e está declarado em outro lugar.
- **Não** decide quando o Epoch 1 começa. A ordem é: emitir → derivar → conferir TS ×
  Python por `sha256` → publicar `ASSIGNMENT.json` → ligar `NOX_P2_OUTCOME=active` →
  Epoch 1. Cada passo trava o seguinte, e **nenhum** deles pode ser antecipado.
- **Não** autoriza análise: o estimando, o desfecho primário e a regra de parada estão em
  `PROSPECTIVE-ESTIMAND-2026-08-30.md`, escrito antes deste documento.

## Resultado

A rodada emitiu em **2026-08-30T21:32:04Z** — **13 min 29 s** depois do push da
declaração (`57980ed`, 21:18:35Z). Os dois horários são fatos independentes: um do Git,
outro do beacon.

| Campo | Valor |
|---|---|
| `randomness` de `R` | `b32cf63d65fd6ca8dbd9d9b08a0bb77efe7144f18bad3dbbfce6816d498d55fd` |
| `seed = SHA256(ascii_hex(randomness))` | `e86436153592e2655e095c58a96400ed4292b69ace6f53f65c0e41b87b290087` |
| **`sha256_da_atribuicao`** | **`2426d13de4cd90e6391573e9edc54786c9fb4ca4304f0ea51e09ca916e5c5bd9`** |
| Distribuição | controle = 117 · tratamento_1 = 39 · tratamento_2 = 39 · tratamento_3 = 39 |
| Arquivo | `ASSIGNMENT.json` |

**Os oito primeiros epochs**, para conferência a olho contra o recompute de terceiro:

`1:controle` · `2:controle` · `3:controle` · `4:tratamento_3` · `5:controle` · `6:controle` · `7:tratamento_2` · `8:controle`

✅ **Concordância verificada.** O bloco de verificação publicado acima — que não depende
deste repositório, só do beacon — e o `assignment_derive.py` produzem o **mesmo**
`sha256_da_atribuicao`. A conferência foi feita comparando os dois hashes, não olhando as
234 linhas.

⚠️ **Este documento não é mais alterável.** A rodada foi consumida; não existe versão
desta seed que possa ser "corrigida". Qualquer defeito encontrado a partir daqui é
declarado como desvio, não emendado no sorteio.
