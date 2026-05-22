# nox-mem Post-Launch Outreach Templates

> Launch: Wed 2026-06-03 | Outreach window: Thu–Fri 2026-06-04–05
> arXiv link available: Tue 2026-06-02

---

## §1 Princípios de outreach

Estas templates existem para facilitar reach-outs **pensados e personalizados** — não cold-spam em escala.

**Regras de ouro:**

1. **Personalize as 2 primeiras frases** — mostre que você leu o trabalho deles. Um artigo específico, um episódio de podcast, uma thread recente. Se não conseguir citar algo real, não envie.
2. **Seja específico sobre o porquê deles** — "vi você no X" não conta. Diga por que o trabalho *deles* em específico cria um ponto de conexão com o que você lançou.
3. **Value-first** — o que eles ganham com isso? Uma história interessante, um ângulo novo, uma metodologia honesta que é raro ver no espaço. Não comece com o que você precisa.
4. **Um ask por email** — cobertura, um episódio, uma call de 20min. Não empilhe pedidos.
5. **Taxa de resposta esperada: ~10%** — é normal. Silêncio não é rejeição, é ruído. Não personalize demais.
6. **Follow-up: máx 2 vezes** — D+7 e D+14. D+21 sem resposta: log "no reply" e siga.
7. **Horário de envio (audiência US):** quinta ou sexta, 8h–10h ET — maximiza janela de resposta antes do fim de semana.

---

## §2 Journalist Outreach

### §2.1 Tech Generalist — TechCrunch / The Verge / Ars Technica

**Subject:** `[Open source] Memory layer for LLM agents — published methodology + benchmarks`

```
Hi [Name],

Your piece on [specific story they wrote — e.g., "LLM agent reliability" from [month]]
stuck with me — particularly the point about [specific detail from the piece]. That's
exactly the gap I've been building into.

I just open-sourced nox-mem, a memory layer for LLM agents. Public launch on HN
today. What's different from the usual "we beat everyone" releases:

— MIT license, solo author, all code + benchmark scripts are public
— Methodology was pre-registered before evaluation (not tuned post-hoc)
— Per-category breakdown published, including categories where we lose
— Compares against Mem0, Zep, Letta/MemGPT, and two others by name

Quick links:
→ HN thread: [URL]
→ Paper (arXiv): [arXiv URL, live Tue 06-02]
→ Code: github.com/totobusnello/memoria-nox

Happy to send screenshots, walk through methodology, or answer questions on
background or for attribution. No pressure either way.

— Toto Busnello
lab@nuvini.com.br
```

---

### §2.2 AI/ML Specialist — Import AI / The Algorithm / Interconnects

**Subject:** `Pain-weighted salience + Conditional Hard Mutex — open ablation methodology`

```
Hi [Name],

I've been reading [specific newsletter issue or post — e.g., "your breakdown of the
MemGPT paper" or "your piece on agent memory architectures"] and I'm glad someone
is covering this space at the technical depth it deserves.

I'm releasing nox-mem today — an open-source LLM memory layer with two specific
technical contributions I think are worth scrutiny:

1. Pain-weighted salience: `salience = recency × pain × importance` — where `pain`
   is a severity signal (0.1 trivial → 1.0 production outage). Ablation results
   show it contributes meaningfully on large corpora only; we publish the null results.

2. Conditional Hard Mutex on section boosting — per-category rather than flat;
   multi-hop queries improve +1.58%, adversarial +3.04%. Details in the paper.

Full ablation log (G1–G12) is in the repo. Methodology was registered before eval.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox
→ HN thread: [URL]

If you want to dig into methodology, happy to do a background call or answer
questions in writing. Genuinely interested in your reaction to the ablation design.

— Toto Busnello
lab@nuvini.com.br
```

---

### §2.3 Open Source / Dev Tooling — LWN / The New Stack / Console.dev

**Subject:** `MIT memory layer for LLM agents — single-file SQLite, zero vendor lock-in`

