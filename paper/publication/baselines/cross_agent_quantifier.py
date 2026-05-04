#!/usr/bin/env python3
"""
cross_agent_quantifier.py — E12 Cross-Agent Intelligence Quantification
nox-mem paper §5 — Diferencial #3: Shared-Canonical Multi-Agent Intelligence

Usage:
    python cross_agent_quantifier.py [DB_PATH] [--migrate] [--json]

    DB_PATH   Path to nox-mem.db (default: /root/.openclaw/workspace/tools/nox-mem/nox-mem.db)
    --migrate Add 'requesting_agent' column to search_telemetry if absent.
              Requires write access (omit ?mode=ro). Safe: ALTER TABLE ADD COLUMN.
    --json    Output raw JSON instead of markdown tables.

Pre-requisites:
    1. SQLite >= 3.38 (json_each support). Verify: python -c "import sqlite3; print(sqlite3.sqlite_version)"
    2. NOX_SEARCH_LOG_TEXT=1 in /root/.openclaw/.env (enables top_chunk_ids logging).
    3. requesting_agent column: either run --migrate once, or add to search.ts
       logTelemetry() call. Without it, Q2–Q5 report 0 eligible rows.
    4. For Q4 + Q6 (nDCG / counterfactual): W2.1 eval harness must have run
       and populated golden_id in search_telemetry. Without goldens, these
       queries return empty — that is expected, not an error.

RELIABILITY THRESHOLDS (documented for paper):
    < 100 eligible telemetry rows  → Q2–Q5 directional only
    < 20  golden-tagged queries    → Q4 + Q6 inconclusive
    ≥ 100 + ≥ 20 goldens          → results suitable for paper §5 table
"""

import sqlite3
import json
import sys
import math
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
SQL_FILE = Path(__file__).parent / "cross_agent_quantifier.sql"

QUERY_LABELS = {
    "Q1": "Chunk Distribution by Originating Agent",
    "Q2": "Cross-Agent Hit Rate (stratified by rank)",
    "Q3": "Cross-Agent Retrieval Matrix (requester × origin, top-5)",
    "Q4": "Cross-Agent Quality Parity (nDCG@10 proxy — requires goldens)",
    "Q5": "Top-10 Cross-Agent Flow Pairs",
    "Q6": "Counterfactual Isolation Simulation (requires goldens)",
}

PAPER_SECTION_TEMPLATE = """
## 5.X Cross-Agent Intelligence (E12)

| Metric | Value | Interpretation |
|---|---|---|
| Total chunks | {total_chunks} | — |
| Named-agent chunks | {named_agent_chunks} | {named_pct}% of corpus |
| Shared/other chunks | {shared_chunks} | cross-agent eligible |
| Cross-agent hits @ rank 1 | {cross_rank1} | best answer from different agent |
| Cross-agent hits @ top-3 | {cross_top3} | — |
| Cross-agent hits @ top-10 | {cross_top10} | — |
| Δ nDCG cross vs same-agent | {ndcg_delta} | quality parity check |
| Recall coverage loss (isolated) | {coverage_gap}% | answers unreachable in isolation |
| Top cross-flow | {top_flow} | dominant dependency pair |
| Telemetry reliability | {reliability} | — |

**Counterfactual baseline (MemGPT/Mem0 style isolated system): 0% cross-agent hits.**
"""


# ---------------------------------------------------------------------------
# Migration helper
# ---------------------------------------------------------------------------

MIGRATION_SQL = """
ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;
CREATE INDEX IF NOT EXISTS idx_search_telemetry_agent
  ON search_telemetry(requesting_agent)
  WHERE requesting_agent IS NOT NULL;
"""


