# D49 Phase 2 — Shadow Activation + Smoke Q105-Q110 vs Proximity Rerank

**Data:** 2026-05-20
**Branch:** `feat/d49-phase2-shadow-activation-2026-05-20`
**Spike origem:** PR #157 (`staged-1.7a/edits/temporal-retrieval.ts`)
**Pré-deploy:** PR #167 (deploy do módulo + opt-in via env)
**Gold set:** PR #168 (Q105-Q110, ranks baseline 5-13)
**Status:** R&D / shadow-only — zero mutação no ranking de produção

## TL;DR

1. **Shadow ATIVADO em prod** via systemd drop-in
   (`/etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf`).
   Service `nox-mem-api` rodando com `NOX_TEMPORAL_PATH=shadow`. Probes
   `temporal_path` aparecem em `journalctl -u nox-mem-api` (5 entries
   capturados durante o próprio smoke).

2. **Smoke Q105-Q110 (6 queries temporais) contra proximity rerank
   simulado:** Δ médio nDCG@10 = **+0.0000 (+0.0%)**. Nenhuma query
   melhorou rank. Razão estrutural: 5/6 das queries Q105-Q110 são
   **adverbial-only** (signal `quando ... foi feito` sem âncora ISO/mês),
   logo o detector marca `isTemporal=true` mas `anchor=null` → spike
   short-circuita pra no-op (delega pra E13, fora do escopo). Apenas
   Q109 tem âncora (`abril 2026` → 2026-04-15); mesmo assim, gold (rank 7)
   não vira porque competidores próximos também caem na gaussiana.

