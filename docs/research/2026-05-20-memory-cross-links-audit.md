# Audit: Cross-links em Memory Entries

**Data:** 2026-05-20  
**Escopo:** `/Users/lab/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`  
**Método:** Extração de todos `[[slug]]` inline + links `[text](file.md)` do MEMORY.md; comparação contra arquivos `.md` reais no diretório.

---

## Sumário

| Item | Count |
|---|---|
| Arquivos `.md` no diretório (excl. MEMORY.md + MEMORY-INDEX.md) | 90 |
| Entries referenciadas em MEMORY.md | 88 |
| `[[cross-links]]` únicos encontrados nos arquivos individuais | 57 |
| **Broken links** (slug sem arquivo correspondente) | **13** |
| **Orphans** (arquivo existe mas não consta em MEMORY.md) | **2** |

---

## Broken Links

Links do tipo `[[slug]]` presentes nos arquivos de memória individual, mas sem arquivo correspondente no diretório.

A convenção de slug é: `feedback_foo_bar.md` → `foo-bar`, `project_foo_bar.md` → `foo-bar`, `reference_foo_bar.md` → `foo-bar`.

| # | Link `[[slug]]` | Arquivo fonte | Diagnóstico | Fix sugerido |
|---|---|---|---|---|
| 1 | `[[d46-headline-canonical-100-6]]` | `project_q2_full_results_2026_05_19.md` | Entry D46 nunca criada (decisão foi incorporada em D47/D48) | Remover ref ou criar entry vazia `project_d46_headline_canonical.md` |
| 2 | `[[esm-static-imports-hoist-before-body]]` | `feedback_no_getdb_in_eval_scripts.md` | Arquivo real é `feedback_esm_static_import_hoisting_captures_env.md` → slug `esm-static-import-hoisting-captures-env` | Corrigir slug no arquivo fonte para `[[esm-static-import-hoisting-captures-env]]` |
| 3 | `[[feedback_no_secrets_in_git]]` | `feedback_user_accepts_gemini_key_risk.md` | Usando nome de arquivo completo com underscore em vez de slug kebab-case; arquivo existe como `feedback_no_secrets_in_git.md` → slug `no-secrets-in-git` | Corrigir para `[[no-secrets-in-git]]` |
| 4 | `[[feedback_validate_features_with_db_not_logs]]` | `project_q3_latency_numbers_2026_05_18.md` | Mesmo padrão — underscore em vez de slug; arquivo existe → slug `validate-features-with-db-not-logs` | Corrigir para `[[validate-features-with-db-not-logs]]` |
| 5 | `[[g2-entity-flavored-eval]]` | `feedback_static_analysis_vs_real_ablation.md`, `project_q2_full_results_2026_05_19.md` | Entry G2 nunca foi criada (eval set só planejado, não executado) | Criar `project_g2_entity_flavored_eval.md` ou remover refs |
| 6 | `[[mercury-agent-vs-nox-mem]]` | `project_personality_files_markdown_layer.md` | Entry de comparação Mercury jamais criada; conteúdo implícito em `project_personality_files_markdown_layer.md` | Criar entry ou reformar para `[[personality-files-markdown-layer]]` |
| 7 | `[[project_api_answer_live_2026_05_18]]` | `project_d43_q4_gate_phase2_open.md`, `reference_path_layout_canonical.md` | Underscore em vez de slug; arquivo existe → slug `api-answer-live-2026-05-18` | Corrigir para `[[api-answer-live-2026-05-18]]` |
| 8 | `[[project_d43_q4_gate_phase2_open]]` | `project_d44_stripe_first_pivot.md` | Underscore em vez de slug; arquivo existe → slug `d43-q4-gate-phase2-open` | Corrigir para `[[d43-q4-gate-phase2-open]]` |
| 9 | `[[project_pricing_prerequisites_2026_05_18]]` | `project_d44_stripe_first_pivot.md` | Underscore em vez de slug; arquivo existe → slug `pricing-prerequisites-2026-05-18` | Corrigir para `[[pricing-prerequisites-2026-05-18]]` |
| 10 | `[[project_q3_latency_numbers_2026_05_18]]` | `project_api_answer_live_2026_05_18.md` | Underscore em vez de slug; arquivo existe → slug `q3-latency-numbers-2026-05-18` | Corrigir para `[[q3-latency-numbers-2026-05-18]]` |
| 11 | `[[project_qap_pillars_strategic_decision]]` | `project_d43_q4_gate_phase2_open.md`, `project_pricing_prerequisites_2026_05_18.md`, `project_q3_latency_numbers_2026_05_18.md` | Underscore em vez de slug; arquivo existe → slug `qap-pillars-strategic-decision` | Corrigir para `[[qap-pillars-strategic-decision]]` |
| 12 | `[[wave-a-deploy-rollback-2026-05-19-pattern]]` | `feedback_vps_build_broken_runs_on_stale_dist.md` | Entry sobre rollback da Wave A nunca criada; evento real mas não documentado como memory entry | Criar `project_wave_a_deploy_rollback_2026_05_19.md` ou remover ref |
| 13 | `[[writer-agent-no-bash-cant-commit]]` | `feedback_aad_bug_caught_by_integration_test.md`, `feedback_executor_high_vs_executor_tradeoff.md`, `feedback_mandatory_closure_steps_pattern.md` | Arquivo real é `feedback_writer_agent_no_bash_tool.md` → slug `writer-agent-no-bash-tool` | Corrigir para `[[writer-agent-no-bash-tool]]` |

