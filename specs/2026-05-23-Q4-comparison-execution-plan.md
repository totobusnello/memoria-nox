# Q4 COMPARISON Execution Plan — nox-mem vs 5 competidores

**ID:** Q4-EXEC
**Status:** READY-TO-EXECUTE (weekend sprint Sat 2026-05-24 / Sun 2026-05-25)
**Owner:** Toto (kick off + narrative); agent (setup + execution)
**Data:** 2026-05-23 (overnight prep) → 2026-05-25 (execution)
**Bloqueia:** GTM Phase 2 launch (gate D43 closed when this lands)
**Cross-link:** `docs/ROADMAP.md` §7 GTM Phase 2, `docs/DECISIONS.md` D43, `docs/COMPARISON.md` (template populated, needs final numbers)

---

## TL;DR

Single weekend sprint pra fechar Q4 gate. Setup overnight Sex 05-23 via agent; execution Sat 05-24; narrative polish + COMPARISON.md final Sun 05-25.

**Target deliverable:** `docs/COMPARISON.md` cravado com:
- Tabela win/loss vs 5 competidores em LongMemEval n=100 + LoCoMo
- Methodology page com setup reproduzível
- Per-category breakdown (single-hop, multi-hop, temporal, adversarial, open-domain)
- Latency tabela p50/p95/p99 cross-system
- Cost tabela (Gemini/OpenAI calls per query)

**Gate D43 close condition:** nox-mem em top-3 em ≥2 dos 4 métricas chave (nDCG@10, R@10, MRR, latency). Atendido → GTM Phase 2 unblocked.

---

## 1. Competitors (5)

Versões pinadas pra reprodutibilidade. Update before run if newer minor releases land.

| System | Stars | Repo | Install | Version pinned | Notas |
|---|---|---|---|---|---|
| **Mem0** | 26k+ | `mem0ai/mem0` | `pip install mem0ai==0.1.x` | Latest stable | Default config: OpenAI embeddings + Chroma vector store |
| **Zep** | 1.8k+ | `getzep/zep` | Docker compose (zep + postgres) | v0.27+ | Local self-host mode |
| **Letta** (ex-MemGPT) | 14k+ | `letta-ai/letta` | `pip install letta` | Latest | Default: SQLite backend |
| **agentmemory** | 11k+ | `rohitg00/agentmemory` | iii-engine runtime | Latest | Stack-bridge mode |
| **EverMind-AI** | 5k+ | EverOS published bench | repo TBD | Latest commit | Benchmark publisher concorrente |

**Why these 5:** maiores stars + active commits + claims similares ao nox-mem. Mem0 + Letta dominam stars; Zep + agentmemory dominam features adjacent; EverMind-AI publica próprios benchmarks (direct comparison threat).

---

## 2. Eval setup padronizado

### Datasets

1. **LongMemEval n=100** — `eval-data/longmemeval-n100/` (already on VPS pré-Q2 done)
2. **LoCoMo full** — `eval-data/locomo/` (already on VPS pré-Q1 done)

### Metrics canonical

| Metric | Formula | Tooling |
|---|---|---|
| **nDCG@10** | gold relevance × discount | `eval/harness/ndcg.py` |
| **R@10** | gold in top-10 / total gold | Same |
| **MRR** | mean reciprocal rank of first relevant | Same |
| **p50/p95/p99 latency** | per-query wall clock | wrapper times each call |
| **Cost** | API calls × pricing | per-system log |

### Categories (LongMemEval)

- `single-hop` (single fact retrieval)
- `multi-hop` (chain of inference)
- `temporal` (date-anchored)
- `open-domain` (generic queries)
- `adversarial` (typos, ambiguity)
- `numeric` (counts, comparisons)

Per-category breakdown obligatory na tabela final.

---

## 3. Harness architecture

