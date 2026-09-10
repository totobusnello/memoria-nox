"""
Tests for the EverOS adapter (`adapters/evermind.py`), everos==1.3.1.

Run:
    python -m pytest eval/q4-comparison/test/test_evermind_ingest.py -v

⚠️ REPLACES a 355-line suite written against a CLI (`evermind retrieve`) and a
module hook (`EVERMIND_PYTHON_MODULE`) that DO NOT EXIST in any published
EverOS. Those tests faked the subprocess and the module, so they passed while
verifying nothing about the real system — the failure mode this file exists to
avoid. Every fake below is built from the REAL `SearchHit`/`DocumentContext`
classes imported from `everos`, so a shape change upstream breaks the test
instead of being papered over by a hand-rolled stub.

Focus areas:
  1. validate() — resolves every LATE import, and does so BEFORE the env leg
  2. mutation — a wrong module path must be named as such, never masked by env
  3. setup() — pins EVEROS_ROOT to an adapter-owned dir; one event loop
  4. ingest_corpus() — refuses the PAID run without the gate, returns estimate
  5. search() — topic hits collapse to k distinct doc_ids, best rank wins
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))

pytest.importorskip("everos", reason="pip install everos==1.3.1")
pytest.importorskip("everalgo", reason="everalgo ships with everos")

ADAPTER = HERE / "adapters" / "evermind.py"

_ENV_OK = {
    "EVEROS_LLM__API_KEY": "fake",
    "EVEROS_LLM__BASE_URL": "http://127.0.0.1:1/v1",
    "EVEROS_EMBEDDING__API_KEY": "fake",
    "EVEROS_EMBEDDING__BASE_URL": "http://127.0.0.1:1/v1",
}


@pytest.fixture
def ad(monkeypatch, tmp_path):
    """Fresh adapter module with credentials present and an isolated root."""
    for key, value in _ENV_OK.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("EVEROS_EVAL_ROOT", str(tmp_path / "everos-eval"))
    monkeypatch.delenv("EVEROS_ALLOW_PAID_INGEST", raising=False)
    mod = importlib.import_module("adapters.evermind")
    importlib.reload(mod)
    yield mod
    mod.teardown()


def _mutante(velho: str, novo: str):
    """Compile the adapter with one substitution and return its validate().

    ``__file__`` is injected because the module body resolves paths from it; a
    namespace without it raises NameError at import, and a mutant that cannot
    import "kills" every case while proving nothing.
    """
    src = ADAPTER.read_text()
    mut = src.replace(velho, novo)
    assert mut != src, f"mutation did not apply: {velho!r}"
    ns = {"__name__": "mutante", "__file__": str(ADAPTER)}
    exec(compile(mut, str(ADAPTER), "exec"), ns)
    return ns


# ── 1. validate ──────────────────────────────────────────────────────────────


def test_validate_ok_with_env(ad):
    v = ad.validate()
    assert v["ok"] is True, v.get("error")
    assert v["version"] == "1.3.1"
    assert "service.knowledge" in v["notes"]
    assert "GATED" in v["notes"], "the paid gate must be visible in the smoke test"


def test_validate_reports_missing_env(ad, monkeypatch):
    monkeypatch.delenv("EVEROS_LLM__API_KEY")
    v = ad.validate()
    assert v["ok"] is False
    assert "EVEROS_LLM__API_KEY" in v["error"]


def test_validate_makes_no_network_call(ad, monkeypatch):
    """validate() must not burn quota: no socket may be opened."""
    import socket

    def proibido(*_a, **_k):  # pragma: no cover - only runs on regression
        raise AssertionError("validate() opened a socket")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket.socket, "connect_ex", proibido)
    assert ad.validate()["ok"] is True


# ── 2. mutation: the import leg, and its position ────────────────────────────


def test_mutation_wrong_module_path_is_named(ad):
    """A wrong module path must be reported AS a module path.

    This is the defect that shipped: `MemoryRoot` was taken from
    `everos.config.settings` (it lives in `everos.core.persistence`) and
    `ParsedContent` from `everos.component.parser` (it is in `everalgo.types`).
    """
    ns = _mutante(
        '("everos.core.persistence", "MemoryRoot"),',
        '("everos.config.settings", "MemoryRoot"),',
    )
    v = ns["validate"]()
    assert v["ok"] is False
    assert "MemoryRoot unresolvable" in v["error"], v["error"]


def test_mutation_import_leg_survives_missing_env(ad, monkeypatch):
    """With env ABSENT the import defect must still surface.

    The original guard put the env leg first, so `ok: false — missing env` was
    returned for the right reason while two wrong import paths sat behind it,
    unreachable until setup(). A leg that decides first hides every leg after it.
    """
    monkeypatch.delenv("EVEROS_LLM__API_KEY")
    ns = _mutante(
        '("everos.core.persistence", "MemoryRoot"),',
        '("everos.config.settings", "MemoryRoot"),',
    )
    v = ns["validate"]()
    assert "unresolvable" in v["error"], f"env leg masked the import defect: {v['error']}"


def test_import_leg_precedes_env_leg_in_source():
    src = ADAPTER.read_text()
    assert src.index('("everos.core.persistence", "MemoryRoot")') < src.index(
        "missing = [v for v in REQUIRES_ENV"
    ), "the import leg must run before the env leg"


def test_validate_covers_every_late_import():
    """Every module imported inside setup/ingest/search must appear in validate().

    Otherwise validate() green-lights an adapter that dies mid-run — which is
    what happened: the two wrong paths were only reached by setup().
    """
    import re

    src = ADAPTER.read_text()
    corpo = src[src.index("def setup(") :]
    tardios = set(re.findall(r"^\s+from ((?:everos|everalgo)[\w.]*) import", corpo, re.M))
    bloco = src[src.index("for _mod, _sym in (") : src.index("missing = [v for v in REQUIRES_ENV")]
    cobertos = set(re.findall(r'\("((?:everos|everalgo)[\w.]*)"', bloco))
    assert tardios <= cobertos, f"late imports not covered by validate(): {tardios - cobertos}"


# ── 3. setup: isolation ──────────────────────────────────────────────────────


def test_setup_pins_root_and_does_not_touch_home(ad, tmp_path):
    home = Path.home() / ".everos"
    existia = home.exists()
    ad.setup()
    alvo = tmp_path / "everos-eval"
    assert alvo.exists()
    assert os.environ["EVEROS_ROOT"] == str(alvo)
    assert str(ad._knowledge_dir).startswith(str(alvo))
    assert home.exists() == existia, "adapter wrote into the user's ~/.everos"


def test_setup_is_idempotent_single_loop(ad):
    ad.setup()
    primeiro = ad._loop
    ad.setup()
    assert ad._loop is primeiro, "a new loop per call would land inside the timed region"


def test_teardown_is_idempotent(ad):
    ad.setup()
    ad.teardown()
    assert ad._loop is None
    ad.teardown()


# ── 4. the paid gate ─────────────────────────────────────────────────────────


def _corpus():
    chunks = []
    for nome in ("locomo.jsonl", "longmemeval.jsonl"):
        caminho = HERE / "cache" / nome
        if not caminho.exists():
            pytest.skip(f"corpus cache missing: {caminho}")
        with caminho.open() as fh:
            for linha in fh:
                linha = linha.strip()
                if linha:
                    chunks.append(json.loads(linha))
    return chunks


def test_ingest_refuses_without_gate_and_reports_the_estimate(ad):
    chunks = _corpus()
    r = ad.ingest_corpus(chunks)
    assert r["ingested"] == 0
    assert r["reason"] == "paid-ingest-gated"
    assert r["gate"] == "EVEROS_ALLOW_PAID_INGEST=1"
    est = r["estimate"]
    assert est["documents"] == est["llm_calls"] == len(chunks)
    assert est["approx_input_tokens"] == est["chars"] // 4
    ad.setup()
    assert not any(ad._knowledge_dir.rglob("*")), "gated ingest wrote to the store"


def test_corpus_is_6830_documents_not_the_query_count(ad):
    """Guards the population, not just the number.

    `cache/queries-rc4-all.jsonl` has 2.482 lines and that figure was quoted as
    the ingest size. The corpus is 5.882 + 948 = 6.830 documents, and the token
    cost is dominated by LongMemEval (14% of documents, ~95% of characters).
    """
    est = ad.ingest_corpus(_corpus())["estimate"]
    assert est["documents"] == 6830, est["documents"]
    queries = HERE / "cache" / "queries-rc4-all.jsonl"
    if queries.exists():
        n = sum(1 for l in queries.open() if l.strip())
        assert est["documents"] != n, "corpus size must not equal the query count"


def test_gate_is_what_holds_the_paid_call(ad):
    """Removing the gate must change behaviour — else the gate is decoration."""
    src = ADAPTER.read_text()
    assert 'if not os.environ.get("EVEROS_ALLOW_PAID_INGEST"):' in src
    assert src.index('if not os.environ.get("EVEROS_ALLOW_PAID_INGEST"):') < src.index(
        "from everos.service.knowledge import create_document"
    ), "the gate must precede the import of the paid call path"


# ── 5. search: topic hits → k distinct doc_ids ───────────────────────────────


def test_search_dedupes_topics_to_distinct_doc_ids(ad, monkeypatch):
    """Several topics can share one document; the adapter must return k docs.

    Hits are built from the real `SearchHit` / `DocumentContext` dataclasses so
    the fake cannot drift from the shape the service actually returns.
    """
    from everos.service.knowledge import DocumentContext, SearchHit, SearchKnowledgeResult

    def hit(doc_id, score, topico):
        return SearchHit(
            topic_id=f"t-{topico}",
            category_id="c1",
            topic_name=topico,
            topic_path=f"/{topico}",
            depth=1,
            summary=f"summary {topico}",
            content=f"content {topico}",
            score=score,
            retrieval_method="hybrid",
            source="knowledge",
            document=DocumentContext(doc_id=doc_id, title=doc_id, summary=""),
        )

    # A ranks first; B appears twice; C and D fill the tail.
    hits = [
        hit("conv-1::D1:1", 0.90, "a1"),
        hit("conv-2::D1:1", 0.85, "b1"),
        hit("conv-2::D1:1", 0.80, "b2"),  # same doc, worse rank → dropped
        hit("conv-1::D1:1", 0.75, "a2"),  # same doc, worse rank → dropped
        hit("conv-3::D1:1", 0.70, "c1"),
        hit("conv-4::D1:1", 0.65, "d1"),
    ]
    capturado = {}

    async def falso(**kwargs):
        capturado.update(kwargs)
        return SearchKnowledgeResult(hits=hits, total=len(hits), took_ms=1.0)

    import everos.service.knowledge as K

    monkeypatch.setattr(K, "search_knowledge", falso)
    ad.setup()
    out = ad.search("quando foi?", k=3)

    assert [i["id"] for i in out] == ["conv-1::D1:1", "conv-2::D1:1", "conv-3::D1:1"]
    assert len({i["id"] for i in out}) == 3, "duplicate doc_ids would inflate nDCG@k"
    assert out[0]["score"] == 0.90, "best-ranked topic must carry the document"
    assert all(i["source"] == "everos:knowledge" for i in out)
    assert out[0]["topics_seen"] == len(hits), "the realised collapse must be reported"


def test_search_overfetches_topics(ad, monkeypatch):
    """top_k sent upstream must exceed k, else granularity caps the result set."""
    from everos.service.knowledge import SearchKnowledgeResult

    capturado = {}

    async def falso(**kwargs):
        capturado.update(kwargs)
        return SearchKnowledgeResult(hits=[], total=0, took_ms=1.0)

    import everos.service.knowledge as K

    monkeypatch.setattr(K, "search_knowledge", falso)
    monkeypatch.setenv("EVEROS_OVERFETCH", "5")
    ad.setup()
    ad.search("q", k=10)
    assert capturado["top_k"] == 50, capturado
    assert capturado["app_id"] == "q4eval"


def test_search_without_overfetch_would_under_return(ad, monkeypatch):
    """The 'no' half of the pair: overfetch=1 cannot recover k distinct docs."""
    from everos.service.knowledge import DocumentContext, SearchHit, SearchKnowledgeResult

    def hit(doc_id, score, topico):
        return SearchHit(
            topic_id=f"t-{topico}", category_id="c", topic_name=topico,
            topic_path="/x", depth=1, summary="", content="", score=score,
            retrieval_method="hybrid", source="knowledge",
            document=DocumentContext(doc_id=doc_id, title=doc_id, summary=""),
        )

    async def falso(**kwargs):
        # Only as many hits as asked for, three of them from one document.
        todos = [hit("d1", 0.9, "1"), hit("d1", 0.8, "2"), hit("d1", 0.7, "3"),
                 hit("d2", 0.6, "4"), hit("d3", 0.5, "5")]
        return SearchKnowledgeResult(hits=todos[: kwargs["top_k"]], total=5, took_ms=1.0)

    import everos.service.knowledge as K

    monkeypatch.setattr(K, "search_knowledge", falso)
    ad.setup()

    monkeypatch.setenv("EVEROS_OVERFETCH", "1")
    assert len(ad.search("q", k=3)) == 1, "3 topics from 1 doc collapse to 1"

    monkeypatch.setenv("EVEROS_OVERFETCH", "5")
    assert len(ad.search("q", k=3)) == 3, "overfetch recovers the k distinct docs"
