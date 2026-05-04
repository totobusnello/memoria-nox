# NOX-Supermem Publication Subproject

> **Mission:** publicar arXiv preprint + blog post + HN submission em **4-6 semanas**, registrando contribuição científica genuína sem entrar em peer-review trap (top-tier conferences = 6 meses gatekeeping).
> **Strategy:** exaltar 3 diferenciais reais, cobrir 5 gaps técnicos, posicionar honestamente vs prior work.
> **Author:** Luiz Antonio Busnello (Toto). **Compiled by:** Claude Opus 4.7.

---

## 📁 Estrutura desta pasta

| File | Propósito | Status |
|---|---|---|
| `00-INDEX.md` | Você está aqui — mapa + status | ✅ |
| `01-positioning-strategy.md` | 3 diferenciais a exaltar + 5 gaps a cobrir + voice/tom | 🔄 draft |
| `02-related-work-notes.md` | Comparison detalhado vs GraphRAG, MemGPT, Mem0, A-MEM, HiRAG, GraphRAG, Cognee, LangChain Memory | 🔄 draft |
| `03-experiments-needed.md` | Ablation studies + 3-corpora plan + new baselines (BM25, BGE, E5) | 🔄 draft |
| `04-paper-arxiv-draft.md` | Paper acadêmico arXiv-ready (~12 pages, 6 sections) | 📋 PENDING |
| `05-blog-post-draft.md` | Blog version (story-driven, ~2500 words, dev-friendly) | 📋 PENDING |
| `06-hn-submission.md` | Hacker News title + first comment template | 📋 PENDING |
| `07-publication-checklist.md` | Checklist priorizado em 4 sprints (P0/P1/P2/P3) | ✅ |

---

## 🎯 Timeline target (4-6 semanas)

| Semana | Sprint | Output |
|---|---|---|
| **W1 (2026-05-04→10)** | P0 — Foundation | Related work notes + experiments plan + positioning final |
| **W2 (05-11→17)** | P1 — Experiments | Ablation studies (10h) + 2 corpora extra runs (BEIR subset + Stack Exchange) |
| **W3 (05-18→24)** | P2 — Writing | arXiv paper draft 12 pages + blog post 2500 words |
| **W4 (05-25→31)** | P3 — Polish | Internal review (Claude critic + 3rd party feedback) + revision |
| **W5 (06-01→07)** | Submission | arXiv submit + blog publish + HN submission Tuesday 09:00 ET |
| **W6 (06-08→14)** | Distribution | Twitter/LinkedIn announce + dev community engagement + cite responses |

**Effort estimado:** 30-40h spread em 6 semanas (~5-7h/sem dentro do budget 6h/sem CEO frente).

---

## 🚦 Gating criteria

| Antes de... | Validação obrigatória |
|---|---|
| arXiv submit | 3-corpora results + 3-run mean±std + ablation table + critic review pass |
| Blog post publish | Code repo público estável + screenshots reais + tagline ≤ 280 chars |
| HN submission | Blog post live ≥ 1 dia + dry-run title test (5 variants) |

---

## 🔗 Cross-refs

- Source draft (single doc inicial): `paper/paper-v2-draft-evidence.md` (DRAFT v2 com 4 critic caveats já aplicados)
- Source histórica: `paper/paper-tecnico-nox-mem.md` (paper v1 March 2026, baseline)
- Engineering source: `~/.openclaw/workspace/tools/nox-mem/src/` na VPS
- Roadmap principal: `docs/ROADMAP.md` (R02 row tracks publication progress)
- Decisions log: `docs/DECISIONS.md` (cite arXiv ID quando publicado)
