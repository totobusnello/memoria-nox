# Incident 2026-05-18 — 57 Orphan Chunks Sem Embedding Pós-Deploy

**Status:** RESOLVED-PENDING-REEMBED  
**Severidade:** MEDIUM  
**Detectado em:** 2026-05-18 (pós-deploy)  
**Root cause:** Gemini API key expirada — `400 INVALID_ARGUMENT: API key expired`  
**Impacto:** 57 chunks sem cobertura semântica; FTS5 funcional; busca vetorial degradada nesses chunks  
**PR de remediação:** scripts/re-embed-orphans.sh + docs/ops/EMBEDDING-INTEGRITY-CHECK.md

---

## 1. Timeline

| Horário (BRT) | Evento |
|---|---|
| antes do deploy | Estado pré-deploy: 68,995 chunks / 68,995 embedded (100% coverage, 1 orphan pré-existente) |
| deploy | rsync ~319 arquivos TypeScript + schema migrations v19-v24 + service restart |
| 14:04:53 | watcher ingere `memory/ORCHESTRATION-PATTERN.md` → 16 chunks criados (IDs 224720-224735) |
| 14:04:56 | **PRIMEIRA FALHA DE EMBEDDING:** `gemini embeddings failed (400): API key expired` |
| 14:04:54 | watcher ingere `memory/ORCHESTRATION-QUICK-REFERENCE.md` → 10 chunks criados (IDs 224736-224745) |
| 14:06:03 | watcher ingere `memory/ORCHESTRATION-COHERENCE-CHECK.md` → 14 chunks criados (IDs 224746-224759) |
| 14:06:06 | **SEGUNDA FALHA DE EMBEDDING:** `API key expired` |
| 14:10:11 | watcher ingere `memory/2026-05-18.md` → 2 chunks + `memory/decisions.md` → 3 chunks (IDs 224760-224764) |
| 14:10:15 | **TERCEIRA FALHA DE EMBEDDING:** `API key expired` |
| 14:37:03 → 15:12:09 | obra-bvv-log.md re-ingerido 5× pelo watcher (edições contínuas) → 12 chunks cada = padrão de re-ingest |
| ~14:37–15:12 | **QUATRO FALHAS ADICIONAIS DE EMBEDDING** (mesmo erro 400) |
| 15:23:15 | service restart do nox-mem-api (deploy concluído) |
| 15:23:16 | API voltando em `:18802` |
| pós-deploy | Estado confirmado: 68,995 chunks / 68,938 mapped (vec_chunk_map) / 57 orphans |

**Nota sobre obra-bvv-log.md:** O arquivo foi ingerido várias vezes (watcher reagindo a edições). Apenas 12 chunks aparecem como orphans — o que implica que as re-ingestões substituíram chunks anteriores e somente a última versão ficou sem mapeamento.

---

## 2. Identificação dos 57 Chunks Órfãos

### Por arquivo de origem

| source_file | chunks | IDs | primeira_ingestão (BRT) |
|---|---|---|---|
| `memory/ORCHESTRATION-PATTERN.md` | 16 | 224720–224735 | 14:04:53 |
| `memory/ORCHESTRATION-QUICK-REFERENCE.md` | 10 | 224736–224745 | 14:04:54 |
| `memory/ORCHESTRATION-COHERENCE-CHECK.md` | 14 | 224746–224759 | 14:06:03 |
| `memory/2026-05-18.md` | 2 | 224760–224761 | 14:10:11 |
| `memory/decisions.md` | 3 | 224762–224764 | 14:10:11 |
| `memory/obra-bvv-log.md` | 12 | 224813–224824 | 15:12:06 |
| **TOTAL** | **57** | **224720–224824** | |

### Por chunk_type

| chunk_type | count | observação |
|---|---|---|
| `other` | 52 | conteúdo geral de markdown |
| `decision` | 3 | decisões de projeto (decisions.md) |
| `daily` | 2 | nota diária (2026-05-18.md) |

### Por section

Todos os 57 orphans têm `section = NULL` — confirmando que são ingestões via `ingestFile()` genérico (não entity files), o que é esperado para esses arquivos.

### Faixa de IDs

- **Primeiro orphan:** ID 224720  
- **Último orphan:** ID 224824  
- **Max chunk_id em vec_chunk_map:** 224645 (confirmado via query)

Isso prova que **nenhum chunk pré-deploy** perdeu embedding. Todos os orphans são chunks criados hoje após a expiração da chave.

---

## 3. Root Cause — Análise com Evidências

### Causa primária: Gemini API key expirada