### Padrão dominante

**8 de 13 broken links** (itens 3, 4, 7, 8, 9, 10, 11) são `[[feedback_foo_bar]]` / `[[project_foo_bar]]` — nome de arquivo com underscore em vez de slug kebab-case. Os arquivos existem; é só convenção de slug errada nos arquivos fonte. Podem ser corrigidos em batch.

---

## Orphan Files

Arquivos `.md` presentes no diretório mas **não referenciados** em MEMORY.md (sem entry na tabela principal).

| # | Arquivo | Conteúdo | Fix sugerido |
|---|---|---|---|
| 1 | `feedback_user_accepts_gemini_key_risk.md` | Decisão de Toto de não rotacionar GEMINI_API_KEY após colagem no chat (2026-05-18); aceita o risco | Adicionar entry em MEMORY.md (entry existe no arquivo mas falta na tabela) |
| 2 | `project_g4_wave_a_results_2026_05_19.md` | Resultados da ablation G4 Wave A — A8 active=0.5702 (+63.5% vs G3 baseline); D48 DEFENSÁVEL | Adicionar entry em MEMORY.md — G4 é referenciado por G5/G6 mas não aparece no índice |

**Nota:** `project_g4_wave_a_results_2026_05_19.md` é referenciado via `[[g4-wave-a-results-2026-05-19]]` em arquivos individuais (e.g. `project_g5_wave_a_post_deploy_2026_05_19.md`), mas a entry não consta em MEMORY.md, o que dificulta navegação pelo contexto.

---

## Ações Recomendadas (priorizadas)

1. **Batch fix underscore→slug** (8 broken links, trivial): corrigir `[[feedback_X]]` / `[[project_X]]` → `[[X-kebab]]` nos arquivos fonte.
2. **Corrigir 2 slugs errados** (itens 2 e 13): `esm-static-imports-hoist-before-body` → `esm-static-import-hoisting-captures-env` e `writer-agent-no-bash-cant-commit` → `writer-agent-no-bash-tool`.
3. **Adicionar 2 orphans ao MEMORY.md** (itens 1 e 2): `feedback_user_accepts_gemini_key_risk` + `project_g4_wave_a_results_2026_05_19`.
4. **Criar entries ausentes** para slugs sem arquivo: `d46`, `g2`, `mercury-agent-vs-nox-mem`, `wave-a-deploy-rollback` — ou remover as refs se conteúdo não existe.

---

*Audit read-only — nenhum arquivo de memória foi modificado.*
