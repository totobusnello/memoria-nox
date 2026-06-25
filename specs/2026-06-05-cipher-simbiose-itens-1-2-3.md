# Cipher × nox-mem Simbiose — Itens 1+2+3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cipher vira 1º cliente interno dos primitivos avançados: escrita 3-seções via `ingest-entity` (item 1), política answer/search nos 6 SOULs (item 3), e `churn --changed-since` com detecção por embedding (item 2).

**Architecture:** Tudo vive no repo `totobusnello/nox-workspace` (working tree prod = `/root/.openclaw/workspace` na VPS). Item 1 = entity file + ingest (dados). Item 3 = bloco idêntico de ~14 linhas nos 6 SOULs + adendo de escrita no Cipher (docs). Item 2 = módulo novo `src/churn.ts` que usa KNN do sqlite-vec contra os embeddings JÁ EXISTENTES em `vec_chunks` ($0 Gemini no path principal) + comando CLI + cron mensal.

**Tech Stack:** TypeScript, better-sqlite3, sqlite-vec (3072d Gemini já materializados), commander, cron.

**Decisões cravadas (Toto, 2026-06-05):**
1. Entity única `memory/entities/process/doc-steward.md` com timeline crescente.
2. Churn por **embedding** (não slug/título).
3. Política answer/search **nos 6 agentes** (nox, atlas, boris, cipher, forge, lex) — bloco idêntico, compacto, cuidando de coerência e tamanho.

**Guardrails herdados:**
- Escrita de entity SEMPRE via `routeIngest()`/`ingest-entity`, NUNCA `ingestFile()` genérico (incident 2026-04-25).
- `answer` nunca é default — budget explícito (quota gemini-2.5-flash-lite).
- Nenhuma op destrutiva em chunks; churn é read-only + report.
- Branch de trabalho via clone fresco em `/tmp` (lição worktree sparse-checkout 2026-05-24), push → PR → merge → pull no working tree prod.
- `git branch --show-current` antes de qualquer commit no working tree prod.

---

## ✅ PINS RESOLVIDOS (Task 0 executada 2026-06-05 ~08:30 BRT)

1. **created_at:** TEXT `YYYY-MM-DD HH:MM:SS` (sem T/Z) → comparações usam `c.created_at >= datetime(?)` (normaliza input ISO).
2. **vec_chunks:** `vec0(embedding FLOAT[3072])` sem distance_metric → **L2**. Gemini-embedding-001 3072d normalizado → `cos = 1 - d²/2` ⇒ `distToSim(d) = 1 - (d*d)/2`. Validar no smoke com par conhecido.
3. **Runner:** `node --test dist/__tests__/*.test.js` (node:test sobre BUILD) → test usa `node:test` + `assert/strict`; rodar `npx tsc && node --test dist/__tests__/churn.test.js`.
4. **KNN canônico** (`embed.ts:262 semanticSearch`): `JOIN vec_chunk_map m ON m.vec_rowid = vc.rowid` + `WHERE vc.embedding MATCH ? AND k = ?` com param `JSON.stringify(Array.from(embedding)))`. Colunas reais de chunks: `source_file, chunk_text, chunk_type, created_at` (NÃO existe title/type).
5. **Entity format** (`ingest-entity.ts`): frontmatter YAML (name/description/type/event_date) + compiled livre até `## Timeline` + bullets `- **YYYY-MM-DD** — [tag] desc`. `<!-- retention: never -->` como 1ª linha do compiled (padrão do exemplo systems/). Dir `process/` novo é aceito (parser não valida lista).
6. **⚠️ Fato novo — types:** `chunk_type IN (decision,lesson,feedback)` = só **56 chunks** no corpus inteiro (team=46.7k, other=33.9k, distilled=11.8k). **Default do churn vira SEM filtro de tipo** + `--max-new 2000` (cap de custo); `--types` disponível pra restringir. Desvio justificado por dado; threshold default 0.80 mantido.

---

## Task 0: Recon pins (read-only, sem commit)

