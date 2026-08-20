# O prefixo travado pelo §2 aponta para um armazém morto

> Achado de 2026-08-20, a partir de uma dúvida do Toto: *"veja direito se parou
> mesmo entity files — acho q não"*. Ele estava certo, e eu estava errado **duas
> vezes**.

## O que eu tinha afirmado, e por que estava errado

Em 19/08 registrei que *"a autoria de entity files parou em 10/07"*, com evidência:
184 arquivos no disco, 184 `source_file` distintos no DB, mtime mais novo 10/07.

**A autoria não parou. O formato mudou.** Medido no DB, chunks escritos nos últimos
7 dias — **232** deles:

| `source_file` | chunks (7 d) | último |
|---|---|---|
| `memory/lessons.md` | **52** | **2026-08-20** |
| `memory/decisions.md` | 11 | 2026-08-20 |
| `memory/projects.md` · `people.md` · `pending.md` | 19 | 2026-08-20 |
| `agents/<nome>/memory/*` | ~40 | 2026-08-19 |
| `events/mac/*`, `shared/*` | resto | 2026-08-18 |

Lições continuam sendo escritas **todos os dias** — em `memory/lessons.md`, o
arquivo agregado plano, e não em `memory/entities/lessons/<slug>.md`, o formato de
3 seções que o §2 descreve.

**Meu erro de método:** verifiquei um diretório e concluí sobre um comportamento.
A pergunta certa não era *"esse diretório recebe escrita?"* e sim **"o que a loja
está recebendo, e de onde vem?"** — uma query, não um `ls`.

## O defeito, que é maior que o meu erro

O pool de cobertura lê de dois conjuntos de padrões, e ambos são explícitos no
código:

```ts
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%"];        // brief.ts:107
const agentFreshPatterns   = scopePatterns(scope, agent);   // => sessions/<agente>/%
```

`memory/lessons.md` **não casa com nenhum dos dois.** Contagem de elegíveis
(nunca-servido + `importance ≥ 0.7 ou pain ≥ 0.7` + idade ≤ 30 d), com o gate real:

| pool | elegíveis |
|---|---|
| `memory/entities/%` — **o que o §2 trava** | **0** |
| `memory/lessons.md` — onde a lição vive hoje | **52** |
| todos os `memory/*.md` planos | **89** |
| tudo elegível fora dos dois padrões | **103+** |

**Consequência em produção:** os 2 slots de cobertura estão **inertes**. Não por
falta de conteúdo — há 103 chunks elegíveis — mas porque os padrões apontam para
onde o conteúdo não está mais. `CUTS-MEASURED-2026-08-18.json` já mostrava
`slots_cobertura: []` com `n_principais: 10` nos seis agentes, e eu li isso como
"pool vazio" em vez de "padrão errado".

Isso é uma regressão silenciosa do mecanismo de cobertura (trabalho D2/D3), desde
que o formato de memória migrou. **Independe do Paper 2** e vale como incidente
próprio.

## O que muda para o estudo — e é substantivo

O §2 trava `source_file` do chunk escrito em `memory/entities/lessons/<episode_id>.md`
justamente para cair no sub-pool global. Isso **funciona** — o padrão casa. Mas:

**O chunk do estudo seria o único ocupante de um pool vazio.** Logo o tratamento
não *desloca* nada: ele **preenche dois slots que hoje ficam vazios**.

O estimando registrado diz que o efeito é *"o efeito de **quais chunks são
servidos**"* — uma repesagem. O que o mecanismo faria, como está, é **acrescentar
dois itens onde não havia nenhum**. São intervenções diferentes:

| | o que o §2 descreve | o que aconteceria |
|---|---|---|
| natureza | repesagem do ranking | adição de conteúdo |
| brief de controle | 10 itens | 10 itens |
| brief de tratamento | 10 itens, 2 trocados | **10 itens, 2 substituídos por lições de falha** |

⚠️ A última célula precisa ser **medida**, não deduzida: se `pick` reserva os 2
slots de cobertura e eles ficam vazios, o brief pode estar servindo 10 do main pool
(preenchimento) ou 8 + 2 vazios. `CUTS-MEASURED` mostra `n_principais: 10`, o que
sugere preenchimento — então o tratamento **substituiria** 2 itens do main pool.
Isso é repesagem, e salva o estimando. **Mas está inferido de uma medição feita para
outra pergunta, e tem de ser medido de propósito.**

## Três opções, e nenhuma é obviamente certa

1. **Manter o prefixo `memory/entities/`.** O estudo funciona, o chunk entra, e a
   ausência de competidores é uma propriedade declarada — mas o tratamento age num
   pool artificialmente vazio, o que enfraquece a generalização ("funcionaria numa
   frota cuja cobertura está viva?").
2. **Consertar `GLOBAL_FRESH_PATTERNS` para incluir `memory/%.md`** antes do estudo.
   Reativa a cobertura, dá 52 competidores reais, e torna a dose significativa no
   sentido registrado — mas é **mudança no caminho de serviço** às vésperas do
   estudo, e muda todo número de competição já medido.
3. **Escrever o chunk do estudo em `memory/lessons.md`.** Não casa com nenhum
   padrão ⇒ o tratamento seria inerte. **Descartada.**

**Não recomendo escolher hoje.** As opções 1 e 2 diferem no que o estudo mede, e a
decisão precisa da rodada de painel (λ) para saber quantos chunks o estudo escreve
por epoch — que é o que determina se 52 competidores é muito ou pouco.

## Correções a fazer nos documentos

- `AUDIT-SECTION2-SERVING-2026-08-18.md` §"sub-pool vazio diagnosticado" afirma
  *"falha de autoria"*. **É falha de prefixo.** O pipeline funciona, a autoria
  funciona, o padrão é que aponta para o lugar errado.
- `EPOCH-SNAPSHOT-ACTIVE-2026-08-19.md` diz *"o corpus está estático desde 10/07"*.
  **Falso:** 232 chunks em 7 dias. O que está estático é o prefixo `entities/`.
- `DOSE-DECISION-2026-08-18.md`: a leitura de "regime real = chunks do estudo
  competindo só entre si" continua válida **sob a opção 1**, e cai sob a opção 2.
