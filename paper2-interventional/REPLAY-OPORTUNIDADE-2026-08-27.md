# Replay de oportunidade — item 1 do protocolo, e o que ele derrubou

> **2026-08-27.** Primeira medição do canal de boost do Paper 2 que exercita o
> **código real de serving**. Fecha o defeito declarado no §4 de
> `DEVIATIONS-FOR-PAPER.md` — *"nada aqui faz replay de `interleaveFresh`,
> `pickDedup`, `pinned`, near-dup ou o corte do `LIMIT 400`; mede-se ordenação,
> não seleção"* — e, ao fechá-lo, **contradiz o achado central da emenda**.
>
> Harness: `measurement/replay-oportunidade.mjs`. Tabelas emitidas por
> `measurement/replay-resumo.py` (nenhum número desta nota é digitado).
> Artefatos: `measurement/out/` (JSON de cada rodada).

---

## 1. O que a harness é, e por que a anterior não servia

`buildBriefDiverse` é **importada do `dist`** e chamada com a mesma assinatura
que `src/api/brief.ts:975` usa em produção, com o provedor de boost montado
igual a `:957`. Logo o replay passa por `fetchRankedPool`, `buildPools`,
`fetchFreshCandidates`, `ordenarCobertura`, `interleaveFresh`, `pinned`,
near-dup e as cinco fases do `pickDedup` — nada é reimplementado.

O que existia antes (`measurement/gap-defs.mjs`) reconstruía **só a ordenação do
sub-pool global**: 108 candidatos de `memory/entities/%`. Media uma coordenada de
um dos dois sub-pools e concluía sobre o canal inteiro.

## 2. Fidelidade contra a produção — 350 de 350

O teste é o mais forte disponível: para cada brief da janela fechada
`[2026-08-26T20:28Z , 2026-08-27T09:00Z)`, replay com o `ts` do próprio brief,
seu `scope`/`agent`/`n`, e comparação com o que a **produção registrou** —
composição do controle, `churn`, `would_enter`, `would_leave`.

Emitido por `replay-resumo.py --campo out/c-350-v3.json --campo-estrito out/c-350.json`:

| corte de serve-state | replayados | controle bate | churn bate | churn produção | churn replay | inventado | perdido |
|---|---|---|---|---|---|---|---|
| **`rowid`** | 350 | **350** | **350** | 12 | **12** | **0** | **0** |
| `estrito` (temporal) | 350 | — | 346 | 12 | 14 | 3 | 1 |

Conferir a composição do **controle** é o que impede fidelidade por coincidência:
sem essa coluna, um brief cujo controle e cujo tratado estivessem os dois errados
poderia bater no `churn` e passar.

## 3. Três defeitos de instrumento no código de PRODUÇÃO

### 3.1 O brief não é função pura de (corpus, serve-state, `nowMs`)

`src/api/brief.ts:645` corta a população elegível com
`julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?` — o
relógio do **SQLite**, não o `nowMs` que o resto da função recebe por argumento.
A população elegível anda sozinha com o tempo de parede.

É a mesma classe de defeito já registrada em três scripts de medição desta linha
de trabalho, agora encontrada no **serving**. Consequência: qualquer replay
ingênuo mede uma população diferente da que a produção viu, e a diferença cresce
com o atraso do replay.

O contorno é exato e não usa fake-clock: como o predicado é `agora − data ≤ K`, o
instante de corte é `agora − K`; para reproduzir o corte de `T_REF − K₀` usa-se
`K = K₀ + (agora − T_REF)`. Aplicado aos **dois** knobs (`freshMaxAgeDays` e
`freshGlobalMaxAgeDays`), porque `:809` e `:845` sobrescrevem o primeiro pelo
segundo no sub-pool global.

### 3.2 `brief_log.served_at` tem resolução de SEGUNDO — e isso é fatal para replay

O cron dispara 6 agentes em 1–2 s, e o `nox` dispara **duas vezes no mesmo
segundo**. Resultado medido: **46,9%** dos 350 briefs dividem o segundo com outro
brief (`measurement/irmaos-no-segundo.py`). Isso é **exposição**, não taxa de
erro — o dano só se materializa quando os picks do irmão intersectam o pool de
cobertura.

O caso que expôs isso: `cipher` e `forge` às 23:07:05, nessa ordem.

| corte | o que o serve-state do `forge` fica | slots de cobertura que saem |
|---|---|---|
| `< 23:07:05` | **perde** as 10 linhas do `cipher` | `308487, 308488` — os picks do próprio `cipher` |
| `<= 23:07:05` | **ganha** as 10 linhas do próprio `forge` | `308260, 308264` |
| produção | depois do `cipher`, antes do `forge` | `308457, 308258` |