Pina 4 fatos que o código das tasks seguintes referencia. Executar via SSH (`ssh root@100.87.8.44`), tudo read-only.

**Files:** nenhum (só leitura).

- [ ] **Step 0.1: Formato de `chunks.created_at`**

```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && sqlite3 nox-mem.db \"SELECT typeof(created_at), created_at FROM chunks ORDER BY rowid DESC LIMIT 2;\""
```

Expected: `text|2026-06-...` (ISO8601). Evidência prévia: `datetime(created_at/1000,'unixepoch')` retornou 1970+2s ⇒ TEXT ISO coagido pra número. **Se vier `integer`**, ajustar comparações do Task 4/5 para epoch (`created_at >= strftime('%s', :since)`), e anotar aqui.

- [ ] **Step 0.2: Métrica de distância do `vec_chunks`**

```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && sqlite3 nox-mem.db \"SELECT sql FROM sqlite_master WHERE name='vec_chunks';\" && grep -n 'MATCH' src/search*.ts src/lib/*.ts 2>/dev/null | head -5"
```

Expected: DDL do vec0 (com ou sem `distance_metric=cosine`) + o snippet KNN que o `search.ts` já usa. Anotar: (a) métrica; (b) query KNN canônica do repo — o `churn.ts` REUSA esse padrão, não inventa outro.

- [ ] **Step 0.3: Test runner**

```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && cat package.json | jq -r '.scripts | {test, build}' && ls src/__tests__/ | head -5"
```

Expected: script de test (vitest ou node:test) + exemplos existentes. O test do Task 4 segue o padrão dos arquivos em `src/__tests__/`.

- [ ] **Step 0.4: Formato real de entity file**

```bash
ssh root@100.87.8.44 "ls /root/.openclaw/workspace/memory/entities/*/ | head; head -40 \$(find /root/.openclaw/workspace/memory/entities -name '*.md' | head -1)"
```

Expected: exemplo vivo com frontmatter YAML + section compiled + timeline. O Task 2 copia ESTE formato exato (headings reais do parser em `src/ingest-entity.ts`), não o esqueleto genérico abaixo.

---

## Task 1: Branch de trabalho via /tmp clone

**Files:** nenhum no repo ainda.

- [ ] **Step 1.1: Clone fresco + branch**

```bash
ssh root@100.87.8.44 'TASK=/tmp/cipher-simbiose-$(uuidgen | cut -c1-8) && git clone --depth 5 https://github.com/totobusnello/nox-workspace.git $TASK && cd $TASK && git checkout -b feat/cipher-simbiose-itens-1-2-3 && echo "WORKDIR=$TASK"'
```

Expected: `WORKDIR=/tmp/cipher-simbiose-XXXXXXXX`. **Anotar o path — todas as tasks 2-6 editam NESTE clone.** (Referido como `$WORKDIR` daqui em diante.)

- [ ] **Step 1.2: Symlink node_modules (build/test sem npm ci)**

```bash
ssh root@100.87.8.44 'cd $WORKDIR/tools/nox-mem && ln -s /root/.openclaw/workspace/tools/nox-mem/node_modules node_modules && npx tsc --noEmit 2>&1 | head -5'
```

Expected: tsc roda limpo (ou só erros pré-existentes conhecidos). Se symlink falhar com native modules: `npm ci` (~3min) como fallback.

---

## Task 2: Item 1 — Entity `process/doc-steward` (escrita 3-seções do Cipher)

**Files:**
- Create: `$WORKDIR/memory/entities/process/doc-steward.md`

- [ ] **Step 2.1: Criar o entity file**

Conteúdo (ajustar headings ao formato pinado no Step 0.4):

