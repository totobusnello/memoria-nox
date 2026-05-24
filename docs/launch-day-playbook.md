# Launch Day Playbook — Wed 2026-06-03 (rev2, Sat closure update)

> **Operador solo:** Toto Busnello  
> **Fuso horário de referência:** BRT (UTC-3)  
> **Base:** PR #227 (baseline) + GTM audit PR #302 (GO-WITH-GAPS, 5 P0) + HN prep PR #323 rev3  
> **Systems ready:** F10 Phase A-D LIVE · 4/6 cross-system adapters validated · HN/Reddit/Twitter/LinkedIn/PH copy final  
> **Kill conditions:** ver §6

---

## Legenda rápida

| Símbolo | Significado |
|---|---|
| ✅ | Executar, marcar como feito |
| ⚡ | Ação crítica — não pular |
| 📊 | Verificar métrica / dashboard |
| 🚨 | Trigger de crise — ver §5 |
| `cmd` | Comando terminal a copiar-colar |

---

## PRÉ-LANÇAMENTO — Seg 2026-06-01

### 09h BRT — Preparação semana de lançamento

- [ ] ✅ Verificar arXiv endorsement em cs.IR: `https://arxiv.org/auth/show-endorsers`
  - Se precisar de endorser: solicitar imediatamente (processo 24-48h)
  - Kill condition: se endorsement não chegar até Ter 22h → lançar sem arXiv (ver §6)
- [ ] ✅ Compilar lista de 20 contatos prioritários para outreach Qua (ver §3)
  - Filtro: técnicos com interesse em AI/memory/agents + LLM infra
  - Template em `docs/outreach-templates.md §2-§4`

---

## PRÉ-LANÇAMENTO — Ter 2026-06-02

### 09h BRT — Verificação arXiv

- [ ] ⚡ arXiv account ativa + endorsement confirmado
- [ ] ✅ Compilar package: `paper/publication/latex/` → PDF limpo via `./xelatex-wrapper.sh`
  - Verificar zero erros LaTeX: `pdflatex --halt-on-error main.tex`
  - Table 8 TBD cells: preencher com dados de `audits/2026-05-21-G12-frontmatter-retrieval-audit.md`
- [ ] ✅ arXiv metadata pronto em `paper/publication/arxiv-submit-metadata.md`
  - Categoria: cs.IR (primary) + cs.AI (secondary)
  - Abstract: `paper/abstract.md` (≤300 palavras, sem redação pré-2026 deprecated)

### 14h BRT — Sanity check final do repo

- [ ] ⚡ `bash scripts/check-pre-launch.sh` → exit 0 obrigatório
  - Se secrets detectados: `git log --all -p -S GEMINI_API_KEY | grep '^+' | grep -v 'YOUR_\|your-key\|\.env'`
- [ ] ✅ Merge PR #297 (README hero com 0.6380 + tabela 2 linhas)
- [ ] ✅ `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1`
- [ ] ✅ VPS health: `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage`
  - Esperado: `embedded == total` (100% coverage)