```
eval/q4-comparison/
├── runner.py              # Main dispatcher
├── adapters/
│   ├── nox_mem.py         # via HTTP /api/search
│   ├── mem0.py            # via Mem0 SDK
│   ├── zep.py             # via Zep SDK
│   ├── letta.py           # via Letta SDK
│   ├── agentmemory.py     # via iii API
│   └── evermind.py        # via repo CLI
├── compose/
│   └── docker-compose.yml # spin up self-hosted ones
├── output/
│   ├── nox_mem.json
│   ├── mem0.json
│   ├── zep.json
│   ├── letta.json
│   ├── agentmemory.json
│   └── evermind.json
└── aggregate.py           # Cross-system table generator
```

**Adapter contract:**
```python
def search(query: str, k: int = 10) -> list[dict]:
    """
    Returns ranked chunks/docs.
    Each item: {id, score, text, source}
    Latency measured externally (around call).
    """
```

---

## 4. Reproducibility

### `docs/Q4-COMPARISON-METHODOLOGY.md` (new file, created Sun 05-25)

Deve documentar:
- Hardware: VPS spec (Hostinger 8 cores 16GB RAM)
- Network: localhost between systems (no internet calls except embeddings APIs)
- Embeddings provider: Gemini 3072d for nox-mem; each competitor's default for theirs (fair comparison = their native config)
- Random seed: 42 (LongMemEval shuffle)
- Eval set version: `commit_hash_at_time_of_run`
- Per-system version: pinned versions table

### Smoke test pre-run

Each adapter must pass:
```python
result = adapter.search("test query", k=5)
assert len(result) >= 1
assert all('id' in r and 'score' in r for r in result)
```

If any adapter fails smoke → skip that competitor + document gap (e.g., "Zep self-host failed Docker setup on Ubuntu 22.04, comparison runs without Zep").

---

## 5. Methodology defensability

### Fair comparison principles (per published benchmark standards)