```markdown
---
name: doc-steward
type: process
owner: cipher
status: active
created: 2026-06-05
---

# compiled

Disciplina de stewardship dos documentos de agentes (SOUL.md, MEMORY.md, TOOLS.md, AGENTS.md) — dono: Cipher.

- **Escrita:** toda intervenção de stewardship (edição de SOUL, remoção de obsoleto, decisão de consistência) registra UM evento na timeline deste arquivo e re-ingere via `nox-mem ingest-entity memory/entities/process/doc-steward.md`. NUNCA usar `nox-mem ingest` genérico neste arquivo (incident 2026-04-25: ingestFile zera section/retention).
- **Política de leitura (answer vs search):** instalada nos 6 SOULs em 2026-06-05 — search é default ($0, ~2.5ms); answer só para síntese/diagnóstico/contradição, com budget.
- **Churn:** report mensal `memory/reports/churn-YYYY-MM.md` (cron dia 1). Re-decisão sobre mesmo tópico = knowledge gap → Cipher propõe consolidação (nunca auto-muta).

# timeline

## 2026-06-05
- Entity criado. Política answer/search v1 replicada nos 6 SOULs. Comando `churn --changed-since` + cron mensal instalados. Origem: plano Cipher×nox-mem aprovado 2026-06-04 (itens 1-3 de 5).
```

- [ ] **Step 2.2: Commit**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && git add memory/entities/process/doc-steward.md && git commit -m "feat(steward): entity process/doc-steward — escrita 3-secoes do Cipher (item 1 plano simbiose)"'
```

- [ ] **Step 2.3: Ingest no prod (após merge — ver Task 7.4)** — placeholder de ordem: o ingest acontece DEPOIS do merge+pull, comando documentado no Task 7.

---

## Task 3: Item 3 — Política answer/search nos 6 SOULs

**Files:**
- Modify: `$WORKDIR/agents/{nox,atlas,boris,cipher,forge,lex}/SOUL.md`

**Regra de coerência:** bloco IDÊNTICO nos 6 (diff entre eles = vazio no bloco). Cipher recebe +3 linhas de adendo de escrita. Tamanho: +14 linhas por SOUL (souls hoje: 92-158 linhas → fica 106-175, aceitável).

- [ ] **Step 3.1: Inserir o bloco padrão nos 6 SOULs**

Inserir ao FINAL de cada SOUL.md (antes de qualquer seção de assinatura/footer, se existir):

```markdown

## Memória nox-mem — answer vs search

| Intenção | Ferramenta | Custo |
|---|---|---|
| Lookup/recall: fato pontual, "o que diz X", buscar por título/entidade | `nox_mem_search` / KG tools | ~2.5ms, $0 |
| Síntese/diagnóstico: "há contradição?", "resuma estado de Y", causa-raiz multi-fonte | `POST /api/answer` | ~1.6s + LLM (quota flash-lite) |

Regras:
1. `search` é o DEFAULT. `answer` nunca é o primeiro recurso.
2. `answer` só quando a resposta exige compor 3+ fontes ou julgar consistência entre elas.
3. Budget: máx 10 `answer`/dia por agente. Excedeu → degrade para `search` + síntese própria.
4. Ao usar `answer`, citar os chunk ids retornados (auditabilidade).
```

- [ ] **Step 3.2: Adendo de escrita SÓ no Cipher**

Logo após o bloco acima, apenas em `agents/cipher/SOUL.md`:

```markdown
### Escrita de stewardship (Cipher)
Toda escrita vai na timeline de `memory/entities/process/doc-steward.md` e re-ingere via `nox-mem ingest-entity` (NUNCA `ingest` genérico — incident 2026-04-25). Report de churn mensal em `memory/reports/` é insumo, não output seu.
```

- [ ] **Step 3.3: Verificar coerência (diff do bloco entre os 6 = vazio)**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && for a in nox atlas boris cipher forge lex; do sed -n "/## Memória nox-mem — answer vs search/,/auditabilidade/p" agents/$a/SOUL.md | md5sum; done'
```

Expected: 6 hashes IDÊNTICOS.

