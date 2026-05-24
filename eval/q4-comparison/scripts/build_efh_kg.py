#!/usr/bin/env python3
"""
Build KG entities + relations on the Path E+F+H @500 eval DB.

Uses Gemini Flash Lite (gemini-2.5-flash-lite) to extract (subject, predicate,
object) triples per chunk. Stores them in two new tables:

    kg_entities (id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT)
    kg_relations (id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER,
                  predicate TEXT, chunk_id TEXT,
                  FOREIGN KEY (source_id) REFERENCES kg_entities(id),
                  FOREIGN KEY (target_id) REFERENCES kg_entities(id))
    kg_chunk_entities (chunk_id TEXT, entity_id INTEGER,
                       PRIMARY KEY (chunk_id, entity_id))

Cost: ~500 chunks × ~500 tokens × $0.075/1M = ~$0.02 (cheap).
Time: 500 chunks × ~50ms (rate-limited) = ~25s + Gemini latency = ~5-8 min.

Idempotent: if kg_entities already populated, skip extraction.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DB_PATH = HERE / "cache" / "efh" / "nox-mem-hybrid-500.db"

KG_MODEL = "gemini-2.5-flash-lite"
KG_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
RATE_DELAY_S = 0.10  # ~10 RPS, well under quota
MAX_CHUNK_CHARS = 1500
MAX_ENTITIES_PER_CHUNK = 8

EXTRACT_PROMPT = """Extract entities and relations from the conversation snippet below.
Return JSON only with this exact schema:
{
  "entities": [{"name": "string", "type": "person|place|object|event|concept|other"}, ...],
  "relations": [{"source": "string", "target": "string", "predicate": "string"}, ...]
}

Rules:
- Use canonical names (e.g. "Deborah" not "she", "Tokyo" not "the city").
- Skip pronouns. Skip generic stop-words.
- Max 8 entities per snippet. Max 6 relations.
- predicate should be 1-3 words: "lives_in", "likes", "met", "owns", etc.
- If nothing notable, return {"entities": [], "relations": []}.

Snippet:
{TEXT}

JSON:"""


def get_key() -> str:
    k = os.environ.get("GEMINI_API_KEY", "")
    if not k:
        raise SystemExit("GEMINI_API_KEY not set — source /tmp/q4-gemini-env.sh first")
    return k


def parse_json_safely(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def create_kg_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS kg_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'other'
        );
        CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name);

        CREATE TABLE IF NOT EXISTS kg_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            predicate TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES kg_entities(id),
            FOREIGN KEY (target_id) REFERENCES kg_entities(id)
        );
        CREATE INDEX IF NOT EXISTS idx_kg_relations_src ON kg_relations(source_id);
        CREATE INDEX IF NOT EXISTS idx_kg_relations_tgt ON kg_relations(target_id);
        CREATE INDEX IF NOT EXISTS idx_kg_relations_chunk ON kg_relations(chunk_id);

        CREATE TABLE IF NOT EXISTS kg_chunk_entities (
            chunk_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            PRIMARY KEY (chunk_id, entity_id),
            FOREIGN KEY (entity_id) REFERENCES kg_entities(id)
        );
        CREATE INDEX IF NOT EXISTS idx_kg_chunk_entities_ent
            ON kg_chunk_entities(entity_id);
    """)
    con.commit()


def kg_ready(con: sqlite3.Connection) -> bool:
    try:
        n = con.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
        return n > 0
    except sqlite3.OperationalError:
        return False


def upsert_entity(con: sqlite3.Connection, name: str, ent_type: str) -> int | None:
    name = (name or "").strip()
    if not name or len(name) < 2 or len(name) > 80:
        return None
    # Normalise: lowercase for matching, but keep original case for display.
    canon = name.lower()
    existing = con.execute(
        "SELECT id FROM kg_entities WHERE LOWER(name)=?", (canon,)
    ).fetchone()
    if existing:
        return existing[0]
    cur = con.execute(
        "INSERT INTO kg_entities(name, type) VALUES (?, ?)",
        (name, (ent_type or "other").lower()),
    )
    return cur.lastrowid


