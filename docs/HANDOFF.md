# nox-mem HANDOFF — estado vivo

> Estado-vivo enxuto. Histórico ≤ 2026-06-14 em `handoffs/_archive/HANDOFF-2026-04-28-a-2026-06-14.md`.

---

## 🟢 Estado atual (2026-06-30)

**Paper arXiv-ready no núcleo.** Zero `[PENDING]` no paper inteiro. **rc4 + rc2 fechados + ablação task-type fechada.**

- **§5 — 12 dimensões SOTA** (EverMemBench 5-batch, MuSiQue, HotPotQA, LoCoMo, LongMemEval cross-bench, produção). Sustenta o paper sozinha.
- **§6 — Q4 head-to-head FEITO + controlled-embedding (rc4) FEITO.** §6.3 (canonical n=100, 06-15): split honesto as-configured — nox ganha LME (0.5234 vs 0.4764), Mem0 ganha LoCoMo (0.4686 vs 0.4263). **§6.3.2 nova (rc4, 06-29, ambos Gemini 3072d, full n=2.482): o split inverte — nox supera o mem0 em AMBOS** (LME 0.5255 vs 0.4061; LoCoMo 0.4952 vs 0.4407; overall 0.5013 vs 0.4337) **e as 5 categorias** (§6.4 preenchido = rc2 done). 3 confounds residuais declarados (mem0 0.1.x→2.0.10; backend faiss→Chroma; sample scope). **Task-type ablacionado (06-30):** nox com embedding genérico (sem task-type, igual ao mem0) cai só −0.34 pp (0.4979) e ainda ganha em tudo → confound (d) neutralizado, vitória é arquitetural. Zep/Letta/EverMind = 3 gaps documentados.
- **D2 (brief diversity) FECHADO** — coverage-sampling `active`, gate 24h 100% (190 chunks / 184-de-184 files), §3.5 cravado.
- **HyDE testado e REJEITADO** (−2.72pp overall, 06-27) — não entra como feature; `eval/*/RESULTS-HYDE.md` cravados.
- **prod v3.8** — 94.9k chunks, ~99.99% vector coverage, salience `active`.
- **Eval harness** — schema-bootstrap fix (nox-ws PR #24) + pacote de observabilidade nos adapters (varredura GLM+Kimi + recheck, `b2ae144`).

**Paper em `v1.0.0-rc4`** (changelog: `paper/CHANGELOG.md`). rc2 (per-category) + rc4 (all-Gemini) fechados 06-29 numa run; rc3 (Claude backbone) dropado (sem $0 possível — Max OAuth é policy violation). **Resta só `v1.0.0`: sweep final de claims + polish + submit arXiv.** Sem bloqueador.

---

## 🎯 Próximos passos — só falta v1.0.0 (sweep + submit)

rc2/rc3/rc4 resolvidos. **Resta o sweep final pra publicar:**

1. **Sweep de claims → v1.0.0 → arXiv.** Auditar abstract-claims vs conteúdo (agora que o §6.3.2 + §6.4 entraram), checar consistência de números entre §5/§6/abstract, rebuild `.pdf`/`.docx` via `scripts/build-paper.sh`, bump header `**Paper version:**` → v1.0.0, submit. **~½ dia.**
   - ⚠️ Revisar no sweep: o §6.3.2 introduz a tese "nox supera o mem0 sob embedding controlado" — garantir que abstract/intro/conclusão estejam coerentes com as DUAS leituras (split as-configured + controlled), sem over-claim. Os 3 confounds residuais (versão mem0, backend, sample scope) precisam aparecer onde o resultado for citado; o task-type já foi ablacionado e neutralizado (06-30).
   - Contagem do abstract refeita pós-ablação: **296 palavras** (`abstract.md` §2, limite 300). OK.

**Decisão de framing (Toto, 06-29):** somar o rc4 sem apagar o split honesto — §6.3 (as-configured) + §6.3.2 (controlled) coexistem. Mais robusto que substituir a tese. Ablação task-type (06-30) blinda o §6.3.2 contra a objeção "a vantagem é só do task-type bonus".

**Paralela (não-paper):** GTM Phase 2 — gate D43 já satisfeito; comercial, migra pra `nox-supermem`. Não bloqueia nem incrementa o paper.

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

## 🗓️ Histórico recente (verbatim, 06-28 → 06-24)

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
A porta 22 da VPS deu timeout no fim da sessão (**ping OK, IP inalterado** `$NOX_VPS_HOST`, serviço saudável via API). Provável **fail2ban** pelas dezenas de conexões SSH da sessão; costuma auto-liberar em ~10-30min. **Contorno que funcionou: Tailscale SSH** (`root@srv1465941.tail4caa5b.ts.net`) bypassa a porta 22 pública. A API HTTP via Tailscale (`https://srv1465941.tail4caa5b.ts.net` + Bearer em `~/.config/nox-mem/token`) também respondeu normal. Se o SSH público persistir bloqueado amanhã, usar o hostname Tailscale.

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