```
Hi [Name],

I follow [specific column / section / recent piece they wrote — e.g., "your coverage
of developer infra tools" or "your piece on SQLite in production"]. That's why
I thought this might be relevant to you.

I released nox-mem today — an MIT-licensed memory layer for LLM agents. The design
philosophy is deliberately different from the commercial alternatives:

— Single SQLite file (FTS5 + sqlite-vec for vector search) — deploy is copying one file
— Zero proprietary APIs required — runs offline with local embeddings
— Observable: health endpoint exposes retrieval telemetry, section distribution,
  vector coverage. Nothing hidden in a hosted black box.
— All benchmark scripts public, all ablation results published (including regressions)

It's a solo project built over ~4 months. I'm not trying to raise a round or sell
a SaaS. I think the open alternative deserved to exist.

→ Code: github.com/totobusnello/memoria-nox
→ Paper: [arXiv URL]
→ HN: [URL]

Happy to provide a deeper technical walkthrough if useful for a piece.

— Toto Busnello
lab@nuvini.com.br
```

---

### §2.4 Imprensa tech brasileira — Mobile Time / Convergência Digital / Olhar Digital

**Assunto:** `[Open source brasileiro] Memória para agentes de IA — metodologia e benchmarks públicos`

```
Olá [Nome],

Acompanho a cobertura de vocês sobre [tema específico — ex: "IA generativa no Brasil"
ou "ferramentas open source para desenvolvedores"]. Esse contexto é o que me fez
pensar em vocês aqui.

Acabei de lançar o nox-mem — uma camada de memória open source para agentes de LLM,
desenvolvida por mim no Brasil ao longo dos últimos meses. O projeto acaba de ir a
público no Hacker News hoje.

O que diferencia:
— MIT, código 100% aberto (github.com/totobusnello/memoria-nox)
— Metodologia de benchmark registrada antes da avaliação — sem ajuste pós-hoc
— Comparação honesta com 5 alternativas comerciais (incluindo onde o nox-mem perde)
— Sem dependência de API proprietária — roda localmente

É raro ver contribuição técnica desse tipo saindo do Brasil para o ecossistema global
de IA. Se fizer sentido para a pauta de vocês, fico à disposição para uma call ou
responder por escrito.

→ Código: github.com/totobusnello/memoria-nox
→ Paper: [URL arXiv]
→ HN: [URL]

Abraço,
Toto Busnello
lab@nuvini.com.br
```

---

## §3 Podcast Host Outreach

### §3.1 Long-form Technical Podcasts — Latent Space / Practical AI / The TWIML AI Podcast / Gradient Dissent

**Subject:** `Pain-weighted hybrid memory + open ablation methodology — episode angle`

```
Hi [Name],

I just listened to [specific episode — e.g., "your episode with [guest] on agent
memory and long-context retrieval"]. The question about [specific point raised —
e.g., "how retrieval degrades on multi-session queries"] is exactly what I've been
measuring in the lab for four months.

I released nox-mem today — an open-source memory layer for LLM agents — and I think
there might be an interesting episode angle here. Not "look at my project" but
genuinely: what does it take to build honest benchmarks in this space?

A few threads I could pull on:

1. Why methodology integrity matters in LLM memory benchmarks — pre-registration,
   per-category breakdown, publishing regression results alongside wins.

2. Pain weighting as a retrieval signal — the intuition, the ablation results (large
   corpus only, neutral on small), and what that means for agent memory design.

3. The tradeoffs of single-author open source vs VC-backed memory infra — where
   the freedom is, where the limits are.

I'm flexible on format — full episode, segment, or even a brief appearance if you're
doing a roundup. Happy to send the paper and ablation log in advance.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox

— Toto Busnello
lab@nuvini.com.br
```

---

### §3.2 Smaller / Focused Podcasts — local AI meetups, community shows, niche dev podcasts

**Subject:** `Open-source LLM memory — happy to join an episode`

```
Hi [Name],

I've been listening to [specific podcast name and recent episode] — your audience
seems genuinely engaged with the technical details, which is rare.

I released nox-mem today, an open-source memory layer for LLM agents with published
benchmarks. It's a solo project, MIT-licensed, built in the open.

If you're ever looking for a guest who can speak to:
— Hybrid retrieval (BM25 + semantic + RRF fusion)
— How to structure honest benchmark evaluation as an indie developer
— Building production-grade agent infra without a team

I'd be happy to join for an episode. No particular time pressure — whenever works
for your schedule and audience.

→ Code: github.com/totobusnello/memoria-nox
→ Paper: [arXiv URL]

— Toto Busnello
lab@nuvini.com.br
```

---

## §4 Conference Organizer Outreach

