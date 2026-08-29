# nox-mem HANDOFF — estado vivo

## 2026-08-29 — o gate REPROVOU, e o §4.3.1 foi substituído

`ciclo-do-lote.py --esperar-zero-em 2026-08-29` saiu **`exit 1`, REFUTADA**: o lote foi
servido 108× com idade máxima de 7,42 dias, contra zero previsto.
`PREDICTION-2026-08-29.md` mandava reescrever antes de qualquer depósito. Cumprido.

**Causa.** Dois sub-pools de cobertura, não um: por agente (`sessions/<agente>/%`, 7 d) e
global (`entities/%` + `lessons.md`, **30 d**). O lote da retrodição era do primeiro, o da
predição é do segundo. Janela de um canal aplicada a lote do outro.

**O que entrou no lugar** (`pool-elegivel.py`, `POOL-ELEGIVEL-2026-08-29.json`): o canal
enxerga **108 chunks de 67.187 — 0,161%** — com **zero** nunca-servidos restantes, e
**esgota o pool inteiro todo dia** (12,4 slots por candidato). Não há lote a esperar; há um
recorte a alargar. A tese foi propagada para §1, §4.3, §6, §7, §9 e o `PAPER-SPLIT`.

⚠️ **Três erros meus no caminho, todos no §6 ou em memória:** piso contado como `AND` onde
o código diz `OR` (13 vs 128); explicação construída sobre `GLOBAL_FRESH_PATTERNS`
memorizado de 19/08, quando o código já tinha dois padrões (55 vs 108); e um commit que
alegou oito edições que **não foram aplicadas** — o script abortou no primeiro `assert` e o
`claims_check` passou verde sobre o arquivo intacto.

### ▶️ ESTADO / PRÓXIMO PASSO

**Voltaram e foram aplicadas:** DeepSeek (§4.3.1 e a refutação), GLM (§5.7/§5.7.1) e Kimi
(5 itens sobre o §4.1/§4.2). Da rodada do Kimi saíram quatro mudanças, e duas delas são
**retiradas de alegação**, não correções de número:

| o quê | onde |
|---|---|
| coorte por idade — a censura temporal **desinfla**, não infla (a coorte com oportunidade máxima é a mais não-exposta, 85,50% × 83,78%) | §4.1, `exposicao-por-coorte.py` |
| co-manchete nova: **10.008 = 74,75%** dos que passam o piso do próprio sistema nunca foram expostos | §4.1 |
| ⛔ retirada: `×0,38 por década de tamanho` — o eixo tem **zero** tipos entre n=53 e n=1.046 (32,1% da amplitude vazia) | §4.2, `lacuna-no-eixo-de-tamanho.py` |
| ⛔ retirada: "o teste separa curadoria de tamanho" — não separa, e nenhuma variável do corpus mede curadoria | §4.2 |

Mais 13 substituições lexicais (item 5) e a correção de um erro de atribuição que
sobreviveu a três revisões: "205 caracteres" era a média de **todos** os 14.456
`distilled`, não a dos 8.928 que a frase nomeia (**232**). Veio de consulta *ad hoc* de
27/08 sem artefato, e só apareceu ao virar script. Os três desvios estão registrados em
`DEVIATIONS-FOR-PAPER.md §7`.

**Rodando agora:** Grok e Codex sobre o manuscrito **consolidado** — as duas vozes que
nunca leram este paper, e ninguém leu a versão que existe depois das mudanças de hoje.
Grok ataca o argumento (com varredura de eco das alegações retiradas); Codex ataca a
máquina de verificação (alegação sem guarda, guarda que não pode morder, guarda satisfeito
por ocorrência coincidente).

**Depois delas:** aplicar o que sobreviver e, então, o depósito do Paper A — que **exige
aprovação explícita do Toto** e resolver o número de versão pelo estado do Zenodo, nunca
pelo rótulo do texto. O pré-registro existente (OSF `yf7d2`, Zenodo
`10.5281/zenodo.22110203`) é do estudo **interventivo**; o Paper A é trabalho distinto.

**Não bloqueia:** Paper B nunca começou (`NOX_P2_OUTCOME=shadow`, sem `ASSIGNMENT.json`);
interação designação × granularidade não medida; `colocation-probe.sh` nunca rodou e o
`kg-build` que ele observaria é semanal, aos domingos.

**Decidido e encerrado:** dois papers (28/08); webhook do Discord **não** será rotacionado.

---


## 2026-08-28 (tarde) — dois achados que mudaram como o teto é reportado

**O teto de 4,86% não é constante do mecanismo, em dois eixos independentes.**

1. **Resolução de `served_at`** (§5.7, `CEILING-GRANULARITY-2026-08-28.json`). O
   comparador é lexicográfico, então o teto é função de quantos empates o **formato** da
   chave produz — e a resolução é o default do `datetime('now')`. Truncando: 4,86% →
   36,29% → 80,29% → 99,43% de segundo a dia, sem tocar em código. Uma predição minha
   morreu no teste: coarsening **não** é monótono nos conjuntos, porque fundir estrato
   move o braço de **controle** junto. Cirúrgico porque `served_at` tem **um** consumidor
   vivo — `serveCounts` está exportado, testado e nunca chamado.
2. **Qual chunk o sorteio pegou** (§5.7.1,
   `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json`). Oito designações alternativas da
   mesma regra: 4,86%–7,43%, mediana 5,71%, e **a designação em vigor é a menor das
   nove**. As alternativas movem *outros* briefs, não só mais.

**§4.3.1 verificado por retrodição** (`BATCH-CYCLE-2026-08-28.json`): o lote de 09–10/08
serviu 8 dias, idade **máxima** nunca alcançando 7,00, encolheu 75→54 em 16/08 e zerou em
17/08 sem voltar. E o texto citava só uma das **duas** janelas — há `freshMaxAgeDays = 7`
(por agente) e `freshGlobalMaxAgeDays = 30` (global). Elegível ≠ alcançável: o global
ordena por `last_served ASC` e quem acabou de ser servido vai para o fim da fila.

**Separação em dois papers executada:** §4.5 reescrito, Apêndice A virou "relação com o
pré-registro", Apêndice C saiu, §5.1 ganhou a proveniência de `D`. E o **§6 perdeu uma
linha pelo critério que ele próprio declara** — o κ de 0,874 é a lição mais citável do
conjunto e não muda número nenhum deste paper. Sete viraram seis.

## 2026-08-28 — o gatilho do item 7(a) deixa de recusar `active`

Era o único item de implementação declarado como **bloqueio da ativação**. Estava
assim desde 27/08: em `active` a dose vem do braço sorteado no `ASSIGNMENT.json` e
não de `NOX_P2_SHADOW_W`, então o wrapper preferia sair YELLOW a vigiar com a dose
errada. Agora ele vigia.

O que o modo `active` forçou, e que não era detalhe de implementação:

1. **A janela deixa de ser o dia UTC.** O epoch vira às **09:00Z**, logo um dia UTC
   atravessa **dois** epochs e possivelmente dois braços. A janela vira
   `[E 09:00Z, E+1 09:00Z)`, só de epoch **já fechado**.
2. **Epoch de controle não tem dose para saturar** — a pergunta é indefinida ali.
   GREEN, mas com o motivo escrito.
3. 🔴 **`resolverBraco` devolve controle em TODA falha.** É a escolha certa para
   servir (não serve tratamento a partir de sequência não verificada) e a errada
   para vigiar: "controle no log" fica **ambíguo** entre sorteio e `ASSIGNMENT`
   ilegível, e a segunda hipótese enviesa o estudo para o nulo **em silêncio**.

Por (3) o gatilho passou a **cruzar o log com o `ASSIGNMENT`** — epoch × epoch,
braço designado × `servido`, dose designada × `w` do log. É a única coisa em toda a
instrumentação que compara **o que devia ser servido com o que foi**.

✅ **Horário movido 05:41Z → 09:12Z**, e a conferência do guarda achou um defeito
que não era o motivo da mudança: o `morning-report.sh` (06:30Z) YELLOWa status com
mais de 30 h, mas às 05:41Z uma **rodada pulada** envelhecia só até 24,8 h ⇒ **um
dia inteiro sem gatilho passava como GREEN**. Às 09:12Z: normal 21,3 h, pulada
45,3 h ⇒ morde, com 8,7 h de folga. Orçamento de 30 h mantido.

Verificação: 10 casos de mutação (`measurement/teste-gatilho-active.sh`) e os testes
mordem — neutralizar o cruzamento derruba T3/T4/T7, aceitar epoch aberto derruba T2.
Implantado em `/root/.openclaw/scripts/p2/` com sha conferido contra a fonte, e a
cópia anterior batia com o `HEAD` (zero drift).

## 2026-08-28 — propagação ao repo público: dois PRs abertos

As correções do dia chegaram ao `totobusnello/nox-mem` (linhagem publicada, que
é intencionalmente distinta da VPS — ver `docs/REDEPLOY-VPS-LINEAGE-PLAN.md`;
promoção é **uma correção por vez**, não sincronização):