def apply_migration(db_path: str) -> None:
    """Add requesting_agent column to search_telemetry if absent."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute("PRAGMA table_info(search_telemetry)")
    cols = [row[1] for row in cur.fetchall()]
    if "requesting_agent" in cols:
        print("[migrate] requesting_agent already present — no action needed.")
        conn.close()
        return
    print("[migrate] Adding requesting_agent column to search_telemetry …")
    conn.execute("ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_search_telemetry_agent "
        "ON search_telemetry(requesting_agent) WHERE requesting_agent IS NOT NULL"
    )
    conn.commit()
    conn.close()
    print("[migrate] Done. Restart nox-mem-api so logTelemetry() populates the column.")
    print(
        "[migrate] Also set NOX_SEARCH_LOG_TEXT=1 in .env if not already set.\n"
        "          Existing rows will have requesting_agent = NULL until new "
        "searches run."
    )


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def load_queries(sql_path: Path) -> list[tuple[str, str]]:
    """Split SQL file by '-- END --' sentinel, return [(label, sql), ...].

    Blocks that contain no executable SQL keyword (WITH/SELECT) are skipped
    so preamble comment sections do not count as queries.
    """
    raw = sql_path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in raw.split("-- END --") if b.strip()]
    result = []
    q_num = 1
    for block in blocks:
        # Skip pure-comment blocks (preamble, section headers, etc.)
        upper = block.upper()
        if "SELECT" not in upper and "WITH" not in upper:
            continue
        label = f"Q{q_num}"
        result.append((label, block))
        q_num += 1
    return result


def run_query(conn: sqlite3.Connection, sql: str) -> tuple[list[str], list[dict]]:
    """Execute a single SQL block, return (columns, rows_as_dicts)."""
    try:
        cur = conn.execute(sql)
        if cur.description is None:
            return [], []
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return cols, rows
    except sqlite3.OperationalError as exc:
        # Common case: requesting_agent column missing
        return ["error"], [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_markdown_table(cols: list[str], rows: list[dict]) -> str:
    if not rows:
        return "_No rows returned — see pre-requisites in file header._\n"
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    body_lines = []
    for row in rows:
        cell_values = [str(row.get(c, "")) for c in cols]
        body_lines.append("| " + " | ".join(cell_values) + " |")
    return "\n".join([header, separator] + body_lines) + "\n"


def render_q3_matrix(rows: list[dict]) -> str:
    """Render Q3 cross-agent matrix as a pivot table."""
    if not rows:
        return "_No rows returned — requesting_agent not populated._\n"

    agents = ["atlas", "boris", "cipher", "forge", "lex", "nox"]
    # Build pivot: requesting_agent → {origin_agent: pct}
    pivot: dict[str, dict[str, str]] = {}
    for row in rows:
        req = row.get("requesting_agent", "")
        orig = row.get("origin_agent", "")
        pct = row.get("pct_of_requester_hits", "")
        if req not in pivot:
            pivot[req] = {}
        pivot[req][orig] = str(pct)

    # Header: origin agents as columns
    origins = sorted(set(row.get("origin_agent", "") for row in rows
                         if row.get("origin_agent") in agents + ["shared_other"]))
    header = "| requester \\ origin | " + " | ".join(origins) + " |"
    separator = "| --- | " + " | ".join(["---"] * len(origins)) + " |"
    body_lines = []
    for req in agents:
        if req not in pivot:
            continue
        cells = [pivot[req].get(orig, "—") for orig in origins]
        body_lines.append(f"| **{req}** | " + " | ".join(cells) + " |")

    note = (
        "\n_Values are % of each requester's cross-agent hits. "
        "Diagonal entries are self-retrieval (excluded from cross-agent count). "
        "shared_other = shared docs/specs._\n"
    )
    return "\n".join([header, separator] + body_lines) + note


# ---------------------------------------------------------------------------
# Paper §5 summary table builder
# ---------------------------------------------------------------------------

def build_paper_summary(results: dict[str, tuple[list[str], list[dict]]]) -> str:
    """Extract key numbers from query results and render §5 template."""

    def safe_get(q_label: str, col: str, default: str = "N/A") -> str:
        _, rows = results.get(q_label, ([], []))
        if not rows or "error" in rows[0]:
            return default
        return str(rows[0].get(col, default))

    # Q1 — chunk distribution
    _, q1_rows = results.get("Q1", ([], []))
    total_chunks = sum(int(r.get("chunk_count", 0)) for r in q1_rows if "error" not in r)
    named_agents = {"atlas", "boris", "cipher", "forge", "lex", "nox"}
    named_chunks = sum(
        int(r.get("chunk_count", 0)) for r in q1_rows
        if r.get("origin_agent") in named_agents and "error" not in r
    )
    shared_chunks = total_chunks - named_chunks
    named_pct = round(100.0 * named_chunks / total_chunks, 1) if total_chunks else 0

    # Q2 — cross-agent hit rates
    cross_rank1 = safe_get("Q2", "cross_agent_pct_rank1") + "%"
    cross_top3  = safe_get("Q2", "cross_agent_pct_top3") + "%"
    cross_top10 = safe_get("Q2", "cross_agent_pct_top10") + "%"
    reliability = safe_get("Q2", "reliability", "NOT COMPUTED — no telemetry")

    # Q4 — nDCG delta
    _, q4_rows = results.get("Q4", ([], []))
    ndcg_by_type = {r.get("top1_type"): r.get("mean_ndcg_at10") for r in q4_rows if "error" not in r}
    cross_ndcg = ndcg_by_type.get("cross-agent")
    same_ndcg  = ndcg_by_type.get("same-agent")
    if cross_ndcg is not None and same_ndcg is not None:
        try:
            delta = round(float(cross_ndcg) - float(same_ndcg), 4)
            ndcg_delta = f"{'+' if delta >= 0 else ''}{delta}"
        except (TypeError, ValueError):
            ndcg_delta = "N/A"
    else:
        ndcg_delta = "N/A — run W2.1 eval harness to populate goldens"

    # Q6 — coverage gap
    coverage_gap = safe_get("Q6", "coverage_gap_pct", "N/A")

    # Q5 — top flow
    _, q5_rows = results.get("Q5", ([], []))
    top_flow = "N/A"
    if q5_rows and "error" not in q5_rows[0]:
        f = q5_rows[0]
        top_flow = f"{f.get('flow', 'N/A')} ({f.get('pct_of_requester_cross_hits', '?')}%)"

    return PAPER_SECTION_TEMPLATE.format(
        total_chunks=f"{total_chunks:,}",
        named_agent_chunks=f"{named_chunks:,}",
        named_pct=named_pct,
        shared_chunks=f"{shared_chunks:,}",
        cross_rank1=cross_rank1,
        cross_top3=cross_top3,
        cross_top10=cross_top10,
        ndcg_delta=ndcg_delta,
        coverage_gap=coverage_gap,
        top_flow=top_flow,
        reliability=reliability,
    )


# ---------------------------------------------------------------------------
# SQLite version check
# ---------------------------------------------------------------------------

def check_sqlite_version(conn: sqlite3.Connection) -> None:
    ver_str = conn.execute("SELECT sqlite_version()").fetchone()[0]
    parts = [int(x) for x in ver_str.split(".")]
    if parts < [3, 38, 0]:
        print(
            f"WARNING: SQLite {ver_str} < 3.38 — json_each() may be unavailable. "
            "Q2–Q6 may fail. Upgrade SQLite or use Python sqlite3 >= 3.38 build.",
            file=sys.stderr,
        )
    else:
        print(f"[info] SQLite {ver_str} — json_each() available.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    migrate = "--migrate" in args
    output_json = "--json" in args
    args = [a for a in args if not a.startswith("--")]

    db_path = args[0] if args else DEFAULT_DB

    # Migration path (requires write access — skip ?mode=ro)
    if migrate:
        apply_migration(db_path)
        print()

    # Open read-only
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        print(f"ERROR: Cannot open database at {db_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    check_sqlite_version(conn)

    queries = load_queries(SQL_FILE)

    # Execute all queries
    results: dict[str, tuple[list[str], list[dict]]] = {}
    for label, sql in queries:
        print(f"[run] {label} …", file=sys.stderr)
        cols, rows = run_query(conn, sql)
        results[label] = (cols, rows)

    conn.close()

    # ---------------------------------------------------------------------------
    # Output
    # ---------------------------------------------------------------------------

    if output_json:
        out = {}
        for label, (cols, rows) in results.items():
            out[label] = {"columns": cols, "rows": rows}
        print(json.dumps(out, indent=2, default=str))
        return

    # Markdown output
    print("# Cross-Agent Intelligence Quantification — E12\n")
    print(
        "> nox-mem paper §5 — Diferencial #3: Shared-Canonical Multi-Agent Intelligence  \n"
        "> Generated by `cross_agent_quantifier.py`\n"
    )

    for label, (cols, rows) in results.items():
        title = QUERY_LABELS.get(label, label)
        print(f"## {label} — {title}\n")
        if "error" in cols and rows:
            err = rows[0].get("error", "")
            if "no such column: requesting_agent" in err or "no column" in err.lower():
                print(
                    "> **MISSING COLUMN**: `requesting_agent` not in `search_telemetry`.  \n"
                    "> Run `python cross_agent_quantifier.py --migrate` once (requires write access),  \n"
                    "> then update `logTelemetry()` in `src/search.ts` to populate it.  \n"
                    "> After ≥100 new searches, re-run this script.\n"
                )
            else:
                print(f"> **SQL ERROR**: `{err}`\n")
        elif label == "Q3" and cols and "error" not in cols:
            print(render_q3_matrix(rows))
        else:
            print(render_markdown_table(cols, rows))

    # Paper §5 summary
    print("---\n")
    print("## Paper §5 — Summary Table\n")
    print(build_paper_summary(results))

    # Reliability notes
    print("\n---\n")
    print("## Reliability Notes\n")
    _, q2_rows = results.get("Q2", ([], []))
    eligible = 0
    if q2_rows and "error" not in q2_rows[0]:
        try:
            eligible = int(q2_rows[0].get("telemetry_eligible_rows", 0))
        except (TypeError, ValueError):
            eligible = 0
    print(
        f"- Eligible telemetry rows (requesting_agent + top_chunk_ids populated): **{eligible}**\n"
        f"- Threshold for statistical reliability: **100 rows** (Q2–Q5), **20 golden queries** (Q4, Q6)\n"
        f"- If counts are low: ensure `NOX_SEARCH_LOG_TEXT=1` + `requesting_agent` column present + "
        f"system has been running searches post-migration.\n"
        f"- Q1 (chunk distribution) is always reliable — does not depend on telemetry.\n"
        f"- source_file pattern coverage: inspect `other` bucket in Q1. If > 5% of total chunks, "
        f"refine CASE patterns in `cross_agent_quantifier.sql` before trusting Q2–Q5.\n"
    )


if __name__ == "__main__":
    main()