### §4.1 PyCon / OSCON / FOSDEM / AI Engineer Summit / NeurIPS Workshops

**Subject:** `Talk proposal: LLM agent memory in the open — pain weighting + honest benchmarks`

```
Hi [Name],

I'm submitting a talk proposal for [conference name + track/CFP deadline if known].

**Proposed title:**
"Building LLM Agent Memory in the Open: Pain-Weighted Retrieval and Benchmark Integrity"

**Abstract (150 words):**
Most LLM memory benchmarks are evaluated after the system is tuned — methodology
chosen to maximize reported numbers. This talk walks through a different approach:
pre-registering methodology, running ablations openly (including regressions), and
publishing per-category results where the system loses.

I'll cover the architecture of nox-mem, an open-source memory layer using hybrid
retrieval (BM25 + Gemini embeddings + RRF fusion), and two specific technical
contributions: pain-weighted salience scoring (weighting retrieval by severity of
the original memory event) and Conditional Hard Mutex (per-category boost gating
that recovers multi-hop and adversarial query performance). Full ablation log with
12 experiments is public.

The talk is aimed at developers building agent systems who want practical retrieval
architecture — not hype. Code, benchmarks, and methodology are all MIT-licensed
and open.

**Speaker bio (one line):**
Toto Busnello is a solo open-source developer and board-level operator; nox-mem is
his personal contribution to LLM agent infrastructure.

**Why this audience:**
[Specific reason — e.g., "PyCon's emphasis on practical Python tooling aligns with
nox-mem's SQLite-first, zero-dependency design" OR "AI Engineer Summit's focus on
production agent systems is exactly where honest retrieval benchmarks matter most."]

Happy to provide slides draft, A/V requirements, or additional detail.

— Toto Busnello
lab@nuvini.com.br
```

---

### §4.2 Meetups locais — São Paulo + eventos remotos em PT-BR

**Assunto:** `Proposta de talk: Memória para agentes de LLM — open source, benchmarks honestos`

```
Olá [Nome],

Acompanho o [nome do meetup/grupo] e gostaria de propor uma apresentação.

**Título:** "Construindo Memória para Agentes de IA em Código Aberto: Retrieval Híbrido e Metodologia Honesta de Benchmark"

**Resumo:**
Vou cobrir a arquitetura do nox-mem, uma camada de memória open source para agentes
de LLM, incluindo: retrieval híbrido (BM25 + embeddings semânticos + fusão RRF),
salience ponderado por "dor" (o quanto um evento importou quando aconteceu), e como
estruturar benchmarks honestos — com pré-registro de metodologia e publicação de
resultados negativos.

O projeto é MIT, desenvolvido por um único autor, e toda a infraestrutura de
avaliação é pública.

**Por que para vocês:** [Motivo específico — ex: "O grupo foca em IA aplicada em
produção, e a arquitetura SQLite-first do nox-mem é relevante para quem precisa
de memória de agente sem dependência de cloud."]

Disponível para formato de 20min + perguntas ou 40min técnico. Remoto ou presencial
em São Paulo.

→ Código: github.com/totobusnello/memoria-nox

Abraço,
Toto Busnello
lab@nuvini.com.br
```

---

## §5 Competitor / Peer Outreach — Critical Diplomacy

> Tone: collegial, not hostile. These are people doing serious work in the same space.
> The goal is methodological transparency and possibly a collaborative relationship — not a marketing move.

### §5.1 Mem0 — Taranjeet Singh / Deshraj Yadav

**Subject:** `Heads-up: I published a comparison including Mem0 — honest methodology`

```
Hi [Name],

I wanted to give you a direct heads-up before you see it elsewhere.

I'm Toto Busnello — I built nox-mem, an open-source memory layer for LLM agents.
I published it today along with a comparison against several memory systems,
including Mem0.

I want to be transparent about the methodology:
— I used Mem0's default configuration (no cherry-picking)
— Results are published per category, including where nox-mem loses
— Benchmark scripts are fully public so you can reproduce every number

I have a lot of respect for what you've built. Mem0's early commitment to memory
as a first-class concern in agent systems shaped how the broader community thinks
about the problem — including me.

If you believe a different Mem0 configuration would produce fairer results, I'd
genuinely like to hear it. I'm open to re-running evaluation with adjusted settings
and publishing an update. The goal is accuracy, not a marketing win.

If there's interest in collaborating on shared methodology or a joint evaluation
framework for the space, I'd welcome that conversation too.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox

— Toto Busnello
lab@nuvini.com.br
```