- [ ] 📊 `/api/answer` smoke test: query simples, latência <3s
- [ ] ✅ Cron healthcheck ativo: `systemctl status nox-mem-healthcheck` (15min interval, PR #164)
- [ ] ✅ F10 dashboards abrindo: `http://127.0.0.1:18802/dashboard` via Tailscale

### 15h BRT — Finalizar COMPARISON.md (se agentmemory full run completo)

- [ ] ✅ Se `agentmemory` full ingest (~52min) concluído: preencher `[PENDENTE]` cells em `benchmark/COMPARISON.md`
- [ ] ✅ Atualizar blog post `docs/launch-blog-v0-draft.md` com números canônicos (30min)
- [ ] ✅ Publicar blog post no site pessoal / dev.to e anotar URL

### 16h BRT — arXiv submission

- [ ] ⚡ Submeter em `https://arxiv.org/submit/`
  - Upload PDF + metadata de `paper/publication/arxiv-submit-metadata.md`
  - Confirmar upload sem erros; anotar submission number
- [ ] ✅ E-mail de confirmação arXiv recebido + ID anotado (formato `https://arxiv.org/abs/26XX.XXXXX`)
- [ ] ✅ Testar PDF em aba anônima: `https://arxiv.org/pdf/26XX.XXXXX`

### 18h BRT — Product Hunt draft

- [ ] ⚡ PH draft criado (se não existir): `https://www.producthunt.com/posts/new`
  - Título: `nox-mem — Pain-weighted hybrid memory for LLM agents`
  - Tagline: `Your SQLite file. Your provider. Benchmarks you can reproduce.`
  - Gallery: mínimo 3 assets (CLI demo GIF + F10 dashboard GIF + architecture diagram)
  - Primeiro comment do maker: 2-3 parágrafos com contexto + convite para feedback
- [ ] ⚡ Agendar PH: **Wed 2026-06-03 00:01 PST = Wed 2026-06-03 05:01 BRT**
- [ ] ✅ Confirmar que Toto está listado como maker no produto

### 18h30 BRT — Assets finais

- [ ] ✅ Demo GIF CLI gravado e commitado em `docs/assets/demo-cli.gif`
  - `cd docs/launch-assets/scripts && bash preflight-check.sh && bash demo-record.sh`
  - `bash cast-to-gif.sh && cp output.gif ../assets/demo-cli.gif`
- [ ] ✅ Demo GIF F10 dashboard gravado: screen-record Tailscale tunnel → compress → commit

### 20h BRT — GitHub Release

- [ ] ✅ Inserir arXiv link em:
  - `docs/releases/v1.0.0-rc1.md` (substituir `[PENDENTE]`)
  - `README.md` badge arXiv (commit direto se não travado por PR)
  - Social copy `docs/launch-social-copy.md` T8/HN body
- [ ] ⚡ `gh release create v1.0.0-rc1 --title "nox-mem v1.0.0-rc1" --notes-file docs/releases/v1.0.0-rc1.md`

### 22h BRT — arXiv approval check

- [ ] 📊 Verificar se arXiv aprovou submission: e-mail de moderação ou `https://arxiv.org/abs/26XX.XXXXX`
  - BRT 22h = ET 19h = cross-over de moderação típico
  - Se ainda em hold: ok — postar sem badge e adicionar depois

### 23h BRT — Go/No-go final (5 minutos)

Responder cada linha. Se alguma for NÃO: ver §6.

| Check | OK? |
|---|---|
| PH agendado 00:01 PST | |
| arXiv PDF acessível (ou hold aceito) | |
| VPS health green | |
| `check-pre-launch.sh` exit 0 | |
| Social copy em arquivo local (não só memória) | |
| Demo GIF commitado | |
| Nenhuma regressão >5% nDCG em eval noturno | |

---

## DIA DO LANÇAMENTO — Qua 2026-06-03

### 05:01 BRT — Product Hunt goes live (automático)

PH lança automaticamente pelo schedule. Nenhuma ação necessária neste momento.

---

### 06:00 BRT — Wake + sanity check (15 min)

- [ ] ⚡ Verificar PH live: `https://www.producthunt.com` → buscar `nox-mem`
  - Confirmar que produto está ativo, maker comment postado, gallery carregando
  - Se NÃO live: ver §5 → crise PH submission bloqueada
- [ ] ⚡ Verificar primeiros votos PH (meta: ≥5 em 1h)
- [ ] 📊 VPS health check rápido:
  ```
  curl http://127.0.0.1:18802/api/health | jq '{vectorCoverage, uptime}'
  ```
- [ ] 📊 `/api/answer` smoke test (30s):
  ```
  curl -X POST http://127.0.0.1:18802/api/answer \
    -H 'Content-Type: application/json' \
    -d '{"query":"what is nox-mem"}' | jq .answer
  ```
  - Esperado: resposta em <3s, texto coerente
  - Se timeout: ver §5 → VPS down durante lançamento
- [ ] ✅ F10 dashboard aberto em background para monitoramento passivo

**Kill: se VPS down e não sobe em 10min → acionar §5 fallback estático.**

---

### 07:00 BRT — Twitter/X thread (20 min)

> Janela ótima: 07:00-08:00 BRT = 06:00-07:00 ET (costa leste abrindo, antes do rush)

- [ ] ⚡ Postar T1 (hook) exatamente às 07:00 BRT
  - Texto em `docs/launch-social-copy.md §1 T1`
  - **Verificar: ≤280 chars antes de postar**
- [ ] ✅ Postar T2-T8 em sequência, ~1 tweet por minuto (07:01-07:08 BRT)
  - T2: problema · T3: solução · T4: arquitetura · T5: números · T6: G-series gauntlet · T7: Autonomy · T8: paper + links
- [ ] ✅ Verificar que thread está linkada (reply encadeado, não tweets soltos)
- [ ] 📊 Monitorar retweets/likes primeiros 15 min (meta: ≥5 engagements na primeira hora)

**Timing crítico: postar thread ANTES de submeter no HN. Thread serve como prova social para HN.**

---

### 07:15 BRT — Hacker News Show HN (5 min)

> Janela ótima HN: 06:00-09:00 ET = 09:00-12:00 BRT. 07:15 BRT = 06:15 ET — zona dourada.

- [ ] ⚡ Abrir `https://news.ycombinator.com/submit`
- [ ] ⚡ Título: `Show HN: nox-mem — Pain-weighted hybrid memory for LLM agents`
  - **REGRA HN: título descritivo, sem hipérboles. Sem "revolutionary", "best", "amazing".**
  - **Sem description field — HN Show HN não usa body no submit form.**
- [ ] ✅ URL: `https://github.com/totobusnello/memoria-nox`
- [ ] ✅ Submit — anotar URL do thread imediatamente
- [ ] ✅ Postar primeiro comment no próprio thread dentro de 2 minutos:
  ```
  Hi HN! I'm Toto, the author.

  nox-mem is a hybrid memory layer for LLM agents — FTS5 BM25 + 
  Gemini embeddings + RRF fusion + a knowledge graph, running on 
  SQLite locally. MIT licensed, no cloud required.

  The Q4 eval shows nDCG@10 0.6380 (+83% vs our baseline). The 
  cross-system comparison (mem0, agentmemory, zep) is in 
  benchmark/COMPARISON.md — including the honest disclosure of 
  what's still pending canonical runs.

  Happy to answer anything about the retrieval design, the ablation 
  series (G3-G12), or the pain-weighted salience formula.
  ```
- [ ] 📊 Monitorar posição HN a cada 30min (meta: top 30 Show HN por 12:00 BRT)

**Kill: se flagado/removido em 30min → ver §5 HN flagado.**

---

### 07:30 BRT — LinkedIn (10 min)

> LinkedIn peak: 07:00-09:00 ET = 10:00-12:00 BRT (postar agora para capturar feed da manhã europeia ainda)

- [ ] ✅ Postar long-form LinkedIn announcement
  - Texto base em `docs/launch-social-copy.md §4 LinkedIn`
  - Inserir arXiv link se disponível
  - Tag relevante: #LLM #OpenSource #AIAgents #MachineLearning
  - **LinkedIn penaliza links externos nos primeiros 30min. Workaround: postar texto sem link, editar e adicionar link após 5min.**

---

### 08:00 BRT — Reddit submissions (20 min)

> Reddit r/ML peak: 08:00-11:00 ET = 11:00-14:00 BRT. Postar agora para capturar abertura.

- [ ] ⚡ Reddit r/MachineLearning:
  - URL: `https://www.reddit.com/r/MachineLearning/submit`
  - Flair: **[Project]** ou **[Research]** (escolher Research se arXiv disponível)
  - Título: `[Project] nox-mem: Pain-weighted hybrid memory for LLM agents (FTS5 + semantic + KG + RRF, MIT)`
  - Body: incluir abstract arXiv + benchmark highlight + link repo
  - **Não linkar para PH — Reddit r/ML proíbe cross-promotion explícita**
- [ ] ✅ Reddit r/LocalLLaMA:
  - URL: `https://www.reddit.com/r/LocalLLaMA/submit`
  - Ênfase: Autonomy pillar — zero cloud dependency, Ollama adapter, seu SQLite
  - Título: `nox-mem: hybrid memory for local LLM agents — SQLite, MIT, your provider`
- [ ] ✅ Reddit r/SideProject (se regras permitirem):
  - Só se não violação de regras do sub (verificar sidebar antes de postar)
- [ ] ✅ Anotar URLs dos posts Reddit

**Kill: se auto-moderado silenciosamente (post some em perfil mas não aparece no sub) → ver §5 Reddit removido.**

---

### 09:00 BRT — Verificação de momentum (10 min)

- [ ] 📊 HN: posição atual + pontos + comentários ativos
- [ ] 📊 PH: posição + votos (meta 2h: ≥15 votos)
- [ ] 📊 Twitter: impressões thread (meta 2h: ≥500 impressões)
- [ ] 📊 Stars GitHub: delta vs pré-launch
- [ ] 📊 VPS: `curl http://127.0.0.1:18802/api/health | jq .requests_24h` — tráfego real

**Decision point às 09:00 BRT:**
- HN < 5 pontos em 90 min → postar comment substancial com highlight de benchmark no próprio thread
- PH < 10 votos em 3h → compartilhar link PH no tweet T9 adicional

---

### 09:30 BRT — Blog post publish + Discord/Slack

- [ ] ✅ Publicar blog post no site pessoal / dev.to (se não publicado Ter):
  - URL anotada para distribuição
- [ ] ✅ Tweet de blog post (tweet solto, não reply da thread): `[URL blog] — Deep dive on the Q4 ablation series + how the conditional hard mutex improved retrieval. [arXiv link]`
- [ ] ✅ Discord announcements (AI/ML engineering channels):
  - Canais sugeridos: Hugging Face Discord, Eleuther AI, LAION, LangChain Discord
  - Mensagem: 3-4 linhas + link repo (sem paste de thread inteira — spam)
  - **Não postar em mais de 3-4 canais Discord no mesmo dia — aparência de spam**
- [ ] ✅ Slack communities (se membro):
  - MLOps Community, ai/ml Slack workspaces conhecidos
  - Mesma regra: 3-4 lines + link, não flood

---

### 10:00 BRT — Email outreach wave 1 (30 min)

- [ ] ✅ Enviar e-mails personalizados para top 20 contatos da lista compilada Seg
  - Template: `docs/outreach-templates.md §2` (journalistas/newsletter) ou `§3` (pesquisadores/podcasters)
  - **Personalização mínima: 1 linha específica ao destinatário antes do boilerplate**
  - Assunto sugerido: `nox-mem: hybrid memory for LLM agents — MIT, SQLite, published benchmarks`
  - CC/BCC: nenhum (e-mails individuais, não blast)
- [ ] ✅ Trendshift submission: `https://trendshift.io/` (5 min — link repo + categoria)

---

### 11:00-13:00 BRT — Active response window 1

> HN thread crítico nestas horas. US west coast acordando, europeus ainda ativos.

**Protocolo de resposta HN:**
1. Abrir thread a cada 15-20 min
2. Responder por ordem: comentários com mais pontos primeiro
3. Tempo de resposta máximo: 10 min por reply (não postar replies sob pressão — 30s de releitura obrigatória)
4. Templates em `docs/launch-hn-comments-prep.md`:
   - Q1 ("Outro memory tool") → template Q1 com números COMPARISON.md
   - Q2 ("SQLite não escala") → template Q2 com latência + roadmap
   - Q3 ("Pain-weighted é gimmick") → template Q3 com G7 + shadow-mode
   - Q4 ("Benchmarks rigged") → template Q4 com protocolo + EverMemBench gap honesto
   - Q5 ("Bus factor 1") → template Q5 honesto
   - Q6 ("Gemini = vendor lock-in") → template Q6 com adapter pattern

**Protocolo de resposta Reddit:**
- Responder comentários técnicos; ignorar trolls
- Se post removido: ver §5

**Protocolo PH:**
- Responder perguntas no first comment + Q&A do produto

---

### 12:00 BRT — Checkpoint do meio-dia (10 min)

| Métrica | Meta mínima 6h | Real | Ação se abaixo |
|---|---|---|---|
| HN pontos | ≥20 | — | Adicionar comment técnico substancial no thread |
| HN posição | Top 50 Show HN | — | Cross-post para comunidades adicionais |
| PH votos | ≥30 | — | Tuitar link PH + ativação contacts |
| GitHub stars Δ | ≥25 | — | Verificar se README hero está carregando (GIF bloqueando?) |
| Twitter impressões | ≥2000 | — | Repost T1 + nova thread com ângulo diferente |

---

### 13:00-18:00 BRT — Active response window 2 (bloco de trabalho)

> US morning peak. Manter resposta ativa mas sem deixar de fazer trabalho paralelo.

- [ ] 📊 A cada hora: checar HN posição + pontos + PH ranking
- [ ] ✅ Responder DMs técnicos no Twitter
- [ ] ✅ Se feedback recorrente identificar gap: abrir GitHub Issue com label `feedback/launch`
- [ ] ✅ Se bug crítico reportado: ver §5 → bug crítico pós-lançamento
- [ ] ✅ Engajar com quem deu star no repo (agradecer no Twitter, se público)

**Regra de ouro HN durante este bloco:**
- Nunca editar o post original (HN exibe "[flagged]" se editado depois de pontos altos)
- Se dado errado citado → reply no thread com correção, não edição
- Nunca votar em si mesmo ou pedir votos diretamente

---

### 18:00 BRT — Checkpoint tarde (10 min)

| Métrica | Meta 12h | Real | Ação se abaixo |
|---|---|---|---|
| HN pontos totais | ≥50 | — | Nenhuma (ciclo já encerrou) |
| HN posição máxima atingida | Top 30 | — | — |
| PH votos | ≥75 | — | Wave 2 outreach (ver 19h) |
| GitHub stars Δ | ≥60 | — | Segunda thread Twitter ângulo técnico |
| Reddit upvotes r/ML | ≥25 | — | — |

---

### 19:00 BRT — Wave 2 outreach + retweet boost (30 min)

- [ ] ✅ Tweet de encerramento de dia com stats destacados:
  ```
  12h update on nox-mem launch:
  [N] GitHub stars | HN: [posição] | PH: [votos]
  
  Top feedback so far: [1-2 temas genuínos]
  Next step: [honest next action — EverMemBench, canonical comparison, etc.]
  
  → github.com/totobusnello/memoria-nox
  ```
- [ ] ✅ Retuitar tweets de terceiros que mencionaram `nox-mem`
- [ ] ✅ Wave 2 e-mail: 10 contatos adicionais da lista (tier 2 — menos prioritários)
- [ ] ✅ GitHub Discussions: abrir discussão "Launch day feedback" no repo
  - Seed posts em `docs/discussions-seed/` (welcome + roadmap + Q&A)

---

### 22:00 BRT — Encerramento do dia

- [ ] 📊 Revisão final de comentários HN/Reddit pendentes
- [ ] ✅ Responder qualquer thread HN que ficou sem resposta
- [ ] 📊 F10 dashboard: snapshot de `requests_24h`, `answer_latency_p95`, `vector_coverage`
- [ ] ✅ `curl http://127.0.0.1:18802/api/health | jq` → salvar output em `docs/launch-retrospective-2026-06-04.md`

---

### 24:00 BRT — Snapshot de métricas D1

Compilar na tabela de retrospectiva (`docs/launch-retrospective-2026-06-04.md`):

| Métrica | Alvo D1 | Real |
|---|---|---|
| GitHub stars Δ 24h | ≥100 (sucesso) / ≥50 (aceitável) | — |
| HN pontos | ≥50 | — |
| HN posição máxima | Top 30 Show HN | — |
| PH votos | ≥100 | — |
| PH posição | Top 5 do dia | — |
| Twitter impressões thread | ≥10k | — |
| Reddit upvotes r/ML | ≥50 | — |
| `/api/answer` requisições | qualquer número positivo | — |
| Issues abertas | — (qualitativo) | — |

**Threshold mínimo de momentum: 100 stars + Top 30 HN + 50 PH = lançamento bem-sucedido**
**Acima do threshold: avaliar GTM Phase 2 gate (1000 stars W1 = product-market signal)**

---

## §1 Canais de comunicação — onde postar + formato

### Hacker News
- **URL:** `https://news.ycombinator.com/submit`
- **Formato:** título descritivo + link repo (sem description field em Show HN)
- **Regras críticas:** sem hipérboles, sem cross-promotion, sem pedir votos
- **Melhor horário:** 07:15 BRT (= 06:15 ET — zona dourada Show HN)
- **Primeiro comment:** postar imediatamente após submit (ver template acima)

### Twitter/X
- **Formato:** thread 8 tweets encadeados (T1-T8 em `docs/launch-social-copy.md §1`)
- **Melhor horário:** 07:00 BRT (= 06:00 ET — costa leste abrindo)
- **Limite:** verificar ≤280 chars por tweet antes de postar
- **Não usar encurtadores de URL** — Twitter/X já encurta automaticamente

### LinkedIn
- **Formato:** long-form (3-5 parágrafos) com contexto técnico + links
- **Workaround do algoritmo:** postar texto, esperar 5min, editar para adicionar link
- **Tags:** #LLM #OpenSource #AIAgents #MachineLearning #SQLite

### Reddit r/LocalLLaMA
- **Flair:** nenhum obrigatório — usar título claro
- **Ênfase:** Autonomy pillar (local, sem cloud, Ollama adapter)
- **Proibido:** links pagos, self-promotion excessiva, cross-posting duplicado

### Reddit r/MachineLearning
- **Flair:** [Research] se arXiv disponível, [Project] caso contrário
- **Ênfase:** benchmarks reproduzíveis + paper arXiv + harness público
- **Incluir:** abstract técnico + números Q4 no body

### Reddit r/SideProject
- **Verificar regras do sub antes de postar** (alguns proíbem lançamentos de tool)
- **Tom:** founder sharing, não marketing

### Discord (AI/ML engineering)
- **Canais:** Hugging Face, Eleuther AI, LAION, LangChain (se membro)
- **Formato:** 3-4 linhas + link — nunca paste de thread inteira
- **Limite:** máximo 3-4 canais no mesmo dia

### Slack
- **Canais:** MLOps Community, ai/ml workspaces conhecidos
- **Mesma regra Discord:** curto + link, não flood

### Email outreach
- **Lista:** top 20 contatos prioritários (compilar Seg 06-01)
- **Template:** `docs/outreach-templates.md §2-§4`
- **Personalização:** 1 linha específica ao destinatário, obrigatória
- **Assunto:** `nox-mem: hybrid memory for LLM agents — MIT, SQLite, published benchmarks`
- **Envio:** individual, não blast — sem CC/BCC

### Trendshift
- **URL:** `https://trendshift.io/`
- **Formato:** form simples — link repo + categoria (5 min)
- **Timing:** qualquer hora do dia de lançamento

---

## §2 Tracking de métricas — alvos por janela

| Janela | Stars Δ | HN | PH votos | Twitter impressões | Reddit upvotes |
|---|---|---|---|---|---|
| 2h (08:00 BRT) | ≥5 | ≥5 pts | ≥15 | ≥500 | — |
| 6h (12:00 BRT) | ≥25 | ≥20 pts / Top 50 | ≥30 | ≥2000 | ≥10 |
| 12h (18:00 BRT) | ≥60 | ≥50 pts / Top 30 | ≥75 | ≥5000 | ≥25 |
| D1 (24h) | **≥100** | — | **≥100** | ≥10k | ≥50 |
| D3 (72h) | **≥500** | — | — | — | — |
| W1 (7 dias) | **≥1000** | — | — | — | — |

**Sinais de product-market fit:**
- 5+ inbound (GitHub Issues, e-mails, DMs) de pessoas não-conhecidas pedindo feature
- 1000+ stars W1 → ativar GTM Phase 2 (Hotmart/Stripe pricing discussions)
- 3+ Discussions threads abertos por terceiros (não seeds)

---

## §3 Outreach — lista de 20 contatos (compilar Seg 06-01)

Preencher antes do lançamento. Template:

| # | Nome | Canal | Contexto | Personalização |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| ... | | | | |

**Critérios de priorização:**
1. Escreveu sobre memory systems / RAG / LLM infra nos últimos 90 dias
2. Audiência técnica (não venture/hype)
3. Respondeu e-mail anterior ou interagiu no Twitter

**Templates por tier:**
- Jornalistas/newsletter: `docs/outreach-templates.md §2`
- Podcasters: `docs/outreach-templates.md §3`
- Pesquisadores/engineers: personalizar com referência específica ao trabalho deles

---

## §4 HN — templates de resposta rápida (top 6 comentários hostiis)

> Extraído de `docs/launch-hn-comments-prep.md`. Copiar-colar no dia.

**Q1: "Outro memory tool — diferença de Mem0/Zep/Letta?"**
> "Fair — the space is crowded. Three concrete differences: (1) open cross-system benchmarks you can reproduce locally (`benchmark/runner.py`) — Q4 eval: nox-mem hybrid nDCG@10 0.6380 vs mem0 0.1315 (at 7.3% corpus cap) vs agentmemory 0.1376 (at 20% cap); (2) MIT licensed, no hosted dependency — your DB file is yours; (3) triple-stack retrieval (BM25 + semantic + KG via RRF) vs vector-only. Full table + disclosure: `benchmark/COMPARISON.md`."

**Q2: "SQLite não escala — use Postgres"**
> "SQLite is a deliberate tradeoff, not naivety. Single-file deployment, zero ops, fully offline for BM25. Current prod instance: 68k chunks, p50 940ms on a 1 vCPU / 2GB VPS. Scale ceiling acknowledged: ~500k chunks documented comfortable limit; beyond that, Postgres migration is spec'd in ROADMAP.md. If you're running millions of chunks today, Postgres is the right call."

**Q3: "Pain-weighted é gimmick / overfitting"**
> "The skepticism is fair. Two honest answers: (1) G7 ablation showed the formula is NEUTRAL on our eval corpus — Δ +0.5% within noise. The value is structured signal for future reranking. (2) It runs shadow-mode by default so you can observe its effect before activating. G11 trim experiments showed over-boosting hurts — interpretable beats black-box."

**Q4: "Benchmarks rigged — sem EverMemBench"**
> "Honest gap acknowledged: we haven't run EverMemBench yet — it's Lab Q1 priority, explicitly in ROADMAP.md. The Q4 cross-system comparison used a shared FTS5-fair protocol against a fixed entity-eval-v2 corpus — the same 100 golden queries, the same DB, for all systems. Two systems (Zep, EverMind) aren't in the table because they couldn't be evaluated under protocol — that's documented. You can run the harness yourself: `benchmark/runner.py`. On LongMemEval n=100: nDCG@10 0.9126, MRR 0.9162."

**Q5: "Bus factor 1"**
> "Bus factor is real and I won't pretend otherwise. MIT license means anyone can fork. The architecture is documented (paper + ADRs in `docs/adr/`), eval harness is reproducible, and the schema is stable. The commercial track (nox-supermem) depends on this being alive — that's the economic incentive. But yes: today it's one author. That's the honest state."

**Q6: "Gemini = vendor lock-in (contraditório com Autonomy)"**
> "Valid catch. The distinction: the embedding provider is configurable via `.env` — no code changes needed (`src/embeddings/`). Adapters exist for OpenAI; Ollama adapter lets you go fully local. Gemini is the default because it has the best quality/cost ratio at 3072d in 2026, not because we're locked to it. The DB format, retrieval logic, and KG are all provider-agnostic."

---

## §5 Playbook de crise

### "API key Gemini exposta no repo"
1. **Imediato (0-5 min):** `curl https://aistudio.google.com/` → revogar key imediatamente
2. **Diagnóstico (5-15 min):** `git log --all -p -S GEMINI_API_KEY | grep '^+' | grep -v 'YOUR_\|your-key\|\.env'` → confirmar qual commit
3. **Limpeza (15-60 min):** BFG Repo Cleaner: `java -jar bfg.jar --replace-text passwords.txt repo.git && git reflog expire --expire=now --all && git gc --prune=now`
4. **Comunicação pública:** Postar no HN thread: "Update: rotated an API key found in git history — no production impact, database not affected. Details in SECURITY.md." Não deletar o post.
5. **Post-mortem:** commit `SECURITY.md` com disclosure completo dentro de 24h

### "VPS down durante lançamento"
1. **Cron alerta em 15 min** (PR #164 healthcheck) — confirmar via ping externo: `ping 187.77.234.79`
2. **Tentativa de recovery (10 min):** SSH → `systemctl restart nox-mem-api` → testar `/api/health`
3. **Fallback (>10 min de downtime):** Atualizar README temporariamente com nota: "Demo API momentaneamente offline — GIF + screenshots estáticos disponíveis abaixo"
4. **HN thread update:** Postar reply no próprio post: "The demo API is briefly offline — working on it. The repo and CLI work fully locally; see QUICKSTART.md. Will update when back."
5. **Não deletar o post HN** — downtime temporário é aceitável e honesto; deletar é fatal

### "HN post flagado/removido"
1. Aguardar 30 min — HN às vezes auto-unflag posts legítimos
2. Se não unflagged: e-mail `hn@ycombinator.com` com subject "Show HN post flagged in error" — contexto técnico + link
3. **Não repostar o mesmo link no mesmo dia** — viola regras HN e piora situação
4. Fallback: Reddit r/ML como canal primário + Twitter amplification
5. Se conta nova (<90 dias) triggering shadow-ban: considerar repost via conta mais antiga

### "HN sem tração (< 10 pontos em 2h)"
1. Postar comment substancial no próprio thread com benchmark highlight específico (não genérico)
2. Compartilhar link HN em Discord/Slack channels técnicos (sem pedir voto explicitamente — apenas "I posted about X, curious what people think")
3. **Nunca votar em si mesmo** — HN detecta IPs adjacentes e penaliza
4. Aceitar o resultado — HN é imprevisível. Redirecionar energia para Reddit/Discord resposta

### "PH submission bloqueada"
1. Verificar: Toto listado como maker? Produto duplicado no PH (busca por "nox-mem")?
2. Suporte PH: `https://www.producthunt.com/contact` — resposta típica em 2-4h
3. Fallback: lançar sem PH — HN + Twitter + Reddit suficientes para tração técnica
4. **Não comprar votos** — PH detecta e penaliza permanentemente (shadow-ban da conta)

### "PH < 10 votos em 3h"
1. Tweet adicional (T9) incluindo link PH explicitamente
2. Compartilhar no Discord/Slack (com contexto, não só link)
3. Contatar 5 conexões próximas diretamente (DM/WhatsApp) — honesto, não compra
4. **Não fazer vote exchange** — detectável e prejudicial long-term

### "Reddit post removido silenciosamente"
1. Checar se post aparece no histórico do perfil mas não no sub → auto-mod shadow-remove
2. DM moderadores do sub com contexto: FOSS project, acadêmico, sem afiliação paga
3. Alternativa: r/programming + r/learnprogramming (menor, mas sem auto-mod agressivo)
4. **Não repostar sem contato com mods** — duplicatas são banidas

### "Números Q4 contestados publicamente"
1. Linkar para arXiv: metodologia seção §3, protocolo de eval seção §4
2. Disponibilizar harness: `benchmark/runner.py` — "run it yourself"
3. Citar os honest disclosures já no COMPARISON.md (competitor cells pendentes documentados)
4. **Nunca editar o post original para mudar números** — HN/Reddit vê a edição
5. Se erro real identificado: reply transparente + commit fix + link para commit

### "Bug crítico descoberto pós-lançamento"
1. Abrir PR com fix imediatamente (prioridade máxima)
2. Postar update no HN thread: "Update: [bug description] identified, fix in progress, PR #XXX. No data loss for existing users."
3. Release patch v3.7.1 assim que fix merge
4. **Nunca deletar o post original** — transparência é a reputação

### "Regressão de performance detectada no eval noturno"
- Regressão <2%: lançar com caveat honesto no HN first comment
- Regressão 2-5%: investigar causa antes de lançar; se não explicável em 2h, adiar
- Regressão >5%: condição de cancelamento — ver §6

---

## §6 Condições de cancelamento (stop-the-launch)

Cancelar e adiar para **Qui 2026-06-04** se QUALQUER condição abaixo for verdadeira:

| Condição | Threshold | Protocolo de adiamento |
|---|---|---|
| arXiv submission falhando no lançamento | Ainda failing às 16h Ter | Adiar ou lançar sem badge (anotar no HN comment que submission está em revisão) |
| Regressão Q4 nDCG@10 vs 0.6380 | >5% abaixo | Investigar. Não lançar com número errado no post. |
| Finding de segurança crítico (CVSS ≥ 7.0) | Descoberto em audit final | Corrigir antes de qualquer coisa. Não há timeline que justifique lançar com CVE conhecido. |
| VPS instável na semana pré-launch | 3+ outages em 7 dias antes de Qua | Resolver infra primeiro. Demo offline no dia de lançamento é fatal. |
| arXiv endorsement não chegou | 22h Ter sem endorsement | Lançar sem badge arXiv — postar note no HN comment que submission está pendente de aprovação |

### Protocolo de adiamento (se necessário):
1. Cancelar PH schedule (sem penalidade — PH permite cancelar draft)
2. Não deletar nenhum rascunho ou assets preparados
3. Reagendar para **Qui 06-04** (mínimo) ou **Qua 06-10** (se adiamento maior)
4. Postar note no Twitter (1 tweet): "Delaying nox-mem launch by 24-48h — [reason, honest]. Back [day]."

---

## §7 Referências rápidas (para o dia)

| Recurso | Link / Comando |
|---|---|
| arXiv submission | `https://arxiv.org/submit/` |
| HN Show HN submit | `https://news.ycombinator.com/submit` |
| Product Hunt dashboard | `https://www.producthunt.com/dashboard` |
| Reddit r/ML | `https://www.reddit.com/r/MachineLearning/submit` |
| Reddit r/LocalLLaMA | `https://www.reddit.com/r/LocalLLaMA/submit` |
| Trendshift | `https://trendshift.io/` |
| GitHub Release | `gh release create v1.0.0-rc1 --notes-file docs/releases/v1.0.0-rc1.md` |
| VPS health | `curl http://127.0.0.1:18802/api/health \| jq .vectorCoverage` |
| VPS IP atual | `187.77.234.79` (PR #164) |
| F10 dashboard | `http://127.0.0.1:18802/dashboard` (via Tailscale) |
| Pre-launch checker | `bash scripts/check-pre-launch.sh` |
| Social copy | `docs/launch-social-copy.md` |
| HN defense prep | `docs/launch-hn-comments-prep.md` |
| Blog post draft | `docs/launch-blog-v0-draft.md` |
| COMPARISON.md | `benchmark/COMPARISON.md` |
| Outreach templates | `docs/outreach-templates.md` |
| Backup snapshot dir | `/var/backups/nox-mem/pre-op/` |

---

*rev2 — Sat 2026-05-24 closure update · consolidado de PR #227 + GTM audit PR #302 + HN prep PR #323 rev3*