1. **No corpus contamination:** competitors get IDENTICAL chunk corpus that nox-mem uses (same `chunks.text`, ingested via each system's native ingest API)
2. **Same eval set:** identical queries + identical gold sets
3. **Each system uses native defaults** — não tunamos os concorrentes pra perder. Se default config é o publishable, é o que publica.
4. **K cutoff fixed at 10:** standardize. Some systems default to 5 ou 20; force to 10.
5. **Same embeddings provider where possible** — Gemini for nox-mem. Outros usam defaults. Pode-se rodar uma variação "all Gemini" como side experiment.

### Anti-cherry-picking

- **All 6 categories reported** — não omitir categoria onde nox-mem perde
- **Both datasets (LongMemEval + LoCoMo)** — não esconder se um nos beneficia
- **Per-system per-category** transparency na tabela
- Worst-case latency reportada (não só p50)

### Pre-registration

Methodology cravada ANTES do run (this spec). Output só atualiza tabelas, não muda methodology retroativo. Honesty wins.

---

## 6. Execution schedule

### Sex 2026-05-23 noite (agent overnight)

| Janela | Item | Quem |
|---|---|---|
| 21h00-22h00 | Agent spawn (executor-high + worktree) | I trigger |
| 22h00-04h00 | Agent installs 5 competitors via Docker compose / pip / repo clones | Background |
| 04h00-06h00 | Agent runs smoke test per adapter, documents gaps | Background |
| 06h00 Sat | Agent opens PR `feat/q4-comparison-setup` with: adapters scaffolded, docker-compose ready, smoke results documented | Background |

### Sat 2026-05-24 (Toto wakes ~9h)

| Janela | Item | Quem |
|---|---|---|
| 09h00 | Review PR, hit `npm run q4:execute` | Toto (~30min) |
| 09h30-14h00 | Q4 execution (~4-5h compute, 6 systems × 2 datasets × n=100) | Background runner |
| 14h00-16h00 | Aggregate.py runs, generates cross-system tables | Background |
| 16h00-18h00 | Toto reviews tables, flags anomalies, narrative polish | Toto (~2h) |
| 18h00-22h00 | L4 first cron fire (Sun 23h UTC = 20h BRT Sat → 17h BRT Sat); watch journalctl | Passive |

### Sun 2026-05-25

| Janela | Item | Quem |
|---|---|---|
| 09h00 | L4 watchpoint query — `extraction_method` distribution post-cron | Toto + me |
| 10h00-14h00 | `docs/COMPARISON.md` final narrative, win/loss claims, per-category breakdown | Toto + me |
| 14h00-16h00 | `docs/Q4-COMPARISON-METHODOLOGY.md` writeup | Toto + me |
| 16h00-18h00 | README excerpts pulled from comparison, paper §6 numbers updated | Me |
| 18h00 | Q4 PR opens, gate D43 confirmed closed (or recommendation pra adjust narrative se gap) | — |

**Weekend outputs:**
- `docs/COMPARISON.md` final cravado
- `docs/Q4-COMPARISON-METHODOLOGY.md` writeup
- Q4 PR merged to main
- README hero excerpts updated
- Paper §6 numbers ready for arXiv submit week 2

---

## 7. Risk mitigation

| Risk | Probabilidade | Impact | Mitigação |
|---|---|---|---|
| Competitor install fails | Médio | Low (skip + document gap) | Pre-smoke test per adapter |
| nox-mem loses in 3+ categories | Médio | High (delays GTM) | Pre-eval ablation já mostrou +18.8% interno, mas externos podem diferir; honest reporting > cherry-pick |
| API quotas (OpenAI/Gemini) hit | Médio | Med (delay 4-6h) | Pre-allocate quotas; fallback to local models if needed |
| Q4 compute time > 8h | Médio | Low (just longer Sat) | Pre-allocate VPS slot Saturday morning |
| Eval set discovers nox-mem corpus contamination | Baixo | High (invalid comparison) | Diff `chunks.source_file` against eval gold sources pre-run |
| L4 first cron NULL again Sunday | Médio | Low (separate concern, doesn't block Q4) | Watchpoint Mon manhã, separate triage |

---

## 8. Stop conditions

Stop the Q4 run if ANY:
1. Adapter smoke fails for 3+ competitors → setup gap too wide, escalate
2. nox-mem performs worse than expected (-15pp vs G5 V3) → investigate corpus drift before publishing
3. Mid-run latency >30s/query consistently → infrastructure issue, retry Mon

Restart in Mon if stop hit.

---

## 9. Cross-references

- `docs/ROADMAP.md` §7 GTM Phase 2 + gate D43
- `docs/DECISIONS.md` D43 (threshold ≥+15% nDCG@10, atendido +18.8% interno)
- `docs/COMPARISON.md` template populated (PR #47) — needs final numbers
- `paper/paper-tecnico-nox-mem.md` §5 reframe (PR #156) — §6 published comparison section pending
- `[[overnight-2026-05-17-delivered]]` — Wave overnight context
- `[[evening-burst-2026-05-21-4prs-f10-deployed]]` — current state

---

## 10. Próximos passos pós-Q4

Assuming D43 confirmed (gate closes):

| Item | ETA | Trigger |
|---|---|---|
| Paper §6 final touches com Q4 numbers | Mon 05-26 → Tue 05-27 | Q4 PR merged |
| arXiv submit prep | Wed 05-28 → Fri 05-30 | Paper §6 done |
| asciinema + F10 GIF | Sat 05-30 (~1h) | Standalone |
| Blog post draft | Sun 05-31 | Paper review done |
| arXiv submit | Tue 06-02 (morning ET) | Per D27 sequencing |
| HN + Twitter + Product Hunt LAUNCH | Wed 06-03 | arXiv live |

**Total time pessoal Toto:** ~10-15h distributed across 2 weeks (Sat 3h + Sun 5h + Mon-Fri light + Sat polish 2h + Sun 2h + Tue submit 1h + Wed launch 2h).
