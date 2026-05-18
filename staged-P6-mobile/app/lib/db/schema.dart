/// db/schema.dart — SQL schema mobile (simplificado do nox-mem VPS).
///
/// Diferenças vs VPS:
///   - sem `vec_chunks` (embeddings 3072d × 5k = ~60MB; v2+)
///   - sem `ops_audit` (log fica na VPS)
///   - `mobile_*` prefix em todas as tabelas (evita colisão se for inspecionar
///     o DB com ferramenta que assume schema VPS)
///   - `vps_id` é coluna canônica de reference; NULL durante captura offline.
///
/// Schema versionado via [SCHEMA_VERSION] + tabela `_meta`.
library schema;

/// Versão atual do schema. Bump quando adicionar migration em
/// `migrations.dart`.
const int schemaVersion = 1;

/// SQL statements para criar schema do zero (v1).
const List<String> createSchemaV1 = [
  // Metadata table (track schema version + last sync ts).
  '''
  CREATE TABLE IF NOT EXISTS _meta (
    key   TEXT PRIMARY KEY,
    value TEXT
  )
  ''',

  // Chunks — subset relevante do corpus VPS.
  '''
  CREATE TABLE IF NOT EXISTS mobile_chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vps_id        INTEGER UNIQUE,
    text          TEXT NOT NULL,
    type          TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    pain          REAL DEFAULT 0.2,
    section       TEXT,
    section_boost REAL DEFAULT 1.0,
    sync_status   TEXT NOT NULL DEFAULT 'pending',
    last_sync_ts  TEXT,
    base_text     TEXT,
    CHECK (sync_status IN ('synced', 'pending', 'conflict'))
  )
  ''',

  // FTS5 vai ser reconstruído após cada sync — não persiste estrutura aqui.
  '''
  CREATE VIRTUAL TABLE IF NOT EXISTS mobile_chunks_fts USING fts5(
    text,
    content='mobile_chunks',
    content_rowid='id',
    tokenize = 'unicode61 remove_diacritics 2'
  )
  ''',

  // KG entities — subset compacto.
  '''
  CREATE TABLE IF NOT EXISTS mobile_kg_entities (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    vps_id  INTEGER UNIQUE,
    name    TEXT NOT NULL,
    type    TEXT,
    summary TEXT
  )
  ''',

  // KG relations.
  '''
  CREATE TABLE IF NOT EXISTS mobile_kg_relations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vps_id           INTEGER UNIQUE,
    source_entity_id INTEGER REFERENCES mobile_kg_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER REFERENCES mobile_kg_entities(id) ON DELETE CASCADE,
    relation_type    TEXT,
    confidence       REAL
  )
  ''',

  // Sync log — append-only, observability.
  '''
  CREATE TABLE IF NOT EXISTS mobile_sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at   TEXT NOT NULL DEFAULT (datetime('now')),
    direction   TEXT NOT NULL,
    chunks_sent INTEGER DEFAULT 0,
    chunks_recv INTEGER DEFAULT 0,
    conflicts   INTEGER DEFAULT 0,
    error       TEXT,
    CHECK (direction IN ('upload', 'download', 'full'))
  )
  ''',

  // Pending uploads — items capturados offline aguardando sync.
  '''
  CREATE TABLE IF NOT EXISTS mobile_pending_uploads (
    local_id   TEXT PRIMARY KEY,
    chunk_id   INTEGER NOT NULL REFERENCES mobile_chunks(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    attempts   INTEGER DEFAULT 0,
    last_error TEXT
  )
  ''',

  // Indices.
  'CREATE INDEX IF NOT EXISTS idx_chunks_sync_status ON mobile_chunks(sync_status)',
  'CREATE INDEX IF NOT EXISTS idx_chunks_updated_at ON mobile_chunks(updated_at)',
  'CREATE INDEX IF NOT EXISTS idx_chunks_type ON mobile_chunks(type)',
  'CREATE INDEX IF NOT EXISTS idx_relations_source ON mobile_kg_relations(source_entity_id)',
  'CREATE INDEX IF NOT EXISTS idx_relations_target ON mobile_kg_relations(target_entity_id)',

  // Triggers de FTS5 sync — mantém índice em sync com mobile_chunks.
  '''
  CREATE TRIGGER IF NOT EXISTS mobile_chunks_ai AFTER INSERT ON mobile_chunks BEGIN
    INSERT INTO mobile_chunks_fts(rowid, text) VALUES (new.id, new.text);
  END
  ''',

  '''
  CREATE TRIGGER IF NOT EXISTS mobile_chunks_ad AFTER DELETE ON mobile_chunks BEGIN
    INSERT INTO mobile_chunks_fts(mobile_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
  END
  ''',

  '''
  CREATE TRIGGER IF NOT EXISTS mobile_chunks_au AFTER UPDATE ON mobile_chunks BEGIN
    INSERT INTO mobile_chunks_fts(mobile_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO mobile_chunks_fts(rowid, text) VALUES (new.id, new.text);
  END
  ''',

  // Init metadata.
  "INSERT OR REPLACE INTO _meta(key, value) VALUES ('schema_version', '1')",
  "INSERT OR REPLACE INTO _meta(key, value) VALUES ('last_sync_ts', '')",
];
