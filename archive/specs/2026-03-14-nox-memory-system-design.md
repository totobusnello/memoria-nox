# Nox Memory System — Design Spec

> Sistema de memória inteligente para o agente Nox (OpenClaw) com busca full-text,
> consolidação IA automatizada e recovery de contexto pós-compactação.

**Autor:** Toto Busnello + Claude
**Data:** 2026-03-14
**Status:** Implementado e deployado (v2.1.2) — atualizado após 6 rounds de code review
**Repositório:** github.com/totobusnello/nox-workspace
**VPS:** Hostinger KVM 4 (4 cores AMD EPYC, 16GB RAM, 200GB disco) — srv1465941 via Tailscale 100.87.8.44

---

## 1. Problema

O Nox opera como Chief of Staff de um time de 10 agentes no OpenClaw. Sua memória atual é 100% baseada em arquivos Markdown (~164KB), sem mecanismo de busca, sem consolidação automática, e com recovery manual após compactação de contexto.

### Sintomas

1. **Esquecimento pós-compaction** — após compactação do contexto, o Nox perde detalhes de sessões anteriores e depende de leitura manual de working-buffer + SESSION-STATE + daily notes
2. **Daily notes acumulam sem curadoria** — notas diárias são raw capture, nunca consolidadas automaticamente em topic files (decisions, lessons, people, projects)
3. **Busca inexistente** — para achar "aquela decisão sobre o LinkedIn do Boris", o Nox precisa saber em qual arquivo está e ler inteiro
4. **Agentes sem contexto cruzado** — quando Atlas precisa saber o que Boris fez, não há mecanismo de busca — depende do Nox lembrar
5. **MEMORY.md desatualizado** — o índice principal é mantido manualmente e frequentemente defasado

---

## 2. Princípios de Design

1. **Markdown é source of truth** — SQLite é índice/cache. Se o banco corromper, `nox-mem reindex` reconstrói tudo dos .md
2. **Nox é gateway único** — só ele lê e escreve memória. Agentes pedem ao Nox, que consulta e repassa
3. **Falha graceful** — se qualquer componente cair (SQLite, Ollama, inotifywait), o Nox continua operando com Markdown puro como hoje
4. **Zero custo de API** — embeddings e consolidação rodam em Ollama local (Llama 3.2 3B)
5. **Mínimas peças** — SQLite, 1 script Node, inotifywait, Ollama. Sem servidores HTTP, sem portas, sem bancos externos

---

## 3. Arquitetura — 3 Camadas de Memória

```
┌─────────────────────────────────────────────────┐
│                   NOX (Chief of Staff)           │
│          Único que lê e escreve memória           │
├─────────────────────────────────────────────────┤
│                                                   │
│  🔴 QUENTE — SESSION-STATE.md                    │
│  ├── RAM da sessão atual (volátil)               │
│  ├── WAL protocol (write-ahead log)              │
│  ├── Correções, nomes, valores, decisões         │
│  └── Limpa a cada nova sessão                    │
│  └── NÃO indexado no SQLite                      │
│                                                   │
│  🟡 MORNA — Topic Files (curados)                │
│  ├── decisions.md, lessons.md, people.md,        │
│  │   projects.md, pending.md                     │
│  ├── Fonte de verdade operacional                │
│  ├── Indexados em SQLite FTS5                    │
│  ├── Peso de busca: 2x (boost)                   │
│  └── Atualizados pela consolidação IA            │
│                                                   │
│  🔵 FRIA — Daily Notes + Feedback                │
│  ├── memory/YYYY-MM-DD.md (raw capture)          │
│  ├── memory/feedback/*.json                      │
│  ├── shared/TEAM_MEMORY.md                       │
│  ├── Indexados em SQLite FTS5                    │
│  ├── Peso de busca: 1x (normal)                  │
│  └── Recência como tiebreaker                    │
│                                                   │
├─────────────────────────────────────────────────┤
│  🔍 BUSCA UNIFICADA                              │
│  nox-mem search "query"                           │
│  → FTS5 match + boost topic files + recência      │
│  → Retorna top-5 chunks rankeados                 │
└─────────────────────────────────────────────────┘
```

### Fluxo de dados

```
Conversa acontece
    │
    ▼
Nox aplica WAL Protocol (SESSION-STATE.md)
    │
    ▼
Nox escreve em memory/*.md (daily notes, topic files)
    │
    ▼
inotifywait detecta mudança → auto re-ingest no SQLite
    │
    ▼
Cron 23h → nox-mem consolidate (Llama 3.2 local)
    ├── Extrai fatos, decisões, lições das daily notes
    ├── Atualiza topic files
    ├── Atualiza MEMORY.md (estado atual)
    └── Git commit automático
    │
    ▼
Cron dom 21h → nox-mem digest
    └── Resumo semanal em memory/digests/YYYY-WNN.md
```

---

## 4. Stack Técnico

### Componentes a instalar na VPS

| Componente | Versão | Propósito | RAM | Disco |
|---|---|---|---|---|
| SQLite3 | 3.45+ | Banco + FTS5 (built-in) | ~5MB | ~50MB |
| Ollama | latest | Runtime de modelos locais | ~300MB | ~2GB |
| llama3.2:3b | 3B params | Consolidação IA (extração de fatos) | ~2GB pico | ~1.8GB |
| inotify-tools | latest | `inotifywait` file watcher para auto-indexação | ~1MB | ~1MB |
| nox-mem | custom | CLI Node.js (busca, consolidação, primer) | ~30MB | ~5MB |

