# P2S1 — Serving-side snapshot (pré-requisito de engenharia do Paper 2)

> **Status:** 📐 SPEC — não implementada.
> **Origem:** `paper2-interventional/PREREG-DRAFT.md` §0 (Route 2-lite) item §9.3. É o **único bloqueador de engenharia** entre o desenho atual e o piloto.
> **Consequência de falhar:** a rota degrada para **Route 1** (fallback documentado) e o paper **perde o claim causal**. Por isso a spec traz *kill criteria* explícitos — descobrir a inviabilidade agora custa uma spec; descobrir depois do pré-registro trancado custa o paper.
> **Data:** 2026-07-25.

---

## 1. O que o experimento exige

Route 2-lite pede: **os briefs do epoch _k_ são servidos a partir do estado do store no início de _k_** (congelamento no lado do serving), enquanto **os writes continuam indo para o store vivo**, sem interrupção, por segurança de produção.

Objetivo causal: impedir que conteúdo escrito *durante* o epoch _k_ apareça nos briefs do próprio epoch _k_. Isso confina o carry-over à fronteira entre snapshots e torna o estimando (§2 do prereg) bem definido.

## 2. Três achados que moldam o desenho

Levantados do sistema real antes de especificar:

**A1 — O serving path já é read-only sobre `chunks`.**
`docs/ARCHITECTURE.md:333` e `docs/PRIMITIVES.md:288`: `/api/brief` é read-only sobre `chunks`; a única escrita é em `brief_log`. **Isso torna o congelamento viável sem tocar no caminho de escrita** — não há mutação a redirecionar.

**A2 — `VACUUM INTO` é seguro com o banco vivo e já é padrão da casa.**
`docs-site/.../backup-runbook.md:43` ("VACUUM INTO is safe while DB is live") e `withOpAudit()` já o usam para snapshots pré-op atômicos. Não é mecanismo novo: é reuso.

**A3 — ⚠️ O coverage-sampling do D2 é _stateful dentro do epoch_.**
`docs/HANDOFF.md:169`: o slot fresh ordena por `MAX(served_at)` do `brief_log` (nunca-servido primeiro). Ou seja, **o que foi servido às 08:00 muda o que é servido às 09:00**. Se congelássemos o `brief_log` junto com o corpus, a rotação de cobertura pararia dentro do epoch e o braço de tratamento passaria a medir *outra coisa* (um brief degenerado), não a política.

> **Decisão de arquitetura que decorre de A3:** o snapshot congela **o corpus** (`chunks`, `chunks_fts`, `vec_chunks`, `vec_chunk_map`), **não o estado de serving**. `brief_log` permanece no store vivo, lido e escrito normalmente. É exatamente o que o estimando pede — congelar *quais chunks estão disponíveis*, não a mecânica de rotação intra-epoch.

## 3. Opções de mecanismo

| # | Mecanismo | Espaço | Fidelidade | Risco |
|---|---|---|---|---|
| **M1** | **Snapshot físico** via `VACUUM INTO` no boundary; brief lê do arquivo do epoch | Alto (ver §4) | **Exata** — inclui updates e deletes | Janela de cópia no boundary |
| **M2** | **Snapshot lógico**: sem cópia; filtro `created_at <= epoch_start` no serving | Zero | **Aproximada** — não captura updates nem deletes posteriores | Vies silencioso se updates forem frequentes |
| **M3** | Híbrido: M2 como caminho normal + M1 semanal como verificação de fidelidade | Baixo | Aproximada, com erro medido | Complexidade |

**Recomendação: M1, com retenção deslizante (§4).** Motivo: M2 tem um modo de falha silencioso — um chunk editado durante o epoch continua visível na versão nova, e o congelamento vira ficção sem que nada acuse. Num pré-registro que reivindica identificação causal, uma aproximação não-medida no mecanismo central é passivo, não economia. M2 fica como fallback se e somente se o custo de M1 for proibitivo *e* o erro de aproximação for medido e declarado (task T7).

## 4. O risco escondido: espaço em disco

O ponto que quase derruba a rota, e que precisa ser medido **antes** de qualquer implementação.

Ordem de grandeza: ~94,9k chunks e ~70k vetores de 3072 dimensões. A 4 bytes por float, só os vetores somam ~860 MB, antes de `chunks`, FTS5 e KG. Um snapshot completo deve ficar na casa do **1–2 GB**.

Se o estudo tiver 40–60 epochs de 24h e todos os snapshots fossem retidos, seriam **60–120 GB** — inviável na VPS.

**Mitigação (e é o que torna M1 viável): não é preciso reter todos.** A análise só precisa de:

