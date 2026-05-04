# Launch Strategy — NOX-Supermem Paper Distribution

> **Goal:** ≥ 1k blog views first 7d + HN frontpage top 30 + ≥ 5 inbound NOX-Supermem product leads + ≥ 50 arXiv downloads first 30d
> **Core principle:** distribution > virality. Quality crowd > broad reach.
> **Time investment:** ~6h spread post-publication (W6 + first 4 weeks)

---

## 🎯 Core thesis da divulgação

**Não é marketing — é positioning.** Você não está "lançando produto"; está **registrando contribuição técnica** com 3 audiences distintos:

1. **Devs/practitioners** (HN/Reddit/dev.to) — credibilidade técnica → product credibility transitiva
2. **Researchers** (arXiv/Twitter ML community) — citation handle → academic legitimacy
3. **Buyers potenciais NOX-Supermem** (LinkedIn/inbound) — converter awareness em leads P01

Cada audience precisa **mensagem diferente**, **timing diferente**, **canal diferente**. Misturar = perder todos.

---

## 📅 Launch sequence (W6 → W6+4 = 5 semanas)

### Day -7 (W5 Friday) — Pre-launch validation
- [ ] arXiv format compliance check (LaTeX builds clean, abstract ≤ 250 words, figures vetoriais)
- [ ] Blog post final read-through em mobile (60% HN traffic é mobile)
- [ ] HN title A/B test em 5 amigos privados (DM título + 1-line, perguntar "click?") → pick winner
- [ ] Repo cleanup final: README publication-ready ✅, CITATION.cff com BibTeX placeholder pra arXiv ID
- [ ] Twitter thread 5 tweets drafted (cada tweet ≤ 280 chars + 1 chart hero)
- [ ] LinkedIn post drafted (business angle, P01 product tease soft)
- [ ] Discord/Telegram private network warmed (3-5 dev contacts pra primeiro upvote)

### Day 0 (W6 Tuesday 09:00 ET) — arXiv submit
**Por que terça 09:00 ET:**
- Manhã US East Coast = peak engagement HN/Twitter ML
- Terça evita Monday distraction + Friday pre-weekend
- 09:00 ET = 06:00 PT = 22:00 BR (perfeito pra você submeter à noite e dormir)

Actions:
- [ ] arXiv submit (cs.IR primary, cs.CL secondary)
- [ ] Aguardar arXiv ID assignment (~4-12h)
- [ ] Update CITATION.cff + README com arXiv ID + BibTeX
- [ ] Commit "arXiv:2606.XXXXX preprint live" + push

### Day +1 (W6 Wednesday 09:00 ET) — Blog publish
- [ ] dev.to publish (primary host) com canonical URL pra Substack pessoal
- [ ] Substack publish (cross-post)
- [ ] LinkedIn publish (business angle versão)
- [ ] Cross-post link em CLAUDE Discord servers + 1-2 dev communities relevantes (NÃO spam)
- [ ] Twitter thread post (5 tweets, schedule espaçado 30min cada)

### Day +2 (W6 Thursday 09:00 ET) — Hacker News submit ⭐
**Critical timing window** — terça/quarta 08:00-10:00 ET é optimal HN.

- [ ] Submit blog post URL (NÃO arXiv — HN crowd prefere narrative)
- [ ] **Within 5 min:** post first comment (template em `06-hn-submission.md`)
- [ ] **Within 1h:** monitor every comment, respond all genuinely
- [ ] **Hour 1-6 critical:** se tiver 5+ pontos hour 1, frontpage virá. Se < 3 pontos, fade.
- [ ] DO NOT ask friends pra upvote (HN detecta, killer)
- [ ] DO share em network privado pos-1h "I just submitted, would value feedback" (não "upvote please")

### Day +3-4 (W6 Fri-Sat) — Reddit + community engagement
- [ ] Se HN frontpage hit: post em r/MachineLearning ("[D] Discussion" tag) referenciando HN thread
- [ ] r/LocalLLaMA com framing diferente (cost angle: "$0 OpenClaw zero-cost backend")
- [ ] r/programming se ângulo geral
- [ ] Respond all comments mantendo tom técnico humilde (NÃO defensive)

