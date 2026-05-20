# source_type Backfill Path-Pattern Mapping (Task C)

> **Trigger:** G4 ablation A5 (source_type_boost only) = 0.4817 = A0 baseline (no boosts) → INERT confirmed.
> **Audit (2026-05-19):** 67,949 chunks (98.48%) com `source_type = NULL` em prod (68,995 total).

---

## Path patterns identificados (n=30 random sample + bucket SQL)

| Pattern | source_type proposto | Count est | % corpus | Rationale |
|---|---|---|---|---|
| `**/entities/**` | `entity` | ~749 | 1.09% | Entity files (compiled/frontmatter/timeline) — highest curation |
| `**/cache/ocr/**` | `ocr-cache` | thousands | ~10%? | OCR scan artifacts — low signal value, candidate pra excluir |
| `**/memory/mac-docs/**` | `personal-doc` | many | ~30%? | Faturamento, contratos, planilhas — high personal info value |
| `**/sessions/*` | `session` | many | ~5%? | Cipher/Atlas/Boris/etc session checkpoints |
| `**/shared/imports/Claude/skills/**` | `skill` | many | ~10%? | Claude Code skill definitions |
| `**/shared/imports/Claude/commands/**` | `command` | small | ~1%? | Slash command definitions |
| `**/memory/lessons/**` OR `*-lessons.md` | `lesson` | small | ~1%? | Retrospective lessons learned |
| `**/Claude/Projetos/**` | `project-doc` | 560 | 0.81% | Project planning docs |
| `**/shared/lex-biblioteca/**` | `legal-template` | unknown | ~1%? | Legal templates (disputes, contracts) |
| `*.md` catch-all | `note` | rest | residual | Generic markdown notes |

## Refined SQL mapping (proposta migration)

```sql
-- DRY RUN counts (rodar antes do UPDATE):
SELECT
  CASE
    WHEN source_file LIKE '%/entities/%' THEN 'entity'
    WHEN source_file LIKE '%/cache/ocr/%' THEN 'ocr-cache'
    WHEN source_file LIKE '%/sessions/%' THEN 'session'
    WHEN source_file LIKE '%/shared/imports/Claude/skills/%' THEN 'skill'
    WHEN source_file LIKE '%/shared/imports/Claude/commands/%' THEN 'command'
    WHEN source_file LIKE '%/shared/lex-biblioteca/%' THEN 'legal-template'
    WHEN source_file LIKE '%/Claude/Projetos/%' THEN 'project-doc'
    WHEN source_file LIKE '%/memory/mac-docs/%' THEN 'personal-doc'
    WHEN source_file LIKE '%/memory/lessons/%' OR source_file LIKE '%-lessons.md' THEN 'lesson'
    WHEN source_file LIKE '%.md' THEN 'note'
    WHEN source_type = 'external' THEN 'external'  -- preserve existing
    ELSE 'other'
  END AS proposed_source_type,
  COUNT(*) AS n
FROM chunks
WHERE source_type IS NULL OR source_type = ''
GROUP BY proposed_source_type
ORDER BY n DESC;
```

## Backfill via withOpAudit (PR `feat/source-type-backfill-2026-05-19`)

```typescript
// scripts/backfill-source-type.ts (new)
import { withOpAudit } from '../src/lib/op-audit.js';
import { getDb } from '../src/db.js';

const PATTERNS: Array<[RegExp, string]> = [
  [/\/entities\//, 'entity'],
  [/\/cache\/ocr\//, 'ocr-cache'],
  [/\/sessions\//, 'session'],
  [/\/shared\/imports\/Claude\/skills\//, 'skill'],
  [/\/shared\/imports\/Claude\/commands\//, 'command'],
  [/\/shared\/lex-biblioteca\//, 'legal-template'],
  [/\/Claude\/Projetos\//, 'project-doc'],
  [/\/memory\/mac-docs\//, 'personal-doc'],
  [/\/memory\/lessons\/|-lessons\.md$/, 'lesson'],
  [/\.md$/, 'note'],
];

function classifyPath(p: string): string {
  for (const [rx, t] of PATTERNS) if (rx.test(p)) return t;
  return 'other';
}

await withOpAudit('backfill-source-type', async (db) => {
  const stmt = db.prepare(`UPDATE chunks SET source_type = ? WHERE id = ? AND (source_type IS NULL OR source_type = '')`);
  const rows = db.prepare(`SELECT id, source_file FROM chunks WHERE source_type IS NULL OR source_type = ''`).all();
  for (const r of rows as Array<{ id: number; source_file: string }>) {
    stmt.run(classifyPath(r.source_file), r.id);
  }
  return { backfilled: rows.length };
});
```

## SOURCE_TYPE_BOOST update (pós-backfill)

Mapping atual em `staged-1.7a/edits/search.ts`:
```typescript
const SOURCE_TYPE_BOOST: Record<string, number> = {
  user_statement: 2.0,  // dead-by-corpus
  compiled: 1.5,        // dead-by-corpus
  timeline: 1.0,        // neutral
  external: 0.8,        // active penalty
};
```

Proposta pós-backfill (evidência-based — high-trust types up, noise types down):
```typescript
const SOURCE_TYPE_BOOST: Record<string, number> = {
  // High-trust (manually curated):
  entity: 1.5,
  lesson: 1.4,
  'legal-template': 1.3,
  'project-doc': 1.2,
  // Medium-trust:
  skill: 1.1,
  command: 1.1,
  note: 1.0,           // neutral baseline
  // Low-trust (noise):
  session: 0.9,        // session checkpoints rarely match queries
  'personal-doc': 0.95, // faturamento/relatórios — sometimes useful
  'ocr-cache': 0.7,    // OCR artifacts — high noise
  external: 0.8,       // web content slight penalty
};
```

## Validation (pós-backfill)

1. Re-run distribution audit — confirm source_type distribution matches expected counts
2. Re-run G5 ablation A5 — should now contribute ≥+0.03 nDCG@10 vs A0
3. Re-run A8 (full) with new SOURCE_TYPE_BOOST mapping — expect lift vs A8 G4 (0.5702)

## Cross-links

- [[g4-wave-a-results-2026-05-19]] — ablation matrix
- [[no-secrets-in-git]] — backfill script must NOT commit DB or tokens
- `docs/audits/2026-05-19-salience-distribution-audit.md` — companion audit (salience formula)
- `staged-1.7a/edits/search.ts:53-58` — SOURCE_TYPE_BOOST atual