- o snapshot do epoch **corrente** (serving), e
- o do epoch **anterior** (co-estimativa A→B, §5 do prereg).

Retenção deslizante de **3 snapshots** (corrente, anterior, +1 de folga) mantém o custo **constante em ~3–6 GB**, não linear no número de epochs. Cada snapshot descartado deixa para trás seu **SHA-256 + manifesto** (contagens por tabela, `user_version`, chunk ids servidos) — o suficiente para auditoria posterior sem guardar o arquivo.

**⛔ Kill criterion K1:** se `df` na VPS não sustentar 3 snapshots simultâneos com ≥20% de folga, M1 morre. Rota: tentar M3; se também não couber, **degradar para Route 1** e ajustar o prereg.

## 5. Riscos adicionais

| Risco | Detecção | Mitigação |
|---|---|---|
| Janela de cópia no boundary (VACUUM INTO de ~2 GB não é instantâneo) | medir em T1 | Snapshot **antes** do boundary lógico; brief continua servindo o snapshot anterior até o novo estar íntegro (troca atômica por symlink) |
| ~~`vec0` / sqlite-vec não abrir no snapshot~~ | ✅ **fechado em T2 (25/07)** | Extensão carrega, JOIN casa 68.068 com 0 órfãos, KNN roda em ~200 ms e o top-10 é byte-idêntico ao live em 20/20 queries |
| Duas conexões (snapshot read-only + live para `brief_log`) | T3 | **Não usar `ATTACH`** — lição registrada em `[[feedback_vacuum_into_attach_reverse_pattern]]`: better-sqlite3 tem limitação de contexto. Abrir os dois bancos separadamente |
| Snapshot corrompido / incompleto serve brief vazio | T4 | Health check pós-cópia (contagens + `PRAGMA integrity_check`) antes da troca; falha ⇒ mantém o anterior e alerta |
| Deriva silenciosa: brief passa a servir do live sem ninguém notar | T5 | `/api/health` expõe `servingSnapshot{path, sha256, epochId, takenAt}`; ausência é RED |
| Consumo de I/O do VACUUM impacta produção | T1 | Rodar no vale de tráfego; medir latência de `/api/brief` durante a cópia |

## 6. Critérios de aceite

- [ ] Brief servido do snapshot é **byte-idêntico** ao brief que o mesmo código produziria contra o store vivo congelado no mesmo instante (validação em shadow, sem tráfego real).
- [ ] Escrita no store vivo **não é afetada** — nenhum write path muda; `ops_audit` sem entradas novas por causa disso.
- [ ] `brief_log` continua registrando serves e a rotação de cobertura do D2 **segue viva dentro do epoch** (contra-prova de A3: cobertura intra-epoch > 1 chunk distinto).
- [ ] Troca de snapshot no boundary é **atômica** — nenhuma requisição vê estado intermediário.
- [ ] Espaço em disco **constante** ao longo de ≥7 boundaries consecutivos (prova da retenção deslizante).
- [ ] `/api/health` reporta o snapshot em uso e seu hash.

## 7. Tasks

### Chunk A — Medição (bloqueia tudo; nada é implementado antes)

- [x] **T0** ✅ **MEDIDO 2026-07-25 na VPS de produção.** Resultados abaixo. **K1 PASSA com folga.**

#### T0 — números medidos

| Métrica | Valor | Leitura |
|---|---|---|
| Disco `/` | 387 G total · 109 G usados · **279 G livres** (28%) | — |
| `nox-mem.db` | **1,5 G** | estimativa da spec (1–2 G) confirmada |
| WAL / SHM | 4,9 M / 32 K | saudável (truncamento em dia) |
| **`VACUUM INTO`** | **9,77 s** · exit 0 | rápido; cabe folgado no boundary |
| Snapshot gerado | 1,5 G · `PRAGMA integrity_check` = **ok** | — |
| Fidelidade `chunks` | **68.070** no snapshot = 68.070 no live | idêntico |
| Fidelidade `vec_chunk_map` | **68.068** = `vectorCoverage.embedded` do live | idêntico |
| DB fonte pós-operação | intacto (mtime e tamanho inalterados) | confirma A2 |
| Inodes | 3% usados | sem pressão |

**K1 — VEREDICTO: PASSA.** 3 snapshots = ~4,5 G = **1,6% do espaço livre**, contra os ≥20% de folga exigidos. Margem larguíssima: mesmo retendo **todos** os ~60 epochs (~90 G) ainda caberia. A retenção deslizante permanece o desenho (previsibilidade e higiene), mas deixa de ser restrição de viabilidade. **A Route 2-lite está de pé; o degrade para Route 1 por espaço está descartado.**

