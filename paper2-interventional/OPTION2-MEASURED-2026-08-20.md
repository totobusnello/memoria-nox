> # 🔴 RETRATADO EM PARTE — 2026-08-20
>
> As seções que tratam a fila como **ponto de massa** e validam a "barra viva
> 0,7345 ≈ `CUT_FRESH` 0,7342" estão **erradas**. Os 0,7345 são o topo do
> subconjunto **já servido**, não a barra; a barra medida é **0,684477** (os 38
> nunca-servidos) e não é um limiar de salience — `fetchFreshCandidates` ordena
> `last_served ASC` **primeiro**, com salience só como desempate.
>
> A coincidência com 0,7342 é numerologia. A tabela de dose derivada dela não vale.
>
> Correção completa, com o mecanismo real e o achado de que a barra é um **estoque
> em dreno** (38 hoje, ~14/dia): **`BAR-RETRACTION-2026-08-20.md`**.
>
> O que sobrevive: a escolha da opção **2a** sobre a 2b — mas por outra razão
> (a homogeneidade vale no subconjunto **nunca-servido**, não no pool inteiro),
> e o conserto do prefixo em si, que está medido e correto.

# Opção 2 medida: consertar o padrão **restaura** a tabela de dose registrada

> Item 1 da ordem acordada. Read-only, cópia fresca do corpus de hoje
> (`VACUUM INTO /tmp/p2-hoje.db`). Script: `opcao2.mjs`.

## O que aparece quando o padrão alcança onde a memória vive

| cenário | padrões | candidatos | slot 1 | slot 2 |
|---|---|---|---|---|
| **opção 1** (atual) | `memory/entities/%` | **0** | — | — |
| **opção 2a** | `+ memory/lessons.md` | **52** | 0,7347357 | **0,7347357** |
| **opção 2b** | `+ memory/%.md` | **89** | 0,7925310 | **0,7347357** |

## O achado: a barra medida é o `CUT_FRESH` registrado

| | |
|---|---|
| barra do slot 2, medida hoje sob a opção 2 | **0,7347357** |
| `CUT_FRESH` registrado no §2 (2026-08-15) | **0,7342** |
| diferença | **0,000536** |

E a tabela de dose inteira volta:

| sev | base @1d | `w` vs barra medida | `w` registrado no §2 |
|---|---|---|---|
| S1 | 0,6695 | **6,07** | 6,03 |
| S2 | 0,6945 | **1,87** | 1,85 |
| S3 | 0,7195 | **0,47** | 0,46 |
| S4 | 0,7445 | **0,00** | 0,00 |

**Todos reproduzem dentro de 0,04 unidade de dose.** E a banda travada funciona como
registrado: `w = 2.0 > 1,87` alcança S2.

## Isto corrige a minha própria auditoria

A auditoria de 18/08 concluiu que *"o modelo de corte não existe — entrar é vencer
fila, não cruzar barra"*, e daí que **14 afirmações** derivadas caíam. A primeira
metade está certa e verificada: `pick` fase 3 não aplica limiar nenhum.

**A segunda metade não segue.** Os 52 chunks de `memory/lessons.md` têm salience
**idêntica** — `0.7347356622860862` nos três primeiros slots, bit a bit — porque
vêm todos de **um arquivo**, logo compartilham `source_date`, `importance` (0,90 via
`TYPE_MAP["memory/lessons.md"] = "lesson"`), `pain` e `access = 0`.

Um pool degenerado num único valor **é** uma barra. "Vencer a fila" e "cruzar
0,7347" são a mesma operação quando a fila é um ponto de massa.

Então `CUT_FRESH = 0.7342` não era constante fictícia: era **descrição empírica
fiel** da barra, medida quando o padrão ainda alcançava conteúdo vivo. Ela ficou
obsoleta porque o **padrão** ficou órfão na migração de formato — não porque o
modelo estivesse errado.

⚠️ **O que continua verdadeiro da auditoria:** o código não tem limiar
*explícito*, então o limiar é **emergente** e depende da composição do pool. Sob a
opção 1 (pool vazio) ele desaparece; sob um pool heterogêneo ele deixa de ser um
número. Registrar `CUT_FRESH` como constante congelada só é defensável **enquanto o
pool for um ponto de massa** — e isso passa a ser premissa declarada, não
propriedade eterna.

## Recomendação: opção 2a

**Consertar `GLOBAL_FRESH_PATTERNS` para `["memory/entities/%", "memory/lessons.md"]`.**