- [ ] **Step 3.4: Commit**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && git add agents/*/SOUL.md && git commit -m "docs(souls): politica answer vs search nos 6 agentes + adendo escrita Cipher (item 3 plano simbiose)"'
```

---

## Task 4: Item 2 — Test do churn (TDD: red primeiro)

**Files:**
- Test: `$WORKDIR/tools/nox-mem/src/__tests__/churn.test.ts`

**Conceito sob teste:** dado um DB com chunk ANTIGO (decision sobre tópico T, embedding e₁) e chunk NOVO (created_at ≥ since, decision sobre T parafraseado, embedding e₂ com cos(e₁,e₂) ≥ threshold), `detectChurn()` retorna 1 par (novo↔antigo). Chunk novo sem vizinho antigo similar → não aparece.

- [ ] **Step 4.1: Escrever o teste falhando**

(Adaptar `describe/it` ao runner pinado no Step 0.3; dims=8 no teste para não depender de Gemini.)

```typescript
import Database from "better-sqlite3";
import * as sqliteVec from "sqlite-vec";
import { detectChurn } from "../churn";

function mkDb() {
  const db = new Database(":memory:");
  sqliteVec.load(db);
  db.exec(`
    CREATE TABLE chunks (id INTEGER PRIMARY KEY, title TEXT, type TEXT, created_at TEXT);
    CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[8]);
    CREATE TABLE vec_chunk_map (rowid INTEGER PRIMARY KEY, chunk_id INTEGER);
  `);
  return db;
}
function insert(db: any, id: number, title: string, createdAt: string, emb: number[]) {
  db.prepare("INSERT INTO chunks (id,title,type,created_at) VALUES (?,?,?,?)").run(id, title, "decision", createdAt);
  const r = db.prepare("INSERT INTO vec_chunks (embedding) VALUES (?)").run(new Float32Array(emb));
  db.prepare("INSERT INTO vec_chunk_map (rowid,chunk_id) VALUES (?,?)").run(r.lastInsertRowid, id);
}
const e = (x: number) => { const v = [x,1,0,0,0,0,0,0]; const n = Math.hypot(...v); return v.map(a=>a/n); };

describe("detectChurn", () => {
  it("flags re-decisão (novo similar a antigo) e ignora tópico novo", () => {
    const db = mkDb();
    insert(db, 1, "Decisão: porta API 18802",      "2026-04-01T00:00:00Z", e(1.00)); // antigo, tópico T
    insert(db, 2, "Re-decisão: porta API mantida",  "2026-06-01T00:00:00Z", e(1.02)); // novo, ~T  → churn
    insert(db, 3, "Decisão: novo tema sem par",     "2026-06-02T00:00:00Z", e(-5));   // novo, ortogonal → não
    const pairs = detectChurn(db, { since: "2026-05-01T00:00:00Z", threshold: 0.8, types: ["decision"], k: 5 });
    expect(pairs).toHaveLength(1);
    expect(pairs[0].newChunkId).toBe(2);
    expect(pairs[0].oldChunkId).toBe(1);
    expect(pairs[0].similarity).toBeGreaterThanOrEqual(0.8);
  });
});
```

- [ ] **Step 4.2: Rodar e ver falhar**

```bash
ssh root@100.87.8.44 'cd $WORKDIR/tools/nox-mem && npx vitest run src/__tests__/churn.test.ts 2>&1 | tail -5'
```

Expected: FAIL — `Cannot find module '../churn'`. (Trocar comando pelo runner do Step 0.3 se não for vitest.)

---

## Task 5: Item 2 — Implementação `src/churn.ts`

**Files:**
- Create: `$WORKDIR/tools/nox-mem/src/churn.ts`

- [ ] **Step 5.1: Implementar**

(REUSAR o padrão KNN pinado no Step 0.2; abaixo o shape — a query `MATCH` deve ser idêntica à do search.ts, inclusive conversão distância→similaridade conforme a métrica pinada.)

```typescript
/**
 * src/churn.ts — item 2 do plano Cipher×nox-mem (2026-06-05).
 * Detecção de churn de decisões: chunk NOVO (>= since) semanticamente
 * próximo de chunk ANTIGO do mesmo tipo = re-decisão = knowledge gap.
 * Read-only. $0 Gemini: usa embeddings já materializados em vec_chunks.
 */
import type Database from "better-sqlite3";