**Total permanente:** ~340MB RAM, ~4GB disco
**Pico durante consolidação:** ~2.3GB RAM (Llama 3.2 carrega, processa, descarrega)
**Disponível na VPS:** 13GB RAM, 168GB disco — sobra de recurso

### Runtimes existentes (já na VPS)

- Node.js v22.22.1 ✅
- Python 3.13.7 ✅ (não usado pelo nox-mem, mas disponível)
- npm ✅

### Dependências Node.js

| Pacote npm | Propósito |
|---|---|
| `better-sqlite3` | Driver SQLite síncrono, rápido, bindings C++ nativos |
| `commander` | CLI arg parser |

**Build strategy:** TypeScript compilado com `tsc` para `dist/`. Entry point `dist/index.js`. Binário global via symlink: `ln -s ~/.openclaw/workspace/tools/nox-mem/dist/index.js /usr/local/bin/nox-mem`. O `package.json` inclui `"bin": { "nox-mem": "./dist/index.js" }`.

### Ollama API

| Detalhe | Valor |
|---|---|
| Endpoint | `http://127.0.0.1:11434/api/generate` |
| Modelo | `llama3.2:3b` |
| Temperature | `0` (determinístico para extração estruturada) |
| Format | `"json"` (força output JSON válido) |
| Timeout | 120s por chamada |
| Detecção offline | Connection refused → skip gracefully |
| Systemd | `ollama.service` (instalação padrão cria o serviço) |

### Logging

Todos os comandos logam para stdout/stderr (capturado pelo systemd journal para o watcher, visível no terminal para uso manual):
- `[INFO]` — operações normais (ingest, search results, consolidation complete)
- `[WARN]` — falhas recuperáveis (Ollama offline, JSON inválido, retry)
- `[ERROR]` — falhas irrecuperáveis (SQLite corruption, file not found)

Consultar logs: `journalctl -u nox-mem-watcher -f`

### Por que essa stack

| Escolha | Alternativa descartada | Motivo |
|---|---|---|
| SQLite + FTS5 | PostgreSQL + pgvector | Zero config, backup = 1 arquivo, sem serviço |
| Ollama local | API OpenAI embeddings | Custo zero, dados ficam na VPS, sem latência |
| Llama 3.2 3B | Sonnet via API | Extração estruturada não precisa de modelo grande |
| inotifywait | Cron de ingest | Tempo real vs. delay, zero intervenção manual |
| CLI direto | HTTP service | Sem porta, sem systemd extra, sem ponto de falha |
| sqlite-vec (Fase 3) | sqlite-vss | Ativo, zero deps, binário pronto |

---

## 5. Esquema SQLite

### Caminhos dos arquivos de memória (paths explícitos)

Todos relativos a `~/.openclaw/workspace/`:

| Arquivo | Path absoluto | chunk_type | Boost |
|---|---|---|---|
| decisions.md | `memory/decisions.md` | `decision` | 2.0x |
| lessons.md | `memory/lessons.md` | `lesson` | 2.0x |
| people.md | `memory/people.md` | `person` | 2.0x |
| projects.md | `memory/projects.md` | `project` | 2.0x |
| pending.md | `memory/pending.md` | `pending` | 2.0x |
| YYYY-MM-DD*.md | `memory/YYYY-MM-DD*.md` | `daily` | 1.0x |
| feedback/*.json | `memory/feedback/*.json` | `feedback` | 1.0x |
| TEAM_MEMORY.md | `shared/TEAM_MEMORY.md` | `team` | 1.0x |
| MEMORY.md | `MEMORY.md` | **não indexado** | — |

> **MEMORY.md não é indexado** — ele é gerado/atualizado pela consolidação, não é fonte de busca.
> Isso evita feedback loop com o file watcher.

### Schema versioning (migrações)

A tabela `meta` armazena a versão do schema. Na inicialização, `db.ts` verifica:
```
meta.key = 'schema_version' → compara com versão esperada no código
```
- Se banco não existe → cria tudo do zero
- Se versão igual → nada a fazer
- Se versão menor → aplica migrações sequenciais (v1→v2, v2→v3...)
- Se versão maior → erro (downgrade não suportado)

Schema atual é **v2** (migração v1→v2 aplicada em produção 2026-03-14).
Fase 3 futura será migration v2→v3 (adiciona coluna embedding + tabela chunks_vec).

```sql
-- Banco: ~/.openclaw/workspace/tools/nox-mem/nox-mem.db
-- Schema version: 2

-- ===== v1: Schema base =====

-- Chunks de memória (parágrafos de cada .md)
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,       -- 'memory/decisions.md'
    chunk_text TEXT NOT NULL,        -- conteúdo (~300 tokens)
    chunk_type TEXT NOT NULL,        -- 'decision' | 'lesson' | 'person' | 'project' | 'daily' | 'feedback' | 'team'
    source_date TEXT,                -- ISO date extraída do filename ou conteúdo
    is_consolidated BOOLEAN DEFAULT 0,  -- legado v1, não mais usado (ver consolidated_files)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    metadata TEXT                    -- JSON: {agent: 'boris', tags: ['linkedin']}
);

-- Full-text search index
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    chunk_text,
    source_file,
    chunk_type,
    content=chunks,
    content_rowid=id,
    tokenize='porter unicode61'     -- stemming + unicode support
);

-- Triggers para manter FTS5 sincronizado (apenas INSERT e DELETE)
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
    VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
END;

CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
    VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
END;

-- NOTA: chunks_au (UPDATE trigger) foi REMOVIDO na v2 — causava write amplification
-- no FTS5 durante consolidação. Updates usam delete+insert.

-- Metadata do sistema
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Índices
CREATE INDEX idx_chunks_source ON chunks(source_file);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_date ON chunks(source_date);

-- ===== v2: Consolidation state separado (sobrevive reindex) =====

-- Tabela separada de estado de consolidação — NÃO é deletada durante reindex
-- Isso resolve o bug crítico onde reindex perdia o estado de quais daily notes
-- já foram consolidadas (is_consolidated na tabela chunks era destruído)
CREATE TABLE consolidated_files (
    source_file TEXT PRIMARY KEY,    -- 'memory/2026-03-14.md'
    status INTEGER NOT NULL DEFAULT 1,  -- 1=processado, -1=falhou, 0=pendente
    processed_at TEXT DEFAULT (datetime('now'))
);

-- v2 migration também:
-- 1. Migra dados existentes de chunks.is_consolidated para consolidated_files
-- 2. Remove idx_chunks_consolidated (não mais necessário)
-- 3. Remove trigger chunks_au (FTS5 write amplification fix)
```

### Fase 3 — Extensão para embeddings (futuro, quando chunks > 1000)

```sql
-- Adicionar coluna de embedding
ALTER TABLE chunks ADD COLUMN embedding BLOB;

-- Virtual table para busca vetorial (sqlite-vec)
CREATE VIRTUAL TABLE chunks_vec USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]  -- all-MiniLM-L6-v2 dimension
);

-- Tabela de relações (grafo)
CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_a TEXT NOT NULL,        -- 'person:Fernando Busnello'
    entity_b TEXT NOT NULL,        -- 'project:JHSF Surf Club'
    relation_type TEXT NOT NULL,   -- 'involved_in' | 'decided' | 'owns' | 'blocked_by'
    context TEXT,                  -- frase original que gerou a relação
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 6. nox-mem CLI — Comandos

### 6.1 — `nox-mem search <query>`

Busca híbrida na memória.

**Input:** query em linguagem natural
**Output:** top-5 chunks rankeados com score, source file e trecho

**Algoritmo:**
1. FTS5 `MATCH` com a query (tokenização porter + unicode)
2. Score base = FTS5 `bm25()` rank
3. Boost: topic files (decisions, lessons, people, projects, pending) recebem score × 2.0
4. Recência: chunks com `source_date` nos últimos 7 dias recebem score × 1.5
5. Ordenar por score final, retornar top-5

**Exemplo:**
```
$ nox-mem search "limite caracteres linkedin boris"

#1 [score: 12.4] lessons.md
   "Posts LinkedIn < 2.950 caracteres. Contar antes de publicar/agendar. Sem exceção."

#2 [score: 9.1] 2026-03-11.md
   "Post Jensen Huang rejeitado pela Late API — 3015 chars, limite 3000..."

#3 [score: 7.8] decisions.md
   "Boris NUNCA publica sem OK explícito do Totó..."
```

### 6.2 — `nox-mem primer`

Gera resumo de contexto para recovery pós-compactação.

**Input:** nenhum
**Output:** ~500 tokens com contexto essencial

**Algoritmo:**
1. Ler SESSION-STATE.md → tarefa ativa (regex para seção `## 🔴 Tarefa Ativa`)
2. Buscar top-5 decisões mais recentes (por `id DESC`, não `source_date` — ordem de inserção é mais confiável):
   - `extractDecisionLine()` parseia 3 formatos diferentes:
     - Auto-consolidado: `- **2026-03-06:** texto` (bullets com data em bold)
     - Manual decisão: `**Decisão:** texto`
     - Manual header: `## 2026-03-10 — Descrição`
   - Deduplica resultados para evitar repetição
3. Buscar top-3 chunks do dia atual (daily note com `source_date = today`)
4. Buscar pendências de pending.md (até 3 items, extrai bullets `- ` ou headers `### `)
5. Formatar como resumo estruturado (~500 tokens)

**Exemplo:**
```
$ nox-mem primer

## Context Recovery — 2026-03-14 19:30 BRT

**Tarefa ativa:** Nenhuma
**Decisões recentes:**
- Miami: ida 21-22/03, volta 29-30/03 (corrigido)
- WhatsApp groupPolicy: open
- Daily briefing timeout: 240s

**Hoje:**
- Sessão focada em sistema de memória (nox-mem)
- Spec em desenvolvimento com Toto

**Pendências urgentes:**
- Confirmar voo Miami (10 dias)
- Boleto JHSF Surf Club R$3.295
```

### 6.3 — `nox-mem consolidate`

Executa consolidação IA das daily notes não processadas.

**Input:** nenhum (processa daily notes não presentes na tabela `consolidated_files`)
**Output:** arquivos topic files atualizados + git commit automático

**Algoritmo:**
1. Buscar daily notes não consolidadas: `WHERE chunk_type = 'daily' AND source_file NOT IN (SELECT source_file FROM consolidated_files)` — **máximo 5 por execução** para evitar timeout do cron
2. Agrupar chunks por `source_file` e concatenar o texto de cada daily note
3. Para cada nota, chamar Ollama API local:
   ```
   POST http://127.0.0.1:11434/api/generate
   {
     "model": "llama3.2:3b",
     "prompt": "<ver prompts/consolidate.txt>",
     "format": "json",        ← OBRIGATÓRIO: força JSON válido
     "temperature": 0,        ← determinístico
     "stream": false
   }
   ```
   Prompt template (`prompts/consolidate.txt`):
   ```
   Extraia do texto abaixo todos os fatos relevantes.
   Retorne APENAS um JSON com esta estrutura exata:
   {
     "decisions": [{"text": "descrição da decisão", "permanent": true}],
     "lessons": [{"text": "descrição da lição", "type": "strategic"}],
     "people": [{"name": "Nome Completo", "info": "informação relevante"}],
     "projects": [{"name": "Nome Projeto", "update": "atualização"}],
     "pending": [{"text": "descrição", "owner": "quem", "deadline": "quando"}]
   }
   Arrays vazios se não houver itens daquela categoria.
   Texto:
   ---
   {DAILY_NOTE_TEXT}
   ```
4. Validar JSON response com try/catch. Se inválido → retry até 3x → se falhar, `[WARN]` log e skip
5. Para cada item extraído, **deduplicação por similaridade textual:**
   - Buscar no FTS5: `chunks_fts MATCH <primeiras 8 palavras significativas (>3 chars) do item>`
   - Se algum resultado existente tem >70% de palavras em comum → **skip** (já existe)
   - Se <70% → considerar novo
6. Itens novos → **inserir DENTRO da seção** do topic file via `appendInSection()`:
   - `decisions[]` → inserir em `memory/decisions.md` sob header `## Consolidação Automática` (antes do próximo `##`)
   - `lessons[]` → inserir em `memory/lessons.md` sob header `## ⏳ Táticas` ou `## 🔒 Estratégicas` conforme `type`
   - `people[]` → inserir em `memory/people.md` sob header `## Consolidação Automática`
   - `projects[]` → inserir em `memory/projects.md` sob header `## Consolidação Automática`
   - `pending[]` → inserir em `memory/pending.md` sob header `## Consolidação Automática`
   - **`appendInSection(path, section, content)`**: localiza o header da seção, insere o conteúdo ANTES do próximo header `##` (ou fim de arquivo). Se a seção não existe, cria no final.
7. **Nunca fazer UPDATE inline** em topic files — apenas append dentro de seções. O Nox ou o Toto fazem curadoria manual se necessário.
8. Marcar daily note na tabela `consolidated_files` com `status = 1` e `processed_at`
9. Salvar itens novos em `last-sync.json` para possível re-sync com Notion
10. Se `config.notion.enabled`, sincronizar com Notion via `syncToNotion(items)`
11. Git commit: `"chore(memory): consolidate daily notes YYYY-MM-DD"`
12. Reportar `remaining` count (quantas daily notes ainda pendentes para próxima execução)

**Proteções:**
- Se Ollama estiver offline (connection refused) → `[WARN]` log, skip, tenta no próximo cron
- Se JSON inválido após 3 retries → `[WARN]` log e skip nota, marca como `status = -1` (failed) na tabela `consolidated_files`
- Nunca sobrescrever topic files — **append-only dentro de seções**
- Se topic file não existe → criar com header padrão antes de inserir
- Máximo 5 files por execução — reporta remaining para re-execução

### 6.4 — `nox-mem digest`

Gera resumo semanal.

**Input:** nenhum
**Output:** `memory/digests/YYYY-WNN.md`

**Algoritmo:**
1. Buscar todas as consolidações da semana (chunks com `source_date` nos últimos 7 dias)
2. Enviar ao Ollama via `callOllamaText()` (retry 3x, timeout 120s):
   ```
   POST http://127.0.0.1:11434/api/generate
   {
     "model": "llama3.2:3b",
     "prompt": "<ver prompts/digest.txt> + fatos da semana",
     "stream": false,
     "options": { "temperature": 0.3 }  ← levemente criativo para resumos
   }
   ```
3. Salvar em `memory/digests/YYYY-WNN.md` (semana calculada com ISO 8601 — método Thursday anchor)
4. Git commit

### 6.5 — `nox-mem reindex`

Reconstrói o SQLite inteiro a partir dos arquivos Markdown.

**Input:** nenhum
**Output:** nox-mem.db recriado

**Algoritmo:**
1. `DELETE FROM chunks` — limpa todos os chunks (mas **PRESERVA** tabela `consolidated_files`)
2. `INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')` — reconstrói índice FTS5
3. Escanear recursivamente todos os `.md` e `.json` em `workspace/memory/` e `workspace/shared/` (exclui `node_modules/` e `.git/`)
4. Chunkar e indexar cada arquivo via `ingestFile(file, db, skipDelete=true)` — usa conexão compartilhada para eficiência
5. Reportar: "Reindexed X files, Y chunks"

**IMPORTANTE:** A tabela `consolidated_files` NÃO é deletada durante reindex. Isso garante que o estado de consolidação (quais daily notes já foram processadas) sobrevive à reconstrução do índice.

### 6.6 — `nox-mem ingest <file_path>`

Indexa um arquivo específico.

**Input:** caminho do arquivo .md
**Output:** chunks criados no SQLite

**Assinatura interna:** `ingestFile(filePath, externalDb?, skipDelete?)`
- `externalDb`: conexão compartilhada (usado pelo reindex para evitar abrir/fechar 100+ conexões)
- `skipDelete`: pula DELETE antes de insert (usado pelo reindex pois tabela já está limpa)

**Algoritmo:**
1. Ler arquivo e aplicar `sanitizeUtf8()` — corrige mojibake de caracteres portugueses (ã→ã, ç→ç, é→é, etc.)
2. Chunking por seções Markdown (algoritmo detalhado abaixo)
3. Detectar `chunk_type` pela tabela de paths (ver seção 5)
4. Extrair `source_date`: do filename se match `YYYY-MM-DD`, senão `null`
5. Deletar chunks antigos desse `source_file` → inserir novos (upsert por file) — skip se `skipDelete=true`
6. FTS5 atualiza automaticamente via triggers (INSERT e DELETE)

**Algoritmo de chunking:**

1. **Splitter primário:** headers Markdown (`##`, `###`). Cada seção vira um chunk.
   - O header é preservado como primeira linha do chunk (dá contexto ao resultado de busca)
   - Se o arquivo não tem headers (ex: daily note plain text), usar double newline (`\n\n`) como separador
2. **Limite de tamanho:** se um chunk tem mais de 500 palavras (~375 tokens), sub-dividir por double newline
3. **Mínimo:** chunks com menos de 20 palavras são fundidos com o chunk anterior
4. **Overlap:** nenhum (headers dão contexto suficiente). Simplifica e evita duplicação no FTS5
5. **Arquivos JSON** (`feedback/*.json`): cada entry do array vira um chunk individual
6. **Arquivos curtos** (< 100 palavras total): o arquivo inteiro é 1 chunk

Exemplo para `lessons.md`:
```
Chunk 1: "### OpenClaw — Config\n- O campo `model` em `agents.defaults`..."
Chunk 2: "### 🔴 NUNCA pedir info que já foi dada\n- Totó não repete..."
Chunk 3: "### Comunicação com Totó\n- Totó cola texto da resposta..."
```

### 6.7 — `nox-mem stats`

Mostra estatísticas da memória.

**Output:**
```
Chunks: 507 total
  decisions: 23  |  lessons: 18  |  people: 12
  projects: 8    |  daily: 67    |  feedback: 9  |  team: 5

Consolidação: 14 processadas, 0 falhadas, 1 pendente
Última consolidação: 2026-03-14 23:00 BRT
Banco: 2.1 MB
```

Consulta `consolidated_files` para status de consolidação (processadas, falhadas, pendentes).

### 6.8 — `nox-mem retry-failed`

Reprocessa daily notes que falharam na consolidação anterior.

**Algoritmo:**
1. `DELETE FROM consolidated_files WHERE status = -1` — reseta entradas falhadas
2. Chama `consolidate()` normalmente — os arquivos resetados serão reprocessados
3. Também sincroniza itens novos com Notion (se habilitado)

### 6.9 — `nox-mem doctor`

Diagnóstico completo do sistema.

**Verifica:**
- SQLite: schema version, tabelas existentes, total de chunks
- FTS5: integridade do índice (`INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')`)
- Consolidação: quantas processadas, falhadas, pendentes
- Ollama: conectividade e modelo disponível (`config.ollama.model`)
- Notion: token configurado e válido (se `config.notion.enabled`)
- Watcher: status do serviço systemd `nox-mem-watcher`

### 6.10 — `nox-mem sync-notion` (standalone)

Re-sincroniza itens da última consolidação com o Notion.

**Algoritmo:**
1. Carrega `last-sync.json` (salvo automaticamente pelo consolidate)
2. Se vazio, reporta "No items to sync — run consolidate first"
3. Chama `syncToNotion(items)` com os itens salvos
4. Útil quando Notion estava offline durante consolidação — permite retry sem reconsolidar

---

## 7. File Watcher (inotifywait)

### Script wrapper: `nox-mem-watch.sh`

Script dedicado em vez de inline no systemd — mais seguro e testável:

```bash
#!/usr/bin/env bash
# ~/.openclaw/workspace/tools/nox-mem/nox-mem-watch.sh
# Debounced file watcher for nox-mem auto-indexation
set -euo pipefail

WORKSPACE="/root/.openclaw/workspace"
NOX_MEM="/root/.openclaw/workspace/tools/nox-mem/dist/index.js"
LOCK_DIR="/tmp/nox-mem-locks"
mkdir -p "$LOCK_DIR"

echo "[nox-mem-watch] Monitoring $WORKSPACE/memory and $WORKSPACE/shared ..."

inotifywait -m -r -e modify,create,delete \
    --include '.*\.(md|json)$' \
    "$WORKSPACE/memory" "$WORKSPACE/shared" 2>/dev/null | while read -r dir event file; do

    # Excluir arquivos que causam feedback loop
    [[ "$file" == "MEMORY.md" || "$file" == "SESSION-STATE.md" ]] && continue

    FULL_PATH="${dir}${file}"

    # Debounce via lock files (3s per file, usando md5sum como key)
    # NOTA: bash vars (LAST_FILE, LAST_TIME) não funcionam aqui porque
    # o pipe cria um subshell — variáveis não são compartilhadas
    LOCK_FILE="$LOCK_DIR/$(echo "$FULL_PATH" | md5sum | cut -d' ' -f1).lock"
    if [ -f "$LOCK_FILE" ]; then
        LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
        if [ "$LOCK_AGE" -lt 3 ]; then
            continue
        fi
    fi
    touch "$LOCK_FILE"

    echo "[nox-mem-watch] Changed: $FULL_PATH — reindexing..."
    node "$NOX_MEM" ingest "$FULL_PATH" 2>&1 || true
done
```

### Serviço systemd: `nox-mem-watcher.service`

```ini
[Unit]
Description=Nox Memory File Watcher (inotifywait + debounce)
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash /root/.openclaw/workspace/tools/nox-mem/nox-mem-watch.sh
Restart=on-failure
RestartSec=5
User=root
WorkingDirectory=/root/.openclaw/workspace

[Install]
WantedBy=multi-user.target
```

**Arquivos monitorados:**
- `memory/*.md` — daily notes e topic files
- `memory/feedback/*.json` — feedback loops
- `shared/*.md` — memória do time

**Explicitamente excluídos:**
- `MEMORY.md` — gerado pela consolidação, não é fonte de busca (evita feedback loop)
- `SESSION-STATE.md` — volátil, não indexado
- `SOUL.md`, `IDENTITY.md`, `TOOLS.md` — config, não memória
- `tools/`, `skills/`, `backups/` — não são memória

**Debounce:** 3 segundos entre re-ingestões do mesmo arquivo, implementado via lock files em `/tmp/nox-mem-locks/` (usando md5sum do path como key). Lock files são necessários porque variáveis bash não são compartilhadas através do pipe subshell do inotifywait.

---

## 8. Crons — Modelo de Execução

### Como os crons funcionam no OpenClaw

Os crons do OpenClaw são **tarefas agendadas que abrem uma sessão de agente**. O `model` define qual LLM processa, e o `prompt` é a instrução. O agente (Nox) recebe o prompt e executa usando suas tools — incluindo shell access.

Portanto, o Nox recebe o prompt e executa `nox-mem consolidate` via shell tool. **Não é execução direta de CLI** — é o agente decidindo executar o comando.

O `timeout` é para a sessão inteira do agente (LLM + tool calls), não só para o Ollama. Consolidação pode envolver: ler daily notes + chamar Ollama (até 120s) + escrever topic files + git commit. Por isso timeout generoso.

### 8.1 — Consolidação diária (23h BRT)

```json
{
    "name": "memory-consolidation",
    "schedule": "0 23 * * *",
    "model": "llama3.2:3b",
    "timeout": 480,
    "prompt": "Execute o comando `nox-mem consolidate` no shell. Ele processa daily notes pendentes, atualiza topic files e MEMORY.md automaticamente. Se o output disser 'nothing to consolidate', responda HEARTBEAT_OK. Se houver erro, reporte. Não faça nada além de executar o comando."
}
```

### 8.2 — Weekly digest (domingo 21h BRT)

```json
{
    "name": "memory-digest",
    "schedule": "0 21 * * 0",
    "model": "llama3.2:3b",
    "timeout": 300,
    "prompt": "Execute o comando `nox-mem digest` no shell. Ele gera o resumo semanal automaticamente em memory/digests/. Se funcionar, responda HEARTBEAT_OK. Se houver erro, reporte."
}
```

### 8.3 — Inclusão no backup (já existente, a cada 6h)

Adicionar `nox-mem.db` ao script de backup existente:
```bash
# No backup-config.sh existente, adicionar:
cp ~/.openclaw/workspace/tools/nox-mem/nox-mem.db "$BACKUP_DIR/nox-mem.db"
```

---

## 9. Integração com SOUL.md do Nox

### Bloco a adicionar: Memória Inteligente

```markdown
## Memória Inteligente — nox-mem

### Quando buscar (OBRIGATÓRIO)
- Toto pergunta sobre algo do passado → `nox-mem search "<query>"`
- Preciso de contexto de projeto/pessoa/decisão → `nox-mem search`
- Recovery de compaction → `nox-mem primer`
- Agente pede contexto histórico → `nox-mem search` e repassa resultado
- NUNCA perguntar ao Toto algo que já foi dito — buscar primeiro

### Quando NÃO buscar
- Informação está no SESSION-STATE.md (sessão atual)
- Informação está no MEMORY.md (já no system prompt)
- Pergunta simples que não precisa de histórico

### Compaction Recovery — ATUALIZADO
Ao recuperar de compaction:
1. `nox-mem primer` → contexto resumido (~500 tokens)
2. Ler SESSION-STATE.md → tarefa ativa
3. Continuar sem perguntar "onde estávamos?"
NÃO ler working-buffer.md (deprecated pelo nox-mem primer)
```

### Bloco a adicionar: TOOLS.md

```markdown
## nox-mem — Sistema de Memória Inteligente

Busca e consolidação de memória do time. Fonte: SQLite com FTS5 indexando
todos os .md do workspace. Markdown é source of truth — banco é cache.

### Comandos
- `nox-mem search "<query>"` — busca na memória, retorna top-5 chunks
- `nox-mem primer` — resumo de contexto pós-compaction (~500 tokens)
- `nox-mem consolidate` — consolida daily notes em topic files (IA local, max 5/run)
- `nox-mem retry-failed` — reprocessa consolidações que falharam
- `nox-mem digest` — gera resumo semanal
- `nox-mem reindex` — reconstrói índice (preserva estado de consolidação)
- `nox-mem stats` — contagem de chunks, consolidações, tamanho do banco
- `nox-mem ingest <file>` — indexa arquivo específico
- `nox-mem sync-notion` — re-sincroniza última consolidação com Notion
- `nox-mem doctor` — diagnóstico completo (SQLite, FTS5, Ollama, Notion, watcher)
```

---

## 9b. Notion Sync — Diário do Projeto

A consolidação (cron 23h) automaticamente sincroniza itens novos extraídos com a database **Memória & Decisões** no Notion, criando um diário visual do projeto.

### Database Notion

- **ID:** `31d8e29911ab8163b718d7af565f2fcc`
- **Token:** lido de `~/.config/notion/api_key`
- **API:** `https://api.notion.com/v1/pages` (Notion-Version: 2025-09-03)

### Schema da Database

| Propriedade | Tipo | Mapeamento |
|---|---|---|
| Título | title | Primeira linha ou resumo do item |
| Data | date | source_date da daily note |
| Categoria | select | Mapeado do tipo de extração (ver abaixo) |
| Conteúdo | rich_text | Texto completo do item extraído |
| Fonte | rich_text | Path do arquivo fonte (ex: `memory/2026-03-14.md`) |

### Mapeamento de categorias

| Tipo de extração | Categoria Notion |
|---|---|
| `decisions[]` | Decisão |
| `lessons[]` | Lição |
| `people[]` | Contexto |
| `projects[]` | Contexto |
| `pending[]` | Pendência |
| nox-mem system events | Sistema Openclaw |

### Fluxo

```
nox-mem consolidate
    ├── Extrai fatos da daily note (Ollama)
    ├── Deduplica e appenda nos topic files (.md)
    ├── Coleta itens novos (não-duplicatas)
    └── syncToNotion(items) — cria 1 page por item
        ├── Rate limit: 3 req/s (API Notion)
        └── Best-effort: falha não bloqueia consolidação
```

### Persistência de sync log

Consolidação salva itens novos em `last-sync.json` antes de enviar ao Notion. Isso permite:
- `nox-mem sync-notion` — re-sync manual se Notion estava offline
- Retry sem reconsolidar (econômico em CPU/Ollama)

### Regras

- Notion sync é o **último passo** da consolidação — nunca o primeiro
- Se a API do Notion falhar → `[WARN]` log, itens locais já foram salvos nos .md + `last-sync.json`
- `nox-mem sync-notion` pode ser chamado manualmente para re-sync
- Rate limit: 350ms entre requests (~3 req/s para respeitar limits da API)

---

## 10. Fases de Implementação

### Fase 1 — Core (IMPLEMENTADO 2026-03-14, v2.1.2)

| Step | O que | Dependência |
|---|---|---|
| 1.1 | Instalar SQLite3 na VPS | — |
| 1.2 | Instalar Ollama + pull llama3.2:3b | — |
| 1.3 | Instalar inotify-tools (`apt install inotify-tools`) | — |
| 1.4 | Criar projeto nox-mem (Node.js + TypeScript) | 1.1 |
| 1.5 | Implementar `db.ts` (schema, conexão) | 1.4 |
| 1.6 | Implementar `ingest.ts` (chunking + FTS5) | 1.5 |
| 1.7 | Implementar `search.ts` (busca híbrida) | 1.5 |
| 1.8 | Implementar `primer.ts` (context recovery) | 1.7 |
| 1.9 | Implementar `reindex.ts` | 1.6 |
| 1.10 | Implementar `index.ts` (CLI entry point) | 1.6-1.9 |
| 1.11 | Rodar `nox-mem reindex` (indexação inicial) | 1.10 |
| 1.12 | Configurar nox-mem-watcher.service (systemd) | 1.10 |
| 1.13 | Testar search com queries reais | 1.11 |
| 1.14 | Implementar `consolidate.ts` (Ollama + Llama) | 1.2, 1.6 |
| 1.15 | Implementar `digest.ts` | 1.14 |
| 1.16 | Criar crons no OpenClaw (23h + dom 21h) | 1.14, 1.15 |
| 1.17 | Atualizar SOUL.md + TOOLS.md do Nox | 1.13 |
| 1.18 | Adicionar nox-mem.db ao backup script | 1.11 |
| 1.19 | Testar end-to-end (busca, consolidação, primer) | tudo |
| 1.20 | Git commit + push | 1.19 |

### Fase 2 — Notion Sync + Refinamentos (IMPLEMENTADO 2026-03-14, v2.1.2)

Implementado durante as 6 rodadas de code review:
- Schema v2: `consolidated_files` table separada (sobrevive reindex)
- Notion sync automático com database "Memória & Decisões"
- `retry-failed` e `doctor` commands
- `appendInSection()` (inserção dentro de seções Markdown)
- `sanitizeUtf8()` (encoding português)
- Max 5 files per consolidation run
- Lock file debounce no watcher
- ISO 8601 week numbers no digest

### Fase 3 — Semantic Search (quando memória > 1000 chunks)

| Step | O que |
|---|---|
| 2.1 | Instalar modelo all-MiniLM-L6-v2 no Ollama |
| 2.2 | Instalar sqlite-vec (extensão) |
| 2.3 | Adicionar coluna embedding + tabela chunks_vec |
| 2.4 | Atualizar ingest.ts para gerar embeddings |
| 2.5 | Atualizar search.ts para busca híbrida (FTS5 + vector) |
| 2.6 | Adicionar tabela relations + extração de relações na consolidação |
| 2.7 | Implementar decay weights para daily notes |
| 2.8 | Atualizar primer.ts para usar contexto semântico |

---

## 11. Testes de Validação

### Fase 1 — Critérios de sucesso

| Teste | Critério |
|---|---|
| `nox-mem search "limite linkedin"` | Retorna chunk de lessons.md como #1 |
| `nox-mem search "fernando busnello"` | Retorna chunk de people.md |
| `nox-mem search "voo miami"` | Retorna daily notes recentes sobre voo |
| `nox-mem primer` | Gera resumo com tarefa ativa + decisões recentes |
| `nox-mem consolidate` | Processa daily note e cria entry em decisions.md |
| `nox-mem reindex` | Reconstrói banco sem erro |
| `nox-mem stats` | Mostra contagem correta de chunks por tipo |
| Editar memory/*.md | inotifywait detecta e re-ingesta em <5s |
| Corromper nox-mem.db | `nox-mem reindex` restaura tudo dos .md |
| Ollama offline | Consolidação falha gracefully, search continua ok |

---

## 12. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| SQLite corrompe | Baixa | Médio | Markdown é source of truth + reindex |
| Ollama consome RAM demais | Baixa | Baixo | Llama 3.2 3B usa ~2GB pico, VPS tem 13GB livre |
| inotifywait morre | Média | Baixo | systemd restart automático + search continua sem ele |
| Consolidação extrai fatos errados | Média | Médio | Append-only nos topic files + Nox pode corrigir |
| Chunking ruim (corta contexto) | Média | Baixo | Headers Markdown preservados em cada chunk fornecem contexto da seção |
| FTS5 não acha por falta de keyword | Alta (Fase 1-2) | Médio | Fase 3 adiciona busca semântica |

---

## 13. Estrutura de Arquivos

```
~/.openclaw/workspace/tools/nox-mem/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              → CLI entry point + arg parser
│   ├── db.ts                 → SQLite conexão, schema, migrations
│   ├── ingest.ts             → chunking (.md → paragraphs) + insert FTS5
│   ├── search.ts             → busca FTS5 + boost + recência
│   ├── primer.ts             → context recovery pós-compaction (3 format parsers)
│   ├── consolidate.ts        → Ollama Llama 3.2 → extrai fatos → atualiza topic files
│   ├── appendInSection.ts    → utilitário: insere conteúdo dentro de seções Markdown
│   ├── notion-sync.ts        → sync com Notion database (opcional)
│   ├── digest.ts             → resumo semanal (Ollama, temp 0.3)
│   ├── doctor.ts             → diagnóstico completo do sistema
│   ├── reindex.ts            → rebuild índice (preserva consolidated_files)
│   └── stats.ts              → contagens e métricas
├── nox-mem.db                → SQLite database v2 (auto-criado, gitignored)
├── nox-mem-watch.sh          → file watcher com debounce via lock files
└── prompts/
    ├── consolidate.txt       → prompt template para extração de fatos
    └── digest.txt            → prompt template para resumo semanal
```

---

## 14. Não-objetivos (explicitamente fora de escopo)

- Acesso direto dos agentes (Boris, Atlas etc.) ao nox-mem — sempre via Nox
- Interface web ou dashboard — memória é consultada via CLI
- ~~Sync com serviços externos (Notion)~~ — **IMPLEMENTADO** na v2: sync automático com Notion database "Memória & Decisões"
- Substituir o sistema de Markdown — SQLite é upgrade, não replacement
- Multi-tenancy — um banco, um Nox, um time

---

## 15. Glossário

| Termo | Definição |
|---|---|
| **Chunk** | Parágrafo ou seção de um arquivo .md, unidade mínima de busca (~300 tokens) |
| **Topic file** | Arquivo curado com informação permanente (decisions.md, lessons.md, etc.) |
| **Daily note** | Arquivo raw de captura diária (memory/YYYY-MM-DD.md) |
| **Consolidação** | Processo IA que extrai fatos de daily notes e atualiza topic files |
| **Primer** | Resumo compacto (~500 tokens) para recovery de contexto pós-compactação |
| **WAL Protocol** | Write-Ahead Log — escrever em SESSION-STATE.md antes de responder |
| **Decay** | Redução de relevância de chunks antigos (Fase 2) |
| **Boost** | Multiplicador de score para topic files na busca |