Nenhuma regra temporal expressa "depois do cipher, antes do forge, no mesmo
segundo". Os 8 picks principais batiam nos três casos: a divergência ficou
confinada aos **2 slots de cobertura** — que é exatamente onde a medida de
desfecho do estudo vive.

**O conserto existe e está no schema:** `brief_log.id` é `AUTOINCREMENT`, isto é,
a ordem de inserção que o timestamp perdeu. O corte `rowid` localiza o brief no
log pelo **grupo de `brief_id`** cujo conjunto de `chunk_id` é igual a
`ids_controle` (assinatura única) e corta em `id < min(id das próprias linhas)`.

⚠️ A primeira versão localizava por `(agent, segundo)` exigindo 10 linhas, e
falhava em **31 de 350** — 25 deles `nox`, justamente por causa das duas
disparadas no mesmo segundo, cujas 20 linhas casavam e eram rejeitadas por
contagem. Localizar por contagem num conjunto com duplicatas é a mesma armadilha
de *invariante verificado sobre o conjunto errado*.

**Consequência quantificada:** sob corte temporal estrito o replay **inventa**
churn 3 vezes e **perde** 1, e a contagem de desfecho sai **14 em vez de 12** —
16,7% de superestimação. Um estimando construído sobre `served_at` sozinho estaria
errado, e errado para cima.

### 3.3 `ordenarCobertura` descarta a chave de estrato do que devolve

`src/api/brief.ts` termina `ordenarCobertura` com
`ranked.map(({ lastServedMs: _drop, ...c }) => c)`. Quem consome o pool devolvido
**não tem** a chave de `last_served` que ordenou o pool. Agrupar por ela no
objeto devolvido dá **um grupo só**, em silêncio — foi o primeiro resultado desta
harness, e parecia um achado sobre produção quando era o campo não existir.

## 4. A âncora citada no protocolo é internamente inconsistente

`PROTOCOL-CALIBRATION-2026-08-27.md` exige reproduzir *"pool 108, 55/55 do
estudo, 44 grupos, nunca-servidos 0, posição 0"* **e** excluir as sondas por
`brief_id`. As duas exigências não coexistem: pela tabela do §1 de
`REMEDIATION-2026-08-27.md`, `44 grupos` é a figura **contaminada**, que vem junto
com `posição 3`; descontaminada é `43 / 0`. **Nenhuma configuração produz
`44 / 0`.**

As duas colunas foram declaradas na harness e reproduzem exatas, pelo
`fetchFreshCandidates` real:

| configuração | pool | estudo | grupos | nunca-servidos | posição | divergências |
|---|---|---|---|---|---|---|
| sondas excluídas | 108 | 55 | 43 | 0 | 0 | nenhuma |
| sondas incluídas | 108 | 55 | 44 | 0 | 3 | nenhuma |

Rodar as duas **é** o teste de que a exclusão morde: se as duas dessem o mesmo
número, a exclusão seria decoração.

⚠️ E há uma assimetria a declarar: excluir sondas é certo para o **estimando** e
errado para **validar contra a produção** — a produção viu as 25 linhas. Os
números do §2 são portanto com serve-state **idêntico ao da produção**; os do §5
são a quantidade de interesse.

## 5. Controle positivo — e o que ele derruba

`w = 0` entra como **controle negativo**: `boostsParaCandidatos` devolve mapa
vazio para `w ≤ 0`, então churn tem de ser 0 em 350/350. Sem essa linha, um bug
que produzisse churn de qualquer jeito passaria por resposta à dose.

Emitido por `replay-resumo.py --dose out/dose-350-v3.json`, 9 doses × 350 estados:

| `w` | estados que mexem | `churn` total | taxa de oportunidade |
|---|---|---|---|
| **0** | **0** | **0** | 0,00% |
| 0,5 | 5 | 5 | 1,43% |
| 1 | 8 | 8 | 2,29% |
| **2** (produção) | **11** | **12** | **3,14%** |
| 4 | 15 | 18 | 4,29% |
| 7,5 | 17 | 20 | 4,86% |
| 15 | 17 | 20 | 4,86% |
| 100 | 17 | 20 | 4,86% |
| **100.000** | **17** | **20** | 4,86% |

**Veredito do controle positivo: PASSA.** A condição 1 de no-go do item 5 **não**
dispara.

Quatro leituras, e a ordem importa:

1. **O controle negativo passa.** `w = 0` dá churn 0 em 350 de 350. Sem essa linha,
   um defeito que produzisse churn de qualquer jeito passaria por resposta à dose.