3. **Veredito:** spike rerank atual **NÃO basta pra mover Q105-Q110**.
   Phase 2 baseline (rodar 7d) ainda vale a pena pra coletar perfil
   estatístico em volume, MAS recomendação **antes do baseline** é
   tunar duas alavancas (boost proporcional ao gap + signal de "deploy
   verb" forçando anchor=now-N), porque o gold set atual já mostra que
   shadow vai logar mostly adverbial → top1DeltaDays sempre null.

4. **Scrape script entregue** (`scripts/scrape-temporal-shadow.sh`),
   testado local contra log real (5 entries, aggregator funcionando).
   Cron sugerido `0 0 * * *` — NÃO instalado.

## Parte A — Shadow activation

### Drop-in

```
/etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf
```

```ini
[Service]
Environment="NOX_TEMPORAL_PATH=shadow"
```

### Sequência

```bash
ssh root@187.77.234.79 \
  'mkdir -p /etc/systemd/system/nox-mem-api.service.d/ && \
   cat > /etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf <<EOF
[Service]
Environment="NOX_TEMPORAL_PATH=shadow"
EOF
   systemctl daemon-reload && \
   systemctl restart nox-mem-api && \
   sleep 5 && \
   systemctl is-active nox-mem-api'
# → active
```

Validação env:

```
$ systemctl show nox-mem-api -p Environment | grep -i temporal
Environment=NOX_TEMPORAL_PATH=shadow
```

### Sample log entries (capturados durante smoke Q105-Q110)

```
May 20 13:00:54 ... {"type":"temporal_path","query_hash":"5f78ea7d013c","ts":1779292854542,
  "applied":false,"isTemporal":true,"signalSource":"adverbial","anchorIso":null,
  "kReranked":0,"top1DeltaDays":null,"rangeStart":null,"rangeEnd":null}

May 20 13:00:56 ... {"type":"temporal_path","query_hash":"e9e1063b8f71",...
  "signalSource":"adverbial","anchorIso":null,"kReranked":0,...}

May 20 13:01:07 ... {"type":"temporal_path","query_hash":"b43c3ca757ff","ts":1779292867249,
  "applied":false,"isTemporal":true,"signalSource":"month_year",
  "anchorIso":"2026-04-15","kReranked":20,"top1DeltaDays":19,
  "rangeStart":"2026-04-01","rangeEnd":"2026-04-30"}
```

`applied:false` em todos confirma shadow puro — nenhum score foi mutado
em prod. Q109 (month_year) é a única do batch onde `kReranked=20` e
`top1DeltaDays` populated (=19 dias entre top1 e anchor).

### Rollback emergencial

```bash
ssh root@187.77.234.79 \
  'rm /etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf && \
   systemctl daemon-reload && \
   systemctl restart nox-mem-api'
```

### Aggregator scrape

Entregue como `scripts/scrape-temporal-shadow.sh` (modo cron daily 00:00
UTC sugerido, NÃO instalado). Testado local contra log de 20 min com 5
entries, aggregator emite distribuição de signalSource correta. Output
canônico em `docs/research/temporal-shadow-baselines/<date>-summary.json`.

## Parte B — Smoke Q105-Q110 vs Proximity Rerank

### Setup

- API: `POST http://127.0.0.1:18802/api/search` (SSH-tunneled) `limit=20`
- Modo simulado: port direto de `detectTemporal()` + `proximityDelta()` +
  rerank rank=20 (script em `/tmp/d49-smoke/rerank.mjs` — não comitado).
- Parâmetros: `sigmaDays=30`, `kRerank=20`, mode=active (`score + delta*10`).
- Fonte `source_date`: prefer `r.source_date`, fallback regex
  `\b\d{4}-\d{2}-\d{2}\b` em `chunk_text` (~50% chunks tem `source_date`
  null porque vem de blocos legacy sem frontmatter).
- nDCG@10: relevance binário (1 se gold no topo-K, 0 caso contrário).
- `nowMs` = 2026-05-20.

### Resultados

| Query | Signal | Anchor | Baseline rank | Rerank rank | Baseline nDCG@10 | Rerank nDCG@10 | Δ |
|-------|--------|--------|---------------|-------------|------------------|----------------|---|
| Q105 | adverbial | none | 6 | 6 | 0.3562 | 0.3562 | 0.0000 |
| Q106 | adverbial | none | 5 | 5 | 0.3869 | 0.3869 | 0.0000 |
| Q107 | none ⚠️ | none | 5 | 5 | 0.3869 | 0.3869 | 0.0000 |
| Q108 | adverbial | none | 13 | 13 | 0.0000 | 0.0000 | 0.0000 |
| Q109 | month_year | 2026-04-15 | 7 | 7 | 0.3333 | 0.3333 | 0.0000 |
| Q110 | adverbial | none | 8 | 8 | 0.3155 | 0.3155 | 0.0000 |

**nDCG@10 mean baseline:** 0.2965
**nDCG@10 mean rerank:** 0.2965
**Δ médio:** **0.0000 (+0.0%)**

Ranks improved: 0 / worsened: 0 / unchanged: 6.

### Análise por query

#### Q105 — "quando o arXiv preprint do paper nox-mem foi planejado publicar"

- Detector classifica `adverbial` (matches `quando`) sem anchor.
- Gold `216210` (rank 6, score 15.15) tem texto `**2026-05-05** — [milestone] Paper materialmente submit-ready`.
- Rerank short-circuita: `intent.anchor=null` → `cfg.mode==="active"` mas
  guard `!intent.anchor` retorna sem mutar.

#### Q106 — "quando o OpenClaw upgrade zero-downtime ... foi feito"

- `adverbial` (`quando` + `feito`), sem anchor.
- Gold `216200` rank 5 (score 16.13). Curiosamente tem `source_date`
  populado (`2026-04-30`), mas spike sem anchor não computa proximity.

#### Q107 — "data em que a KG migration Ollama para Gemini foi completada"

- **Detector classifica NÃO temporal (`signal=null`)**. Razão: regex
  `(?:^|\s)(quando|que\s+dia|que\s+data|qual\s+(?:data|dia)|em\s+que\s+(?:dia|data))(?=\s|[.,?!]|$)`
  não tem padrão pra `data em que ... foi` (anchor verbal). Achado
  diagnóstico — falta de cobertura no detector.
- Gold `216195` rank 5, `source_date="2026-04-11"`.

#### Q108 — "em que data o corpus do nox-mem triplicou ..."

- Match `em que (dia|data)` → `adverbial`. Sem anchor.
- Gold `216198` rank 13 (fora do top-10 → nDCG@10=0).
- Mesmo se tivesse anchor inferido (now-N), proximity boost local
  precisaria de delta > +0.5 pra subir 3 posições (gap top10 → 13 é
  largo).

#### Q109 — "quando o active-memory foi migrado para Gemini flash lite **em abril 2026**"

- **ÚNICA query com anchor real:** `month_year` → 2026-04-15.
- Gold `216192` rank 7 (`source_date=2026-04-21`, Δ=6d, delta=0.4917).
- Rerank aplicado top-20: gold sobe de 16.04 → 20.96. **Mas:**
  - Top1 baseline (`212260`, 21.49) tem `source_date=2026-05-04` (Δ=19d,
    delta=0.4134) — sobe pra 25.99.
  - Top2 (`117603`, 16.13) é `2026-04-20` (Δ=5d, delta=0.4944) — sobe pra 21.07.
  - Top3 (`117355`, 16.39) é `2026-04-01` (Δ=14d, delta=0.4449) — sobe pra 20.84.
- Gold sobe absolute MAS sobem juntos. Ordem relativa praticamente
  preservada porque a gaussiana é "branda" no range 1-30d → todo mundo
  ganha boost similar.
- **Falha do mesmo formato vista no smoke 2026-05-20 anterior (Q71):
  boost absoluto + 10 ≪ score base original quando há cluster temporal
  denso.**

#### Q110 — "quando a search quality e core memory quality foram melhoradas"

- `adverbial` (`quando` + `foram melhoradas`? não — só `quando`). Sem anchor.
- Gold `216193` rank 8. Mesmo cenário Q105/Q106.

### Observações estruturais

1. **5/6 queries Q105-Q110 são adverbial-only.** Distribuição esperada
   pra "quando X foi Y" portuguesa (gold cu interado priorizou perguntas
   naturais sem date). O spike atual delega adverbial pra E13 — logo
   o gold set Q105-Q110 não exerce o caminho ativo do rerank.

2. **Q107 expõe gap do detector** — `data em que ... foi` não é matched.
   Lista de patterns ADVERBIAL_PATTERNS precisa receber alternativa
   `(?:em\s+que\s+(?:dia|data|momento))` (já tem `em\s+que\s+(?:dia|data)`
   mas só matcha se palavra exata cravada — review regex needed).

3. **Q109 expõe limite do design atual:** mesmo com anchor explícito,
   `delta * 10` adicionado a scores RRF-fused (16-21 range) gera boost
   `~+5` que é diluído porque competidores próximos no tempo também
   recebem boost similar. O smoke 2026-05-20 anterior já tinha
   diagnosticado isso pra Q71 (mesma família de problema). PR #157
   discussion notes mencionam "boost proporcional ao gap" como fix
   candidato — Q109 confirma a necessidade.

4. **`source_date` cobertura:** ~60% dos chunks Q105-Q110 retornam
   source_date populado. Os legacy (sem frontmatter) ficam null e o
   fallback regex `chunk_text` resgata maioria. Não é blocker pra
   rerank, mas é dado importante pra Phase 2 baseline.

## Veredito

**Δ médio = +0.0000 → bem abaixo do +5% threshold do briefing.**

**Recomendação: TUNAR antes de rodar Phase 2 baseline 7d.**

Justificativa: rodar 7d de shadow sem mudanças vai produzir log dominado
por `signalSource=adverbial, anchor=null, kReranked=0`. Dados de baseline
ainda úteis (volume de temporal queries, distribuição signal source),
mas o telemetro chave (`top1DeltaDays`, `kReranked`) ficará vazio em
~80%+ dos casos — baseline não informa o que precisa ser informado.

**Sequência sugerida (em ordem):**

1. **Patch detector — Q107 gap** (1h): adicionar pattern `data\s+em\s+que`
   + `momento\s+em\s+que` na lista ADVERBIAL_PATTERNS. Validar com
   smoke re-run Q107.

2. **Patch detector — adverbial-to-anchor fallback** (4h): quando signal
   é adverbial + query menciona verbo de evento (`deployado`, `feito`,
   `completada`, `triplicou`, `migrado`, `melhoradas`), atribuir
   `anchor=now-90d` como heurística "evento provavelmente recente". É
   chute, mas exerce o rerank path pra dar dado mensurável.

3. **Patch rerank — boost proporcional ao gap** (4h):
   `score_new = score_old + delta * max(0, top1_score - own_score) * factor`
   com factor=2.0 inicial. Garante que candidatos com boost máximo (delta=0.5)
   na posição N podem virar top quando o gap é pequeno.

4. **Re-rodar smoke Q105-Q110** após patches (1h) — sanity check
   antes de Phase 2 baseline.

5. **Phase 2 baseline 7d** ATIVAR cron daily após smoke confirmar lift
   > +3% em pelo menos Q108 (rank 13 → ≤10) ou Q109 (rank 7 → ≤5).

**Drop-in atual pode ser removido OU mantido** — Toto decide. Manter
oferece volume de telemetria orgânica (queries reais do uso normal,
não só smoke) que ainda informa "qual % do tráfego é temporal?"
mesmo sem rerank ativo. Custo: ~30B/query no stderr da service.

## Artefatos

- Drop-in VPS: `/etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf`
- Scrape script: `scripts/scrape-temporal-shadow.sh` (executável)
- Baselines dir: `docs/research/temporal-shadow-baselines/` (vazia, populada pelo cron)
- Sim script local (não comitado): `/tmp/d49-smoke/rerank.mjs`
- Raw results: `/tmp/d49-smoke/results.json`
- Spike implementation: `staged-1.7a/edits/temporal-retrieval.ts`
- Smoke anterior (Q70/71/87/88): `docs/research/2026-05-20-temporal-smoke-test.md`
- Golden Q105-Q110: `eval/golden-queries.jsonl:61-66`

---

*Conduzido em ~40min wall-clock contra prod VPS. Shadow opt-in via
systemd drop-in (não immutable), zero risk de mutação de ranking. PT-BR
"você + 3ª pessoa" conforme CLAUDE.md hard rule.*
