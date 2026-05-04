# SESSION RESUME — Próxima sessão começa AQUI

> **Para Claude da próxima sessão:** Toto vai abrir nova session pra começar paper sprint. Este arquivo é o **único contexto necessário** pra começar trabalhar — não precisa ler HANDOFF gigante nem outros arquivos.

---

## 🎯 Decisão tomada (NÃO re-discutir)

- **Sistema técnico está em steady state** (Wave 1+2 done, R01a/b/c done, F15a/b ativos com cron Discord). NÃO há "fechar sistema" pendente.
- **Paper científico em PARALELO** (não sequencial) — começar AGORA, não esperar.
- **Divisão 80/20 paper/sistema** confirmada: 11h/sem paper + 1h/sem sistema (sanity check + activate gate 05-09).
- **Timeline 3 semanas** (W1-W3, 12h/sem cada = 2h/dia × 6 dias) — compressed do plan original 6 semanas.
- **Target outputs:** arXiv preprint + dev.to/Substack blog post + Hacker News submission. NÃO submeter top-tier conference.

---

## 📁 Stack do projeto paper (ler nessa ordem)

| Ordem | File | Por quê |
|---|---|---|
| 1 | `paper/publication/00-INDEX.md` | Mapa geral 8 docs + 6-week timeline → adjusted pra 3-week |
| 2 | `paper/publication/01-positioning-strategy.md` | 3 diferenciais a EXALTAR + 5 gaps a COBRIR + tom por channel |
| 3 | `paper/publication/02-related-work-notes.md` | 8 papers PRIMARY + 4 secondary + objection preempção |
| 4 | `paper/publication/03-experiments-needed.md` | 13 experiments com Python adapter outlines + 36h budget |
| 5 | `paper/publication/04-paper-arxiv-draft.md` | Skeleton 7 sections + appendices |
| 6 | `paper/publication/05-blog-post-draft.md` | Structure 2500w + 5 title variants + code snippets |
| 7 | `paper/publication/06-hn-submission.md` | 5 title variants + first comment template + objection responses |
| 8 | `paper/publication/07-publication-checklist.md` | P0/P1/P2/P3 + sprints + stop conditions |
| 9 | `paper/publication/08-launch-strategy.md` | Distribution strategy 5 weeks pós-publish |
| 10 | `paper/publication/09-storytelling-strategy.md` | ⭐ Hero narrative "The Pain Diary + Shadow Discipline" + sub-narratives + hooks por canal |

**Plus contexto sistema (consultar SE necessário):**
- `paper/paper-v2-draft-evidence.md` — draft v2 inicial com evidências quantitativas (preserve, será fonte pra `04-paper-arxiv-draft.md` polished)
- `docs/HANDOFF.md` — estado vivo do sistema técnico
- `docs/ROADMAP.md` — Phase Matrix + capacity

---

## 🚀 W1 Day 1 — começar AGORA quando session abrir

### Sanity check (3min)
```bash
ssh root@187.77.234.79 'curl -s http://127.0.0.1:18802/api/health | jq "{total: .chunks.total, embedded: .vectorCoverage.embedded}"'
ssh root@187.77.234.79 'tail -3 /var/log/nox-seh-report.log'
```
Esperado: 64.180+ chunks 100% embedded + cron SEH alerts=0.

### Stack a despachar AGORA (auto mode active)

**Spawn 4 agents paralelos via Task tool** (não sequencial):

1. **researcher / research-analyst** — task: validar BibTeX dos 8 papers PRIMARY do `02-related-work-notes.md` via Google Scholar. Output: `paper/publication/refs.bib` com entries corretos arXiv IDs + venues.

2. **python-pro** — task: criar adapter outline `paper/publication/baselines/bm25_baseline.py` (Pyserini implementation per spec em `03-experiments-needed.md` E1). NÃO rodar ainda — só código + docstring pronta pra Toto rodar manualmente após validar Pyserini install.

3. **python-pro #2** — task paralelo: criar adapter `paper/publication/baselines/bge_baseline.py` (BGE-M3 per E2 spec). Mesma regra: código + docstring, não rodar.

4. **content-marketer** — task: A/B test 5 HN title variants do `06-hn-submission.md`. Output: ranking refinado por predicted CTR + 2-3 variants novos baseado em HN top posts last 30d (research via WebFetch).

### W1 Day 2-7 work breakdown

| Dia | Toto (2h) | Background (overnight VPS cron + Anthropic Routines) |
|---|---|---|
| Tue | Review related work agents output + decidir HN title finalist | VPS cron noturno: install Pyserini + BGE-M3 deps |
| Wed | Hands-on validar BM25 adapter rodando em corpus nox-mem real | Continue setup overnight |
| Thu | Run BM25 baseline + BGE-M3 baseline 3-batch each | Logs em `/var/log/nox-paper-experiments.log` |
| Fri | Analyze results + start tabela paper §5.2 | DB snapshot + backup |
| Sat | Review week + ajustar W2 plan + 25min activate gate (05-09) | — |
| Sun | Buffer / overflow | — |

### Skills/plugins a usar máximo

**High ROI (use sempre):**
- `superpowers:dispatching-parallel-agents` — orchestration paralela 4 agents simultaneous
- `superpowers:writing-plans` — planning W1 detalhado
- `claude-mem` (mcp-search) — cross-session continuity entre 12h dias
- `WebSearch` + `WebFetch` — validar prior art real-time