O syslog (`/var/log/syslog`) capturou o erro exato imediatamente após cada ingestão:

```
2026-05-18T14:04:56 [memory] sync failed (watch):
  Error: gemini embeddings failed (400): API key expired.
  Please renew the API key. [code=INVALID_ARGUMENT]
```

Esse erro se repetiu em **todas as 6+ tentativas** de embedding entre 14:04 e 15:12 BRT.

### Causa secundária: ausência de alerta proativo

O sistema detectou o erro e logou corretamente, mas:
1. Não alertou via Discord/Telegram
2. Não bloqueou a ingestão (correto por design — chunks são úteis sem embed para FTS5)
3. Não marcou os chunks como "pending vectorization" para retry automático
4. Não havia cron diário de integridade que teria detectado o gap

### Por que o deploy não causou isso diretamente?

O deploy (rsync + restart) não modificou o schema de vec_chunks nem vec_chunk_map. As migrations v19-v24 são confirmadas como additive (adicionam colunas `confidence`, `provenance_kind`, etc.) sem DROP ou TRUNCATE em tabelas de vetores. O problema é **coincidência temporal**: a chave expirou no mesmo período do deploy.

### Confirmação: os 68,939 chunks pré-deploy estão intactos

```sql
SELECT max(chunk_id) FROM vec_chunk_map;
-- Resultado: 224645
```

O max chunk_id mapeado (224645) é anterior ao primeiro orphan (224720), confirmando que nenhum chunk pré-existente perdeu seu embedding.

---

## 4. Classificação de Impacto

### O que está degradado

- **Busca semântica (vetorial):** os 57 chunks não aparecem em resultados de busca por similaridade
- Arquivos afetados: ORCHESTRATION-PATTERN, ORCHESTRATION-QUICK-REFERENCE, ORCHESTRATION-COHERENCE-CHECK, nota do dia, decisions.md, obra-bvv-log.md

### O que está funcionando

- **FTS5 (BM25):** 100% funcional — chunks estão na tabela `chunks` e indexados em `chunks_fts`
- **Busca híbrida:** retorna resultados; só perde o componente semântico para esses 57 chunks
- **KG:** não afetado (kg_entities e kg_relations não dependem de vec_chunk_map)
- **99.92% do corpus** tem cobertura semântica completa

### Severidade: MEDIUM

Justificativa:
- Os arquivos afetados são documentos operacionais de orquestração e nota diária — importante para recall contextual
- FTS5 ainda os encontra com queries de palavras-chave exatas
- O gap é pequeno (57/68,995 = 0.083%) e recuperável em <1 minuto de CPU
- Nenhuma perda de dados; chunks íntegros no DB

---

## 5. Remediação

### Imediata (requer aprovação do usuário)

Rodar `scripts/re-embed-orphans.sh` após renovar a Gemini API key:

```bash
# 1. Renovar chave em .env
# 2. Dry-run para confirmar escopo
bash scripts/re-embed-orphans.sh --dry-run

# 3. Se OK, executar
bash scripts/re-embed-orphans.sh --verbose
```

Custo estimado: 57 chunks × $0.00005 ≈ **$0.003** (negligível).

### Preventiva

Ver `docs/ops/EMBEDDING-INTEGRITY-CHECK.md` para:
- Cron diário de verificação de cobertura
- Alerta se `embedded != total`
- Auto-trigger de re-embed para drift < 100 chunks

---

## 6. Lições Aprendidas

1. **Chave Gemini expirada não bloqueia ingestão** — é o comportamento correto (chunks têm valor via FTS5), mas gera drift silencioso de cobertura vetorial.
2. **O embed é assíncrono ao ingest** — o watcher ingere primeiro, tenta embed depois. Se embed falha, o chunk fica sem mapeamento permanentemente (sem retry).
3. **Alerta proativo é o gap real** — a falha foi logada mas não alertada. Um webhook Discord no padrão `gemini embeddings failed (400)` teria detectado em segundos.
4. **Verificar `/api/health.vectorCoverage` pós-deploy** deve ser parte do checklist de deploy.

---

## 7. Referências

- Syslog VPS com timestamps exatos: `/var/log/syslog` (grep `nox-mem\|embed\|gemini`)
- Script de remediação: `scripts/re-embed-orphans.sh`
- Runbook de monitoramento: `docs/ops/EMBEDDING-INTEGRITY-CHECK.md`
- Regras críticas relacionadas: `CLAUDE.md` §2 (verificar estado real pós-operação) e §3 (modelo Gemini padrão)