export interface ChurnOpts {
  since: string;            // ISO8601 — formato de created_at pinado no Step 0.1
  threshold?: number;       // similaridade mínima (default 0.80)
  types?: string[];         // default ["decision","lesson","feedback"]
  k?: number;               // vizinhos por chunk novo (default 5)
}
export interface ChurnPair {
  newChunkId: number; newTitle: string; newCreatedAt: string;
  oldChunkId: number; oldTitle: string; oldCreatedAt: string;
  similarity: number;
}

// Conversão pinada no Step 0.2: cosine → 1-d ; L2 sobre vetores normalizados → 1-(d*d)/2
function distToSim(d: number): number { return 1 - d; } // AJUSTAR conforme métrica real

export function detectChurn(db: Database.Database, opts: ChurnOpts): ChurnPair[] {
  const threshold = opts.threshold ?? 0.80;
  const types = opts.types ?? ["decision", "lesson", "feedback"];
  const k = opts.k ?? 5;
  const ph = types.map(() => "?").join(",");

  const newChunks = db.prepare(
    `SELECT c.id, c.title, c.created_at, v.embedding
       FROM chunks c
       JOIN vec_chunk_map m ON m.chunk_id = c.id
       JOIN vec_chunks v ON v.rowid = m.rowid
      WHERE c.created_at >= ? AND c.type IN (${ph})`
  ).all(opts.since, ...types) as any[];

  const knn = db.prepare(
    `SELECT m.chunk_id, c.title, c.created_at, v.distance
       FROM vec_chunks v
       JOIN vec_chunk_map m ON m.rowid = v.rowid
       JOIN chunks c ON c.id = m.chunk_id
      WHERE v.embedding MATCH ? AND k = ?
      ORDER BY v.distance`
  );

  const pairs: ChurnPair[] = [];
  for (const nc of newChunks) {
    const neighbors = knn.all(nc.embedding, k + 1) as any[]; // +1: ele mesmo vem primeiro
    for (const nb of neighbors) {
      if (nb.chunk_id === nc.id) continue;
      if (nb.created_at >= opts.since) continue;            // só vizinho ANTIGO conta como re-decisão
      const sim = distToSim(nb.distance);
      if (sim >= threshold) {
        pairs.push({
          newChunkId: nc.id, newTitle: nc.title, newCreatedAt: nc.created_at,
          oldChunkId: nb.chunk_id, oldTitle: nb.title, oldCreatedAt: nb.created_at,
          similarity: Math.round(sim * 1000) / 1000,
        });
        break; // 1 par por chunk novo (o mais próximo)
      }
    }
  }
  return pairs.sort((a, b) => b.similarity - a.similarity);
}

export function churnReportMd(pairs: ChurnPair[], since: string): string {
  const lines = [
    `# Churn report — desde ${since} — ${new Date().toISOString().slice(0, 10)}`,
    "",
    `${pairs.length} re-decisões detectadas (similaridade ≥ threshold). Re-decisão = knowledge gap: a memória não preveniu retrabalho. Ação: Cipher propõe consolidação (NUNCA auto-muta).`,
    "",
  ];
  for (const p of pairs) {
    lines.push(`- **${p.similarity}** novo #${p.newChunkId} "${p.newTitle}" (${p.newCreatedAt.slice(0,10)}) ↔ antigo #${p.oldChunkId} "${p.oldTitle}" (${p.oldCreatedAt.slice(0,10)})`);
  }
  if (!pairs.length) lines.push("_Nenhum churn no período._");
  return lines.join("\n") + "\n";
}
```

- [ ] **Step 5.2: Rodar o teste e ver passar**

```bash
ssh root@100.87.8.44 'cd $WORKDIR/tools/nox-mem && npx vitest run src/__tests__/churn.test.ts 2>&1 | tail -5'
```

Expected: PASS (1 test). Se falhar por métrica de distância: ajustar `distToSim` conforme Step 0.2 — esse é o único ponto móvel.

- [ ] **Step 5.3: Commit**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && git add tools/nox-mem/src/churn.ts tools/nox-mem/src/__tests__/churn.test.ts && git commit -m "feat(churn): detectChurn por embedding KNN sobre vec_chunks + report md (item 2 plano simbiose)"'
```