---

### §5.2 Zep — Daniel Chalef et al.

**Subject:** `Heads-up: I published a comparison including Zep — open methodology`

```
Hi [Name],

Giving you a direct heads-up before you encounter this elsewhere.

I'm Toto Busnello. I built and released nox-mem today — an open-source memory layer
for LLM agents. The release includes a comparison against several memory systems,
including Zep.

On methodology:
— Default Zep configuration used throughout
— Per-category results published (including where nox-mem underperforms)
— All benchmark scripts are MIT-licensed and public

Zep's work on temporal context and graph-structured memory has been an important
reference point in how I thought about the problem. That's reflected in how I
designed the evaluation categories.

If the configuration used isn't representative of Zep at its best, I'm open to
re-running with adjusted settings and publishing results publicly. Let me know.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox

— Toto Busnello
lab@nuvini.com.br
```

---

### §5.3 Letta — Charles Packer et al. (MemGPT)

**Subject:** `Heads-up: comparison including Letta — + acknowledgment of MemGPT's influence`

```
Hi [Name],

Direct heads-up before you see this elsewhere.

I'm Toto Busnello. I released nox-mem today — open-source memory layer for LLM
agents — with a comparison including Letta/MemGPT.

I want to say this clearly: the MemGPT paper (2023) was foundational for this
project. The framing of agents with self-directed memory management shaped how I
thought about salience and retrieval from the beginning. That's cited explicitly
in the paper.

On the comparison methodology:
— Default Letta configuration; no cherry-picking
— Per-category results, including where nox-mem loses
— All scripts public and reproducible

If the configuration used doesn't represent Letta fairly, I'd genuinely welcome
feedback and will re-run with corrected settings. I'd rather publish accurate
numbers than favorable ones.

Happy to discuss methodology or share evaluation data directly if useful for your
own benchmarking work.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox

— Toto Busnello
lab@nuvini.com.br
```

---

### §5.4 agentmemory / EverMind-AI authors

**Subject:** `Heads-up: comparison including [project name] — open methodology`

```
Hi [Name],

Quick heads-up — I released nox-mem today with a comparison that includes
[agentmemory / EverMind-AI, as applicable].

Methodology: default config, per-category results, scripts fully public.
I publish categories where nox-mem loses alongside categories where it wins.

Your work on [specific contribution — e.g., EverMemBench as a standardized eval
framework / agentmemory's lightweight approach] has been a useful reference.
If there's a configuration that better represents your system, I'm open to
re-running and publishing updated results.

→ Paper: [arXiv URL]
→ Code: github.com/totobusnello/memoria-nox

— Toto Busnello
lab@nuvini.com.br
```

---

## §6 Investor / Advisor Outreach

> This section is optional — only if you want to. Open-source launch doesn't require it.
> If you do send, the goal is FYI, not ask. No pitch deck, no fundraise announcement.

### §6.1 AI Infra Funds — Khosla / Bain Capital Ventures / etc.

**Subject:** `FYI — open-source LLM memory infra launched today`

```
Hi [Name],

Brief FYI in case it's relevant to your portfolio visibility.

I released nox-mem today — an MIT-licensed memory layer for LLM agents, built
as a solo project. It has published benchmarks vs Mem0, Zep, Letta, and others,
and a technical paper on arXiv.

Not a fundraise announcement — just sharing in case the space is on your radar.
If you're curious about the technical approach or know someone building in agent
infra who might find it useful, happy to connect.

→ github.com/totobusnello/memoria-nox
→ Paper: [arXiv URL]

— Toto Busnello
lab@nuvini.com.br
```

---

### §6.2 Advisor Candidates — board-level operators interested in research/product direction

**Subject:** `Open-source LLM agent memory — launched today, would value your perspective`

```
Hi [Name],

I released nox-mem today — an open-source memory layer for LLM agents I've been
building for the past several months. It includes published benchmarks and a
methodology paper.

I'm not looking for capital. I'm at a point where I'd value perspective from
someone who thinks seriously about [their specific angle — e.g., research
integrity in ML / product positioning in developer infra / open-source go-to-market].

If you have 20 minutes in the coming weeks and the topic is interesting to you,
I'd welcome a conversation. No agenda beyond getting your read on the work.

→ github.com/totobusnello/memoria-nox
→ Paper: [arXiv URL]

— Toto Busnello
lab@nuvini.com.br
```