### Day +7 (W6+1 Tuesday) — Twitter ML community push
- [ ] DM 5-10 ML researchers ativos Twitter (não cold spam, escolher quem cita papers similares)
- [ ] Reply thread referenciando trabalhos de quem você cita (acknowledge prior work publicly)
- [ ] Pin thread no perfil com chart hero

### Day +14 (W6+2) — Mid-launch checkpoint
- [ ] Stats dump: HN final score, Reddit upvotes, dev.to views, arXiv downloads
- [ ] Identify top inbound channel → double down nesse
- [ ] If product leads ≥ 5: spawn lead nurture workflow (Slack channel pra triage)
- [ ] If product leads < 5: pivot LinkedIn focus pra direct outreach P01

### Day +30 (W6+4) — Post-mortem + iteration
- [ ] Post-launch retrospective em `09-launch-postmortem.md` (criar quando chegar)
- [ ] Cite responses tracking (Google Scholar alert configurado)
- [ ] If ≥ 3 citations: paper v2 worth (incorporar feedback peer)
- [ ] If product leads convertendo: P01 timeline accelerated

---

## 🎨 Mensagem por audience (3 versões da mesma história)

### Versão 1 — Devs/practitioners (HN, Reddit, dev.to)
**Hook:** "FTS5 vs Hybrid: I measured a 97.7% gap"
**Angle:** counterintuitive empirical finding > engineering details > 3 contributions
**Tone:** humble, code-first, honest about limitations
**CTA:** "code MIT, repo link, suggest queries for held-out eval"
**Length:** 2500w blog post + 500-char HN first comment

### Versão 2 — Researchers (arXiv, Twitter ML)
**Hook:** "Pain-weighted salience: missing dimension in agent memory"
**Angle:** novel contribution + replication-aware methodology + comparison vs literature
**Tone:** academic formal, hedged claims, explicit limitations
**CTA:** "arXiv preprint, BibTeX, replication artifacts"
**Length:** 12-page paper + 1-tweet hook + thread acknowledging prior work

### Versão 3 — Buyers potenciais NOX-Supermem (LinkedIn, inbound)
**Hook:** "4 months running 6 AI agents in production. What I learned."
**Angle:** business/operational lessons → product credibility → soft P01 tease
**Tone:** professional, story-driven, business outcomes focused
**CTA:** "if you're scaling AI agents in your business, DM"
**Length:** 1500w LinkedIn post + 1-line summary + 1 chart screenshot

**NEVER mix.** Cada versão é destino-específica.

---

## 🚀 Channels rankeados por ROI esperado

| Channel | Effort | Reach potential | Quality of audience | ROI score |
|---|---|---|---|---|
| **Hacker News** ⭐ | 30min submit + 6h monitoring first day | 50k-500k views se frontpage | A+ (technical decision-makers) | 9/10 |
| **arXiv** ⭐ | 1h format + submit | 200-2000 paper downloads | A (researchers, citation handle) | 8/10 |
| **dev.to** | 1h post + tag selection | 1k-50k views | A- (devs implementing) | 8/10 |
| **Twitter ML community** | Ongoing 1h/sem | 5k-100k impressions | A (ML researchers) | 7/10 |
| **r/MachineLearning** | 30min post + monitoring | 10k-200k views | B+ (mixed academic/industry) | 7/10 |
| **r/LocalLLaMA** | 30min post | 5k-50k views | B (LLM enthusiasts, cost-sensitive) | 6/10 |
| **LinkedIn** | 30min post + replies | 500-5k views | B+ (business buyers) | 6/10 |
| **Substack pessoal** | Cross-post 5min | 100-1000 subscribers organic | B (long-term audience build) | 5/10 |
| **r/programming** | 30min post | 20k-200k views | C+ (mixed quality) | 4/10 |
| **Twitter geral** | Daily 10min | 5k-50k impressions | C (mixed) | 4/10 |
| **Discord/Slack communities** | Ad-hoc 15min each | 50-500 views per server | A- (very specific audiences) | 6/10 |
| **Cold email researchers** | 1h crafting + sending | 10-30 responses | A (direct conversation) | 7/10 |