**Medium ROI (use quando necessário):**
- `chrome-devtools-mcp` — capturar screenshots reais blog post (W3)
- `d3js-visualization` skill — charts paper §5 (W3)
- `slides` skill — deck Twitter chart hero (W6)
- `context-mode` — reduzir context blowup em runs longos

**Skip (não relevante):**
- Vercel skills (não é Vercel project)
- Mobile/Android specific skills

### Routines/cron a configurar W1 Day 1

```bash
# VPS overnight runner — paper experiments batch
ssh root@187.77.234.79 'cat > /root/.openclaw/scripts/paper-experiments-overnight.sh <<BASH
#!/bin/bash
set -euo pipefail
LOG="/var/log/nox-paper-experiments.log"
echo "[\$(date -Iseconds)] paper experiments overnight start" >> "\$LOG"

# Setup Python venv pra baselines (idempotent)
cd /root/paper-experiments 2>/dev/null || mkdir -p /root/paper-experiments && cd /root/paper-experiments
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q pyserini==0.36.0 FlagEmbedding==1.2.10 beir==2.0.0 datasets 2>>"\$LOG"

# TODO Day 2: invoke baseline scripts here após Toto validar
echo "[\$(date -Iseconds)] paper experiments overnight done" >> "\$LOG"
BASH
chmod +x /root/.openclaw/scripts/paper-experiments-overnight.sh

# Cron 02:00 BRT daily (05:00 UTC)
(crontab -l; echo "0 5 * * * /root/.openclaw/scripts/paper-experiments-overnight.sh") | crontab -'
```

---

## 🛡️ Sistema (trilho 2, 1h/sem)

### Sanity check daily (opcional, 3min)
Mesmo SSH command acima.

### Activate gate 2026-05-09 sábado (obrigatório, 25min)
1. Verificar GitHub Issue gerada pela routine `trig_012nuCN14VwcxGLq8ERaLPCK`
2. Aplicar 1-2 env edits + restart se ACTIVATE
3. Validate pós-activate
4. Re-baseline R01c hybrid pra confirmar não-regression

Checklist completo em `docs/HANDOFF.md` section "PARA PRÓXIMA SESSÃO".

### Cron SEH daily Discord
Já automático. Nenhuma ação se sistema saudável.

### Reagir a incidents
Se cron alertar ALERT severity OR sanity falhar → pause paper, fix sistema.

---

## 🎯 3 diferenciais finais (memorize, repete em cada doc)

1. **Pain-weighted salience** — primeiro RAG documentado a modelar incident severity como retrieval signal (`recency × pain × importance`)
2. **Shadow-mode discipline** — primeira memory system com regra arquitetural codificada de ≥7d shadow + automation enforcement
3. **Shared-canonical multi-agent** — diferente de MemGPT/mem0 isolation; cross-agent intelligence sem federation overhead

## ⚠️ 5 gaps a cobrir (P0 obrigatório pre-arXiv submit)

1. Single corpus → BEIR-COVID + StackExchange 10K
2. Internal-curator bias → external 10 queries (BEIR cobre)
3. Sem strong baselines → BM25 (Pyserini) + BGE-M3 + E5-mistral
4. Sem ablation → 4 ablations (FTS-only / sem-RRF / sem-salience / sem-section_boost)
5. Voyage cut → BGE-M3 cobre como proxy alt-provider

---

## 📅 Calendar key dates

| Date | Event | Action |
|---|---|---|
| **2026-05-04 (W1 Mon)** | W1 Sprint start | Spawn 4 agents paralelos via Task |
| **2026-05-09 (W1 Sat)** | Activate gate routine fires | 25min checklist (interromper paper) |
| **2026-05-11 (W2 Mon)** | W2 Sprint start | Experiments primary execution |
| **2026-05-18 (W3 Mon)** | W3 Sprint start | Writing intensive + critic review |
| **2026-05-19 (W3 Tue 09:00 ET)** | Target: arXiv submit | LaTeX final + arXiv form |
| **2026-05-20 (W3 Wed)** | Target: blog publish dev.to + Substack | Cross-post + Twitter thread |
| **2026-05-21 (W3 Thu 09:00 ET)** | Target: HN submit | First comment within 5min |
| **2026-05-26** | P01 NOX-Supermem elegível (E01 estável 30d) | Soft tease no blog post + LinkedIn |
| **2026-06-04 (Day +14)** | Mid-launch checkpoint | Stats dump + pivot decision |
| **2026-06-18 (Day +30)** | Post-mortem | `09-launch-postmortem.md` |

---

## 💬 HARD RULE PT-BR (reforço escalated 2×)

**NUNCA** usar "tu/te/ti/teu/tua/vc". **SEMPRE** "você + 3ª pessoa". São Paulo register. Cross-project.

Pre-send mental grep mandatório toda resposta Portuguese.

Detalhes: `~/.claude/CLAUDE.md` linha 10 + `memory/feedback_use_voce_not_tu_in_portuguese.md`.

---

## ✅ Quando começar

Próxima sessão Claude:
1. Ler **APENAS este arquivo** + `paper/publication/00-INDEX.md` (5min total)
2. Spawn 4 agents paralelos descritos acima (Task tool com `run_in_background: true`)
3. Configurar cron VPS overnight runner
4. Toto faz seu trabalho (review outputs quando ready), agents trabalham async
5. End of W1 Day 1: tabela inicial baselines + bibtex completo + HN title finalist

**Auto mode está active.** Execute imediatamente, não pergunte clarifying questions desnecessárias. Course corrections do Toto são normais.

Boa sorte. 🚀
