# Audit — L4 `extraction_method` NULL across 21 518 relations

**Data:** 2026-05-21 (end of day)
**Severity:** INFORMATIONAL (não regressão; expectativa pré-primeiro-cron)
**Investigator:** descoberto durante PR #209 cleanup investigation
**Cross-link:** PR #195 (L4 hybrid_shadow merge), PR #209 (foundation duplicate, reverted), PR #210 (cleanup)

---

## Finding

Live production `nox-mem.db` reports:

| Coluna | Valor |
|---|---|
| `kg_relations` total rows | 21 518 |
| `kg_relations.extraction_method IS NOT NULL` | **0** |
| `kg_relations.relation_reason IS NOT NULL` | 21 518 |
| `MAX(kg_relations.created_at)` | **2026-05-16 10:33:01** |

A coluna `extraction_method` (adicionada por L4 spec §9 pra differential entre `regex_only` / `gemini_only` / `regex_primary_gemini_secondary` / `gemini_only_after_regex_zero`) está **totalmente NULL**.

## Context

### Schema da coluna está correto

```sql
CREATE TABLE kg_relations (
  id INTEGER PRIMARY KEY,
  source_entity_id INTEGER,
  relation_type TEXT,
  target_entity_id INTEGER,
  ...
  relation_reason TEXT,      -- ✅ populated (mentions/depends_on/...)
  extraction_method TEXT,    -- ❌ all NULL
  ...
  FOREIGN KEY (source_entity_id) REFERENCES kg_entities(id),
  FOREIGN KEY (target_entity_id) REFERENCES kg_entities(id)
);
```

Index existe: `CREATE INDEX idx_kg_relations_reason ON kg_relations(relation_reason)` — mas NÃO há index em `extraction_method` (não-blocker; column é NULL anyway).

### Pipeline de extraction está integrado em `kg-llm.ts`

```typescript
// staged-1.7a/edits/kg-llm.ts:27
import { regexExtract, isAmbiguous, type RegexExtractionResult }
  from "./regex-extract.js";

// :44 — default mode é hybrid_shadow
function resolveExtractMode(): KGExtractMode {
  const raw = process.env["NOX_KG_EXTRACT_MODE"];
  if (!raw) return "hybrid_shadow"; // safe default
  ...
}
```

`regexExtract` é chamado em três call sites (linhas 375, 398, 440). Em `hybrid_shadow`, deveria escrever rows com `extraction_method` populado.

### Mas KG build roda só **aos domingos** (Phase 4 do nightly-maintenance.sh)

```bash
# /root/.openclaw/scripts/nightly-maintenance.sh:83-89
log "Phase 4: Sunday — kg-build + kg-merge"
node dist/index.js kg-build --limit 1000 >> "$LOG" 2>&1 || true
node dist/index.js kg-merge >> "$LOG" 2>&1 || true
...
node dist/index.js kg-stats > /root/.openclaw/workspace/memory/KG-SUMMARY.md
```

E o cron entry:
```cron
# ── Nightly maintenance (orchestra reindex/consolidate/kg/vectorize) ─
0 23 * * * /root/.openclaw/scripts/nightly-maintenance.sh >> /var/log/nox-maintenance.log 2>&1
```

Roda diariamente 23:00 UTC, mas Phase 4 (KG) só dispara `if [ DOW -eq 0 ]` (Sunday).

### Timeline reconcilia

- **2026-05-16 (Friday)** — última row em `kg_relations` (`MAX(created_at)`)
- **2026-05-17 (Saturday → Sunday morning UTC)** — domingo seguinte; deveria ter rodado KG build. Mas latest row 2026-05-16, então: ou Sunday 2026-05-17 não adicionou nada (sem chunks novos worth processing), ou rodou mas falhou silenciosamente
- **2026-05-18 (Monday)** — PR #195 mergeado em main; L4 foi incorporado ao código ativo
- **2026-05-21 (Thursday, today)** — descoberta NULL
- **2026-05-24 (next Sunday)** — primeira janela onde L4 + KG cron podem co-rodar e popular `extraction_method`

**Conclusão:** o NULL state NÃO é regressão — é o pre-first-cron state esperado de L4 desde sua merge. Toda row em `kg_relations` é pré-L4 (criada ≤ 2026-05-16). L4 nunca rodou em produção ainda.

## Daily distribution últimos 30 dias

```
2026-05-16 | 523
2026-05-07 | 16 331   ← massive backfill
2026-05-06 | 3 557
2026-05-04 | 1
2026-05-03 | 563
2026-04-23 | 27
```

KG extraction é episódica (não-contínua). Ondas grandes seguidas por dias sem novos rows. Faz sentido com regime "Sunday-only" da cron.

## Action items

1. **Watchpoint 2026-05-24 (Sunday) noite:**
   - Cron deveria disparar 23:00 UTC
   - Após Phase 4 terminar, query: `SELECT extraction_method, COUNT(*) FROM kg_relations WHERE created_at >= DATE('2026-05-24') GROUP BY extraction_method`
   - **Esperado:** rows com `extraction_method` populado em uma das 4 values do enum
   - **Anomalia:** rows novos com `extraction_method = NULL` → wire-up está broken

2. **Monitoring durante watchpoint:** Cipher (debug agent) pode validar via tail journalctl:
   ```bash
   journalctl --since "2026-05-24 23:00" | grep -E "regexExtract|extraction_method|kg-build"
   ```

3. **Findings adicionais úteis:**
   - `NOX_KG_EXTRACT_MODE` NÃO está set em prod env (`systemctl show nox-mem-api -p Environment` returns empty)
   - Default `hybrid_shadow` deveria aplicar, mas confirme via dry-run pre-cron
   - Memory entity files de Toto (`agents/nox.md`) NÃO usam wikilink convention `[[type/slug]]` — frontmatter é simples (`name`, `description`, `type`, `retention`). Isto reduz drasticamente o yield esperado de `extractEntityRefsRegex` em corpus real.

4. **Convention question pra Toto:** entity files podem ser refatoradas pra incluir wikilinks structurally (ex: `references: [[lessons/sqlite-text-affinity-coerces-int-back]]` ao invés de plain text), o que multiplicaria o yield do regex extractor 10×+. Mas isso é authoring convention change — fora do scope L4 sem decisão.

## Cross-references

- Spec: `specs/2026-05-18-L4-regex-first-extraction.md`
- Implementation: `staged-1.7a/edits/regex-extract.ts` (PR #195)
- Wire-up: `staged-1.7a/edits/kg-llm.ts:27-49` (mode resolution)
- Cron script: `/root/.openclaw/scripts/nightly-maintenance.sh` Phase 4
- Cleanup PR: #210 (removed `regex-link-extract.ts` duplicate from PR #209)
- Memory: `[[evening-burst-2026-05-21-4prs-f10-deployed]]` (today's PR set)
- Memory: `[[ship-ranking-changes-in-shadow-mode-first]]` (L4 deployment discipline)

## Not in scope

- Adicionar `extraction_method` validation trigger (insert-time enforce)
- Backfill retroativo de `extraction_method='gemini_extracted'` em rows antigas (spec §9 explicitly rejected)
- Modificar cron pra rodar KG build diariamente (volume não justifica)
- Adicionar entity types plurais ao DIR_PATTERN do `regex-extract.ts` (concern separado, levantado em PR #210)
