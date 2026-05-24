#!/usr/bin/env python3
"""
Build the @500 cap hybrid DB for Path E+F+H ablation by SUBSETTING the
existing full hybrid DB (6822 chunks → first 500 LoCoMo chunks).

WHY subset rather than re-ingest?
- The full DB (`cache/nox-mem-eval-hybrid.db`, 6822 chunks) was built by
  PR #338 with the same Gemini embeddings we'd otherwise re-spend $$ on.
- The PR #318 baseline (hybrid@500 = 0.0918) used the *first 500 ingested
  chunks*, which by construction are the first 500 LoCoMo chunks
  (rowid <= 500, dataset='locomo'). Subsetting reproduces that exact set.
- Gemini cost: $0 (no re-embedding) vs ~$0.003 for fresh ingest.

Output DB: `cache/efh/nox-mem-hybrid-500.db` (~8 MB)
"""
from __future__ import annotations

import shutil
import sqlite3
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/
SRC = HERE / "cache" / "nox-mem-eval-hybrid.db"
DST_DIR = HERE / "cache" / "efh"
DST = DST_DIR / "nox-mem-hybrid-500.db"


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: source DB not found at {SRC}", file=sys.stderr)
        return 1

    DST_DIR.mkdir(parents=True, exist_ok=True)
    if DST.exists():
        print(f"[build_500] removing existing {DST}", file=sys.stderr)
        DST.unlink()

    # Step 1: read source chunks (rowid <= 500) into a memory list, plus their vectors.
    print(f"[build_500] reading source: {SRC}", file=sys.stderr)
    src_con = sqlite3.connect(str(SRC))

    # Load sqlite-vec into source (needed for reading vec0 BLOBs).
    import sqlite_vec  # type: ignore
    src_con.enable_load_extension(True)
    sqlite_vec.load(src_con)
    src_con.enable_load_extension(False)

    chunks = src_con.execute(
        "SELECT id, dataset, conv_id, day, text "
        "FROM eval_chunks "
        "WHERE rowid <= 500 AND dataset='locomo' "
        "ORDER BY rowid"
    ).fetchall()
    print(f"[build_500] selected {len(chunks)} chunks", file=sys.stderr)

    # Pull vectors keyed by chunk_id via eval_chunk_rowids
    chunk_ids = [c[0] for c in chunks]
    placeholders = ",".join("?" for _ in chunk_ids)
    vec_rows = src_con.execute(
        f"SELECT r.chunk_id, v.embedding "
        f"FROM eval_chunk_rowids r JOIN eval_vecs v ON v.rowid = r.rowid "
        f"WHERE r.chunk_id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    vec_map = {cid: blob for cid, blob in vec_rows}
    print(f"[build_500] selected {len(vec_map)} vectors", file=sys.stderr)

    # Probe dimension
    embed_dim = None
    for blob in vec_map.values():
        embed_dim = len(blob) // 4  # float32
        break
    if embed_dim is None:
        print("ERROR: no vectors found", file=sys.stderr)
        return 1
    print(f"[build_500] embedding dim={embed_dim}", file=sys.stderr)

    src_con.close()

    # Step 2: create destination DB with hybrid schema
    print(f"[build_500] building destination: {DST}", file=sys.stderr)
    dst_con = sqlite3.connect(str(DST))
    dst_con.enable_load_extension(True)
    sqlite_vec.load(dst_con)
    dst_con.enable_load_extension(False)
    dst_con.execute("PRAGMA journal_mode=WAL")

    dst_con.executescript(f"""
        CREATE TABLE eval_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE eval_chunks (
            id      TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            conv_id TEXT NOT NULL,
            day     INTEGER NOT NULL DEFAULT 0,
            text    TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE eval_chunks_fts USING fts5(
            text,
            content='eval_chunks',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER trg_hybrid_ai AFTER INSERT ON eval_chunks BEGIN
            INSERT INTO eval_chunks_fts(rowid, text) VALUES (new.rowid, new.text);
        END;
        CREATE TRIGGER trg_hybrid_ad AFTER DELETE ON eval_chunks BEGIN
            INSERT INTO eval_chunks_fts(eval_chunks_fts, rowid, text)
                VALUES ('delete', old.rowid, old.text);
        END;
        CREATE TABLE eval_chunk_rowids (
            chunk_id TEXT PRIMARY KEY,
            rowid    INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE eval_vecs USING vec0(embedding float[{embed_dim}]);
    """)
    dst_con.execute(
        "INSERT INTO eval_meta(key, value) VALUES ('embed_dim', ?)",
        (str(embed_dim),),
    )
    dst_con.commit()

    # Step 3: insert chunks + vectors
    inserted = 0
    for cid, dataset, conv_id, day, text in chunks:
        dst_con.execute(
            "INSERT INTO eval_chunks(id, dataset, conv_id, day, text) VALUES (?, ?, ?, ?, ?)",
            (cid, dataset, conv_id, day, text),
        )
        new_rowid = dst_con.execute(
            "SELECT rowid FROM eval_chunks WHERE id=?", (cid,)
        ).fetchone()[0]
        vec_blob = vec_map.get(cid)
        if vec_blob is not None:
            dst_con.execute(
                "INSERT INTO eval_vecs(rowid, embedding) VALUES (?, ?)",
                (new_rowid, vec_blob),
            )
            dst_con.execute(
                "INSERT INTO eval_chunk_rowids(chunk_id, rowid) VALUES (?, ?)",
                (cid, new_rowid),
            )
            inserted += 1

    dst_con.commit()
    print(f"[build_500] inserted {inserted} chunks+vectors", file=sys.stderr)

    # Verify
    cnt_chunks = dst_con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
    cnt_vecs = dst_con.execute("SELECT COUNT(*) FROM eval_vecs").fetchone()[0]
    cnt_fts = dst_con.execute("SELECT COUNT(*) FROM eval_chunks_fts").fetchone()[0]
    print(
        f"[build_500] VERIFY: chunks={cnt_chunks} vecs={cnt_vecs} fts={cnt_fts}",
        file=sys.stderr,
    )

    dst_con.close()
    size_mb = DST.stat().st_size / (1024 * 1024)
    print(f"[build_500] DONE: {DST} ({size_mb:.1f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