---

## Task 6: Item 2 — Comando CLI `churn --changed-since` + cron

**Files:**
- Modify: `$WORKDIR/tools/nox-mem/src/index.ts` (após o bloco `kg-path`, ~linha 505)

- [ ] **Step 6.1: Registrar o comando**

```typescript
program
  .command("churn")
  .description("Detecta re-decisões (knowledge gaps) por similaridade de embedding — read-only, $0")
  .requiredOption("--changed-since <iso>", "ISO date: só chunks criados desde essa data")
  .option("--threshold <n>", "similaridade mínima", "0.80")
  .option("--types <csv>", "tipos de chunk", "decision,lesson,feedback")
  .option("--report <path>", "grava report markdown nesse path")
  .option("--json", "output JSON em vez de texto")
  .action(async (opts) => {
    const { getDb } = await import("./db.js");
    const { detectChurn, churnReportMd } = await import("./churn.js");
    const db = getDb();
    const pairs = detectChurn(db, {
      since: opts.changedSince,
      threshold: parseFloat(opts.threshold),
      types: opts.types.split(","),
    });
    if (opts.json) console.log(JSON.stringify(pairs, null, 2));
    else console.log(churnReportMd(pairs, opts.changedSince));
    if (opts.report) {
      const { writeFileSync, mkdirSync } = await import("node:fs");
      const { dirname } = await import("node:path");
      mkdirSync(dirname(opts.report), { recursive: true });
      writeFileSync(opts.report, churnReportMd(pairs, opts.changedSince));
      console.log(`[CHURN] report: ${opts.report}`);
    }
  });
```

Nota: CLI usa `getDb()` normalmente (proibição de getDb é para EVAL scripts, não CLI prod).

- [ ] **Step 6.2: Build + smoke no clone apontando pro DB prod (read-only)**

```bash
ssh root@100.87.8.44 'cd $WORKDIR/tools/nox-mem && npx tsc && set -a && source /root/.openclaw/.env && set +a && node dist/index.js churn --changed-since 2026-05-05T00:00:00Z --threshold 0.85 2>&1 | head -20'
```

Expected: report com N pares plausíveis (maio teve re-decisões conhecidas: D48 saga, IP swap, worktree 3×) ou `Nenhum churn`. **Crash = fix antes de seguir.** Threshold 0.85 no smoke pra reduzir ruído; default fica 0.80.

- [ ] **Step 6.3: Commit**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && git add tools/nox-mem/src/index.ts && git commit -m "feat(cli): comando churn --changed-since com report md/json (item 2 plano simbiose)"'
```

---

## Task 7: PR → merge → deploy prod → validações E2E

- [ ] **Step 7.1: Push + PR**

```bash
ssh root@100.87.8.44 'cd $WORKDIR && git push -u origin feat/cipher-simbiose-itens-1-2-3'
gh pr create --repo totobusnello/nox-workspace --head feat/cipher-simbiose-itens-1-2-3 --title "Cipher simbiose itens 1-3: entity doc-steward + politica answer/search 6 SOULs + churn por embedding" --body "Plano: memoria-nox specs/2026-06-05-cipher-simbiose-itens-1-2-3.md. Item 1: entity process/doc-steward (3 secoes). Item 3: bloco identico nos 6 SOULs + adendo Cipher. Item 2: src/churn.ts (KNN sqlite-vec, \$0 Gemini) + CLI churn + test."
```

- [ ] **Step 7.2: Review (Forge ou Toto) + merge** — gate humano; não auto-mergear.

- [ ] **Step 7.3: Pull + build no working tree prod**

```bash
ssh root@100.87.8.44 'cd /root/.openclaw/workspace && git branch --show-current && git pull && cd tools/nox-mem && npx tsc && echo BUILD_OK'
```

Expected: `main` + `BUILD_OK`. Sem restart de serviço (api-server não mudou).

- [ ] **Step 7.4: Ingest do entity (item 1 vira dado)**

```bash
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; cd /root/.openclaw/workspace/tools/nox-mem && node dist/index.js ingest-entity ../../memory/entities/process/doc-steward.md && sqlite3 nox-mem.db "SELECT section, count(*) FROM chunks WHERE title LIKE \"%doc-steward%\" GROUP BY section;"'
```

Expected: N+2 chunks com sections `frontmatter`/`compiled`/`timeline` (N eventos). Validar também `curl -s http://127.0.0.1:18802/api/health | jq .sectionDistribution`.