**~~⚠️ `vec_chunks` — teste INCONCLUSIVO~~ → RESOLVIDO em T2, ver §T2 abaixo.** O `Error: in prepare, no such module: vec0` do `sqlite3` CLI era, como se suspeitava, limitação do CLI sem a extensão carregada — não perda de vetores. Confirmado com `better-sqlite3` + `sqliteVec.load()`.

**Nota de corpus:** o live reporta **68.070 chunks** (`/api/health`), não os 94,9k que o `CLAUDE.md` ainda cita (número de 2026-06-04, anterior ao dedup). Divergência de documentação a corrigir fora desta spec.

**Pendente de T0 (não bloqueante):** latência de `/api/brief` durante a cópia — medir junto com T6, em shadow, onde o efeito é observável sem instrumentar produção só para isso.

### Chunk B — Mecanismo

- [x] **T1** ✅ **EM PRODUÇÃO 2026-07-26** — `snapshotForEpoch()` em `src/lib/epoch-snapshot.ts` ([#34](https://github.com/totobusnello/nox-workspace/pull/34) + [#35](https://github.com/totobusnello/nox-workspace/pull/35)). Smoke na VPS: **1,60 GB em 17,8 s**, `integrity_check` ok, `user_version` 18, manifesto atestando as 6 tabelas do corpus (`chunks` 68.115 · `chunks_fts` 68.115 · `vec_chunks` 70.149 · `vec_chunk_map` 68.075 · `kg_entities` 15.621 · `kg_relations` 18.074).
  - **Primitiva `atomicSnapshotTo()` extraída** do `op-audit` para `lib/atomic-snapshot.ts`: o op-audit valida `NOX_DB_PATH` **no escopo de módulo**, então só importá-lo dispara o guard — a primitiva não podia carregar política que não é dela. Proteções (`.tmp` + integrity + re-stat TOCTOU + rename + `0600`) seguem em **uma** implementação.
  - **Invariante travada em teste:** escrita posterior ao boundary **não** aparece no snapshot do próprio epoch. Sem ela o congelamento é ficção e o claim causal cai junto. 6/6 passando.
  - ⚠️ **Armadilha reincidente:** o manifesto nascia com `vec_chunks: -1` porque abria o snapshot sem carregar `vec0` — mesma causa que deixou o teste do T0 inconclusivo. Só apareceu no smoke em produção, não nos testes.
- [x] **T2** ✅ **VALIDADO 2026-07-25 na VPS.** O caminho semântico abre e é fiel no snapshot. Resultados abaixo.

#### T2 — resultados medidos

Snapshot fresco por `VACUUM INTO` (**8,05 s**, 1,5 G — consistente com os 9,77 s do T0), aberto read-only com `better-sqlite3` + `sqliteVec.load()`.

| Verificação | Resultado |
|---|---|
| `vec0` carrega no snapshot | **OK** (`vec_chunks USING vec0(embedding FLOAT[3072])`) |
| Contagens snapshot vs live | `chunks` 68.077=68.077 · `vec_chunk_map` 68.068=68.068 · `vec_chunks` 70.142=70.142 |
| JOIN `vec_chunk_map→chunks` | 68.068 casados, **0 órfãos de mapa** |
| `PRAGMA integrity_check` | `ok` · `user_version` 18 (bate com o live) |
| KNN real (`MATCH` + `k`) | funciona; **192–206 ms** para k=10 sobre 70k vetores |

**O critério que decide: equivalência, não perfeição.** A pergunta certa não é "o KNN do snapshot é bom?" e sim "o snapshot se comporta como o live?". Em **20/20** queries independentes (seeds espalhados por `vec_rowid % 997 = 3`), o top-10 veio **byte-idêntico** — mesmos `rowid`, mesmas distâncias com 6 casas. **A cópia é fiel; o braço de tratamento mede o mesmo mecanismo do controle, só congelado.**

**Achado colateral — 29,2% do corpus é texto duplicado, mas isso NÃO chega ao brief.** Ao testar self-match, três seeds se encontraram em rank 3–5 com distância `0.000000` e um não se achou no top-10: estavam **empatados em zero com cópias idênticas de si mesmos**. Medido no corpus: **19.869 de 68.068 chunks vetorizados (29,2%) estão em 4.303 grupos de texto idêntico; o maior grupo tem 629 cópias.**

Isso não ameaça o T2 (o live se comporta igual — é por isso que a equivalência dá 20/20). Levantou-se a hipótese de que fosse confound do Paper 2: se o brief serve por similaridade, um top-k poderia ser preenchido por gêmeos do mesmo texto. **Medido em `brief_log` sobre 7 dias (7.141 briefs, 50.848 slots): hipótese REFUTADA — 0,00% dos slots servidos são texto duplicado de outro slot.** Nos 7 dias, 362 chunks distintos servidos correspondem a 361 textos distintos. A duplicação do corpus mora em regiões que o brief não alcança. **Nada a declarar no §9 por esta via.**

#### ⚠️ O que a medição encontrou de verdade: `brief_log` não identifica o brief

A investigação passou por um falso positivo instrutivo. Agrupando `brief_log` por `(scope, agent, served_at)`, 10,34% dos slots pareciam `chunk_id` repetido — o que sugeriria falha de dedup na montagem. **Não é bug.** Evidência que fecha:

- multiplicidade máxima é **exatamente 2×**, nunca 3;
- distribuição bimodal — 3.539 grupos de 10 slots com **zero** repetição, 574 grupos de 20 slots com repetição em **todos**;
- a ordem de inserção do pior grupo mostra duas sequências idênticas de 10, ids contíguos, **diferindo só no último item** (o slot fresh rotacionando).

São **dois briefs consecutivos servidos dentro do mesmo segundo**. `pickDedup` (`src/api/brief.ts:350`) é hermético — `seenIds` bloqueia repetição em todas as fases, inclusive a fresh — e o `INSERT` percorre `result.items`, já deduplicado.

**A falha real é de instrumento:** o schema é `brief_log(id, chunk_id, scope, agent, served_at)`, **sem `brief_id`**, e `served_at` tem resolução de 1 segundo. **Não há como separar dois briefs coincidentes no mesmo segundo** — e isso acontece em ~9% dos casos hoje.

Para o Paper 2 isso importa: o desfecho é medido **por brief servido**. Sem `brief_id`, qualquer análise por-brief funde silenciosamente briefs co-ocorrentes, exatamente como aconteceu comigo aqui. **Ação: adicionar `brief_id` (ou `served_at` com resolução de ms) antes do início do estudo — vira item novo do §9 e pré-requisito de T3.** É barato: coluna nova, sem ALTER destrutivo, mesmo padrão da criação do `brief_log`.

**Nota de método:** esta seção mudou de conclusão três vezes (duplicata de corpus → bug de dedup → artefato de agrupamento). O que a estabilizou foi olhar a ordem de inserção bruta em vez de confiar no agregado. Registrado porque o mesmo agrupamento ingênuo está disponível para quem for analisar o desfecho do estudo.

**Nota:** os 2.074 vetores sem entrada em `vec_chunk_map` (70.142 − 68.068) são os órfãos pré-existentes que o cron das 06:20 poda; o snapshot os reproduz fielmente, como esperado.
- [x] **T2b** ✅ **EM PRODUÇÃO 2026-07-25 19:53 UTC** — `brief_id TEXT` no `brief_log` ([nox-workspace#27](https://github.com/totobusnello/nox-workspace/pull/27)). Deploy verificado na VPS: snapshot pré-op (1,5 G, `integrity_check` ok) → `git pull --rebase --autostash` (27 arquivos sujos preservados) → `npm run build` **exit 0** → restart. Migração rodou sozinha no `ensureBriefLog`: coluna presente, primeiro brief real gravou **5 slots sob um único `brief_id`**; 349.762 linhas antigas ficaram `NULL`, como previsto. **T3 desbloqueado.**
  - ✅ **Build verde entregue** ([nox-workspace#28](https://github.com/totobusnello/nox-workspace/pull/28)): `npm run build` saiu de **exit 2 / 31 erros** para **exit 0 / 0 erros**. O vermelho escondia um bug de produção: `src/index.ts:279` chamava `previewMergeEntities()`, que não existia — ou seja, **`kg-merge --dry-run` lançava `TypeError`** e a proteção exigida pela regra #6 do CLAUDE.md não existia de fato. Implementada.
  - ✅ **A suíte VIROU gate (25/07):** **294 passam / 0 falham** na VPS (era 245/50). O que travava não era ambiente — era drift real de schema: tabelas e colunas que existiam em produção mas nenhum caminho do repo criava (`kg_*`, `eval_*`, `ocr_jobs`, 16 colunas de `search_telemetry`). O DDL de `eval_*`/`ocr_jobs` **não existia no repo** e foi reconstruído do `sqlite_master` de produção. **T3/T6 desbloqueados.** ~~Texto anterior:~~ 198 passam / 67 falham, conjunto idêntico antes e depois da mudança (verificado por stash). As 67 são **ambientais**: todas nos 7 arquivos de teste que hardcodam `/var/backups/`, que exige root — passariam na VPS, não verificado lá. **Para T6 valer como validação, a suíte precisa rodar onde o shadow roda.**
  - ⚠️ **Dívida aberta, precisa de decisão:** `validate.test.ts` foi excluído do build. Testa contrato que `answer.ts` não implementa (espera **422** com `details.{field,got,max}`; código lança **400** `invalid_body` sem details). Reescrever para 400 seria enfraquecer o teste para caber no código. **Enquanto durar, `validateBody` — que serve `/api/answer` em produção — está sem cobertura.**
- [x] **T3** ✅ **EM PRODUÇÃO 2026-07-26 (modo `off`)** — [#36](https://github.com/totobusnello/nox-workspace/pull/36). `handleBrief` aceita `{corpus, live}`; `resolveCorpus()` em `lib/epoch-serving.ts` escolhe o handle por `NOX_EPOCH_SNAPSHOT`.
  - **O nó era `fetchFreshCandidates`:** lia `chunks` mas ordenava por `last_served` (de `brief_log`, subquery correlacionada), e o `LIMIT 400` caía **depois** dessa ordenação. Quebrado em elegíveis-do-snapshot → `MAX(served_at)`-do-vivo → junção e corte em JS. **Em ASC o SQLite põe NULL primeiro** — é o que faz o nunca-servido liderar; inverter mataria a cobertura em silêncio.
  - **Escala medida antes de desenhar:** o `WHERE` devolve **170** linhas (agente) e **693** (global) contra pool de 400 — trazer tudo é barato.
  - **`off` é bit-idêntico por construção:** o caminho dividido só roda com handles diferentes; em `off` a query original executa intocada.
  - **Teste de equivalência (5/5):** corpus e live no mesmo banco ⇒ split devolve o que a query única devolvia. Sem isso, erro na replicação da ordenação quebraria o D2 sem alarme.
- [x] **T4** ✅ **EM PRODUÇÃO 2026-07-26** — [#37](https://github.com/totobusnello/nox-workspace/pull/37). `rename()` sobre symlink (atômico no mesmo FS): `symlink()` falha se o destino existe, então `unlink`+`symlink` abriria janela sem ponteiro. Só troca após reconferir `integrity_check` do manifesto. **`resolveCorpus` passa a preferir o ponteiro** — "mais recente por mtime" era corrida (durante a cópia o mtime já é o mais novo e o arquivo ainda não está íntegro).
- [x] **T5** ✅ **EM PRODUÇÃO 2026-07-26** — [#37](https://github.com/totobusnello/nox-workspace/pull/37). Mantém 3, poda preservando `.manifest.json`, e **nunca poda o alvo do `current`**. `/api/health.servingSnapshot` expõe `{mode, epochId, path, sha256, takenAt, degraded}` — `off` não é degradação; RED é `degraded: true`. Smoke em prod: ciclo snapshot→point→prune com 2 epochs, manifestos preservados.
  - `EPOCHS_DIR` virou `epochsDir()`: como `const` de módulo amarrava no import, exigia restart para mudar e deixava o caminho de degradação **intestável**. Descoberto por 2 testes falhando — mesma família da lição do singleton `getDb()`.

### Chunk C — Validação

- [ ] **T6** Shadow: rodar N boundaries sem tráfego real, verificar todos os critérios do §6.
- [ ] **T7** Medir o erro de M2 contra M1 (quantos chunks divergiriam por epoch se usássemos só o filtro lógico) — é o número que decide se M2 é fallback aceitável, e entra no prereg como declaração.
- [ ] **T8** Ensaio de falha: snapshot corrompido, disco cheio, `vec0` ausente. Confirmar que o sistema degrada para o snapshot anterior em vez de servir vazio.

### Chunk D — Fechamento

- [ ] **T9** Atualizar `PREREG-DRAFT.md` §9 item 3 com os parâmetros medidos (duração do boundary, retenção, hashes) e fechar o item.
- [ ] **T10** Se K1 falhar: escrever o degrade para Route 1 no prereg (remover fraseado causal do §1-H1) e registrar em `paper2-interventional/DECISIONS.md`.

## 8. Fora de escopo

Não muda: caminho de escrita, watcher/ingest, vectorize, KG, consolidação noturna, `withOpAudit()`. O snapshot é **aditivo ao serving**; se desligado por env, o sistema volta ao comportamento atual.

## 9. Flag

`NOX_EPOCH_SNAPSHOT=off|shadow|active`, mesmo padrão de `NOX_BRIEF_DIVERSITY`. Default `off`. Produção só vai para `active` depois de T6 verde.
