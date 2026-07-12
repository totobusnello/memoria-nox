# Próximos passos — Paper 2

> Postura atual: **esperando o arXiv ID do Paper 1** (`2507.XXXXX`, em *on hold* desde 2026-07-01).

## Gate

Nada de execução do Paper 2 começa antes de:

1. **Paper 1 sair do hold** (ID `2507.XXXXX` público).
2. Fechar o loop técnico do Paper 1 (badge do README + `CITATION.cff` + os 2 blocos BibTeX com o ID real — arquivos na raiz do repo).

## Quando o ID sair → primeiro entregável

~~**Concept note de 1 página**~~ ✅ **FEITA (antecipada 2026-07-12, autorizada pelo Toto)** → **`CONCEPT-NOTE.md`** — problema · claim em 2 camadas · 2 figuras · reusa/constrói · guardas (SUTVA + pré-registro + adjudicação + artefato + COI) embutidas; em inglês (vai circular pra auditor externo). Execução segue gated no ID.

**Novo primeiro entregável pós-ID:** rascunho de **pré-registro OSF** (primeiro item do checklist abaixo).

## Checklist de metodologia (a coisa de verdade — 80% do paper)

- [ ] Rascunho de **pré-registro OSF** (outcome primário, sample size, stopping rule)
- [ ] Desenho de **randomização SUTVA-safe** (cluster por agente / bloco de tempo / washout)
- [ ] Spec de **sanitização** do benchmark (hashing, buckets, esquema de labels, IAA)
- [ ] Recrutar **auditor externo** (≥1, outra instituição)
- [ ] Selecionar **≥2 baselines** pra rodar por gente de fora do time
- [ ] Construir **counterfactual replay harness** (offline, grosso)
- [ ] Construir **A/B low-stakes** ao vivo (validação)

## Riscos / kill-conditions (GLM)

- ❌ **Sem pré-registro** → whitepaper de vendor, não passa.
- ❌ **SUTVA cross-agent não tratado** → reviewer 2 mata em NeurIPS D&B, desk-reject provável em COLM.
- ❌ **"Causal" sobrevendido** → desk-reject por inflation terminológica.
- ⚠️ **Selection/survivorship** nos traces + **Hawthorne/drift** na janela do A/B — endereçar no desenho.

## Timeline (rough, condicional ao ID)

- **T0** = arXiv ID do Paper 1 público.
- T0 + dias: ~~concept note~~ (✅ pronta, 2026-07-12) + rascunho de pré-registro.
- Depois: desenho SUTVA + harness replay → pré-registro trancado → A/B → análise → draft.

## Fora de escopo (não fazer aqui)

- Produtização / campanha de estrelas do `nox-mem` → repo-produto `nox-mem` (ex-supermem), outra conversa. Este workspace é só o paper.
