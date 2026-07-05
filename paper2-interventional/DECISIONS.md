# Martelo — Decisões travadas (Paper 2)

> Convergência de 3 vozes adversariais (Codex/Kimi/GLM) + síntese. Detalhe das vozes em `REVIEWS.md`.
> Data: 2026-07-05.

## ✅ Spine (confirmado pelas 3 vozes)

Representação ≠ decisão. Retrieval mede o primeiro; o valor da memória do agente está no segundo. **É o paper.** A intuição é "forte e genuinamente subexplorada" (consenso das 3 vozes).

## ✅ Framing — a regra mais importante

**NÃO** usar "causal/interventional" como claim guarda-chuva. Foi o alerta mais forte (Codex + GLM):

- Só o **braço A/B randomizado** é interventional. O benchmark de traces + o outcome-weighting são **observacionais retrospectivos**.
- Chamar tudo de "causal" = **inflation terminológica → desk-reject** (area chair do COLM).
- **Regra:** reservar "causal" exclusivamente pro braço randomizado. No resto: *"decision-relevant"*, *"outcome-associated"*, *"behaviourally validated"*.
- **Methods em duas camadas explícitas:**
  - *Benchmark contribution:* retrospective log study (n=…, período=…).
  - *Causal claim:* only for the randomized withholding arm (n=…, pre-registered primary outcome).

## ✅ Título (working — nome exato não travado)

Candidatos, todos evitando "causal" no headline como claim absoluto:

- *Interventional Memory: Decision-Relevant Retrieval from Live Multi-Agent Traces*
- *Retrieval Metrics Can't See What Agent Memory Is For* (gancho do gap de avaliação)

Pain aparece como **motivação/primitivo**, nunca no título.

## ✅ Venue

- **COLM 2027** — alvo primário (interactions / multi-agent / evaluation encaixam).
- **NeurIPS D&B 2027** — se o artefato público for sério (dataset + código).
- **EMNLP 2027** — fallback, moldura *negative-finding + resource*.

## ✅ Onde o paper se ganha

**80% é metodologia, não escrita.** Ver `METHODOLOGY.md`. A prioridade zero é blindar o desenho (pré-registro + SUTVA + auditoria + artefato), não escrever melhor.

## ❌ O que rejeitamos explicitamente

- **Pain-weighting como mecanismo-protagonista** — beco morto do Paper 1 (insignificante). Vira primitivo, não headline.
- **"Causal" sem randomização** — hype; abate no desk-reject.
- **A/B ingênuo on/off** sem tratar interferência cross-agent — quebra o estimador (ver SUTVA em `METHODOLOGY.md`).
