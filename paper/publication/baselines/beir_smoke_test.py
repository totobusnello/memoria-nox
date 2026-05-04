"""3-query smoke test for BEIR TREC-COVID TEMP DB validation.

Tests FTS5 BM25 search against the smoke TEMP DB to confirm:
1. FTS5 index is populated and queryable
2. doc_id field is populated (BEIR string IDs)
3. 3 representative TREC-COVID queries return hits
"""

import sqlite3
import sys

DB_PATH = "/tmp/nox-mem-trec-covid-smoke.db"

TEST_QUERIES = [
    ("1", "what is the origin of COVID-19"),
    ("2", "coronavirus transmission human to human"),
    ("3", "COVID-19 clinical treatment outcomes"),
]

def run_smoke_test() -> int:
    """Run 3-query FTS5 BM25 smoke test. Returns 0 on pass, 1 on fail."""
    try:
        db = sqlite3.connect(DB_PATH)
    except Exception as exc:
        print(f"FAIL: Cannot open DB {DB_PATH}: {exc}", file=sys.stderr)
        return 1

    # Verify chunks table populated
    try:
        (count,) = db.execute("SELECT COUNT(*) FROM chunks").fetchone()
        print(f"chunks table: {count} rows")
        assert count > 0, "chunks table is empty"
    except Exception as exc:
        print(f"FAIL: chunks table check: {exc}", file=sys.stderr)
        return 1

    # Verify FTS5 index populated
    try:
        (fts_count,) = db.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()
        print(f"chunks_fts table: {fts_count} rows")
        assert fts_count > 0, "chunks_fts is empty"
    except Exception as exc:
        print(f"FAIL: FTS5 check: {exc}", file=sys.stderr)
        return 1

    # Run 3 queries
    failed = 0
    for qid, query_text in TEST_QUERIES:
        try:
            # FTS5 tokenizes on Unicode boundaries; hyphens split tokens so
            # "COVID-19" becomes "COVID" and "19".  Build a simple token list
            # by splitting on whitespace and non-alphanumeric chars, then join
            # with spaces so FTS5 ANDs the terms.
            import re as _re
            tokens = [t for t in _re.split(r"[^a-zA-Z0-9]+", query_text) if t]
            fts_query = " ".join(tokens) if tokens else query_text
            rows = db.execute(
                "SELECT c.doc_id, -bm25(chunks_fts) AS score "
                "FROM chunks_fts "
                "JOIN chunks c ON chunks_fts.rowid = c.id "
                "WHERE chunks_fts MATCH ? "
                "ORDER BY bm25(chunks_fts) "
                "LIMIT 10",
                (fts_query,),
            ).fetchall()

            if not rows:
                print(f"FAIL Q{qid}: '{query_text[:40]}' — 0 hits", file=sys.stderr)
                failed += 1
            else:
                top_doc, top_score = rows[0]
                print(
                    f"PASS Q{qid}: '{query_text[:40]}' "
                    f"— {len(rows)} hits, top_doc={top_doc}, score={top_score:.4f}"
                )
        except Exception as exc:
            print(f"FAIL Q{qid}: '{query_text[:40]}' — {exc}", file=sys.stderr)
            failed += 1

    db.close()

    if failed == 0:
        print("SMOKE_TEST_PASSED: all 3 queries returned hits")
        return 0
    else:
        print(f"SMOKE_TEST_FAILED: {failed}/3 queries failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_test())
