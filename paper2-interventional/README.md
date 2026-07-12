# Paper 2 — Interventional Memory · Planning Workspace

> **Status:** PLANNING · gated no arXiv ID do Paper 1 (`2507.XXXXX`, em *on hold* na moderação desde 2026-07-01).
> **Escopo:** só planejamento/decisão do próximo paper. O paper em si nasce quando o ID do Paper 1 sair.
> **Criado:** 2026-07-05.

## Em uma frase

Métricas de retrieval (nDCG/recall) medem **representação**, não **decisão** — e a memória de um agente serve pra *evitar repetir ações custosas* (valor **interventional**), algo a que essas métricas são estruturalmente cegas. Este paper introduz uma avaliação de ação-desfecho + um braço A/B randomizado ao vivo pra medir o que o retrieval não vê.

## De onde veio

Paper 1 (*Pain-Weighted Hybrid Memory*, submetido cs.IR+cs.LG) teve um achado honesto: **pain-weighting foi estatisticamente insignificante** — o driver real foi *section-aware*. Em vez de enterrar o pain, o reframe: **pain é o sinal de desfecho de uma intervenção** — não estava errado, estava sendo medido com o instrumento errado (retrieval). Paper 2 é essa evolução: do *pain* (mecanismo não-validado) pro *interventional value* (o que o pain queria capturar), medido direito.

## Navegação

| Arquivo | Conteúdo |
|---|---|
| [`CONCEPT-NOTE.md`](CONCEPT-NOTE.md) | **A concept note de 1 página (EN)** — destilado pronto pra circular (auditor externo, colaboradores); guardas embutidas. Feita 2026-07-12 (antecipada com autorização) |
| [`CONCEPT.md`](CONCEPT.md) | A tese, o claim, a âncora de fronteira, o moat |
| [`DECISIONS.md`](DECISIONS.md) | O martelo — decisões travadas (framing, título, venue) + razões |
| [`REVIEWS.md`](REVIEWS.md) | Revisão adversarial de 3 vozes (Codex/Kimi/GLM) — convergência e divergência |
| [`METHODOLOGY.md`](METHODOLOGY.md) | Desenho experimental + as guardas metodológicas (pré-registro, SUTVA, auditoria, artefato) |
| [`NEXT-STEPS.md`](NEXT-STEPS.md) | Tarefas gated no arXiv ID · riscos/kill-conditions · timeline |

## Relação com o resto do repo

- **Paper 1** (artefato): `paper/`.
- Este é o **workspace de planejamento** do Paper 2, não o paper. Quando virar draft, migra pra `paper/` seguindo a convenção do Paper 1.
- **Produtização + campanha de estrelas NÃO vivem aqui** — vão pro repo-produto `nox-mem` (ex-supermem). Este repo é core + paper.

## Proveniência

Todo o conteúdo desta pasta é o destilado de uma sessão de brainstorm (2026-07-05) que cruzou o perfil do autor + o ativo nox-mem + a agenda de fronteira do Nando de Freitas, validada por **3 vozes adversariais independentes** (Codex/Kimi/GLM). Detalhe das vozes em `REVIEWS.md`.
