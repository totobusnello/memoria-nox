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