2. **A dose de produção reproduz o número publicado.** `w = 2` dá 11 estados e 3,14%
   — os mesmos `11/350 = 3,1429%` da janela fechada. O replay não é só fiel brief a
   brief; é fiel no agregado que a emenda publica.
3. **A resposta é monótona e satura exatamente em `w = 7,5`.** De 15 a 100.000 o
   resultado é idêntico ao de 7,5. O teto é **17/350 = 4,86%** — a capacidade do canal,
   qualquer que seja a dose.
4. **As três doses registradas são DISTINGUÍVEIS:** `2,0 → 11`, `4,0 → 15`,
   `7,5 → 17` estados (12, 18, 20 eventos de churn).

**O que a emenda afirma, e que esta rodada contradiz.** O §1 de
`DEVIATIONS-FOR-PAPER.md` (herdado da emenda) diz:

**O que a emenda afirma, e que esta rodada contradiz.** O §1 de
`DEVIATIONS-FOR-PAPER.md` (herdado da emenda) diz:

> Controle positivo com `w = 100.000` dá `churn` **0** com os 19 boosts emitidos —
> dose absurda sem efeito não é ruído, é prova de que o parâmetro não está na
> coordenada que decide.

**Esse controle positivo rodou sobre o pool reimplementado**, e o número está
errado no pipeline real: `w = 100.000` dá churn **20**, não 0.

O argumento **estrutural** segue de pé — o comparador é lexicográfico, `salience`
só desempata `last_served` idêntico, e é por isso que a resposta **satura**. Mas
as três conclusões tiradas dele caem:

| o registro diz | a rodada mede |
|---|---|
| `w = 100.000` dá churn 0 | churn **20**, em 17 de 350 estados |
| "o parâmetro não está na coordenada que decide" | decide **dentro** do estrato, e é onde a medida de desfecho vive |
| as duas doses superiores são "indistinguíveis por construção do dado" | `4,0 → 15` e `7,5 → 17` estados: **distinguíveis** |

⚠️ **Isto piora o custo aceito na decisão de 27/08 de não emendar.** As três linhas
falsas listadas no `DEVIATIONS-FOR-PAPER.md` superestimavam o desenho; esta
**subestima** — o registro afirma que o parâmetro não tem efeito quando tem, e
que a banda é vazia quando ela é justamente a faixa entre sub-saturação e
saturação. É a segunda linha do registro em que a realidade é *melhor* que o que
está publicado, e nenhuma das duas se conserta com o tempo.

⚠️ **E não afirmo que a banda foi bem escolhida de propósito.** A saturação cair
exatamente em `7,5`, o topo da banda, é observação; o que a decisão de 26/08
registra é outra derivação. Coincidência favorável não é desenho.

⚠️ **O que ainda não está medido, e não vou inferir:** por que a saturação chega
onde chega. O gap máximo intra-estrato publicado (0,0318) foi medido **só no
sub-pool global**, e o pipeline real tem dois sub-pools intercalados mais a
disputa contra o pool principal por `salience` crua no `pickDedup`. Os gaps do
sub-pool do agente **não foram medidos**. Sem eles, a localização da saturação é
observação, não mecanismo.

## 6. O que isto licencia, e o que não

**Licencia:** uma definição de oportunidade que corresponde ao código, porque o
replay reproduz a produção em 350 de 350 briefs — controle, churn e identidade dos
ids que entram e saem. É o pré-requisito do item 4 (o `N = f(dados)`) e do item 5
(o critério de no-go).

**Não licencia:**

- **nenhum estimando de efeito.** Toda a janela é `modo: shadow`,
  `servido: controle` em 352/352 — nada foi tratado. `churn` é taxa de
  oportunidade **contrafactual**;
- **nenhuma alegação sobre auto-extinção.** A série é toda anterior ao tratamento;
- **nenhuma inferência sobre a banda registrada** sem antes medir os gaps
  intra-estrato do sub-pool do **agente**;
- **nada sobre carry-over.** `last_served` não é congelado pelo snapshot de epoch
  e realimenta: tratar em `T` altera a estrutura de estratos em `T+1`. É o item 6
  do protocolo, deliberadamente aberto.

## 7. Um resultado negativo que vale registrar

A escolha de corpus é **inerte** aqui. Os 11 briefs com churn reproduzem
idênticos com o snapshot de `26/08` e com o de `27/08` — e o símbolo `current.db`
virou às 06:01Z de 27/08, no meio da janela, então a produção usou **os dois**.
Todo o churn é dirigido pelo **serve-state**, não pelo corpus.

Isso não dispensa passar o corpus por caminho explícito: dispensa **supor** que a
escolha não importa. Aqui não importou, e agora está medido.