| | |
|---|---|
| restaura o estimando registrado | o tratamento **repesa** (2 slots disputados) em vez de **acrescentar** (2 slots vazios) |
| restaura a tabela de dose | 6,07 / 1,87 / 0,47 / 0,00 vs 6,03 / 1,85 / 0,46 / 0,00 |
| conserta regressão de produção | 2 de 10 slots do brief voltam a funcionar |
| não exige emenda dos números de dose | eles voltam a valer, em vez de mudar |

**Por que 2a e não 2b:** a 2b traz 89 candidatos incluindo `decisions.md`
(`importance` 0,95 ⇒ salience 0,7925), o que **eleva** a barra e torna o pool
heterogêneo — matando a propriedade de ponto de massa que faz o `CUT_FRESH`
registrado valer. A 2a mantém o pool homogêneo e é a mudança mínima.

⚠️ **E é conserto de bug, não mudança motivada pelo estudo.** A distinção importa
para integridade de pré-registro: o §2 descreve um mecanismo de cobertura que a
produção deixou de executar. Restaurá-lo é recuperar fidelidade ao registrado, não
escolher o mundo que favorece o resultado. Isso precisa estar escrito na emenda com
esta justificativa, e a data do conserto registrada.

## Fragilidade que a medição expôs, e não estava registrada

Com 52 candidatos **empatados no mesmo valor**, o desempate de `coverageCompare`
recai em ordem arbitrária (inserção/`id`) depois de esgotar `last_served` e
salience. Ou seja: **quais 2 dos 52 ocupam os slots é indeterminado** pela regra
registrada.

Não afeta o braço de controle (é a mesma indeterminação nos dois braços), mas
afeta a interpretação: o chunk do estudo, quando impulsionado acima de 0,7347,
desloca **um dos 52 arbitrariamente**, não "o mais fraco". Precisa ser declarado.

## Reproduzir

```sh
sqlite3 -readonly "$NOX_DB_PATH" "VACUUM INTO '/tmp/p2-hoje.db'"
node opcao2.mjs /tmp/p2-hoje.db
```


---

## ✅ Implantado — 2026-08-20

Aprovado pelo Toto, `nox-workspace#44` (squash `4239d1be`), buildado e em produção.

```ts
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"];
```

**Efeito medido em produção**, contra baseline capturado imediatamente antes:

| agente | itens novos | brief mudou? |
|---|---|---|
| nox · atlas · boris · cipher · forge · lex | **2 cada** | sim, nos seis |
| **total** | **12/60 — 20,0%** | |

Exatamente `freshSlots = 2` por agente. Nem 1, nem 3: o mecanismo voltou a
funcionar como projetado, nos seis agentes ao mesmo tempo.

Os itens que entraram, verificados no DB:

```
memory/lessons.md | importance 0.90 | pain 0.90 | salience 0.7345
```

⚠️ `pain = 0.90`, não 0,20 — o `inferPain` casou `HIGH_PAIN_PATTERN` no texto das
lições. Isso **não** muda a barra (a salience medida, 0,7345, bate com a prevista,
0,7347357, dentro do decaimento de algumas horas), mas confirma pelo lado prático
o que a auditoria já dizia: `pain` em produção é **regex sobre prosa**, e é por
isso que o write path do estudo o sobrepõe explicitamente.

**A barra viva é 0,7345**; `CUT_FRESH` registrado é **0,7342**. Diferença de
**0,0003** — mais perto ainda do que a medição em cópia dava.

Zero erros no log desde o deploy.

### O que isto fecha

| | |
|---|---|
| regressão de produção | **consertada** — 2 de 10 slots do brief voltaram a servir |
| estimando do §2 | **restaurado** — o tratamento agora **repesa** um pool disputado, não preenche vazio |
| tabela de dose registrada | **volta a valer** (S1 6,07 · S2 1,87 · S3 0,47 · S4 0,00) |
| `CUT_FRESH = 0.7342` | **volta a ser descrição fiel**, com 0,0003 de erro |

### O que isto abre

Os 52 competidores agora são reais, então **os números de competição medidos entre
18 e 19/08 sob pool vazio estão obsoletos** — `CUTS-MEASURED`, `INGRESS-*` e a
tabela de λ da barra endógena mediram um regime que não existe mais. Precisam ser
refeitos sob o pool restaurado, e é isso que a emenda vai citar.
