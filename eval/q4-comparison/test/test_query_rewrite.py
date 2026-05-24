"""
Tests for the NOX_QUERY_REWRITE layer in the nox_mem adapter.

The rewrite layer (Gemini Flash Lite) is fully mocked in these tests —
no network calls are made, so they run offline + cost $0. Real-API smoke
runs live in audits/2026-05-24-query-rewrite-layer.md.

Coverage:
  1. _parse_rewrite_response handles fenced + bare + malformed JSON.
  2. _rewrite_query returns N variants when LLM is mocked.
  3. Variants are diverse (de-duplicated against original).
  4. _hybrid_single_pass returns a per-chunk RRF dict.
  5. _search_hybrid_local: rewrite=0 → baseline path (no LLM call).
  6. _search_hybrid_local: rewrite=1 → 1 + N passes, merged RRF.
  7. Failure in rewrite degrades gracefully (baseline scores intact).

All tests use an in-memory hybrid DB seeded with toy chunks.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import struct
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_Q4_DIR = _HERE.parent
if str(_Q4_DIR) not in sys.path:
    sys.path.insert(0, str(_Q4_DIR))


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _reload_adapter(monkeypatch: pytest.MonkeyPatch):
    """Fresh import of the adapter (resets module-level counters/cache)."""
    monkeypatch.setenv("NOX_EVAL_MODE", "hybrid")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    import adapters.nox_mem as mod  # type: ignore
    importlib.reload(mod)
    return mod


def _seed_toy_hybrid_db(mod, tmp_path: Path) -> sqlite3.Connection:
    """Open a tiny in-memory-ish hybrid DB with 4 toy chunks + fake embeddings.

    Sets `mod._hybrid_con` so `_hybrid_single_pass` works without a real
    `setup()` call (which would hit the network).
    """
    db_path = tmp_path / "rewrite-toy.db"
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")

    try:
        import sqlite_vec  # type: ignore
    except ImportError:
        pytest.skip("sqlite-vec not installed in this environment")

    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)

    dim = 4  # tiny embedding dim, plenty for toy ranking
    con.executescript(f"""
        CREATE TABLE IF NOT EXISTS eval_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS eval_chunks (
            id      TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            conv_id TEXT NOT NULL,
            day     INTEGER NOT NULL DEFAULT 0,
            text    TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS eval_chunks_fts
            USING fts5(text, content='eval_chunks', content_rowid='rowid',
                       tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER IF NOT EXISTS trg_ai
            AFTER INSERT ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(rowid, text) VALUES (new.rowid, new.text);
            END;
        CREATE TABLE IF NOT EXISTS eval_chunk_rowids (
            chunk_id TEXT PRIMARY KEY,
            rowid    INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS eval_vecs USING vec0(embedding float[{dim}]);
    """)

    toy = [
        ("conv-1::D1:1", "Deborah finds peace at the lakeside cabin", [1.0, 0.0, 0.0, 0.0]),
        ("conv-1::D2:1", "The Tokyo trip was the best vacation", [0.0, 1.0, 0.0, 0.0]),
        ("conv-2::D1:1", "Deborah enjoys quiet mountain trails", [0.9, 0.1, 0.1, 0.0]),
        ("conv-2::D2:1", "Cooking with mom on Sundays", [0.0, 0.0, 1.0, 0.0]),
    ]
    for cid, text, vec in toy:
        con.execute(
            "INSERT INTO eval_chunks(id,dataset,conv_id,day,text) VALUES (?,?,?,?,?)",
            (cid, "locomo", cid.split("::")[0], 0, text),
        )
        rowid = con.execute("SELECT rowid FROM eval_chunks WHERE id=?", (cid,)).fetchone()[0]
        con.execute(
            "INSERT INTO eval_vecs(rowid, embedding) VALUES (?, ?)",
            (rowid, struct.pack(f"{dim}f", *vec)),
        )
        con.execute(
            "INSERT INTO eval_chunk_rowids(chunk_id, rowid) VALUES (?, ?)",
            (cid, rowid),
        )
    con.commit()

    mod._hybrid_con = con
    mod._hybrid_db_path = db_path
    mod._hybrid_dim = dim
    return con


class _FakeGenAI:
    """Stand-in for google.generativeai with deterministic embeddings."""

    def __init__(self, map_text_to_vec: dict[str, list[float]] | None = None):
        self.calls: list[tuple[str, str]] = []
        self._map = map_text_to_vec or {}

    def embed_content(self, model: str, content: str, task_type: str) -> dict:
        self.calls.append((task_type, content))
        # Match against any seeded text; default to a low-overlap vector.
        for key, vec in self._map.items():
            if key.lower() in content.lower():
                return {"embedding": vec}
        return {"embedding": [0.25, 0.25, 0.25, 0.25]}


# ---------------------------------------------------------------------------
# 1. JSON parsing robustness
# ---------------------------------------------------------------------------


def test_parse_response_bare_json(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    raw = '["where does deborah relax", "deborah peaceful place", "calm spot deborah"]'
    out = mod._parse_rewrite_response(raw, 3)
    assert len(out) == 3
    assert all(isinstance(s, str) and s for s in out)


def test_parse_response_code_fenced(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    raw = '```json\n["a", "b", "c"]\n```'
    out = mod._parse_rewrite_response(raw, 3)
    assert out == ["a", "b", "c"]


def test_parse_response_extracts_embedded_array(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    raw = 'Sure, here you go:\n["x", "y"]\nLet me know!'
    out = mod._parse_rewrite_response(raw, 3)
    assert out == ["x", "y"]


def test_parse_response_garbage_returns_empty(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    assert mod._parse_rewrite_response("", 3) == []
    # Truly non-JSON garbage with no array bracket falls through cleanly
    assert mod._parse_rewrite_response("?????", 3) == []


# ---------------------------------------------------------------------------
# 2 & 3. _rewrite_query (fully mocked HTTP)
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _gemini_payload(variants: list[str]) -> dict:
    import json as _json
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": _json.dumps(variants)}]
                }
            }
        ]
    }


def test_rewrite_query_returns_n_variants(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    monkeypatch.setenv("NOX_QUERY_REWRITE_N", "3")

    captured = {}

    def fake_post(url, params=None, json=None, timeout=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        return _FakeResp(
            _gemini_payload([
                "where does Deborah unwind",
                "Deborah relaxation spots",
                "places of calm for Deborah",
            ])
        )

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    variants = mod._rewrite_query("What places give Deborah peace?")
    assert len(variants) == 3
    assert "gemini-2.5-flash-lite" in captured["url"]
    # The API key MUST travel via the `key` query param, never in the URL path
    assert captured["params"].get("key") == "test-key-not-used"
    # The prompt embeds the original query
    sent_text = captured["json"]["contents"][0]["parts"][0]["text"]
    assert "Deborah" in sent_text


def test_rewrite_query_dedupes_original(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")

    def fake_post(*a, **kw):
        return _FakeResp(_gemini_payload([
            "Original Query",  # same as input
            "diverse variant 1",
            "diverse variant 2",
        ]))

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    variants = mod._rewrite_query("Original Query")
    # Original-matching variant filtered out
    assert all(v.lower() != "original query" for v in variants)
    assert len(variants) >= 2


def test_rewrite_query_caches_within_process(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")

    call_count = {"n": 0}

    def fake_post(*a, **kw):
        call_count["n"] += 1
        return _FakeResp(_gemini_payload(["a", "b", "c"]))

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    mod._rewrite_query("repeat me")
    mod._rewrite_query("repeat me")
    mod._rewrite_query("repeat me")
    assert call_count["n"] == 1  # cached after first call


def test_rewrite_query_graceful_on_http_error(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")

    def fake_post(*a, **kw):
        raise RuntimeError("network down")

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    variants = mod._rewrite_query("any query")
    assert variants == []


def test_rewrite_error_never_leaks_api_key(monkeypatch, capsys):
    """Regression: requests.HTTPError str() embeds the URL incl. ?key=. Must redact."""
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyABCDEF1234567890_test_key_value_DEFG")

    leaky_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-lite:generateContent?key=AIzaSyABCDEF1234567890_test_key_value_DEFG"
    )

    def fake_post(*a, **kw):
        raise RuntimeError(f"503 Server Error: Service Unavailable for url: {leaky_url}")

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    variants = mod._rewrite_query("trigger leak path")
    assert variants == []

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # Neither the raw API key nor the leaky URL query param may appear in any output.
    assert "AIzaSyABCDEF1234567890_test_key_value_DEFG" not in combined, (
        "API key leaked to logs!"
    )
    assert "key=AIzaSyABCDEF" not in combined, "Key query param leaked to logs!"
    # But the redacted placeholder should be present (proves the redactor ran)
    assert "<REDACTED>" in combined


def test_rewrite_query_disabled_when_no_key(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Should short-circuit before attempting HTTP
    variants = mod._rewrite_query("query without key")
    assert variants == []


# ---------------------------------------------------------------------------
# 4. _hybrid_single_pass
# ---------------------------------------------------------------------------


def test_hybrid_single_pass_returns_scores(monkeypatch, tmp_path):
    mod = _reload_adapter(monkeypatch)
    _seed_toy_hybrid_db(mod, tmp_path)

    # Mock _get_genai to avoid real API
    fake = _FakeGenAI({"peace": [1.0, 0.0, 0.0, 0.0]})
    monkeypatch.setattr(mod, "_get_genai", lambda: fake)
    monkeypatch.setattr(mod, "_embed_query", lambda g, t: g.embed_content(
        model="", content=t, task_type="RETRIEVAL_QUERY")["embedding"])

    scores = mod._hybrid_single_pass("Deborah peace", k_fetch=10, genai=fake)
    assert isinstance(scores, dict)
    assert len(scores) > 0
    # Top chunk should be the lakeside one (matches peace text + dense vec)
    top = max(scores.items(), key=lambda x: x[1])[0]
    assert top == "conv-1::D1:1"


# ---------------------------------------------------------------------------
# 5 & 6. _search_hybrid_local: baseline vs rewrite-on
# ---------------------------------------------------------------------------


def test_baseline_no_rewrite_call(monkeypatch, tmp_path):
    """When NOX_QUERY_REWRITE=0, the LLM rewrite endpoint is never invoked."""
    mod = _reload_adapter(monkeypatch)
    monkeypatch.delenv("NOX_QUERY_REWRITE", raising=False)
    _seed_toy_hybrid_db(mod, tmp_path)

    fake = _FakeGenAI()
    monkeypatch.setattr(mod, "_get_genai", lambda: fake)
    monkeypatch.setattr(mod, "_embed_query", lambda g, t: g.embed_content(
        model="", content=t, task_type="RETRIEVAL_QUERY")["embedding"])

    rewrite_calls = {"n": 0}

    def boom(*a, **kw):
        rewrite_calls["n"] += 1
        raise AssertionError("LLM rewrite endpoint must NOT be called when disabled")

    import requests
    monkeypatch.setattr(requests, "post", boom)

    out = mod._search_hybrid_local("Deborah peace", k=3)
    assert len(out) > 0
    assert rewrite_calls["n"] == 0


def test_rewrite_layer_merges_variant_scores(monkeypatch, tmp_path):
    """With rewrite ON, variants contribute RRF scores merged into final ranking."""
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    monkeypatch.setenv("NOX_QUERY_REWRITE_N", "2")
    _seed_toy_hybrid_db(mod, tmp_path)

    fake = _FakeGenAI()
    monkeypatch.setattr(mod, "_get_genai", lambda: fake)
    monkeypatch.setattr(mod, "_embed_query", lambda g, t: g.embed_content(
        model="", content=t, task_type="RETRIEVAL_QUERY")["embedding"])

    def fake_post(*a, **kw):
        return _FakeResp(_gemini_payload([
            "Tokyo vacation",
            "mountain trails",
        ]))

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    out = mod._search_hybrid_local("Deborah peace", k=4)
    ids = [r["id"] for r in out]

    # Original-only baseline would not surface Tokyo or mountain chunks.
    # With variants merged, both should appear in top-4.
    assert any("conv-1::D2:1" == cid for cid in ids), (
        f"Tokyo variant chunk missing from rewrite-merged results: {ids}"
    )
    assert any("conv-2::D1:1" == cid for cid in ids), (
        f"Mountain variant chunk missing from rewrite-merged results: {ids}"
    )


def test_rewrite_failure_falls_back_to_baseline(monkeypatch, tmp_path):
    """If the LLM call fails, search returns baseline hybrid (no crash)."""
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    _seed_toy_hybrid_db(mod, tmp_path)

    fake = _FakeGenAI()
    monkeypatch.setattr(mod, "_get_genai", lambda: fake)
    monkeypatch.setattr(mod, "_embed_query", lambda g, t: g.embed_content(
        model="", content=t, task_type="RETRIEVAL_QUERY")["embedding"])

    def fake_post(*a, **kw):
        raise RuntimeError("simulated network failure")

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    out = mod._search_hybrid_local("Deborah peace", k=3)
    assert len(out) > 0  # baseline still works
    # Should still rank the peace chunk highly
    assert out[0]["id"] in {"conv-1::D1:1", "conv-2::D1:1"}


# ---------------------------------------------------------------------------
# 7. Diversity assertion + helper flags
# ---------------------------------------------------------------------------


def test_rewrite_variants_are_diverse(monkeypatch):
    """Variants from a healthy LLM call should differ from the original."""
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")

    def fake_post(*a, **kw):
        return _FakeResp(_gemini_payload([
            "what locations relax Deborah",
            "Deborah peaceful settings",
            "calm places Deborah enjoys",
        ]))

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    q = "What places give Deborah peace?"
    variants = mod._rewrite_query(q)
    assert len(variants) == 3
    for v in variants:
        assert v.lower() != q.lower()
        assert v.strip()  # non-empty


def test_get_rewrite_stats_exposes_counters(monkeypatch):
    mod = _reload_adapter(monkeypatch)
    monkeypatch.setenv("NOX_QUERY_REWRITE", "1")
    stats = mod.get_rewrite_stats()
    assert stats["enabled"] is True
    assert "calls" in stats
    assert "errors" in stats
    assert "cache_entries" in stats
    assert stats["variants_per_query"] == 3  # default