**Top 5 priority:** HN + arXiv + dev.to + Twitter ML + r/MachineLearning. Resto é optional bonus.

---

## ⚠️ Anti-patterns a EVITAR

### ❌ Não faça
1. **Beg for upvotes** em HN/Reddit — instant detect kill
2. **Mass DM cold** Twitter — spam flag risco
3. **Repost mesmo content** múltiplos subreddits same day — ban risco
4. **Polemizar em comments** — responda criticism com data, não emoção
5. **Hide weaknesses** do paper — reviewer vai achar; melhor disclose primeiro
6. **Over-promise product** P01 NÃO está pronto pra venda — soft tease apenas
7. **Atacar competitors** (mem0/MemGPT) — posicione com respeito, foco no que você faz diferente

### ✅ Faça
1. **Acknowledge prior work** publicamente em Twitter (reply ao authors quando relevante)
2. **Respond all comments** primeiras 24h — algoritmos premiam engagement
3. **Pin best chart** no perfil + tweet
4. **Share data behind claims** — link pra repo + reproducibility instructions
5. **Be wrong gracefully** se reviewer aponta erro real → admit + fix + thank
6. **Time submit** terça/quarta 09:00 ET (data-validated optimal)

---

## 📊 Validação tactical (como medir se está funcionando)

### Sinais POSITIVOS (Day 0 → Day 7)
- HN frontpage hit (top 30) → reach orgânico mais 24-48h
- arXiv downloads ≥ 50 first week → researcher attention
- ≥ 3 substantive comments per post asking technical questions → quality engagement
- 1+ academic Twitter account RT/cite → citation potential
- ≥ 1 inbound product email → P01 lead pipeline started

### Sinais NEUTROS (continuar normalmente)
- HN points ≤ 5 first hour → likely fade, accept
- Blog views < 500 first day → channel mismatch, pivot
- 0 Reddit pickup → drop subreddits attempts

### Sinais NEGATIVOS (pivot needed)
- HN flagged/buried → repost wrong, retry diferente angle
- Reviewer crítica fundamental no Twitter (não responde defensive) → revise paper antes próxima ronda
- Product leads = 0 after 30d → P01 messaging não conecta, ajustar landing

---

## 🎯 Validação acadêmica (longer term)

### Citation tracking (mensal)
- Google Scholar alerts pra "NOX-Supermem", "Busnello memory", arXiv ID
- Semantic Scholar profile pra trackear bibliographic mentions
- Connected Papers gráfico pra ver papers downstream

### Conferência target post-paper (se tração for significativa)
- **NeurIPS Workshop on Foundation Models for Decision Making** (Q3 2026)
- **EMNLP Industry Track** (Q4 2026, deadline geralmente Jul)
- **CIKM short paper** (4 pages, easier acceptance)
- **VLDB Industrial track** (system experience papers welcome)

Ver venue selection só **após** Day +30 retrospective — se paper tração foi alta, vale upgrade pra peer-review formal.

### Convidar feedback estruturado
- Form simples (Google Forms 5 perguntas) link no blog post final: "Used nox-mem? Share what worked/failed"
- 10+ structured responses = data pra paper v2

---

## 🔥 Quick wins que multiplicam reach (low effort)

1. **Cross-post no Slack /r/<community>** específico (CLAUDE Discord, OpenAI dev forum, Gemini API dev forum) — autores costumam ler, citation potential
2. **Show & Tell em meetup/podcast** (1h preparado serve 5-10 lugares diferentes ao longo do mês)
3. **Twitter "what I learned" thread** semanalmente após launch — sustaining interest sem gatekeeping
4. **GitHub Discussions abertas** no repo — convida community participation
5. **Newsletter mention** — submit aos curators (TLDR AI, The Batch, AlphaSignal) com 1-line + link

---

## 📈 Stretch goals (se Day +30 retrospective for muito bom)

- **Convite pra podcast** (Latent Space, MLOps Community, This Week in ML & AI) — 1 episódio pode 10× reach
- **Workshop submission** NeurIPS 2026 (deadline costuma Jul) — peer-review credibility
- **YouTube technical talk** (15min architectural overview) — alcance dev visual
- **Hackathon NOX-Supermem** (community-driven adoption) — viralidade orgânica
