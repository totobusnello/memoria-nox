# Cost Projection — Pay-per-token alternatives (F13)

> **Última atualização:** 2026-05-01
> **Owner:** Toto
> **Cross-ref:** `docs/RUNBOOKS.md#rb-05-gemini-spof-mitigation-p0` (F12)
> **Status do roadmap item F13:** `📋 QUEUED` → este doc é o deliverable.

---

## Por que existe este doc

nox-mem hoje depende de duas fontes pagas:
- **Gemini Embedding API** (`gemini-embedding-001`, 3072d) — SPOF embedding
- **Gemini 2.5 Flash-lite** (KG extraction + reflect cache) — flash-lite default por regra crítica 4 do CLAUDE.md

Anthropic Max OAuth zero-cost cobre **agent inference** (Maestro/personas) — não cobre embeddings nem KG. Logo, mesmo com $0 em chat costs, há um custo baseline em embedding.

Quando ROI inverter (ex: Gemini sobe preço 3×, ou OpenAI baixa 50%), F13 documenta a decisão de switch.

---

## Custo atual baseline (Gemini, 2026-05-01)

### Embedding (`gemini-embedding-001`)

| Item | Volume | Custo |
|---|---|---|
| Pricing oficial | $0.000125 / 1k tokens (3072d output gratuito) | — |
| Chunks atuais (corpus completo) | 62.923 chunks | one-time done |
| Avg tokens/chunk | ~120 (estimate p/ markdown) | — |
| **Embedding cost histórico** | 62.923 × 120 = ~7.5M tokens | **~$0.94 cumulativo** |
| Mensal recorrente (novos chunks ~500/dia × 120 tok) | 1.8M tok/mês | **~$0.23/mês** |
| Reembed total (cenário switch) | 7.5M tokens | ~$0.94 one-shot |

### KG extraction (`gemini-2.5-flash-lite`)

| Item | Volume | Custo |
|---|---|---|
| Pricing input | $0.10 / 1M tokens | — |
| Pricing output | $0.40 / 1M tokens | — |
| Reflect cache (Fase 1.7a) | ~50 calls/dia × ~2k tok in / ~500 out | ~3M in + 750k out / mês |
| KG nightly extraction | ~200 calls/noite × ~3k in / ~1k out | ~18M in + 6M out / mês |
| **Mensal recorrente KG** | ~21M in + 6.75M out | **~$2.10 + $2.70 = $4.80/mês** |

### Total baseline mensal: ~$5/mês ✅

Praticamente nada hoje. **Não é hot path de custo.** F13 importa pra cenários de mudança, não otimização atual.

---

## Trigger pra revisitar cost projection

Quaisquer destes:

1. **Custo Gemini sobe 3× ou mais** (ex: API price hike, change tier obrigatório, Workspace SKU mudança)
2. **Volume cresce 10×** (ex: corpus vai de 62k → 620k chunks via SLAB import) → reembed baseline vai de $0.94 → $9.40 (ainda barato; gatilho mais real é mensal recorrente subir pra $50+/mês)
3. **Quota free tier exhaurido** (Gemini paid já configurado mas se tier free cair: hoje grátis em flash-lite, outros tiers podem ficar sem free)
4. **Modelo deprecated** (forced migration, ex: `gemini-2.0-flash` shutdown 2026-06-01 obriga decision)
5. **Anthropic Max OAuth perde zero-cost** (Anthropic muda termos) → reavaliar custo total stack
6. **F12 RB-05 trigger** (outage Gemini >2h ou key issue) → switch emergencial pode virar permanente

---

## Alternativas (mantidas warm como F12 backup)

### Comparativo quick-ref

| Provider | Modelo embedding | Dim | $/1M tok | Dim match? | Switch effort |
|---|---|---|---|---|---|
| **Gemini** (atual) | `gemini-embedding-001` | 3072 | $0.125 | — | — |
| **OpenAI** | `text-embedding-3-large` | 3072 | $0.13 | ✅ exato (vec_chunks reusable) | 1h env switch + 0h reembed (vetores reusáveis em metric similar) |
| **OpenAI** | `text-embedding-3-small` | 1536 | $0.02 | ❌ (precisa vec_chunks_small) | 2-3h: tabela nova + reembed batch ~21h |
| **Voyage AI** | `voyage-3` | 1024 | $0.06 | ❌ (precisa vec_chunks_voyage) | 2-3h: tabela nova + reembed batch ~21h |
| **Voyage AI** | `voyage-3-large` | 2048 | $0.18 | ❌ (precisa vec_chunks_voyage_large) | 2-3h: tabela nova + reembed batch ~21h |
| **Cohere** | `embed-v3.0` | 1024 | $0.10 | ❌ | 2-3h |
| **Self-hosted** | `mxbai-embed-large-v1` (local llama-server) | 1024 | $0 (CPU) | ❌ | 4-6h: infra setup + slow inference |

### Recomendação F13: priorizar OpenAI text-embedding-3-large pra emergency switch

**Razões:**
1. Match dimensional exato 3072d → `vec_chunks` reusável sem migração
2. Custo similar ($0.13 vs $0.125) → não muda budget
3. SDK estável + status historicamente bom
4. Chave OpenAI já é familiar (provável Toto já tem)

**Backup secundário: Voyage AI voyage-3** (custo 50% menor, mas dim mismatch obriga migração).