- [ ] **Step 7.5: Cron mensal (dia 1, 03:17 — off-minute)**

```bash
ssh root@100.87.8.44 'cat >> /var/spool/cron/crontabs/root <<EOF
# ── Churn mensal (re-decisões = knowledge gaps) — plano Cipher simbiose 2026-06-05
17 3 1 * * set -a; . /root/.openclaw/.env; set +a; cd /root/.openclaw/workspace/tools/nox-mem && node dist/index.js churn --changed-since \$(date -d "1 month ago" +\%Y-\%m-01)T00:00:00Z --report /root/.openclaw/workspace/memory/reports/churn-\$(date +\%Y-\%m).md >> /var/log/nox-churn.log 2>&1
EOF
crontab /var/spool/cron/crontabs/root && crontab -l | grep churn'
```

Expected: linha instalada. Nota deliberada: `memory/reports/` é watched → report vira chunk daily/90d automaticamente (loop se auto-documenta). Confirmar que watcher allowlist NÃO exclui `reports/`.

- [ ] **Step 7.6: Smoke do brief pós-SOULs (personas leem SOUL no boot)**

```bash
ssh root@100.87.8.44 'curl -s -H "Authorization: Bearer $(cat /root/.config/nox-mem/token 2>/dev/null || echo X)" https://srv1465941.tail4caa5b.ts.net/api/brief?scope=cipher | head -5; for a in nox atlas boris cipher forge lex; do wc -l /root/.openclaw/workspace/agents/$a/SOUL.md; done'
```

Expected: brief responde 200 + 6 SOULs com +14/+17 linhas vs baseline (92-158 → 106-175).

---

## Task 8: Fechamento — docs + memória

- [ ] **Step 8.1: HANDOFF.md** — nova entrada Thu 2026-06-05: itens 1-3 do plano Cipher entregues; restam itens 4 (access_count audit, gated em sanity) e 5 (contradições via answer). Janela de observação do priming loop segue.
- [ ] **Step 8.2: Memória do projeto** — atualizar `project_cipher_nox_mem_simbiose_plan_2026_06_04.md`: itens 1-3 SHIPPED (PR #N), aprendizados (métrica vec, threshold churn observado no smoke).
- [ ] **Step 8.3: Commit docs no memoria-nox (Mac, branch main)**

```bash
cd /Users/lab/Claude/Projetos/memoria-nox && git branch --show-current && git add docs/HANDOFF.md specs/2026-06-05-cipher-simbiose-itens-1-2-3.md && git commit -m "docs(handoff+spec): itens 1-3 plano Cipher simbiose shipped — entity doc-steward + politica answer/search + churn embedding"
```

---

## Self-review (feito 2026-06-05)

1. **Cobertura:** item 1 → Tasks 2+7.4; item 2 → Tasks 4+5+6+7.5; item 3 → Task 3+7.6. Decisões do Toto (entity única / embedding / 6 agentes) todas mapeadas. ✓
2. **Placeholders:** Step 0.x pina os 4 pontos móveis (created_at, métrica vec, runner, formato entity) — únicos pontos onde código depende de recon; `distToSim` marcado como o único ajuste pós-pin. ✓
3. **Consistência de tipos:** `detectChurn(db, opts)`/`ChurnPair` idênticos entre Task 4 (test) e Task 5 (impl); CLI do Task 6 importa os mesmos nomes. ✓
4. **Riscos cobertos:** clone /tmp (worktree lesson), read-only churn, ingest-entity (não ingestFile), gate humano no merge, branch check antes de commits em prod/Mac. ✓