---

## §7 Developer / Potential User Outreach

### §7.1 Developer Tools Companies — LangChain / LlamaIndex / CrewAI users and contributors

**Subject:** `Open memory layer for agents — might be useful if you're building with [their tool]`

```
Hi [Name],

I saw your [project / post / contribution — e.g., "work on long-running agent
loops in LangChain" or "your repo for multi-agent memory sharing"]. That's the
use case nox-mem was built for.

I released it today — MIT, SQLite-based, designed to drop into existing agent
pipelines without changing your stack. It does hybrid retrieval (BM25 + semantic
+ RRF) with a salience layer that weights by recency and event severity.

If you're building something where agent memory is a pain point, it might be
worth a look. Not asking for anything — just thought it was directly relevant
to what you're working on.

→ github.com/totobusnello/memoria-nox
→ Quick start: [README link]

— Toto Busnello
lab@nuvini.com.br
```

---

## §8 Follow-Up Cadence

All follow-ups should be shorter than the original email. One sentence context, one sentence ask.

### D+7 Follow-up (if no reply)

```
Subject: Re: [original subject]

Hi [Name],

Just bumping this in case it got buried. Happy to answer questions or
adjust the angle if it's not a fit for your current coverage / schedule.

— Toto
```

### D+14 Final Follow-up

```
Subject: Re: [original subject]

Hi [Name],

One last note — no pressure at all if the timing isn't right or it's not
a fit. The project is live at github.com/totobusnello/memoria-nox if you
ever want to circle back.

— Toto
```

### D+21

Log "no reply" in the CRM table (§9) and move on. No third follow-up.

---

## §9 CRM Tracking Table

Use this to track who received what. Copy and paste into your preferred tool.

```markdown
| Date sent  | Recipient         | Organization       | Type               | Status       | Notes                                      |
|------------|-------------------|--------------------|--------------------|--------------|---------------------------------------------|
| 2026-06-04 | [Name]            | [Org]              | journalist-general | sent         | Covered [X story]; personalized intro       |
| 2026-06-04 | [Name]            | [Org]              | podcast-longform   | sent         | Ep [N] on [topic]; offered 3 angles         |
| 2026-06-04 | [Name]            | Mem0               | competitor-peer    | sent         | Heads-up + methodology transparency         |
| 2026-06-04 | [Name]            | Letta              | competitor-peer    | sent         | MemGPT acknowledgment included              |
| 2026-06-05 | [Name]            | [Org]              | journalist-ai-ml   | sent         |                                             |
|            |                   |                    |                    |              |                                             |
```

Status values: `draft` / `sent` / `replied` / `follow-up-1` / `follow-up-2` / `no-reply` / `not-interested` / `connected`

---

## §10 Anti-patterns — o que não fazer

- **Não fazer BCC em massa.** Cada email vai para uma pessoa. Lista de BCC coloca você na pasta de spam de toda gente.
- **Não usar ferramentas de automação de marketing** para esses reach-outs personalizados. Hubspot sequences, Mailchimp, Apollo — não aqui. Essas ferramentas deixam rastros que destroem credibilidade com jornalistas e pesquisadores.
- **Não fazer follow-up mais de 2 vezes.** Depois de D+14, pare. Persistência além disso vira assédio.
- **Não ficar na defensiva se a resposta for hostil.** Leia, agradeça internamente, feche o email. Não responda com contra-argumentos.
- **Não compartilhar detalhes privados sobre sistemas de competidores.** Comparações ficam nos números públicos e na metodologia. Nada especulativo sobre arquitetura interna deles.
- **Não prometer coisas que não vai entregar.** Não diga "vou integrar com X no próximo mês" sem compromisso real. Não faça promessa de cobertura que depende de terceiros.
- **Não enviar sem personalizar as 2 primeiras frases.** Se o template saiu direto sem personalização, não enviou — está spammando. Deletar o draft e só enviar quando tiver a personalização real.
- **Não copiar o mesmo assunto de email para todos.** Jornalistas veem padrões. Varie o assunto por audiência.