### Self-hosted é tentação cara — NÃO É RECOMENDADO

Mesmo com custo $0/mês, self-hosting (mxbai/bge-large/etc) implica:
- 2-3GB RAM permanentemente reservados na VPS Hostinger KVM 4 (compete com OpenClaw + nox-mem-api + sessions)
- Latência embedding 1-3s vs 100ms cloud (4× pior em search recall lookups warm-up)
- Manutenção: upgrades modelo + OOM handling + rebuild quando llama.cpp atualiza
- Quality gap real: Voyage/OpenAI/Gemini hoje >> mxbai em benchmarks MTEB

Stack lean violation regra DECISIONS §3 — só revisitar se Gemini+OpenAI+Voyage TODOS quebrarem simultaneamente.

---

## Cost projection cenários (12 meses)

Assumindo crescimento corpus orgânico 2× (62k → 124k chunks):

### Cenário A — manter Gemini (status quo)

```
Embedding mensal:  ~$0.50 (2× novos chunks/mês)
KG mensal:         ~$10 (2× volume)
Total/ano:         ~$126
```

### Cenário B — switch OpenAI embedding-3-large (mantém KG Gemini)

```
Embedding switch one-shot reembed:  ~$1 (124k × 120 tok × $0.13/1M)
Embedding mensal pós-switch:        ~$0.52
KG mensal (mantém Gemini):          ~$10
Total/ano:                          ~$127
```

Diferença irrelevante. Switch só faz sentido por motivos de availability/SPOF, não custo.

### Cenário C — switch full OpenAI (embedding + LLM)

```
Embedding mensal:                   ~$0.52
KG mensal (gpt-4o-mini equivalent): ~$5 (mais barato que Gemini hoje)
Total/ano:                          ~$66
```

50% mais barato que Cenário A. **Trigger pra avaliar:** se Gemini quota free for abolido OU se gpt-5-nano lançar com pricing similar.

### Cenário D — Anthropic Max OAuth também perde zero-cost

Hoje agentes (Maestro/personas) rodam $0 via Anthropic Max OAuth. Se isso quebrar:

```
Tokens/dia agentes (estimate):       ~5M in + 1.5M out
Custo Sonnet 4.6 (assume):           $3/1M in + $15/1M out
Daily:                               $15 + $22.50 = ~$37.50/dia
Monthly:                             ~$1,125 (mil cento e vinte e cinco dólares/mês)
```

**Single-handedly justifies pivot** se Anthropic mudar termos. Trigger documentado em `feedback_openclaw_max_oauth_zero_cost.md` (memory).

---

## Plano de switch emergencial (executável em 1h durante incident)

Pré-requisitos (preparados ANTES, não improvisado):
- [ ] OPENAI_API_KEY cadastrada em `/root/.openclaw/.env` (commented out até ativar)
- [ ] `src/embedding.ts` tem switch `NOX_EMBEDDING_PROVIDER=gemini|openai|voyage` (necessita feature flag — F13b deliverable)
- [ ] vec_chunks reusável (3072d match) — confirmado para OpenAI text-embedding-3-large

Em incident (1h total):
```bash
# 1. Activate OPENAI_API_KEY (uncomment .env)
ssh root@100.87.8.44 'sed -i "s/^# OPENAI_API_KEY=/OPENAI_API_KEY=/" /root/.openclaw/.env'

# 2. Switch provider
ssh root@100.87.8.44 'sed -i "s/^NOX_EMBEDDING_PROVIDER=gemini/NOX_EMBEDDING_PROVIDER=openai/" /root/.openclaw/.env'

# 3. Restart services
ssh root@100.87.8.44 'systemctl restart nox-mem-api nox-mem-watcher'

# 4. Smoke test embedding
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  curl -s https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"input\":\"healthcheck\",\"model\":\"text-embedding-3-large\"}" | jq ".data[0].embedding | length"'
# Esperado: 3072

# 5. Search smoke test
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  nox-mem search "nox-mem sistema memoria" --hybrid 2>&1 | head -5'
```

**Caveat:** vetores Gemini-existing têm distribuição diferente de OpenAI-new — recall pode degradar 5-15% até reembed completo. Aceitar 7-14d de degradação ou forçar reembed batch overnight (~21h tmux).

---

## Gatilho de monitoramento

```bash
# Cron mensal: report custo Gemini real do mês anterior
# Output: /var/log/nox-mem-cost-monthly.log
0 9 1 * * /root/.openclaw/scripts/cost-projection-monthly.sh
```

Script `cost-projection-monthly.sh` (criar como F13c follow-up):
- Pull billing API Gemini (custo real mês passado)
- Comparar com baseline previsto deste doc (Cenário A)
- Discord alert se variação >50%
- Output JSON com previsão próximos 3 meses linear

---

## Cross-reference

| Item | Onde |
|---|---|
| F12 SPOF mitigation | `docs/RUNBOOKS.md#rb-05-gemini-spof-mitigation-p0` |
| Modelo Gemini default flash-lite | `CLAUDE.md` regra 4 |
| Anthropic Max OAuth zero-cost | `docs/DECISIONS.md` §3 OpenClaw |
| Self-hosted llama violou stack lean | `docs/DECISIONS.md` §2 Q5 reranker reasoning |
| Roadmap F13 | `docs/ROADMAP.md` Foundation table |