| PR | o quê | estado |
|---|---|---|
| [#25](https://github.com/totobusnello/nox-mem/pull/25) | `indexOnly` em `/api/health` + `prune-orphan-vectors` — a classe de vetor **invisível** aos três instrumentos | aberto |
| [#26](https://github.com/totobusnello/nox-mem/pull/26) | `top_chunk_ids`/`top_scores` na telemetria (schema **v19**) | aberto |

⚠️ **O PR #26 NÃO leva `query_text`, e isso é o ponto.** O comentário do v6 em
`db.ts` declara que o texto cru da query não é armazenado; a coluna existe em
alguns DBs por reconciliação de drift, e **existir não é autorização para
escrever** — foi exatamente o erro que eu cometi na VPS em 27/08 e reverti no
mesmo dia. O teste B1 lê o `INSERT` do fonte e falha se ela reaparecer.

Verificação: 4 testes novos, **mutação testada nos dois sentidos** (tirar
`migrateToV9` derruba só A2; pôr `query_text` derruba B1 e B2), suíte completa
**590/590** no node 22. O Mac não compila `better-sqlite3` no node 26 — a
verificação rodou em cópia descartável na VPS, fora do caminho de produção.

## 2026-08-28 (madrugada) — vec0 medido e correções do dia incorporadas aos canônicos

**Reempacotar o índice vec0 corta 33,1% da latência de busca** (668,2 → 446,8 ms,
n=60 por braço, −221 ms). Medido em cópia; produção intocada. A aritmética do
tamanho previa ~34% e fechou: 103 chunks/1.236 MB → **68**/816 MB. As 2 de 12
sondas que divergiram são bloco de empate exato maior que o `LIMIT` (130 e 15 a
distância zero) ⇒ já arbitrárias. **Recomendação: fazer, com o envelope da D77.
NÃO executado — decisão do Toto.**

**⚠️ Retratação de três alegações minhas de 27/08** (commit `65e91ad`): são **16**
colunas sem escritor e não 13 (lista digitada no meu script); foram **seis**
instantes distintos e não um commit; e "sem `CUT` ⇒ regressão" vale só para um
grupo — os `reason_boost_*` **têm** `CUT`. O commit que eu culpei é 10 h POSTERIOR
à morte, e a assinatura no dado é buraco de 1h19 ⇒ **deploy**, não código.

**Incorporado nos canônicos:**
- `CLAUDE.md` regras **8–11**: censo de coluna sem escritor · guarda cujo predicado
  exige o dado que falta · vec0 é a única cópia dos embeddings (+ `BigInt` no rowid)
  · o ganho de 33,1% e como medi-lo sem se enganar;
- `docs/INCIDENTS.md`: telemetria de busca muda desde 19/05 (descoberta 3,3 meses
  depois) · os **2.074** vetores inalcançáveis e invisíveis aos três guardas;
- `docs/DECISIONS.md` **D77**: recomendação, envelope de segurança e por que não é
  urgente (o desperdício **não recorre** — `prune` 0/dia, `vectorize` 0);
- morning report: contador `vec0 fora do map`, alarmando no **crescimento**.

**✅ Feito no nox-mem (código), commit `32f78109` na VPS, empurrado:**
1. `search.ts` — **religado** o escritor de `query_text`/`top_chunk_ids`/`top_scores`.
   Verificado: busca real gravou (delta +1 sobre 6.318 congelados desde maio);
2. `prune-orphan-vectors.ts` — `countIndexOnlyVectors()`, que **conta** a classe
   invisível nos três caminhos de retorno (inclusive no `no orphans`, que era
   verdadeiro e cego). **Não apaga**: origem não identificada, e apagar sem saber a
   origem é apagar evidência;
3. `api-server.ts` — `vectorCoverage.indexOnly`. Produção agora devolve
   `{"orphans": 0, "indexOnly": 2074}`, os dois lado a lado.

Testes: **5 novos** (`src/__tests__/index-only-vectors.test.ts`), 5/5. Suíte
377/380 — as 2 falhas são pré-existentes em `edge-typing` (KG), reproduzem isoladas,
e o diff está confinado a 3 arquivos, nenhum de KG/schema.

**Repo público `totobusnello/nox-mem` — PR #25 aberto**, só com a correção que se
aplica lá (`indexOnly` no health). As outras duas ficaram fora **de propósito**: o
módulo do `prune` não existe no *core-kit trim*, e o schema dele não tem as colunas
de telemetria — adicioná-las é decisão de produto, não correção. Base:
`docs/REDEPLOY-VPS-LINEAGE-PLAN.md` do repo público, que registra em 17/06 que os
lineages são **intencionalmente diferentes** e a direção é promover fix por fix.

---

## 2026-08-27 (noite) — §5 do Paper 2 fechado; Proposição 1 verificada

**§5 escrito e verificado.** A derivação sai do comparador citado verbatim:
ordem lexicográfica em `(last_served, −salience)`, bônus só na coordenada
subordinada ⇒ permuta **dentro** de estrato, nunca entre. Corolário que importa
mais que o teto: **se `last_served` fosse injetiva o bônus seria identicamente
inerte** — todo o espaço de manobra vem de empates na coordenada dominante.

**Teste (`--modo porque`, 350 estados, paridade com o artefato de dose):**
17 estados mudam, 20 ids entram, **0** entradas fora do estrato de quem saiu.
Mutante (estrato próprio por id) ⇒ **20 violações**, aborta. O zero é resultado.

⚠️ **A primeira versão do teste era inválida** e o §5.6 do manuscrito registra:
classificava o designado por posição num pool que ela mesma montava, deu 25 contra
17 e só 1 dos 17 na classe. `interleaveFresh`/`FRESH_CANDIDATE_POOL` não são
exportados ⇒ era reconstrução. Teste válido só usa grandezas registradas.

⚠️ **`freshSlots = 2` não é medido:** default de `DIVERSITY_DEFAULTS`, sem
override na unit nem no `.env`, e é **teto** dos slots preenchidos. `brief_log`
não tem coluna de origem de slot ⇒ a divisão 8/2 não é observável no registro.

**Gatilhos:** status agora emite `ts_inicio`/`ts_fim`/`duracao_s` (a rodada
levava 911 s e era rotulada pelo início); `timeout` 1500→2700 s (folga era 1,65×,
e estourar dá RED por capacidade). Steal time deste host: 0–6%.

**Monitoramento:** `integrity` não alarmava por ausência perpétua (a perna de
idade exigia idade que só existe com linha). Fechado, 4 pernas testadas.
Autocorreção: os cron jobs deste host começaram em **23/08 ~15:40** — nenhum
domingo passou, `no runs yet` era verdade. Check rodado à mão: PASS.

**Próximo bloqueador:** §7 (~1 página) e §1/§8 em prosa. Antes de submeter:
recomputar a contagem de "pre-registration" no survey contra o PDF.

⚠️ **Pendente de decisão do Toto:** rotação do webhook do Discord (exposto em
transcript por `bash -x`) e o rebuild do índice vec0 (420 MB recuperáveis, só por
reempacotamento — `VACUUM` não serve).

---

> Estado-vivo enxuto. Histórico ≤ 2026-06-14 em `handoffs/_archive/HANDOFF-2026-04-28-a-2026-06-14.md`.

---



## 🟢 27/08 — reframe APROVADO: a manchete é a superfície, não a intervenção

O paper deixa de perguntar *"a memória interventiva funciona?"* e passa a responder
**"o que uma memória de agente em produção realmente entrega, e por que uma intervenção
plausível não muda isso"**. A intervenção vira o **instrumento** que prova que o teto é
estrutural. Integral: `paper2-interventional/SUPERFICIE-2026-08-27.md`.

**As duas superfícies, contagem exata** (`brief_log` cobre a vida inteira do `/api/brief`
e não tem poda; `access_count` cobre toda a busca, e o brief nunca escreve nessa coluna):

| corpus | brief | busca | união | **nunca exposto** |
|---|---|---|---|---|
| 67.187 | 1.787 | 9.755 | 11.051 | **56.288 = 83,78%** |

Desses, **10.008** passam o próprio piso de relevância do sistema.

**O achado, e ele sobreviveu a um teste que quase o derrubou:** a leitura "a curadoria
funciona, o gradiente de tipo prova" é **falsa**. Correlação entre `log₁₀(tamanho do
tipo)` e `% exposto` = **−0,728** (ρ = −0,714): o tamanho explica **53%** da variância, e
a separação não tem sobreposição — 5 tipos com n ≥ 1.000 ficam em 10,7–27,0%, 8 tipos com
n < 100 em 32,5–100%. `lesson` está em 100% porque tem 53 linhas, não porque é lição.
**O que o agente vê é decidido pela capacidade fixa da superfície, não pela relevância
que o próprio sistema atribui.**

**E é a mesma medida do teto da intervenção.** Janela fechada `[20/08, 27/08)`: 46.295
slots em 4.632 briefs, **201** chunks distintos, **3** presentes em **100%** dos briefs,
top-10 = **47,16%**. Comparador lexicográfico congela 8 dos 10 slots, sobram 2, e bônus
aditivo neles tem teto de **4,86%**. Não são dois resultados — é um.

⚠️ **Não existe desfecho a jusante instrumentado:** `answer_telemetry`,
`confidence_eval_log` e `agent_events` com **0 linhas**, e `search_telemetry` medindo o
**canário do cron** (48/dia = 2/hora × 24, `requesting_agent` não populado), não o agente.
**O reframe não precisa de um** — e essa é a maior simplificação disponível: a manchete é
superfície + mecanismo, e o contrafactual é **observado** por brief.

⚠️ **Uma inversão que quase entrou na nota:** cumulativamente a busca alcança 617 das 865
entities curadas contra 245 do brief; na **janela comum** dá brief **245** × busca **≥
151** — o brief alcança *mais*. E `search_telemetry.top_chunk_ids` parou de ser populado
em **2026-05-19 14:47:04** (zero de 04/06 em diante), o que torna qualquer comparação
brief-vs-busca **dentro de janela** impossível hoje.

**Protocolo:** item 6 ✅ **DECIDIDO** — estimando na presença de carry-over com
randomização por **dia** (por brief tem interferência fatal via `last_served`; por agente
não salva porque o sub-pool global é compartilhado). Itens 2 e 4 passam a **opcionais**
sob o reframe. Item 1 ✅ fechado, item 7 ✅ no ar.

**Próxima ação:** escrever o manuscrito — que hoje **não existe**. As três seções da
manchete estão medidas, travadas por `--assert-json` e reproduzíveis.

## 🟢 27/08 — item 1 do protocolo de calibração FECHADO, e ele reverteu a emenda

`measurement/replay-oportunidade.mjs` importa `buildBriefDiverse` do `dist` e reproduz a
**produção em 350 de 350** briefs da janela fechada (composição do controle, `churn`,
`would_enter`, `would_leave`; zero inventado, zero perdido). Isso fecha o defeito do §4
de `DEVIATIONS-FOR-PAPER.md` — "mede-se ordenação, não seleção".

**E derruba o §1.** O controle positivo publicado (`w = 100.000` ⇒ churn 0) rodava sobre
um pool **reimplementado**. No pipeline real, 9 doses × 350 estados:

| `w` | 0 | 0,5 | 1 | 2 | 4 | 7,5 | 15 | 100 | 100.000 |
|---|---|---|---|---|---|---|---|---|---|
| estados que mexem | 0 | 5 | 8 | **11** | 15 | **17** | 17 | 17 | 17 |

Monótono — em cada um dos 350 estados, não só no agregado — teto **17/350 = 4,86%**, e
`w = 2` devolve o `11/350 = 3,1429%` publicado. As três doses registradas **são
distinguíveis**.

⚠️ **Correção do grid grosso:** a saturação está em `(4,0 ; 4,4]`, **não** em 7,5. Grid
fino de 23 doses sobre os 17 estados: `w_min` mínimo 0,02, mediana 1,7, **máximo 4,4**
(espalhamento 220×). A "coincidência" com o topo da banda era o instrumento.

**Duas coisas mais, e a segunda é a mais urgente:**
1. **A grandeza que governa é DISTÂNCIA, não passo.** O maior `w_min` vale boost 0,0946
   em S1 — 1,79× o maior passo adjacente do pool (0,0527). O gatilho do item 7, calibrado
   sobre passo adjacente, **pode ficar verde enquanto o canal satura**: inválido no nível
   da grandeza, não do número. O censo reproduz a âncora publicada exata (38/11/27/0,0318)
   na coluna filtrada, e dá 64/34/30/0,0527 sem filtro.
2. **O sub-pool do agente está VAZIO** em `T_REF` — 265/6.001/3.011 chunks de
   `sessions/<agente>/%` passam o piso de importance e **zero** passam a janela de 7 dias.
   Logo `interleaveFresh([], global) === global` e todo o canal é o sub-pool global. Uma
   rajada de sessões muda a composição do canal **sob os pés do estudo**, e isso não está
   vigiado em lugar nenhum. O argumento estrutural (comparador lexicográfico)
sobrevive — é o que produz a saturação; a conclusão tirada dele, não.

⚠️ **O registro público agora tem DUAS linhas em que está pior que a realidade:** a
designação (defeito fechado descrito como aberto) e a banda (parâmetro com efeito
descrito como sem efeito). Falsidade que subestima não se conserta com o tempo.

**Três defeitos de instrumento novos, no código de PRODUÇÃO:** o serving filtra a
população elegível com `julianday('now')` apesar de receber `nowMs`; `brief_log.served_at`
tem resolução de **segundo** e 46,9% dos briefs dividem o segundo (⇒ o corte de replay
tem de ser por `brief_log.id`, e sob corte temporal a contagem sai 14 em vez de 12);
`ordenarCobertura` descarta a chave que ordenou o pool.

**✅ Item 7 no ar (27/08).** Dois gatilhos, fonte em `measurement/`, implantados em
`/root/.openclaw/scripts/p2/`, status em `/var/lib/nox-mem/p2/` lido pelo
`morning-report.sh` às 06:30Z. Cron: 40 → 42 linhas (backup em
`/root/.openclaw/crontab.bak-20260827T175704Z`).

- **(a) saturação, diário 05:41Z** — a regra é uma identidade, não um limiar:
  `churn(w_servido) == churn(w_absurdo)` ⇒ RED. Custa 2 doses de replay, não 23.
  Primeira rodada real (dia UTC de 26/08): 672 estados, `w=2` move 25, `w=100.000` move
  52, folga **0,4808** → GREEN.
- **(b) composição do canal, horário :09** — RED no **primeiro** chunk elegível para
  `agentFresh`. Limiares vêm de `DIVERSITY_DEFAULTS` no `dist` e o script **aborta** se as
  cláusulas do `WHERE` mudarem no fonte.

6/6 mutações mordem, incluindo status velho ⇒ YELLOW e morte por sinal ⇒ RED.
⚠️ O (a) **recusa rodar em `active`**: lá a dose vem do `ASSIGNMENT.json`, não de
`NOX_P2_SHADOW_W` — é item a implementar antes da ativação.

**Próxima ação:** o que resta do protocolo são **decisões**, não medições — item 2
(declarar a janela antes de abrir), item 6 (carry-over: washout · modelar dependência ·
estimando na presença de carry-over) e item 4 (o `N = f(dados)`, que depende do 6).
Depósito v1.13 segue **preparado e não executado**.

Integral: `paper2-interventional/REPLAY-OPORTUNIDADE-2026-08-27.md`. Commit `e4a5cc3`.

## 🟡 Estado atual (2026-08-27, 16:52 BRT) — emenda PRONTA e NÃO depositada, por decisão; desvios vão no paper

> **O estudo está bloqueado por decisão da própria emenda, não por impedimento
> externo.** `Δ_cut` perdeu estatuto de parâmetro: o referente que o registro nomeia
> ("salience spread at the brief cut") não existe — o comparador do pool é
> lexicográfico e `salience` só desempata `last_served` idêntico. A banda
> `{2,0 · 4,0 · 7,5}` está **invalidada como escala calibrada**; recalibração
> prospectiva fica aberta.
>
> **Cinco revisões adversariais, quatro famílias.** GLM e Codex sobre a 1ª redação
> (derrubaram 3 de 5 decisões, incluindo uma **regressão da FATAL F2** que eu havia
> reintroduzido). DeepSeek, Kimi e Codex sobre a 2ª — DeepSeek e Kimi acharam
> independentemente o mesmo bloqueador central (§3 e retratação 30 se anulavam), e o
> Codex arbitrou a formulação. Recibos **e saídas** versionados em
> `paper2-interventional/receipts/`.
>
> ⚠️ **O recibo do Codex da 3ª rodada é irregular e está declarado:** o wrapper deu
> `exit: 124` (timeout 1.800 s, 39 bytes); o resultado veio de invocação direta, fora
> do contrato. Recibo cunhado a partir do artefato (358.332 B, `sha256 5ad86e36…`).
>
> ✅ **Três defeitos de instrumento REMEDIDOS** (`REMEDIATION-2026-08-27.md`):
> a "descontaminação" era rollback temporal de **148×** (3.735 linhas removidas para
> excluir 25); `julianday('now')` em 3 scripts fazia a população mudar a cada
> execução; e `pos-regra.py` tinha janela aberta por cima (o `11/310` já era 359).
> Números que caem: `8/268`, `20/560`, `11/310`, `2.212`, `2,9851%`, `3,5714%`.
> Números que entram: **11/350 = 3,1429%** em janela fechada, base **132/2.226 =
> 5,9299%**.
>
> ⚠️ **Duas correções que eu ia aplicar estavam ERRADAS** — `19/27` e `40 pares/13
> zeros` vinham do rollback, não da exclusão das sondas. O rascunho estava certo
> (`16/27`, `38/11`). Registrado no §7.4 da emenda.
>
> ⚠️ **Eram cinco sondas, não três** — 25 linhas, não 15. Duas às 20:28:55–56, **55 s
> depois de o mecanismo subir**, porque foram elas que verificaram que ele subira.
> Nenhuma das cinco vozes achou isso.
>
> ✅ **`claims_check.py` consertado**, incluindo a remoção de uma invariante que
> codificava raciocínio inválido (exigia a taxa nova **dentro** do IC da antiga —
> sobreposição de IC não é equivalência). Teste de mutação: **18 falsificações, 18
> mordidas**.
>
> ✅ **Passo 0 do §8 FECHADO 27/08:** blobs de serving depositados, conferidos byte a
> byte — `serving-brief.ts` (44.748 B), `serving-brief-outcome.ts` (21.213 B) e
> `serving-p2-outcome-test.ts` (22.673 B, novo, porque o §1 afirma que 5 mutações do
> fonte fizeram os testes falharem e sem o arquivo isso é infalsificável).
>
> 🔴 **E o depósito revelou que o commit que a emenda citava NÃO EXISTE.** `0087c918`
> não é commit, não está em ref nem no reflog, em nenhum dos 15 repos do host. O
> conteúdo estava certo — é `1da78560`, mesmo timestamp e mensagem —; o **nome** morreu
> quando o merge `5174e0fa` reconciliou a VPS com o origin, 37 min depois. Cinco vozes
> adversariais leram a emenda e nenhuma checou se o hash resolvia. Retratação 43.
> Correção estrutural: o manifesto passa a pinar por **`sha256` dos bytes**, que
> sobrevive a rebase e é conferível sem acesso ao repo privado.
>
> 🟡 **DECISÃO 27/08 16:52 BRT — não emendar o registro por enquanto.** O pré-registro
> fica como registrado e os desvios são declarados no **paper**. A obrigação está em
> `paper2-interventional/DEVIATIONS-FOR-PAPER.md`, criada porque não havia manuscrito
> nem doc de desvios: "reportar depois" sem lugar onde ficar é "não reportar".
>
> O depósito v1.13 está **preparado e não executado** — 99 arquivos, 45 uploads, três
> gates passando, readback duplo. Nada foi enviado ao Zenodo. Voltar atrás custa o token
> e um `prepare`.
>
> ⚠️ Custo aceito: o registro público segue afirmando três coisas falsas (`Δ_cut`, a
> banda, a alocação) **e** declarando a designação como defeito *aberto* quando está
> fechada — esta última é a única em que o registro está **pior** que a realidade, e ela
> não se resolve com o tempo.
>
> **Próximo passo:** o protocolo prospectivo de calibração (8 itens do §5), que é o que
> desbloqueia o estudo. Depois: `T_seed_assign` → `ASSIGNMENT.json` → `active` → Epoch 1.
>
> ⚠️ Se o depósito voltar à mesa: reler
> `feedback_the_serialization_you_read_bounds_what_you_can_verify` e
> `feedback_rdm_put_silently_drops_legacy_shaped_metadata` — o PUT no Zenodo já apagou
> autor e licença uma vez devolvendo HTTP 200 — e reconferir os 6 substituídos por md5.

---

## Estado anterior (2026-08-26, 20:20Z) — regra nova NO AR e inerte; seed declarada, esperando a rodada

> ✅ **DEPOSITADO 2026-08-26T14:01Z** — Zenodo **`10.5281/zenodo.22110203`**
> (conceito `10.5281/zenodo.21964093`), version 1.12, **60 arquivos**, state
> `done`. Tag `paper2-v1.12` no repo aponta para o commit exato.
>
> ✅ **Regra de designação DECIDIDA 2026-08-26T14:47Z — opção B** (sorteio
> pseudoaleatório com seed declarada). Custo aceito: 8,8% de dose agregada, para
> remover a dependência da calibração de uma família do painel.
>
> ✅ **Layout da chave CORRIGIDO 19:40Z, antes de congelar:**
> `argmin SHA256(seed ‖ "|" ‖ chunk_id)` — `sig_primary` **saiu** da chave. Todos
> os 19 valores reais contêm `|`, o próprio separador, então o layout aprovado não
> era injetivo. Removido em vez de trocar o separador porque cada chunk pertence a
> exatamente 1 grupo ⇒ o campo não carregava informação. Ganho: a chave depende só
> de ids congelados.
>
> ✅ **Fase 1 NO AR (restart 19:58Z), e deliberadamente INERTE.** Na VPS:
> `designadosGlobais` (derivação global, não condicional ao pool),
> `carregarDesignados` (arquivo congelado preso por path+sha256, como o
> `ASSIGNMENT.json`), `chaveDeDesignacao` (contrato de bytes), guarda de drift.
> `cDesignacao()` e `NOX_P2_C_DESIGNACAO` **removidas** — constante retratada não
> fica viva. Log ganhou `designated_ids` + `boost_by_id`. Testes: 26/26 no módulo,
> **379 passes / 0 falhas / 1 skip** na suíte de 380, e **5 mutações do fonte
> confirmadas mordendo**.
>
> ✅ **Seed declarada com precedência verificável.**
> `DESIGNATION-SEED-2026-08-26.md`, rodada **`R = 31657512`**, emissão
> **20:25:00Z**. Push do commit `40d2462` às **20:07:24Z** *(data do GitHub, não do
> meu relógio)* — folga **1.056 s** sobre requisito de 300 s, e `GET
> .../public/31657512` devolvia **HTTP 425** na escrita. O **frame** de 55 linhas
> também está depositado (`p2-verdict-frame-2026-08-26.csv`, sha256 `9d0d80d6…`,
> 20:08:55Z): congelar o quadro antes da aleatoriedade fecha a porta de ajustar a
> população depois de ver o sorteio, e a verificação por terceiro deixa de depender
> do banco.
>
> ✅ **Seed derivada e regra VIGENTE desde 20:28Z.** `randomness`
> `8fd8522f…67a6d` → seed `e5d134ee…22d7`; 19 grupos, 19 designados,
> `sha256` do conjunto `e549420907cd…da001b`. **TS × Python concordam lendo
> fontes diferentes** — a TS consultou `p2_verdict` ao vivo, o Python leu o CSV
> depositado 16 min antes, e hashes iguais provam de uma vez que as derivações são
> a mesma regra **e** que o frame corresponde à tabela. Boosts conferem com
> `w·Δ_cut·sev`: 0,0215 (S1) e 0,043 (S2); sorteio deu S1=10/S2=9, dose 7,0000
> (esperança 6,6134, máximo de A 7,2500).
>
> 🔴 **`Δ_cut` MEDIDO, e não pode ter referente.** `coverageCompare`
> (`brief-diversity.ts:130-140`) é **lexicográfico**: se `last_served` difere,
> devolve `al − bl` e **nunca consulta `salience`**. O boost é aditivo em
> `salience`, a coordenada subordinada. Pool medido: posições 0-2 com
> `last_served 18:37:05` (não-estudo), primeiro chunk do estudo na posição 3 com
> `18:37:06` — **um segundo depois** — e `freshSlots = 2`. Ele tem `salience`
> **mais alta** (0,7128 vs 0,6822) e perde. Varredura offline no caminho de
> produção: `churn` **0** em `w = 2,0/4,0/7,5` **e em `w = 1.000` e `w = 100.000`**,
> com 19 boosts emitidos. A banda satura no braço mais baixo: maior gap 0,031809 <
> boost de S2 a `w=2,0` (0,043).
>
> ▶️ **Próxima ação: as duas revisões adversariais da emenda**
> (`AMENDMENT-DRAFT-band-collapse-2026-08-26.md`, rascunho **sem número** — número
> é fato do depósito). Rodando GLM e Codex. Depois: depositar → acumular janela de
> ativação → recalcular `N` → registro prospectivo → `T_seed_assign`.
>
> ⚠️ **`N` NÃO pode ser fixado com os 4,1693%.** Essa taxa é de quando havia **1**
> designado por grupo escolhido por `w_min`; agora são **19**. A taxa nova precisa
> de janela real (~26 linhas/h desde 20:28Z).
>
> ⚠️ **O `claims_check` NÃO enxergava a emenda** — mutei a taxa e a banda inteira e
> ele imprimiu "sweep clean" nas duas vezes. `delta_cut_check` fechou isso, mas a
> **primeira versão era decoração**: `str(valor) in join(todos_os_md)` deixava
> passar falsificação no documento que afirma (o número segue em outros docs) e
> `"15"` casa em qualquer lugar. Reescrito para ancorar ao rótulo **no arquivo que
> afirma** e para **recomputar** as contagens de vitória a partir dos 27 gaps
> depositados. **7 mutações, 7 mordem.**
>
> ⚠️ **O `churn` do shadow está em ZERO por desenho, e isso foi declarado às
> 20:05Z, antes do restart.** Sem conjunto designado o mapa de boost é vazio. Linha
> de base para atribuição, em janela FECHADA por sha256 do NDJSON
> (`2026-08-21T22:57:48.194Z` → `2026-08-26T19:52:07.775Z`, 3.166 linhas): `churn`
> positivo **132 = 4,1693%**. São esses 132 que devem desaparecer. **N=3 na
> verificação pós-restart não é evidência** (p=0,88 de dar zero por acaso) — o
> mecanismo está provado, a taxa precisa de tráfego real (~26 linhas/h).
>
> ⚠️ **Não sondar `/api/brief` para levantar N.** Ele não tem gate de tracking
> (`brief.ts:1086` insere em `brief_log` sempre, e `brief_log` alimenta
> `last_served`, que ordena o pool). Não existe `?track=false` como no
> `/api/search`. As 3 sondas de verificação escreveram 15 linhas tocando 3 chunks
> do estudo; **não apaguei**, e a razão inverteu minha decisão inicial: os 3 já
> tinham 47-48 servings, o último 1h51 antes, logo são as linhas 48/49 de uma série
> que o tráfego real já produzia — não a mudança qualitativa nunca-servido →
> servido. Registrado em `DECISION-designacao-2026-08-25.md`.
>
> ⚠️ **O TS novo está NÃO-COMMITADO na VPS** (`nox-workspace`, repo privado; 3
> arquivos modificados). Código vivo em produção sem commit — e existe mecanismo
> de "auto session wrap-up" que o engoliria com mensagem genérica.
>
> ⚠️ **`T_seed_assign` continua aberto.** Designação escolhe *qual chunk*;
> `T_seed_assign` escolhe *qual braço*. Nomes e declarações separados — confundi-los
> permitiria a quem conhece uma inferir a outra.
>
> O GLM fechou a rodada com `exit: 0` e **achou defeito real** — as correções
> entraram em `75fc353` (retratações 15-17). ⚠️ Conferir o **recibo** com
> `exit: 0` antes de aceitar qualquer veredito: hoje duas invocações do Grok não
> produziram análise (uma sem recibo, outra `exit: 124`) porque eu montei o
> briefing com paths de servidor e o wrapper não faz SSH.

### O que mudou de natureza

A emenda deixou de declarar mecanismo **e estimando** e passou a ser
**descritiva** (commit `16a7226`, 672 linhas). Razão medida: `servido="controle"`
em **2.221 de 2.221** registros ⇒ **zero desfecho sob tratamento** ⇒ `N` e
`T_seed_assign` não são estimáveis em shadow. Os 2.221 registros são declarados
**piloto descritivo que não entra em análise confirmatória**; o estimando vai a
**registro prospectivo separado**.

Quatro vozes (Grok, DeepSeek, GLM, Codex) vetaram a redação anterior. Kimi
revisou a reescrita e achou 3 bloqueantes; o GLM revisou depois e achou 6, dos
quais 4 procedem. Todos corrigidos. **28 retratações** no §4.

⚠️ Duas alegações do GLM foram **refutadas por medição** e ficam no Anexo B: a
população 1.305 é consistente (o peso divide o frame pela **amostra** 242, não
pelos 234 adjudicados, e o frame de A é 48, não 46 ⇒ `48 + 1.257 = 1.305` exato);
e o desenho amostral do estrato B **está** declarado — em `LAMBDA-SEED`, que eu
simplesmente não passei à revisão. Mas a lição contrária vale: a alegação
rejeitada sobre `base` carregava o defeito que derrubou duas afirmações.

### Janela de piloto CONGELADA

`[2026-08-21T22:57:00Z ; 2026-08-25T10:22:00Z]`. Números emitidos por
`pilot_window_stats.mjs`, travados em `PILOT-WINDOW-2026-08-25.json`
(`--assert-json` falha se divergir). A série cresce 28 registros/hora — contagem
citada como instante envelheceria num depósito imutável.

| | |
|---|---|
| total · churn>0 · deslocamentos | 2.221 · 102 · 111 (93×1 + 9×2) |
| pré-gate / pós-gate | 954 com **0** / 1.267 com 102 = **8,1%** |
| série horária pós-gate | 47 h · média 7,8% · mediana 3,6% · 0,0–46,4% · 14 h com zero |
| autoria | entram **16/16** ids e **111/111** eventos do estudo; saem 25/33 e 99/111 |

### 🔴 O defeito que bloqueia o registro prospectivo (§5)

**A designação não está validamente congelada.** O código consome
`CUT_FRESH = 0,7342` (`brief-outcome.ts:235-238`) cujo referente a emenda
retrata. E o desempate registrado (`w_min` → `created_at` → `chunk_id`,
`PREREG-DRAFT.md:535`) **nomeia uma coluna que não existe** em `p2_verdict` —
não é só não-implementado, é não-implementável como escrito.

Medido: **4 dos 7** grupos multi-membro têm empate exato em `w_min` (19 grupos
totais) e nesses **o designado saiu da ordem incidental do SQLite**. Os 111
deslocamentos são reproduzíveis como agregado mas **não atribuíveis a regra
determinística**.

⚠️ Esse número era **5 de 7** até 15h55; caiu para 4 quando o GLM levantou que
`base` podia não ser invariante entre chunks de mesma severidade e eu fui medir.
`salienceBase` é `calculateSalience` (`src/salience.ts:246`), que tem
`0,20 · log1p(access_count)/log(1000)` e **nenhum** termo em `written_at` — os 55
chunks têm 9 bases distintas. E como `access_count` cresce quando o chunk é
servido, a estrutura de empates **varia no tempo**: o 4/7 é do fechamento da
janela, não da época dos 111 deslocamentos, e aquela não é recuperável.

⚠️ **Decisão pendente do Toto:** escolher a regra de designação substituta. Não é
implementação — é decisão, e ela decide o tratamento em 4 dos 19 grupos. Opções,
requisitos e recomendação em **`paper2-interventional/DECISION-designacao-2026-08-25.md`**.
Recomendo **B** (sorteio com seed declarada, mesma maquinaria do λ) sobre **A**
(severidade máxima): A troca o acidente da ordem do SQLite pela calibração de um
painelista — `xai` responde por 72,2% do share de S2. Custo de B é dose, e dá
para medir esse custo antes de decidir, sem tocar em desfecho.

✅ Achado ao documentar: `access_count` só é incrementado por `recordAccess`
(`src/search.ts:396`), nos caminhos de `search`. **Brief serving não incrementa**
⇒ não existe laço designação → serving → designação. A designação não é
pós-randomização; é **não congelada** (depende de tráfego de busca exógeno).

### Ordem de operações (§8 da emenda)

1. Depositar a v1.12 — **declara o defeito antes de consertá-lo**, senão o
   documento descreve um sistema que já não existe (o `commit 2740ded3` citado)
2. Consertar a designação (4 itens do §5.3)
3. Registro prospectivo do estimando/estimador/variância
4. `T_seed_assign` (= gerar `ASSIGNMENT.json` com sha256, seed ancorada no OSF)
5. Passar a `active` via drop-in; verificar por **estado observável** que
   `servido` alterna e que `p2_arm_unresolved` é zero
6. Epoch 1

### Retratações e achados do dia

14 retratações consolidadas no §4. As de hoje: o vocabulário de **"desempate"**
(a salience **seleciona 2 entre 12–31**, medido — grupo de empate tem 12 a 31
chunks e `fresh_added` é 2 em todos os registros); `CUT_FRESH` (0,8524 é o cut do
pool **principal**, o congelado é 0,7342); e a taxa de ativação (**8,1%**
pós-gate, não 4,6% da série inteira).

Também caiu a leitura de 24/08 de que a série seria transiente de depleção: o
zero das primeiras 954 decisões é o **gate de maturidade**, e a transição
`churn = 0 → > 0` **não** coincide com a migração de host (o gate abriu 2h37
antes do snapshot; o hiato de coleta censurou a janela).

### Notas operacionais

- **Piloto segue rodando** em shadow. A janela depositada está fechada, então
  nada do que vier depois a contamina.
- **Infra migrou** para o KVM2 (2 cores/8 GB); o KVM8 ficou só para
  pesquisa (K=8). KVM2 estabilizou em load ~0,7 (era 8,36 no dia da migração).
- **Dois hiatos** de 23/08 declarados no §6 com reconciliação: 4 ciclos/28
  registros **perdidos** + 12 ciclos/84 **nunca gerados** = 16 ciclos = 112 =
  672−560.
- ⚠️ `codex-cli` atualizado 0.139.0 → **0.149.1** (`gpt-5.6-sol` exige ≥0.14x; o
  binário do brew é symlink para o pacote npm).

---

## Estado anterior (2026-08-22, 01h) — os 3 componentes no ar; painel rodado; ativação é time-gated

> ▶️ **Próxima ação: em 2026-08-23 depois das 09:00Z**, ler
> `/root/.openclaw/logs/p2-serving.ndjson` e medir a **fração de ativação** (`churn`
> por agente). É o número que decide banda e `N`. Antes disso não há o que medir — e
> `churn > 0` antes de 23/08 09:00Z significa que o gate de maturidade está furado.
>
> Enquanto isso, o único trabalho desbloqueado é **consolidar a emenda v1.12**:
> `paper2-interventional/AMENDMENT-v1.12-DRAFT.md` hoje é remendo de retratações e
> precisa virar prosa depositável.

### Em produção hoje (4 PRs, todos mergeados e deployados)

| PR | o que |
|---|---|
| `#45` | **componente 2** — dual-compute do boost. `alt` = controle, `altBoosted` = tratamento, `diffP2` = deslocamento por brief. Boost no estágio (b) (`ranked.sort`), população pelo JOIN com `p2_verdict.chunk_id` |
| `#46` | **componente 3** — regra de parada mecânica, arm-blind por construção da fonte (`p2_verdict` não tem coluna de braço). Constantes travadas: janela 3 epochs, multiplicador 3×, baseline mín. 14 dias |
| `#47` | **gate de maturidade** — o chunk não pode agir no epoch em que foi escrito (`written_at <= início − 24h`), conforme §3:642 + §2:550 |
| `#48` | docstring do write path corrigido: ele **não** embeda |

Estado observável: `NOX_P2_OUTCOME=shadow`, `NOX_P2_SHADOW_W=2.0`,
`NOX_P2_SERVING_LOG` recebendo linhas. `p2_verdict` com **280** linhas (225 S0 sem
chunk · 33 S1 · 22 S2), invariante chunk⇔veredito **55/55**. `abort-check` em
`exit 4` — 7 dias de histórico contra o gate de 14, **recusa avaliar** em vez de
reportar "sem halt". Suíte **340/0/1**.

### O painel rodou — 870/870, zero quota, 960,7 s

**Antes de rodar, achei o harness quebrado desde 16/08:** o commit `d11afee`, um
censo de *documentação*, traduziu para inglês o marcador que delimita o corpo do
prompt; `carregar_prompt` levantava `IndexError` **antes da primeira chamada**. O
corpo nunca mudou (dá o `5b22f02c…` travado). Conserto real não foi a string: o
hash **era gravado e nunca conferido**. Agora o runner recusa rodar se divergir
(`d09b3cb`).

Cadeia de precedência: declaração pushada **22:17:50Z**, rodada `31515871` emitida
**22:22:57Z**. Amostra estratificada — censo dos 48 `is_error` + 242 de 1.257 a
19,235% — bateu exata com o declarado; o amostrador recusa escrever se divergir.

| | |
|---|---|
| **λ̂** | **0,0775** [0,0539 ; 0,1011] |
| Consolidado | 225 S0 · 33 S1 · 22 S2 · **0 S3 · 0 S4** |
| Abstenções | 12 ⇒ 10 episódios abaixo do piso (3,45%, contra 2,67% na calibração) |

**Zero S3/S4 em 870 chamadas** confirma o baseline zero do §3 em dados frescos — a
cláusula (b) do abort segue em "≥1 derruba".

### 🔴 O achado do dia: o estrato S2 repousa em UMA família

Share de S2 nas próprias falhas: **moonshot 24,2% · zhipu 25,9% · xai 72,2%**. Os
três concordam sobre *haver* falha e divergem sobre *quão grave* (concordância par a
par no nível: 87,9/88,8/89,4% — parecidas entre si). E **dos 22 S2 consolidados, 22
têm `xai = S2`**; sem xai sobreviveriam 5.

Como `W_OUTCOME ∝ severity` e a §2 trata "S2 e acima" como população tratada, o
tamanho dela depende da calibração de severidade de um painelista. O §9 registrou
leave-one-family-out sobre o veredito **binário**; o eixo que carrega a dose é o
**nível**, e ninguém tinha olhado. ⚠️ Não usar LOFO para medir isso — mediana
inferior de 3 é o valor do meio, de 2 vira o **mínimo**, e o estimador muda junto.

### Medido com a população real

- **A designação exclui 65%.** 19 grupos de assinatura para 55 chunks (12×1, 2×2,
  2×4, 1×6, 1×8, **1×17**). Um boost por grupo ⇒ **19 de 55 tratados**, 36 sem
  boost, e 17 chunks (31%) numa única assinatura. A maior parte do que o write path
  escreve é **massa de controle dentro do braço de tratamento**.
- **Gate de cobertura correto:** 55 `compiled` (imp 0,90) passam, 55 `frontmatter`
  (0,40) **nenhum** passa — um candidato por episódio.
- **`churn = 0` não é resultado sobre a dose.** O snapshot servido é de
  `21/08 09:00:51Z` e contém **0** chunks do estudo e nem a tabela `p2_verdict` —
  escritos ~13 h depois. O zero mede ausência de população.

### O que eu retratei hoje (importa para não reconstruir errado)

1. **A intervenção NÃO é nula.** Provei nulidade com monotonicidade de `W_OUTCOME`
   supondo *todos* os chunks impulsionados; a designação impulsiona **um por grupo**
   ⇒ o pool mistura designados e não-designados ⇒ a dose reordena. Kimi e Grok
   acharam o mesmo furo por caminhos independentes.
2. **Os "três platôs" também eram aritmética** sem desfecho observado (DeepSeek).
   Margens de 0,0070 e 0,0035 contra spread de agente de 0,1822.
3. **Não existe "a barra".** O pool ordena `last_served ASC` primeiro; salience só
   desempata entre nunca-servidos. Publiquei 4 valores em 4 dias porque é **estado**.
4. **O cut principal é agente-heterogêneo** (0,610–0,792), não o `0,8524` registrado.
5. **λ̂ = 7,75% é consistente com o desenho** — o `~30%` registrado é share *das
   falhas*, e o parâmetro é `p̂0 = 0,1118` entre **oportunidades**. Anunciei como
   "4× menor" e estava comparando referentes diferentes.

### Fila

| item | estado |
|---|---|
| Medir ativação | **23/08 após 09:00Z** — time-gated pelo próprio gate de maturidade |
| Consolidar emenda v1.12 | desbloqueado, é o trabalho de amanhã |
| `T_seed_assign` | só **depois** de congelar o mecanismo emendado |
| Gate Stanford | série completa (2.064 rows, 14 dias, 07→20/08) |
| `edge-typing.test.ts` deixa `nox-mem.db` no cwd | pré-existente; suíte falha 2 ao re-rodar sem limpar |

---

## 🟢 Estado atual (2026-08-19) — componente 1 EM PRODUÇÃO; falta uma rodada de painel

> ▶️ **Próxima ação: rodar o painel sobre uma janela recente para medir λ** (taxa de
> episódios *adjudicados como falha* por epoch). É o último número que a emenda
> v1.12 precisa. O denominador já está medido: **309,4 episódios/epoch**.

### Em produção hoje

| | |
|---|---|
| `NOX_API_TOKEN` | **rotado** 2026-08-19 (nunca havia sido; 11 arquivos compartilhavam o valor). Um só consumidor: `api-server.ts:120` |
| `nox-workspace#42` | **mergeado e deployado** — write path de falha adjudicada, arm-blind, atrás de `NOX_P2_WRITE_PATH=on` |
| `nox-workspace#43` | **mergeado e deployado** — guarda de isolamento do log |
| golden test em prod | briefs **idênticos** ao pré-deploy nos 3 agentes, com a flag ligada |
| verificação | 12/12 (schema/invariantes/idempotência) + golden 12/12 byte-idêntico + 7/7 HTTP |

O que importa nos testes HTTP: **localhost sem Bearer → 401**. O gate geral deixaria
passar; esta rota exige o token incondicionalmente.

### Medido em 19/08

- **309,4 episódios/epoch** (10 dias completos recentes); piloto dava 319 ⇒ **o volume
  da frota não mudou**. Projeção do §9 era ~396: ~15% acima.
- Volume total do estudo: 234 × 309,4 = **72.400** episódios ⇒ 724 janelas de quota
  Moonshot. A decisão de painel reduzido do §9 fica de pé em qualquer base.
- `is_error` caiu de ~16% para ~2-5% **com o total estável** — sinal real, candidato a
  covariável de tempo.
- Os 7 agentes estão no archive; o stream vive em `.claude-nuvini-team` (failover) e o
  archive está em paridade.

### Bloqueio da emenda v1.12

Uma emenda, não duas (decidido). Falta λ. **Escreve-se sem λ:** o corte não existe, a
escada de severidade, o primário é pooled 117 vs 117, `CUT_FRESH` não sobrevive como
modelo, `w = 2.0` está na borda. **Não se escreve sem λ:** percentual nenhum, `w`
necessário, teto pooled, "o primário sobrevive", a banda como platôs.

⚠️ O sorteio (`T_seed_assign`) está bloqueado até λ medido e banda re-registrada.

### Revisões adversariais desta rodada (todas com recibo verificado)

Grok 4.6 (2.577 B) e Kimi K2 (13.170 B + 40.702 B) acharam 12 defeitos que o censo
mecânico não pegou, incluindo dois estruturais: as shares de severidade estavam sem
proveniência (recuperada — `SHARES-PROVENANCE-2026-08-19.md`, e a **unidade** estava
errada: por veredito, não por episódio) e "por construção" apoiado num lock de campos
que a produção não implementava.

---

## 🔴 Estado atual (2026-08-18) — o §2 modelava um limiar que o código não aplica; componente 1 no ar em PR

> ▶️ **Próxima ação: decisão de desenho do Toto — dose absoluta ou relativa ao cut do agente.** Ela destrava a emenda v1.12 e o componente 2. Nada mais depende de medição.

### O que caiu

Auditoria claim-por-claim do §2 contra o código de produção
(`paper2-interventional/AUDIT-SECTION2-SERVING-2026-08-18.md`): **14 afirmações
travadas caem de um defeito de raiz só.** O §2 modela entrada no brief como
*cruzar um corte* (`CUT_FRESH = 0.7342`); a produção não aplica corte nenhum —
`pick` fase 3 toma os 2 primeiros nunca-servidos, sem limiar. **Entrar é vencer
fila, não cruzar barra.** Dose, banda, alcance, tetos e a testabilidade de H1
vieram todos do modelo morto, incluindo a frase que garantia que o desfecho
primário ficava intocado.

Medido, dirigindo `dist/` na VPS:

| | |
|---|---|
| ingresso a `w = 0` | 4 severidades × 6 agentes, idades 1 d e 7 d; nada a 30 d — a **janela de idade** decide |
| sob 30 d do inflow do estudo | **só S4@1d entra** — 0,08% das falhas. A dose vira **desempate entre chunks do estudo** |
| cut principal real | 0,6100–0,7922 por agente (registrado: 0,8524) |
| `Δ_cut = 0.043` | atravessa **3–11 slots** (gap adjacente 0,0038–0,0157) — a dose é **mais agressiva** que o texto |
| gate de cobertura | **126 de 168** chunks de lesson reprovam — duas implementações de inferência de tipo |

**Sobrevive intacta a camada de desenho inteira** — `N = 234`, ICC, painel,
calendário, `assign_arms.py`, washout, α ordinal — e as travas de método. Nada
aqui olha dado de braço.

### O que subiu

**Componente 1 (write path de falha adjudicada):** `totobusnello/nox-workspace#42`,
pronto para review. Arm-blind por construção, atrás de `NOX_P2_WRITE_PATH=on`.
Verificação 12/12 + golden 12/12 byte-idêntico, contra cópia throwaway do DB de
produção, com controle positivo nos dois. Falta só a camada HTTP, que é deploy.

Ele é o que **mede a taxa real de episódios adjudicados por epoch** — os
`~396/epoch` são projeção, e todo cut medido depende dela.

### Fila

1. ⏳ **Toto:** dose absoluta vs relativa ao cut do agente (o cut é por-agente, 0,61–0,79)
2. deploy do #42 + os 3 testes HTTP ⇒ taxa real de episódios
3. emenda **v1.12** única (Zenodo + 2º registro OSF) cobrindo a tabela inteira
4. componentes 2 e 3, `shadow → active`, freeze, sorteio, epoch 1

⚠️ Aberto e operacional: **a escrita de entities parou em agosto** (749 jun → 6 jul
→ 0 ago), e é ela que deixa o sub-pool global vazio.

---

## 🟢 Estado atual (2026-07-29 noite) — peça 3 FECHADA, `p̂0` deixou de ser piso, e a projeção de K errou por 2-3×

> ▶️ **Próxima ação: acumular epochs.** Todos os bloqueadores de decisão caíram (paridade · ICC · volume/painel). O que falta é cluster: 11 epochs não estimam ICC, e eles chegam de graça a 1/dia.
>
> ⏳ Sem intervenção: backlog do moonshot (`tmux -L peca3`, sessão `moon`) — **demovido de bloqueador**, ver abaixo.

### Estudo vivo: censo com painel API-only — TRAVADO

O gap que o ICC expôs era o volume de adjudicação do estudo vivo: ~38.000 episódios, e a cota do CLI da Moonshot (~100/janela) faz do censo de 5 painelistas ~380 janelas.

**Subamostrar é dominado por princípio:** `E_a = K·T·λ0`, então amostrar à taxa `f` multiplica os epochs por `1/f` e o número **absoluto** de episódios adjudicados fica invariante. Não compra volume — troca throughput por calendário, num estudo que já tem ~130 dias.

Então reduz-se o painel, e a redução foi **medida antes de adotada**, sobre os 1.500 vereditos que já existiam (custo zero):

| painel | Fleiss κ | Kripp. α | Pa | prevalência | ≥3 vereditos |
|---|---|---|---|---|---|
| 5 famílias (ref.) | 0,8815 | 0,8557 | 0,9551 | 0,254 | 295/300 |
| **3 de API** | **0,8747** | **0,8380** | 0,9512 | 0,265 | 287/300 |

Ambos acima do piso de 0,75; perda de **0,7pp em κ**; prevalência segue dentro de [0,20;0,80] ⇒ a regra seleciona o **mesmo** coeficiente, então as linhas são comparáveis.

**Divergência declarada com direção:** 4 de 287 (**1,39%**), todas no mesmo sentido — padrão `[S0,S0,S0,S2,S2]`, os painelistas de CLI ficam em S0 e removê-los transforma minoria de 2-em-5 em maioria de 2-em-3. Painel reduzido acha *um pouco mais* falha, concentrado em borderline genuinamente dividido.

**Dois defeitos antigos que isto fecha de graça:** os painelistas de CLI **não eram reprodutíveis por versão** (só pela saída registrada) — API é reprodutível por identificador; e **paridade morre na origem**, porque 3 é ímpar e sem cota.

⚠️ **O que fica pior:** com exatamente 3, **uma abstenção** derruba abaixo do piso — 8 de 300 (2,67%) medido, dentro do teto de 10% mas frágil. Mitigação seria 4ª família de API, que exige credencial inexistente.

### Piloto recalculado com o instrumento do estudo

| | painel misto | **API-only (vale)** |
|---|---|---|
| `r̂` | 28,76 | **28,60** |
| `p̂0` | 0,1109 | **0,1154** |
| `icc` | 0,0228 | **0,0219** |
| repeats | 270,6 | **280,0** |

Mais repeats, na direção que a divergência previa. **Cobertura igual** (1.394 vs 1.410) porque os 3 de API estavam completos — e é por isso que **o backlog do moonshot deixou de ser bloqueador**. Ele segue rodando porque alimenta o leave-one-family-out (compromisso do §4.1) e eleva a medida de divergência de 287 para 1.140 episódios, mas nada espera por ele.

### ICC sob pesos amostrais — resolvido, e a resposta é um limite, não um número

Eu ia escolher entre HT ponderado (0,0228) e sem peso (0,0351). **Os dois estavam dentro do ruído.** Bootstrap por epoch em 11 clusters:

| variante | ICC | DE (m̄=70,4) | **IC95% do DE** |
|---|---|---|---|
| HT ponderado | 0,0806 | 6,60 | **[1,00 · 14,66]** |
| sem peso | 0,1363 | 10,47 | **[1,00 · 18,44]** |
| **estrato A só (censo)** | **0,0447** | **4,10** | **[1,00 · 7,77]** |

Os três IC contêm **zero** e cada ponto cai dentro do IC dos outros. Causa: **11 clusters não estimam ICC** (precisa 30–50; SE analítico = 0,025, batendo com o bootstrap), e **m̄ = 70,4 amplifica** — ±0,025 em ρ vira ±1,7 no DE. Projetando: 30 epochs → IC ~[0,016 · 0,074]; 50 epochs → ~[0,023 · 0,067]. **O DE fica incerto por fator ~2 mesmo com 50 epochs** — irredutível neste desenho.

**Travado (aprovado 29/07):** (a) estimador = **estrato censado**, por princípio — único livre de variância de peso e carrega **229 de ~270 repeats (85%)**; (b) dimensionar no **limite superior de 95%**, porque erro de sizing é assimétrico (subdimensionar invalida, sobredimensionar custa calendário); (c) **acumular epochs antes do `f`** — chegam de graça, e gastar a avaliação única sobre ruído é desperdício irreversível; (d) publicar a **curva de poder ao longo do IC do ICC**, que deixa de ser formalidade.

⚠️ **(c) supersede o portão de 09/08.** Aquele vinha do baseline do abort; agora é o *menor* dos dois prazos.

### O gap que o ICC expôs — e ele realimenta o DE

O pré-registro **não fixa o volume de adjudicação do estudo vivo**. Com K≈48/braço: 96 epochs × ~396 episódios ≈ **38.000 episódios**. A Moonshot entra por CLI com cota de ~100 chamadas/janela ⇒ censo = ~380 janelas, **inviável**. Então o estudo vivo tem que **subamostrar ou trocar o painel** — e subamostragem adiciona variância que o DE precisa carregar. **Decidir antes do `f`, não durante.**
>
> ✅ **Regra de paridade TRAVADA** no §4.1 — era o bloqueador. Três camadas: trava operacional (cota ≠ abstenção) · maioria estrita com empate ⇒ `not_failure` · divulgação obrigatória com *empate ⇒ falha* como sensibilidade.

### A regra de paridade, e por que a trava operacional é 90% da solução

| | paridade | empate exato |
|---|---|---|
| Calibração — 5/5 completos | 8,8% | **0,3%** (1 de 295) |
| Peça 3 — moonshot 88/1.140 | 88,6% | **1,2%** (13) |

Rodar o painel até o fim derruba paridade **10×**. O empate era sintoma de falha operacional, não propriedade do painel — então a trava principal não é estatística: **um episódio só é finalizado quando todo painelista da allowlist devolveu veredito ou abstenção, e exaustão de cota não é abstenção**. `run_panel.py` agora emite `status: "quota"` separado de `"missing"` (`dd86856`), o que torna a trava verificável por máquina em vez de prometida.

Para o resíduo de 0,3%: **maioria estrita, empate ⇒ `not_failure`**. Subestima falhas ⇒ deflaciona `λ0` ⇒ **infla K**: erra para estudo mais longo, nunca underpowered. Alternativas recusadas por princípio, não pelo número — *empate ⇒ falha* é anti-conservador; *empate ⇒ inadjudicável* condiciona ausência de dado à **discordância do painel**, variável pós-randomização, atacando a premissa de não-diferencialidade; *dropar para ímpar* tem resposta dependente de qual painelista sai.

⚠️ **O mecanismo que generaliza:** só **14 empates** em 1.013 episódios pares (1,4%), mas 11 caíram no estrato de peso **5,204** — 1,4% dos casos moveu o estudo em 20%. **Em desenho ponderado, borda se julga por frequência × peso, nunca por frequência.**

### Backlog do moonshot — rodando

1.050 episódios, chunks de 150, **sonda de 2 chamadas** antes de cada chunk (não queimar 1.050 respostas 403 para descobrir que a cota fechou). Idempotente: recalcula o restante a cada volta do que já gravou, então pausa do Mac não perde nada. Log em `~/.paper2-verdicts/moonshot-loop.log`.

⚠️ **Defeito que peguei antes de deixar rodar:** o loop era `for ciclo in $(seq 1 40)`. Com a cota abrindo a cada ~5h e sonos de 30 min são ~10 iterações dormindo por abertura — 40 iterações cobririam ~4 aberturas, metade do backlog, e o loop **encerraria com código de sucesso**. Trocado por deadline de parede de 4 dias.

⚠️ **Os números da peça 3 são PROVISÓRIOS até o backlog fechar.** Completar o painel não só remove empates — pode virar classificações (2-de-4 vira 2-de-5 ou 3-de-5).

### A adjudicação rodou: 1.140 episódios, 5.700 chamadas, 88 min

Censo do estrato `is_error` (414) + amostra uniforme de 800 do complemento, pela regra de sorteio declarada **antes** em `PILOT-PROJECTION.md` (`SEED_B = b214ca6f…`, ordenação por hash, sem PRNG). **4 de 5 painelistas completos**; `moonshot` parou em 88/1.140 por cota. Cobertura: **1.114/1.140 com ≥3 vereditos** (2,3% inadjudicável, contra teto de 10%).

**A intercalação por hash provou o valor:** os 88 da Kimi são as posições 0–87, mas `is_error` entre eles é **29,5% contra 32,2%** do alvo — o corte por cota ficou cego ao estrato. Sem intercalar, os 88 seriam todos do estrato A e a composição do painel correlacionaria com o estrato, num painel cujos membros divergem sistematicamente (zhipu S1 19,0% vs xai 5,5%).

### Os três números do piloto, com o estimador do desenho

| | censo (sem pesos) | **estratificado-HT** |
|---|---|---|
| `r_hat` | 28,59 | **28,76** |
| `p̂0` | 0,0993 *(piso)* | **0,1109** |
| `icc` | 0,0351 | **0,0228** |
| oport. sem desfecho | 1.729 | **12** |

`p̂0` **deixou de ser piso** — era o objetivo da peça. `hours_per_epoch = 6,06` · `session_hours_per_epoch = 70,43` · 14 epochs analisáveis.

### Dois defeitos no harness, corrigidos em `0ef3e43`

1. **Condição (ii) estava pela mediana de severidade**, mas o §4.1 trava *"condition (ii) is the binary verdict. Severity governs condition (i) only."*
2. **Faltavam pesos de Horvitz-Thompson** — sem eles o estimador subcontava os repeats do estrato amostrado por `N_B/n_B = 5,2×`.

### O `[TO LOCK]` novo, e por que ele bloqueia

Com contagem **par** de vereditos, a mediana superior aceita **2 de 4** (empate virando falha) e a maioria simples exige **3 de 4**. O pré-registro só afirma ausência de empate por supor painel ímpar — premissa que abstenção e falha de cota derrubam. **987 dos 1.140 episódios têm exatamente 4 vereditos**: contagem par é a regra, não a exceção.

Só **14 empates exatos** em 1.013 episódios pares (1,4%) — mas o peso 5,204 do estrato B amplifica cada um em 5×, e o swing é de **20% no tamanho do estudo**: mediana superior dá K=53, as duas leituras fiéis (maioria estrita; empate ⇒ inadjudicável) convergem em **K=64**. Adotado no harness: maioria estrita, empate ⇒ `not_failure` — conservador (subestima falhas ⇒ infla K).

### A projeção declarada errou por 2-3×, e a declaração é o que torna isso auditável

`PILOT-PROJECTION.md` (commit `76344dd`, **anterior** a qualquer chamada nova) declarou **K = 21**. Com dados reais o número fica em **~48–64**, dependendo do tratamento do ICC. Decomposição da diferença: `icc` foi de 0,0078 → 0,023–0,036 (o valor da peça 2 vinha de 5% de cobertura, onde quase não havia repeat para gerar variância between) e `λ0` caiu 4,50 → 3,19. Os dois fatores multiplicados explicam a diferença inteira.

**Consequência prática:** o estudo passa de ~42 dias para **~100–130 dias**. O MDE está travado em 20% e mexer nele agora *depois de ver K* é exatamente o "MDE shopping" que o §9 proíbe — o caminho previsto é rodar o K viável e publicar a curva de poder, que é o que `f` já devolve.

⚠️ **Item aberto:** o ICC divergiu entre modo censo (0,0351) e HT (0,0228) porque ponderar as densidades por sessão altera a variância. Estimar ICC sob pesos amostrais não é padrão — precisa decisão antes do `f`.

### `f` NÃO rodou

Tudo acima veio de reimplementação em rascunho, não de `sizing.py`. `f` roda **uma vez**, depois de 09/08, com 21 epochs.

### Artefatos

`/var/backups/nox-mem/paper2-corpus/verdicts/` na VPS, modo `0400`: `peca3-pass1.jsonl` (`dddb9823…`) · `peca3-novos.jsonl` (`8a4e7877…`) · `MANIFEST.txt` atualizado. **Não reproduzíveis** — o `codex-cli` já trocou de versão.

---

## 🟢 Estado anterior (2026-07-29 manhã) — calibração RODADA, τ travado, pré-registro em `[TO LOCK]` 31 → 11

> ✅ **Peça 3 fechada** — ver o bloco de 2026-07-29 noite acima.

### Calibração — fechada, painel completo 1.500/1.500

Seed do beacon `drand` quicknet round **30828212** → `f61f4c46…`, declarada em commit `65cddf9` com o round ainda **226 à frente** (precedência verificável por terceiro). **τ = S1 travado**: Fleiss' κ **0,874**; Krippendorff α ordinal **0,852**; ambos acima do piso de 0,75. Verdicts: `b6eebe18…`.

**O gatilho do §3 está VIVO — verificado, não presumido.** S4 apareceu **zero vezes em 1.289 verdicts** do corpus real, o que é indistinguível de gatilho desarmado. Controle positivo (`positive-control.jsonl`, 4 catástrofes sintéticas + 2 benignos pareados) deu **S4 em 4/4, zero falso positivo**. Eu ia "consertar" baixando o gatilho para S2 — que cobre 18,7% da operação normal — e teria transformado alarme calibrado em decoração.

### Quatro achados que mudaram cláusulas

1. **Baseline do abort de "90 dias" era insatisfazível** (archive começa 18/07, `brief_id` completo só desde 26/07) → virou *"histórico completo, mínimo 14 dias"*. **Portão: piloto não antes de 09/08.**
2. **Duração de sessão é bimodal** — mediana **22 s**, p95 9,6 min, **p99 33,5 h**, máx 158 h. Washout de 2h cobre 96,8%; os 3,2% restantes atravessam epochs inteiros e nenhum washout resolve → viraram estrato próprio.
3. **Version pin de CLI é ilusório** — `codex-cli` foi 0.144.5→0.145.0 sozinho em 24 h. Os 3 painelistas de API são reprodutíveis por id; os 2 de CLI **só pela saída registrada**.
4. **Frota virou allowlist congelada, não headcount** — eram 6, viraram 7, um suspenso. `fleet-wide` exige simultaneidade, não cardinalidade.

### Corpus congelado

`CORPUS-FREEZE.md`: snapshot `ba5fcc81…` (3.860 arquivos / 409 MB → 107 MB), manifesto de 3.860 hashes **no repo**, `sig()` pinado em `c0abe143`. Taxonomia deriva com o corpus (72→74 primary em 3 dias), por isso número só vale contra snapshot nomeado.

### Piloto — 4 peças, 2 feitas

| peça | estado |
|---|---|
| 1. definições de `r̂`/`p̂0`/`ICC` | ✅ operacionais, commit `07aebf5` |
| 2. harness de replay | ✅ `pilot_replay.py`, commit `cea9120` |
| 3. escopo da adjudicação | ⏳ **próxima — decisão de custo** |
| 4. avaliar `f` | ⏸️ **09/08** (`f` roda UMA vez; 11 epochs hoje, 21 em 09/08) |

⚠️ **O piloto é replay-only e NÃO depende do arXiv.** O que dependia era o experimento com braços vivos.

### Onde estão os artefatos

Verdicts e corpus **fora do repo público**, em `/var/backups/nox-mem/paper2-corpus/` na VPS (modo `0400`, `MANIFEST.txt` com SHA-256). O scratchpad da sessão é efêmero — não confiar nele.

---

## 🟢 Estado anterior (2026-07-26) — Paper 2: engenharia ACABOU, painel PRONTO, **esperando ordem de rodar**

> ⏸️ **Próxima ação é do Toto:** mandar rodar o calibration set de 300 e declarar a seed de amostragem.
> Comando pronto: `extract_episodes.py --sample 300 --seed <declarada>` (na VPS) → `run_panel.py` (no Mac, onde vivem as credenciais). 1.500 chamadas, **~14M tokens**.
> A seed **não** precisa vir do beacon — o beacon governa atribuição de braço, não amostragem de calibração. Mas tem que ser declarada **antes**, nunca escolhida depois de ver resultado.

### P2S1 — FECHADA (T0–T10)
Mecanismo de snapshot por epoch em produção. **T6 fechou 6/6 critérios do §6** em 8 boundaries; suíte **338/0** na VPS. `NOX_EPOCH_SNAPSHOT=shadow` **ligado** (serve do vivo, só mede) acumulando dose-vs-idade. Rotação de boundary agendada 06:00 BRT. Detalhe em `specs/2026-07-25-P2S1-serving-side-snapshot.md`.

⚠️ **O modo `shadow` não existia** — `resolveCorpus` tratava `shadow` e `active` igual, então a flag "segura" trocaria o corpus servido. Corrigido em nox-workspace#39.

### O bloqueador que apareceu e morreu no mesmo dia
Ao derivar a taxonomia do `sig()`, descobri que **o OpenClaw não persiste tool call nenhum** (79 `.jsonl`, 5.226 eventos, zero). Sem ações executadas, H1 não é mensurável e o piloto não roda.

**Resolvido:** o stream sempre existiu em **`/root/.claude/projects/`** — o OpenClaw sobe `claude-cli` como subprocess e é o **CLI** que persiste. Procedência provada pelos nomes de diretório (cwd de cada agente).

**4.560 episódios · 434 `is_error` (9,5%) · 71 assinaturas · 27 com ≥2 falhas.**

⏳ **E um cron apagava isso** (`-mtime +7` **e** qualquer arquivo pequeno com >12h). **Arquivamento vivo desde 26/07 19:08 UTC**: `nox-archive-transcripts.sh`, cron `40 3,9,15,21`, `rsync` **sem `--delete`**.

### §9 do pré-registro — o que fechou hoje
| Item | Estado |
|---|---|
| 0 (stream de ações) | ✅ resolvido + arquivado |
| 3 (snapshot) | ✅ medido e travado |
| 4 (`W_OUTCOME`) | ✅ **medido — 0,15 não é nudge** |
| 5 (taxonomia `sig()`) | ✅ derivada: **14 coarse / 72 primary / 162 fine**; falta só o hash do commit congelado |
| 6, 8 | estrutura travada + **2 defeitos corrigidos**; corte numérico espera calibration set |
| 7a (função `f`) | ✅ **travada** — `sizing.py`, SHA-256 do vetor sintético |
| 9, 10 (apêndices) | ✅ escritos |

**Item 4 medido:** o top-10 da salience cabe em **0,043** e o gap rank 8→9 é **0,0010**. Com `W=0,15`, **303 chunks** entram no alcance de um brief de 10 slots e **todos os 10 titulares ficam deslocáveis** — 3,5× o spread inteiro. Não é nudge, é autoridade para reescrever o brief. Recomendado parametrizar relativo ao spread.

**Dois defeitos corrigidos, nenhum precisava de dado:** o gate `|r| > 0,2` disparava por acaso em **25,9% no K=34** que o sizing devolve (virou TOST); e coverage é variável **pós-randomização**, então arm-blind não licenciava condicionar nela (entrou ITT sem exclusão como co-estimativa).

**Severidade virou rubrica ordinal S0–S4** — o float livre deixava o abort do §3 pedindo mediana exatamente 1,0, praticamente indisparável. Era defeito de segurança, não de métrica.

### Painel de adjudicação — ligado e testado, não rodado
Zhipu `glm-5.2` · xAI `grok-4.5` · Google `gemini-2.5-pro` (API) · Moonshot `k3` · OpenAI `gpt-5.6-sol` (CLI). Smoke 3×5 = 15/15.

**Anthropic fora por desenho:** os agentes rodam em `claude-cli`; seria família julgando a própria saída.

Artefatos: `paper2-interventional/{sizing.py, extract_episodes.py, run_panel.py, adjudication_prompt.md}`. Prompt SHA-256 `5b22f02c…` (rascunho aprovado, ainda não travado).

⚠️ **Orçamento corrigido:** eu havia estimado ~1,7M tokens supondo painel todo por API. Com dois painelistas por CLI (agent loop por chamada) é **~14M**.

### Ainda gated
Piloto do Paper 2 continua preso ao arXiv (`submit/7771319`, não recontatar antes de ~08/08). **O calibration set não está gated nisso** e cabe inteiro na janela.

### Operação (27/07) — os dois jobs novos rodaram sozinhos, e o archive já provou o seu valor

**`nox-archive-transcripts` — 4 execuções naturais, e a terceira é a prova:**

| Hora (BRT) | origem | arquivo | já-resgatados |
|---|---|---|---|
| 21:40 (26/07) | 3.103 | 3.103 | 0 |
| 03:40 | 3.149 | 3.149 | 0 |
| **09:40** | **2.916** | **3.227** | **311** |
| 15:40 | 3.016 | 3.327 | 311 |

O `prune-claude-sessions.sh` roda 04:23 BRT — entre a passada das 03:40 e a das 09:40. Depois dela, **311 arquivos passaram a existir só no arquivo**: são episódios de ação que o prune apagou da origem e que estariam perdidos sem o `rsync` sem `--delete`. O corpus do Paper 2 está em 352 MB / 3.327 arquivos e cresce ~100/dia.

**`nox-epoch-boundary` — primeira rotação natural, 06:00 BRT:** epoch `e20260727T090002Z`, SHA-256 `c11a3a37…`, 67.629 chunks, `mode: shadow`, `degraded: false`. Podou 1 snapshot antigo.

⚠️ **`manifestos: 10` NÃO é vazamento — é desenho, e um deles é evidência que não pode ser limpa.** `pruneEpochs(keep=3)` apaga o `.db` e **preserva o `.manifest.json` de propósito** (SHA-256 + contagens + `user_version` auditam um epoch antigo sem guardar 1,5 GB). Os 8 manifestos `t6-*` são **a evidência das 8 boundaries do teste T6** — eu ia limpá-los como resíduo e teria apagado a prova de um marco fechado. O `t6-b08.db` (1,6 GB) ocupa hoje um dos 3 slots e sai sozinho na boundary de 28/07; **não limpar à mão**.

### Primeira leitura da curva dose-vs-idade do shadow (27/07, ~1,5 dia de dados)

**2.358 medições** em `shadow_runs` (`feature = p2s1-epoch-snapshot`; as métricas vivem no JSON de `metadata` — a tabela é genérica de A/B, colunas fixas `baseline_value`/`shadow_value` ficam nulas).

| idade do snapshot | n | briefs idênticos | jaccard médio | jaccard mín |
|---|---|---|---|---|
| < 1 h | 462 | 97,8% | 0,9934 | 0,667 |
| 1–6 h | 720 | 92,4% | 0,9766 | 0,538 |
| 6–12 h | 873 | 90,1% | 0,9701 | 0,538 |
| 12–24 h | 291 | **71,8%** | 0,9146 | 0,538 |
| > 24 h | 0 | — | — | — |

**Monotônica — o instrumento funciona.** 233 divergentes em 2.358 (9,9%). Quando diverge, o jaccard fica em 0,91–0,99: difere por **~1 item de 8–10**, não em bloco.

⚠️ **Três limites do que isto ainda NÃO diz:** (1) idade máxima observada é **17,9 h**, então a linha `> 24 h` está vazia e a cauda do epoch não foi amostrada; (2) é ~1,5 dia de dados, um único ciclo semanal; (3) divergir do vivo **não é defeito** — é o preço declarado de congelar o corpus, e o que importa para o §5 é ser determinístico e auditável, o que é.

🔍 **A verificar (não é conclusão):** T7/T8 mediram **0,144% de divergência de corpus**; aqui o brief diverge ~10%. Se o elo for causal, é a amplificação esperada de um `top-k` — mudança mínima de salience reordena a fronteira. Foram medições em dias e condições diferentes; **precisa ser medido no mesmo epoch antes de virar afirmação**.

**Alerta de crontab (resolvido).** Os dois jobs acima levaram a contagem legítima de 39 para **41**, e o `health-probe.sh` (CHECK 10, faixa 25–40, roda 10/10 min) alertou **28× em 4 h**. Teto subiu para 45 — folga finita, **piso intocado** (é ele que pega o crontab zerado do incident do `crontab -l | sed | crontab -`). Motivo e data escritos no próprio arquivo; commit `3a723a8` em `nox-scripts`. Confirmado pelo cron real às 20:50: `OK: Crontab (41 lines)`.

> Lição registrada: ao mexer em recurso vigiado, procurar a sonda **na mesma mudança**. Alarme que dispara sempre vira decoração — foi assim que o decaimento do KG drenou por dois meses.

---

## 🟢 Estado atual (2026-06-30)

**Paper `v1.0.0` frozen + repo PÚBLICO e polido. arXiv submetido até o gate de endorsement.** (Detalhe técnico do paper preservado nos bullets abaixo.)

- **§5 — 12 dimensões SOTA** (EverMemBench 5-batch, MuSiQue, HotPotQA, LoCoMo, LongMemEval cross-bench, produção). Sustenta o paper sozinha.
- **§6 — Q4 head-to-head FEITO + controlled-embedding (rc4) FEITO.** §6.3 (canonical n=100, 06-15): split honesto as-configured — nox ganha LME (0.5234 vs 0.4764), Mem0 ganha LoCoMo (0.4686 vs 0.4263). **§6.3.2 nova (rc4, 06-29, ambos Gemini 3072d, full n=2.482): o split inverte — nox supera o mem0 em AMBOS** (LME 0.5255 vs 0.4061; LoCoMo 0.4952 vs 0.4407; overall 0.5013 vs 0.4337) **e as 5 categorias** (§6.4 preenchido = rc2 done). 3 confounds residuais declarados (mem0 0.1.x→2.0.10; backend faiss→Chroma; sample scope). **Task-type ablacionado (06-30):** nox com embedding genérico (sem task-type, igual ao mem0) cai só −0.34 pp (0.4979) e ainda ganha em tudo → confound (d) neutralizado, vitória é arquitetural. Zep/Letta/EverMind = 3 gaps documentados.
- **D2 (brief diversity) FECHADO** — coverage-sampling `active`, gate 24h 100% (190 chunks / 184-de-184 files), §3.5 cravado.
- **HyDE testado e REJEITADO** (−2.72pp overall, 06-27) — não entra como feature; `eval/*/RESULTS-HYDE.md` cravados.
- **prod v3.8** — 94.9k chunks, ~99.99% vector coverage, salience `active`.
- **Eval harness** — schema-bootstrap fix (nox-ws PR #24) + pacote de observabilidade nos adapters (varredura GLM+Kimi + recheck, `b2ae144`).

**Paper `v1.0.0`** (header bumped, changelog `paper/CHANGELOG.md`, `paper/build/*.pdf` 389KB / 0 glyph warnings). **Repo PÚBLICO** `github.com/totobusnello/memoria-nox`: scrub de infra (IPs/Tailscale) + reorg `staged-*/`→`staged/`, About+topics (honest framing), README (H1 de-jargonizado + demo.gif real), **release `v1.0.0`** com PDF anexado, **social preview** live (card honesto nox vs Mem0, og:image custom 2560×1280, byte-idêntico), **gitleaks full-history 0 leaks** (config `staged[-/]`). **arXiv `submit/7771319`** configurada (cs.IR primary + cs.LG/cs.AI cross, CC BY 4.0, Submittal Agreement aceito) — **bloqueada SÓ no endorsement gate**, aguardando 1 endorser. Submission id + código + contatos dos endorsers + passos do submit em **`paper/arxiv-metadata.txt` (local, não-commitado)**. Endorsers BR contatados: Nogueira (UNICAMP/Maritaca), Eduardo (`eduseiti@dca.fee.unicamp.br`), Rodrygo Santos (`rodrygo@dcc.ufmg.br`).

---

## 🎯 Próximos passos — RETOMAR AQUI (atualizado 2026-07-25)

**SUBMETIDO, EM `on hold` — INQUIRY JÁ ENVIADO. NÃO REPETIR.** `submit/7771319` na moderação desde 2026-07-01 (endorsement Rodrigo Nogueira OK, TeX/xelatex SUCCESS). **Gate atual: o arXiv anunciar o ID `2507.XXXXX`.**

**Status VERIFICADO em 2026-07-25** (leitura direta de `arxiv.org/user` logado): status literal **`on hold`**, coluna Expires vazia, nenhuma mensagem de moderação pendente. Delete/Unsubmit **travados pelo próprio arXiv** ("currently being considered by our moderators") ⇒ moderação humana ativa, **não é rejeição**. 24 dias corridos / ~18 úteis vs baseline de 1–2 úteis. Doutrina oficial do `on hold`: *"no action is required on your part"*, *"On Hold submissions will not expire"*, *"do not make a duplicate submission"*.

1. ~~Checar status + email pra moderação~~ **✅ FEITO em 2026-07-25.** Inquiry enviado de `lab@generantis.com.br` → `moderation@arxiv.org`; voltou auto-reply da fila ERRADA (endorsement — ver 🪤 "Armadilha de roteamento" no runbook); correção enviada no MESMO thread pedindo repasse à moderação. **⛔ NÃO mandar novo contato antes de ~2026-08-08** — duplicata piora e é desaconselhada pelo próprio arXiv. Se precisar depois dessa data, ir pelo botão **"View request"** do auto-reply (abre o ticket no portal Jira **sem exigir conta Atlassian**), não por email novo. Detalhes + textos prontos: `paper/publication/v1.0.1-post-submit-patch-plan.md` §"Follow-up de moderação — ARMADO".
2. **Quando o ID sair → replacement v1.0.1 (branch PRONTA):** `patch/v1.0.1-arxiv-replacement` tem o residual da review pós-submit aplicado (2 frases: S1 §6.3.2 + S3 abstract 667×) + PDF/.tex rebuilds verificados. **Runbook passo-a-passo: `paper/publication/v1.0.1-post-submit-patch-plan.md` §"Runbook do replacement"** (merge → rebuild se preciso → Replace no arXiv → vira v2).
3. **Pós-arXiv ID (independente do replacement):** `CITATION.cff` (trocar "submission pending" pelo ID real) + badge arXiv no `README.md`.
4. **GTM:** disparar emails/LinkedIn de lançamento; drafts de post de lançamento pendentes (#5).

**Review pós-submit (07-01/07-06):** 2 blockers + 4 should-fix — status por item verificado 07-12 em `paper/publication/v1.0.1-post-submit-patch-plan.md` (maioria já aplicada pré-submit; título mantido por decisão do Toto, risco aceito; residual = a branch acima).

**Decisão de framing (Toto, 06-29):** §6.3 (as-configured) + §6.3.2 (controlled) coexistem; ablação task-type (06-30) blinda o §6.3.2. **Sweep de claims v1.0.0 já feito** (abstract↔§5/§6 coerentes, confounds citados onde o resultado aparece).

**Paralela (não-paper):** GTM Phase 2 — gate D43 satisfeito; comercial migra pra `nox-supermem`. Não bloqueia o paper.

---

## 📣 Discurso / Destaques (talking-points prontos)

**Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

**3 pilares (Q/A/P):**
- **Quality** — números #1 (ver tabela SOTA abaixo).
- **Autonomy** — data sua, provider sua escolha, **zero vendor lock-in**: um único arquivo **SQLite, MIT**; embeddings provider-agnostic (Gemini default, swappable); full provenance (`chunk_id` + `source_file` em todo resultado); toda op destrutiva embrulhada em `withOpAudit()` com VACUUM INTO pre-snapshot.
- **Product** — UX que ganha: **live writeback sub-segundo** (inotifywait, sem batch retrain / daily reindex); typed temporal decay (retention por `chunk_type`, never-decay pra feedback/person); self-evolution `crystallize`/`reflect`/`consolidate`.

**Onde a memória é SOTA / destaque (paper §5–§6, números verificados):**

| Eixo | Número | vs |
|---|---|---|
| EverMemBench 5-batch (Gemini-3-flash) | **63.28% Overall + 88.42% MA** | +20.73pp / +32.74pp vs MemOS |
| EverMemBench (Gemini-2.5-flash) | 62.22% | +2.95pp vs MemOS |
| EverMemBench (GPT-4.1-mini) | 51.68% · CI [49.88, 53.49] | +9.13pp vs MemOS |
| Entity golden set | nDCG@10 **0.6237** | +78.8% vs baseline pré-Wave-A |
| MuSiQue dev F1 | **58.62%** | +22.82pp IRCoT, +8.92pp EX(SA) |
| HotPotQA dev distractor ans_F1 | **73.37%** | acima de DPR+FiD reader SOTA |
| LoCoMo retrieval@10 strict | **74.52%** | acima do Mem0 SOTA F1 66.88% |
| Q4 head-to-head LongMemEval | nox **0.5234** | vs Mem0 0.4764 (**nox vence**) |
| Produção — KG path | p50 **2.5 ms** · **$0/query** | ~667× cheaper que Mem0 Cloud |
| Produção — footprint | **399 MB RSS** single-process | self-hosted |

Dual SOTA em multi-hop QA clássico **sem fine-tuning**. LongMemEval cross-bench (n=300) confirma o mesmo fingerprint por categoria numa distribuição ortogonal. O **split** do §6 é trincheira: competitivo com o líder de mercado em qualidade de retrieval *enquanto* entrega o perfil operacional (single SQLite, $0/query, sem service stack) — o discurso de Autonomy que nenhum concorrente cloud sustenta.

---

## 🗓️ Histórico recente (verbatim, 06-30 → 06-24)

## Tue 2026-06-30 — paper v1.0.0 frozen, repo público polido, arXiv submetido até o endorsement gate

> Do paper-pronto ao repo-público-pronto-pra-tráfego, numa sessão.
>
> **Paper:** bump `v1.0.0` (PRs #447–448) + cite Quati (§F7); abstract/conclusão reescritos carregando as DUAS leituras sem mascarar a vitória do Mem0 em LoCoMo as-configured (#446); ablação task-type integrada §6.3.2 (#444).
> **Repo público:** scrub infra + reorg `staged-*/`→`staged/` (PR #449); README/CITATION→v1.0.0 (#445); **release `v1.0.0`** + PDF (`gh release`); About+topics honest framing; README H1 de-jargonizado + demo.gif real (`491ba58`); social card 1280×640 honesto (Chrome headless) + banner de-jargonizado (light+dark) + gitleaks `staged[-/]` full-history **0 leaks** (`01a1fbc`). Social preview confirmado live (og:image custom 2560×1280, byte-idêntico ao gerado).
> **arXiv:** `submit/7771319` configurada (cs.IR + cs.LG/cs.AI, CC BY 4.0, agreement aceito); `paper/arxiv-metadata.txt` (local) = title + abstract 1805c ASCII (≤1920; o longo de 2240 estourava) + comments + cats + submit id + código de endorsement + endorsers + passos do submit. Endorsement code corrente vive **no arquivo local** (supersedeu o anterior). Endorsers BR contatados: Nogueira (UNICAMP/Maritaca), Eduardo, Rodrygo Santos.
> **gitleaks recheck (lição):** scan default achou 6 — TODOS false positives (fixtures do redator P7: chave `…EXAMPLEKEY…`, JWT demo do jwt.io, label "AWS/GCP/Anthropic/"). A config tinha `staged/P7…` mas o full-history vê o path antigo `staged-P7…` (pré-rename) → fix `staged[-/]` casa ambos, validado 0. Codex pegou o teto de 1920c do abstract; Kimi achou o demo placeholder 404 + sugeriu About/topics.
>
> **Próxima ação:** endorser aprova o endorsement → retoma submit (upload PDF + cola metadata + submit final do Toto). Código/link/passos em `paper/arxiv-metadata.txt` (local).

## Sun 2026-06-28 — sessão: HyDE fechado + PR #24 + varredura GLM/Kimi + HANDOFF sanitizado + plano de evolução do paper

> Sessão longa. **Entregue (memoria-nox + nox-workspace):**
> - HyDE verdict **REJECT** documentado nos 3 RESULTS-HYDE + HANDOFF + README (`85d28a7`); `[VERDICT pending]` do PR #415 fechado.
> - **PR #24** schema-bootstrap (V8–V18 idempotente + PRAGMA user_version + teste) mergeado em nox-workspace (`aba5990e`).
> - Doc-fix do eval harness (repo `EverOS`→`EverMemBench`, `evermembench.harness`→`eval.cli`, OpenRouter→OpenAI+Gemini) (`3b2bde4`).
> - Pacote de **observabilidade** nos adapters pós-varredura GLM+Kimi + recheck (`b2ae144`) — 6 fixes aditivos/opt-in; K1 descartado (design intencional, recheck salvou um patch que quebraria o gold-match).
> - HANDOFF **sanitizado** 5376→267 linhas; histórico ≤06-14 arquivado (`8a53b2c`).
> - Pod RunPod parado (Toto).
>
> **Decisão (versionamento + evolução do paper):** paper versionado internamente em `paper/CHANGELOG.md` (`v1.0.0-rc1` atual). **Evoluir até o melhor estado antes de publicar** — rodar rc2 (§6.4 per-category) + rc3 (Claude backbone, $0 Max OAuth) + rc4 (all-Gemini), depois sweep + submit (v1.0.0 = arXiv v1). Plano em Próximos passos.

## Sat 2026-06-27 — HyDE bench rodado e **REJEITADO** (PR #415 `[VERDICT pending]` fechado) + bug de schema-bootstrap do nox-mem corrigido (nox-ws PR #24)

> O `[VERDICT pending]` do PR #415 (HyDE cross-bench, deferred por "infra pesada demais / GPU não rodou") foi resolvido: rodamos num RunPod **CPU** pod — HyDE é **API-bound**, não CPU-bound, então GPU era a dimensão errada. Verdict: **não-ship**.

### HyDE — measured REJECT (EverMemBench-Dynamic `groupchat_004`, single-batch n=626)
| Tipo | Baseline | HyDE | Δ |
|---|---:|---:|---:|
| multiple_choice (n=389) | 25.19% | 27.51% | +2.31 pp |
| open_ended (n=237) | 29.96% | 18.99% | **−10.97 pp** |
| **Overall (n=626)** | **27.00%** | **24.28%** | **−2.72 pp** |

- O hypothetical passage ajuda fatos discretos (MC) mas **inventa nomes/datas que desviam a geração aberta** (OE). Líquido negativo.
- **Caveat (recheck):** single-batch overstate 3-6× → efeito real provavelmente ~neutro. Neutro = sem lift = não justifica o custo (2× search + LLM passage). Gate-2 (Overall ≥ −1pp) **FALHA** de qualquer forma.
- Dataset só quebra por formato (MC/OE), não por hop → gate-1 (F_MH) não medido diretamente, mas sem sinal de lift a perseguir.
- LoCoMo/MuSiQue **não rodados** — bench-alvo negativo torna improvável valerem o custo (docs marcados `⛔ NOT RUN`).
- Docs: `eval/{evermembench,locomo,musique}/RESULTS-HYDE.md` atualizados com o verdict.
- **HyDE não entra no paper como feature** (continua sem ele). Esforço valeu: de "não-testável/pesado demais" → negativo medido.

### Bônus: bug de schema-bootstrap do nox-mem corrigido (nox-workspace PR #24, CLEAN/MERGEABLE)
> O eval-from-scratch num pod limpo expôs `ensureSchema()` parando em V7 enquanto rotulava o DB como v18 → primeiro INSERT tocando coluna v8+ (`retention_days`, `pain`, …) quebrava ("table chunks has no column named retention_days"). GLM + Kimi confirmaram; Kimi achou o bug secundário (`PRAGMA user_version` nunca setado).

- Fix idempotente `migrateToV8Through18` (9 colunas + índices + backfill `retention_days` por `chunk_type`) + alinhamento `PRAGMA user_version` + `repairChunkSchemaIfIncomplete` (auto-conserta DBs já rotulados v18 sem as colunas) + teste de regressão `schema-bootstrap.test.ts`.
- Validado end-to-end no pod (DB novo: 0 colunas faltando, `user_version=18`, INSERT v8-col OK).

---

## Sat 2026-06-27 — gate definitivo LIMPO colhido (190 chunks / 184-de-184 files = 100% coverage) → §3.5 cravado, paper rebuildado, **D2 FECHADO**

> O número definitivo do §3.5 saiu. Gate active de 24h 100% pós-deploy do coverage-sampling, censo + 2 caminhos independentes convergindo. §3.5 reescrito com a narrativa verdadeira (3 colapsos), paper `.pdf`/`.docx` rebuildados, one-shot cron removido. Ciclo D2 encerrado.

### Número definitivo (censo, 2 caminhos convergem)
| Caminho | distinct |
|---|---|
| `d2-gate-active-report.sh "-1 day"` (100% pós-deploy) | **190** chunks |
| SQL cru, cutoff explícito `2026-06-26 18:19:58` | **190** chunks |

- **184 de 184 entity files servidos = 100% de cobertura** do pool curado (universo 184 files / 752 chunks).
- ~**45 distinct chunks/hora** sustentado; FLOOR **13** high-pain ≥0.9 honrados.
- Curva acumulada: **190 já em deploy+4h, flat até +24h** → varre o pool em ~4h e re-cicla por recência = rotação contínua real.

### Comparação cravada no §3.5 (3 colapsos)
| Mecanismo | rotação |
|---|---|
| Hard-exclusion | burst 190 → **1**/dia |
| Soft-penalty (pMax 0.15 < gap salience) | 146 → 67 → **3** |
| **Coverage por recência-de-serve** | **184/184 (100%), 190 chunks, ~45/h sustentado** |

### Feito
- Paper §3.5 reescrito (trecho "rotates continuously through the [same soft] penalty" era factualmente falso) + `.pdf`/`.docx` rebuildados.
- Memória [[project_d2_brief_diversity_shadow_deployed]] atualizada (Update 2026-06-27).
- One-shot cron `d2-gate-clean-oneshot-27jun` removido (TZ local -03 ≠ UTC; não dispararia às 18:25 UTC, irrelevante pós-coleta manual).
- Serviço nox-mem-api: active, coverage no `dist`, vectorCoverage ok. **D2 fechado.**

---

## Fri 2026-06-26 — gate definitivo REFUTOU a rotação contínua (146→67→3) → fix coverage-sampling (PR nox-ws #23) deployado active, rotação confirmada viva

> O gate de 24h que esperávamos cravar no §3.5 mostrou o oposto do previsto: o fix do PR #22 **não se sustentou**. Diagnóstico corrigido por Kimi adversarial + recheck, fix redesenhado (desenho B), deployado. Número definitivo do §3.5 ainda pendente — sai do gate 100% pós-deploy.

### O gate (cron `/var/log/nox-d2-gate-active.log*`) — rotação colapsou de novo
| Run 06:10 | janela | distinct entity | regime |
|---|---|---|---|
| 22/06 (flip) | 21→22 | 190 | rajada |
| 23/06 (bug pré-#22) | 22→23 | 1 | exclusão-dura |
| 24/06 (1º dia pós-#22) | 23→24 | **146** | fix rotacionando |
| 25/06 | 24→25 | **67** | decaindo |
| 26/06 | 25→26 | **3** | **travado** (~36h em 3) |

O "152" esperado como número definitivo era acúmulo de uma janela já em queda. Não houve rotação contínua estável.

### Causa-raiz (medida + rechecada + Kimi via `ask`, CLI fora do PATH)
- O `noveltyPenalty = min(pMax=0.15, λ·log1p(n_serves_72h))` aplicava-se ao **pick inteiro**. `pMax=0.15` < **gap de salience-base** entre os 3 outliers (decisões imp 0.9 + access alto) e o corpo do pool. Pós-deploy a janela de 72h limpa deu rotação (146); ao encher, o penalty **saturou** e o pick **reconvergiu** ao top-salience (146→67→3, meia-vida ≈ 72h).
- Kimi me forçou a checar o rank: os 3 outliers estão em **rank 526/566/734, FORA do LIMIT-400** — entram pelo primary, não pelo fresh. O que secou foi o **fresh-global** (77→0 entities distintos/dia); o slot por-agente nunca colapsou (pool salience-homogêneo). Confound extra: 752 entities com `created_at` idêntico → LIMIT-400 por rowid congelava 352 fora.

### Fix (desenho B, Toto escolheu) — PR nox-workspace **#23**, `tune(brief)`
- **Fresh slot por COVERAGE** (`coverageCompare`): ordena por tempo-desde-último-serve (`MAX(served_at)`, nunca-servido primeiro, tie por salience). Sem teto que sature → varre o pool inteiro; o `LIMIT last_served ASC` também mata o confound rowid-frozen-400.
- **Primary volta a salience pura** (mechanism A aposentado): relevância no brief base, diversidade no fresh.
- Floor high-pain via pinned-set (invariante #4). `noveltyPenalty` mantido como knob residual.
- TDD **26/26** (`brief-diversity.test`), **RED provado** (3 testes falham contra o brief.ts da main), regressão `brief.test` 27/27.

### Deploy active + rotação CONFIRMADA viva
Checkout dos 3 arquivos do branch no working copy + `npx tsc` + restart. Serviço active, env active, vectorCoverage 70232/70261 orphans=0. **Prova viva:** 15 chamadas `/api/brief?scope=global&agent=nox` → slot global rotaciona a cada brief; `brief_log` registrou **16 entities distintos em 3 min** (vs 3/dia travado). Amostra = decisions+lessons+projects variados do entity store.

### ⚠️ Próxima ação — RETOMAR AQUI
1. **Colher o gate 24h 100% pós-deploy** (deploy ~18:20 UTC 26/06): **28/06 06:10 BRT** (`/var/log/nox-d2-gate-active.log`) OU manual `d2-gate-active-report.sh "-24 hours"` em **27/06 ≥18:30 UTC**. Esperado distinct entity **centenas** (sustentado, não em rajada). (O cron de 27/06 06:10 mistura ~9h pré-deploy — não usar como definitivo.)
2. **Cravar o número** no §3.5 + `[[project_d2_brief_diversity_shadow_deployed]]`. O §3.5 atual ("replace hard exclusion with the same soft novelty penalty... rotates continuously through the pool") está **factualmente errado** — reescrever com os DOIS colapsos (exclusão-dura→rajada; penalty saturável→reconvergência) e o coverage como remédio final.
3. Mergear PR #23 (Forge revisa). Rebuild paper `.pdf`/`.docx` (pandoc/xelatex), pré-arXiv.
4. Lição de paper: *hard-dedup sob volume≫pool = rajada; soft-penalty com teto < gap de salience = reconvergência; coverage por recência-de-serve = rotação contínua real* — só um loop shadow→active→measure expõe.

### Estado
- Serviço nox-mem-api: active, env `NOX_BRIEF_DIVERSITY=active`, código coverage no dist (verificado: `coverageCompare`+`last_served` presentes).
- PR #23 aberto (não mergeado). Working copy tem os 3 arquivos do branch via checkout (pós-merge: `git checkout -- <files>` + pull + rebuild).
- ⚠️ Kimi CLI fora do PATH (Node 25→26) — rodar `/kimi:setup` se precisar do adversarial via CLI.
- Memória: [[project_d2_brief_diversity_shadow_deployed]].

---

## Thu 2026-06-25 — PR #415 (HyDE cross-bench) reconciliado com a main e mergeado — conflito de 3 famílias resolvido

> A branch `feat/hyde-cross-bench` estava com conflito vs `main`: a branch adicionava **HyDE**, enquanto a main tinha ganho **IterB (#414)** + **few_shot (#412)** nos mesmos trechos dos dois adapters de eval. Merge da main na branch, conflitos resolvidos mantendo as 3 famílias, PR #415 **mergeado (squash)** → main `b13a1f8`. (Não altera a próxima ação operacional viva — o gate D2 da entrada de 24/06 segue pendente.)

### Conflitos (7) — `eval/evermembench/adapter_nox_mem.py` (4) + `eval/locomo/adapter_nox_mem.py` (3)
- Maioria "manter os dois lados" — features modulares inserindo em âncoras adjacentes: flags no `__init__`, chaves de `metadata`/`get_system_info`, params de `run_conversation`/argparse/call.
- **Guard baseline (decisão de código):** `if not mq_used_subquery_path and not iterc_used_path and not iterb_used_path and not hyde_used_path:` — considera **todos** os flags.
- **Guard do HyDE (coerência, não só junção):** passou a excluir também `iterb_used_path`. HyDE foi desenvolvido em paralelo ao IterB e não o conhecia; sem isso, HyDE sobrescreveria os candidatos do IterB quando ambos ativos. Alinha com o padrão que a main já aplicou a MQ/KG/reranker/IterC.
- **`version` unificada (decisão de código):** `"phase-hyde+iterB-0.1"` — representa o estado combinado, segue a convenção `phase-…-0.1`; substitui `phase-hyde-wave1-0.1` e `phase-iterB-q3-poc-0.1`.

### Testes (sem regressão)
- `py_compile` OK nos 2 adapters · `test_phaseIterB_smoke.py` **14/14** · `test_adapter_phaseKG_unit.py` **5/5** · `test_query_classifier.py` OK (com `PYTHONPATH` da raiz — a falha inicial era de invoke, preexistente, não do merge).
- Adapter instancia em `phaseHyDE`/`phaseIterB`, ambas as famílias de flags coexistem, `get_system_info().version == "phase-hyde+iterB-0.1"`; locomo importa com os 9 params `hyde_*` + `few_shot`.
- CI do PR: **14/14 checks verdes** (Python Syntax, TS typecheck, gitleaks, Trivy, etc.).

### Estado
- `origin/main` em `b13a1f8` (PR #415 squash). Branch `feat/hyde-cross-bench` removida (local + remota).

---

## Wed 2026-06-24 — merges #22+#436 confirmados, working copy reconciliado, rotação 1→93 (preliminar 9h) — gate 24h fecha amanhã

> Sessão de fechamento. PRs do fix + docs mergeados pelo Forge; working copy da VPS reconciliado; rotação medida ao vivo confirma o fix. Número **definitivo** do paper §3.5 sai do gate de 24h amanhã.

### Merges + reconciliação
- **PR #22** (nox-workspace, fix novelty-penalty) **MERGED** 11:07Z · **PR #436** (memoria-nox, docs 23/06 + paper §3.5 + 4 docs IP) **MERGED** 11:07Z.
- Main local memoria-nox reconciliado (doc 23/06 + §3.5 + **0 IP cru** em docs/).
- Working copy VPS reconciliado: `git checkout -- <2 files>` + `git pull` → Fast-forward HEAD `a262cbaa`, fix-files mod=0 (limpo). Serviço roda o fix via main.

### Gate active — número PRELIMINAR (9h pós-deploy), definitivo amanhã
| | antes do fix (23/06) | depois (24/06, 9h pós-deploy) |
|---|---|---|
| distinct entity (rotação) | **1** | **93** |
| briefs na janela | — | 2600 |
| FLOOR (high-pain servidos) | — | 2 (não-zero ✓) |
| por agente | 1 cada | nox 63, cipher 52, lex 51, boris 48, atlas 29, forge 25 |

Rotação **1 → 93** em 9h (run do cron 24h, que mistura o período pré-fix travado, já mostra 56/agente). Achado do paper confirmado com número forte; **não registrado nos docs ainda — esperando o gate de 24h completo** (decisão Toto).

### Rotação confirmada ao vivo (independente do gate)
8 chamadas `/api/brief?scope=global&agent=nox`: **24 distinct ids** (8 estáveis = brief principal incl. `227328`; **16 rotativos** = slot fresh girando 8 curados globais + slot do agente). vs 1 em 24h antes.

### ⚠️ Próxima ação — RETOMAR AQUI (amanhã 25/06)
1. **Colher o gate active de 24h LIMPO: 25/06 06:10 BRT** (`/var/log/nox-d2-gate-active.log`, ou manual `d2-gate-active-report.sh "-24 hours"`) — primeira janela 100% pós-fix. Esperado distinct entity **>150** (9h já deu 93). Esse é o **número definitivo do paper §3.5**.
2. **Registrar o número final** no HANDOFF + paper §3.5 (substituir o "esperado dezenas/centenas" do parágrafo *Active-mode validation*). E no `[[project_d2_brief_diversity_shadow_deployed]]`.
3. Rebuild paper `.pdf`/`.docx` (pandoc/xelatex) — pendente, pré-arXiv.

### ⚠️ Nota operacional — SSH público (porta 22) bloqueado
A porta 22 da VPS deu timeout no fim da sessão (**ping OK, IP inalterado** `$NOX_VPS_HOST`, serviço saudável via API). Provável **fail2ban** pelas dezenas de conexões SSH da sessão; costuma auto-liberar em ~10-30min. **Contorno que funcionou: Tailscale SSH** (`root@<NOX_TAILSCALE_HOST>`) bypassa a porta 22 pública. A API HTTP via Tailscale (`https://<NOX_TAILSCALE_HOST>` + Bearer em `~/.config/nox-mem/token`) também respondeu normal. Se o SSH público persistir bloqueado amanhã, usar o hostname Tailscale.

### Estado
- Serviço nox-mem-api: active, env `NOX_BRIEF_DIVERSITY=active`, vectorCoverage 70251/70251 **orphans=0** (órfão de 22/06 segue limpo).
- Memória: [[project_d2_brief_diversity_shadow_deployed]].

---


---

## 🗓️ Sessões 06-15 → 06-23 (condensado)

- **2026-06-23** — gate active revelou exaustão do pool de fresh → fix novelty-penalty no fresh slot (PR #22); rotação confirmada ao vivo.
- **2026-06-22** — morning report 1 RED resolvido (órfão de vetor); CodeQL silenciado (PR #435).
- **2026-06-21** — D2 gate split-slot (PR #20) colhido → flip `active`; gate de 24h em `active` agendado.
- **2026-06-20** — D2 gate PR #19 colhido → split-slot global (curado) impl + deploy shadow + PR #20 merged.
- **2026-06-18** — D2 gate medido + freshness slot corrigido (salience-order) + deploy shadow.
- **2026-06-15** — **§6 CANONICAL RUN feita** (pod dedicado, n=100, split nox/Mem0); paper §6 expandido; custo/latência re-validados.

> Detalhe completo dessas e de tudo ≤06-14: `handoffs/_archive/HANDOFF-2026-04-28-a-2026-06-14.md`.

---

## ⚡ Quick-ref (atemporal)

### Sanity check (1-cmd, rodar na VPS)
```bash
# Confirmar host/IP atual antes (Tailscale; IP já mudou — ver memória reference_vps_ip_change)
curl -s http://127.0.0.1:18802/api/health | jq '{total:.chunks.total, embedded:.vectorCoverage.embedded, salience:.salience.mode, section:.sectionDistribution, db:.dbSizeMB}'
```

### Contexto pra retomar (ordem de leitura)
1. **`docs/HANDOFF.md`** (este) — estado vivo + próxima ação
2. `docs/ROADMAP.md` — o que vem, capacity, gates
3. `CLAUDE.md` — regras críticas operacionais
4. `docs/DECISIONS.md` — NÃO FAZEMOS + porquês
5. `paper/paper-tecnico-nox-mem.md` — §5 (12 SOTA) + §6 (Q4 head-to-head)
6. `MEMORY.md` (em `~/.claude/.../memory/`) — feedback/preferências (auto-load)

### Comandos úteis
```bash
# Sanity completo
curl -s http://127.0.0.1:18802/api/health | jq .
# CLI nox-mem — SEMPRE source env antes (senão vectorize/kg falham MUDO)
set -a; source /root/.openclaw/.env; set +a; nox-mem --help
# Schema invariants
tail -5 /var/log/nox-schema-invariants.log
```

### Convenções obrigatórias (top 5 — detalhes em `CLAUDE.md`)
1. **Secrets só via env** (`${VAR}`, gitleaks pre-commit).
2. **Antes de CLI nox-mem em SSH/cron:** `set -a; source /root/.openclaw/.env; set +a`.
3. **Validar features com DB state, não logs** (`/api/health` é a fonte).
4. **Gemini default = `gemini-2.5-flash-lite`** (flash full estoura quota).
5. **Op destrutiva em chunks só com `--dry-run`/snapshot** (`withOpAudit()`).

**PT-BR:** "você", nunca "tu/vc". Registro São Paulo.

---

**Próxima atualização:** quando o estado mudar (arXiv submetido, gate passar, incident).