def extract_one_chunk(text: str, api_key: str) -> dict:
    import requests
    payload = {
        "contents": [
            {"parts": [{"text": EXTRACT_PROMPT.replace("{TEXT}", text[:MAX_CHUNK_CHARS])}]}
        ],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.95,
            "maxOutputTokens": 400,
            "responseMimeType": "application/json",
        },
    }
    url = KG_ENDPOINT.format(model=KG_MODEL)
    try:
        r = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=20,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        msg = str(e)
        msg = re.sub(r"key=[A-Za-z0-9_\-]+", "key=<REDACTED>", msg)
        msg = re.sub(r"AIza[A-Za-z0-9_\-]{10,}", "AIza<REDACTED>", msg)
        return {"_error": f"{type(e).__name__}: {msg}"}

    candidates = data.get("candidates") or []
    if not candidates:
        return {"_error": "no candidates"}
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text_out = "".join(p.get("text", "") for p in parts)
    parsed = parse_json_safely(text_out)
    if not isinstance(parsed, dict):
        return {"_error": "non-dict response"}
    return parsed


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}. Run build_efh_500_db.py first.", file=sys.stderr)
        return 1

    api_key = get_key()

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    create_kg_schema(con)

    if kg_ready(con):
        n_ent = con.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
        n_rel = con.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
        n_chunk_ent = con.execute("SELECT COUNT(*) FROM kg_chunk_entities").fetchone()[0]
        print(
            f"[build_kg] KG already built: {n_ent} entities, "
            f"{n_rel} relations, {n_chunk_ent} chunk-entity links. Skipping.",
            file=sys.stderr,
        )
        return 0

    chunks = con.execute(
        "SELECT id, text FROM eval_chunks ORDER BY rowid"
    ).fetchall()
    print(f"[build_kg] extracting KG from {len(chunks)} chunks via {KG_MODEL}...", file=sys.stderr)

    n_ok = 0
    n_err = 0
    n_ents = 0
    n_rels = 0
    n_chunk_ents = 0
    t_start = time.time()

    for i, (chunk_id, text) in enumerate(chunks, 1):
        time.sleep(RATE_DELAY_S)
        result = extract_one_chunk(text, api_key)
        if "_error" in result:
            n_err += 1
            if n_err <= 5:
                print(f"[build_kg] chunk {chunk_id} error: {result['_error']}", file=sys.stderr)
            if i % 50 == 0:
                elapsed = time.time() - t_start
                print(
                    f"[build_kg] progress {i}/{len(chunks)} "
                    f"({n_ok} ok, {n_err} err, "
                    f"{n_ents} ents, {n_rels} rels) — {elapsed:.0f}s",
                    file=sys.stderr,
                )
            continue

        n_ok += 1
        entities = (result.get("entities") or [])[:MAX_ENTITIES_PER_CHUNK]
        relations = (result.get("relations") or [])[:6]

        # Insert entities + chunk-entity links
        name_to_id: dict[str, int] = {}
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            ent_id = upsert_entity(con, ent.get("name", ""), ent.get("type", "other"))
            if ent_id is None:
                continue
            name_to_id[(ent.get("name") or "").strip().lower()] = ent_id
            try:
                con.execute(
                    "INSERT OR IGNORE INTO kg_chunk_entities(chunk_id, entity_id) "
                    "VALUES (?, ?)",
                    (chunk_id, ent_id),
                )
                n_chunk_ents += 1
            except sqlite3.IntegrityError:
                pass
            n_ents += 1

        # Insert relations
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            src_name = (rel.get("source") or "").strip().lower()
            tgt_name = (rel.get("target") or "").strip().lower()
            predicate = (rel.get("predicate") or "").strip()
            if not src_name or not tgt_name or not predicate:
                continue
            src_id = name_to_id.get(src_name) or upsert_entity(con, rel.get("source", ""), "other")
            tgt_id = name_to_id.get(tgt_name) or upsert_entity(con, rel.get("target", ""), "other")
            if src_id is None or tgt_id is None or src_id == tgt_id:
                continue
            con.execute(
                "INSERT INTO kg_relations(source_id, target_id, predicate, chunk_id) "
                "VALUES (?, ?, ?, ?)",
                (src_id, tgt_id, predicate[:40], chunk_id),
            )
            n_rels += 1

        # Commit every 25 chunks so we don't lose progress on interrupt.
        if i % 25 == 0:
            con.commit()
            elapsed = time.time() - t_start
            print(
                f"[build_kg] progress {i}/{len(chunks)} "
                f"({n_ok} ok, {n_err} err, "
                f"{n_ents} ents-stored, {n_rels} rels, "
                f"{n_chunk_ents} links) — {elapsed:.0f}s",
                file=sys.stderr,
            )

    con.commit()
    elapsed = time.time() - t_start

    # Final stats
    total_ents = con.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
    total_rels = con.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
    total_links = con.execute("SELECT COUNT(*) FROM kg_chunk_entities").fetchone()[0]
    print(
        f"[build_kg] DONE in {elapsed:.0f}s — "
        f"unique entities={total_ents}, relations={total_rels}, "
        f"chunk-entity links={total_links}, errors={n_err}",
        file=sys.stderr,
    )

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
