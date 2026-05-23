"""
Tests for `lib.corpus_loader` — Q4 COMPARISON shared corpus loader.

Strategy
--------
The full LoCoMo (~10 MB) and LongMemEval splits (3 MB → 600 MB) live on
upstream hosts (GitHub raw + HuggingFace). Pulling them during unit tests
would (a) make the suite network-dependent and slow, (b) blow up the
sandbox quota, and (c) break in CI without outbound HTTPS.

So we test the **parsing contract** against:

  1. Mock raw payloads that embed every gold_chunk_id from the existing
     `eval/{locomo,longmemeval}/dry-run-sample.json` files. This proves
     the loader's id encoding matches what `runner.py::_to_record` and the
     downstream metrics path expect — closing the gap that produced 0/20
     gold hits before this PR.

  2. The real `eval/longmemeval/dry-run-sample.json` (records-shape) to
     verify the loader's defensive dry-run-detection branch yields no
     chunks instead of crashing.

  3. Cache hit / miss / refresh paths via the same mock payloads.

A separate, env-gated `test_real_network_*` set of tests runs against
upstream when explicitly opted into via `Q4_CORPUS_LOADER_NETWORK_TESTS=1`.
Those validate the live ballpark chunk counts (LoCoMo ~9-10k, LongMemEval
oracle ~3-5k) — Toto can run them manually before any Q4 launch.

Run:
    cd eval/q4-comparison
    python3 -m pytest test/test_corpus_loader.py -v
    Q4_CORPUS_LOADER_NETWORK_TESTS=1 python3 -m pytest test/ -v -k network
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Allow `import lib.corpus_loader` when running pytest from `eval/q4-comparison/`.
HERE = Path(__file__).resolve().parent
Q4_DIR = HERE.parent
if str(Q4_DIR) not in sys.path:
    sys.path.insert(0, str(Q4_DIR))

from lib import corpus_loader  # noqa: E402
from lib.corpus_loader import (  # noqa: E402
    ChunkRecord,
    LONGMEMEVAL_DEFAULT_SPLIT,
    load_locomo_corpus,
    load_longmemeval_corpus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_cache(monkeypatch, tmp_path: Path) -> Path:
    """Redirect the loader's cache + raw dirs to a pytest tmp_path so each
    test gets an isolated filesystem. Avoids polluting `eval/q4-comparison/cache/`.
    """
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(corpus_loader, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(corpus_loader, "RAW_DIR", raw_dir)
    monkeypatch.setattr(corpus_loader, "LOCOMO_RAW_FILE", raw_dir / "locomo10.json")
    monkeypatch.setattr(corpus_loader, "LOCOMO_CACHE", tmp_path / "locomo.jsonl")
    # LongMemEval helpers compute paths from these constants at call time;
    # they re-read CACHE_DIR/RAW_DIR via the module globals, so the two
    # monkeypatches above are sufficient.
    return tmp_path


def _gold_ids_from_dryrun(path: Path) -> list[str]:
    payload = json.loads(path.read_text())
    ids: list[str] = []
    for r in payload.get("records", []):
        ids.extend(r.get("gold_chunk_ids") or [])
        ids.extend(r.get("answer_session_ids") or [])
    return ids


# ---------------------------------------------------------------------------
# Mock raw payload builders — match real upstream schema
# ---------------------------------------------------------------------------


def _mock_locomo_raw(extra_gold_ids: list[str]) -> list[dict]:
    """Build a tiny snap-research/locomo10.json-shaped payload that contains
    every gold id from `extra_gold_ids` (format `{sample_id}::{dia_id}`).

    Groups dia_ids by sample_id and synthesises minimal session structure.
    """
    by_sample: dict[str, list[str]] = {}
    for gid in extra_gold_ids:
        sid, _, dia = gid.partition("::")
        if not sid or not dia:
            continue
        by_sample.setdefault(sid, []).append(dia)

    convs: list[dict] = []
    for sid, dia_ids in by_sample.items():
        conversation: dict[str, Any] = {
            "speaker_a": "Alice",
            "speaker_b": "Bob",
            "session_1_date_time": "2024-01-01 10:00",
            "session_1": [
                {"speaker": "Alice" if i % 2 == 0 else "Bob",
                 "dia_id": dia,
                 "text": f"mock turn {dia} for {sid}"}
                for i, dia in enumerate(dia_ids)
            ],
        }
        convs.append({
            "sample_id": sid,
            "conversation": conversation,
            "qa": [],
        })
    return convs


def _mock_longmemeval_raw(extra_gold_ids: list[str]) -> list[dict]:
    """Build a HF longmemeval-cleaned-shaped payload.

    Each `extra_gold_ids` entry is a raw session_id. We bundle them into a
    single question's haystack so the loader yields them as chunks.
    """
    haystack_session_ids = list(dict.fromkeys(extra_gold_ids))  # dedupe preserve order
    haystack_dates = [f"2024-01-{i+1:02d} 09:00" for i in range(len(haystack_session_ids))]
    haystack_sessions = [
        [
            {"role": "user", "content": f"hello in session {sid}"},
            {"role": "assistant", "content": f"acknowledged {sid}"},
        ]
        for sid in haystack_session_ids
    ]
    return [
        {
            "question_id": "mock-q-1",
            "question_type": "single-session-user",
            "question": "mock question 1?",
            "answer": "mock answer",
            "question_date": "2024-02-01 12:00",
            "haystack_session_ids": haystack_session_ids,
            "haystack_dates": haystack_dates,
            "haystack_sessions": haystack_sessions,
            "answer_session_ids": list(haystack_session_ids[:2]),
        },
    ]


# ---------------------------------------------------------------------------
# Helpers — seed the cache without network
# ---------------------------------------------------------------------------


def _seed_locomo_raw(tmp_cache: Path, payload: list[dict]) -> None:
    corpus_loader.LOCOMO_RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    corpus_loader.LOCOMO_RAW_FILE.write_text(json.dumps(payload), encoding="utf-8")


def _seed_longmemeval_raw(tmp_cache: Path, split: str, payload: list[dict]) -> None:
    raw = corpus_loader._longmemeval_raw_file(split)
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(payload), encoding="utf-8")


def _block_network(monkeypatch) -> None:
    def _refuse(*_a, **_kw):
        raise AssertionError(
            "network access during unit test — _download() was called unexpectedly"
        )

    monkeypatch.setattr(corpus_loader, "_download", _refuse)


# ---------------------------------------------------------------------------
# LoCoMo tests
# ---------------------------------------------------------------------------


def test_locomo_loads_from_mock_raw(tmp_cache: Path, monkeypatch):
    """Smoke: with a hand-built raw file, loader produces ChunkRecords."""
    payload = _mock_locomo_raw([
        "conv-A::D1:1",
        "conv-A::D1:2",
        "conv-B::D7:3",
    ])
    _seed_locomo_raw(tmp_cache, payload)
    _block_network(monkeypatch)

    records = list(load_locomo_corpus())

    assert len(records) == 3
    for r in records:
        assert isinstance(r, ChunkRecord)
        assert r.dataset == "locomo"
        assert "::" in r.id
        assert r.text
        assert r.metadata["dia_id"]


def test_locomo_gold_ids_findable_from_dryrun_sample(tmp_cache: Path, monkeypatch):
    """Critical contract: every gold_chunk_id in the existing
    `eval/locomo/dry-run-sample.json` MUST be present in the loaded chunk
    stream. This is what `0/20 gold hits` regressed on before this PR.
    """
    repo_root = Q4_DIR.parent.parent
    dryrun = repo_root / "eval" / "locomo" / "dry-run-sample.json"
    assert dryrun.exists(), f"missing reference dry-run sample at {dryrun}"
    gold_ids = _gold_ids_from_dryrun(dryrun)
    # LoCoMo dry-run-sample uses `{sample_id}::{dia_id}` format; filter for those.
    locomo_gold = [g for g in gold_ids if "::" in g and not g.startswith("answer_")]
    assert locomo_gold, "expected at least one LoCoMo gold id in dry-run-sample.json"

    payload = _mock_locomo_raw(locomo_gold)
    _seed_locomo_raw(tmp_cache, payload)
    _block_network(monkeypatch)

    chunk_ids = {r.id for r in load_locomo_corpus()}

    missing = [g for g in locomo_gold if g not in chunk_ids]
    assert not missing, (
        f"loader missed {len(missing)} LoCoMo gold ids; first few: {missing[:5]}"
    )


def test_locomo_day_extracted_from_session_key(tmp_cache: Path, monkeypatch):
    """`day` field is derived from `session_N`. Verify it round-trips."""
    payload = [
        {
            "sample_id": "conv-X",
            "conversation": {
                "session_5_date_time": "2024-03-01 10:00",
                "session_5": [
                    {"speaker": "A", "dia_id": "D5:1", "text": "hi"},
                ],
            },
            "qa": [],
        },
    ]
    _seed_locomo_raw(tmp_cache, payload)
    _block_network(monkeypatch)

    records = list(load_locomo_corpus())
    assert len(records) == 1
    assert records[0].day == 5
    assert records[0].metadata["session_key"] == "session_5"


# ---------------------------------------------------------------------------
# LongMemEval tests
# ---------------------------------------------------------------------------


def test_longmemeval_loads_from_mock_raw(tmp_cache: Path, monkeypatch):
    payload = _mock_longmemeval_raw([
        "answer_aaa_1",
        "answer_aaa_2",
        "filler_xyz_3",
    ])
    _seed_longmemeval_raw(tmp_cache, "oracle", payload)
    _block_network(monkeypatch)

    records = list(load_longmemeval_corpus("oracle"))

    assert len(records) == 3
    ids = {r.id for r in records}
    assert ids == {"answer_aaa_1", "answer_aaa_2", "filler_xyz_3"}
    for r in records:
        assert r.dataset == "longmemeval"
        assert r.conversation_id == "mock-q-1"
        assert r.metadata["session_id"] == r.id


def test_longmemeval_gold_ids_findable_from_dryrun_sample(tmp_cache: Path, monkeypatch):
    """Critical contract: chunk.id must equal raw session_id (matches the
    runner's gold extraction fallback in `_to_record`).
    """
    repo_root = Q4_DIR.parent.parent
    dryrun = repo_root / "eval" / "longmemeval" / "dry-run-sample.json"
    assert dryrun.exists(), f"missing reference dry-run sample at {dryrun}"
    payload_raw = json.loads(dryrun.read_text())
    gold_sids: list[str] = []
    for r in payload_raw.get("records", []):
        gold_sids.extend(r.get("answer_session_ids") or [])
    assert gold_sids, "expected at least one LongMemEval gold session_id"

    payload = _mock_longmemeval_raw(gold_sids)
    _seed_longmemeval_raw(tmp_cache, "oracle", payload)
    _block_network(monkeypatch)

    chunk_ids = {r.id for r in load_longmemeval_corpus("oracle")}

    missing = [g for g in gold_sids if g not in chunk_ids]
    assert not missing, (
        f"loader missed {len(missing)} LongMemEval gold session_ids; "
        f"first few: {missing[:5]}"
    )


def test_longmemeval_dedupes_repeated_session_ids(tmp_cache: Path, monkeypatch):
    """Within a single question, repeated session_ids in haystack_session_ids
    should collapse to the first occurrence (mirrors parser.ts dedup).
    """
    payload = [
        {
            "question_id": "q-dedup",
            "question_type": "multi-session",
            "question": "any?",
            "answer": "yes",
            "question_date": "2024-01-01 10:00",
            "haystack_session_ids": ["sid-1", "sid-1", "sid-2", "sid-1"],
            "haystack_dates": ["d1", "d1", "d2", "d1"],
            "haystack_sessions": [
                [{"role": "u", "content": "first"}],
                [{"role": "u", "content": "DUP — should be skipped"}],
                [{"role": "u", "content": "second"}],
                [{"role": "u", "content": "DUP2 — should be skipped"}],
            ],
            "answer_session_ids": ["sid-1"],
        },
    ]
    _seed_longmemeval_raw(tmp_cache, "oracle", payload)
    _block_network(monkeypatch)

    records = list(load_longmemeval_corpus("oracle"))
    assert len(records) == 2
    by_id = {r.id: r for r in records}
    assert "first" in by_id["sid-1"].text
    assert "DUP" not in by_id["sid-1"].text
    assert by_id["sid-1"].metadata["is_answer_session"] is True
    assert by_id["sid-2"].metadata["is_answer_session"] is False


def test_longmemeval_dryrun_sample_shape_yields_zero(tmp_cache: Path, monkeypatch):
    """The local dry-run-sample is a `{meta, records}` shape WITHOUT
    haystack_sessions. Loader must detect this and yield 0 chunks instead
    of crashing on a missing field.
    """
    payload = {"meta": {"n": 1}, "records": [
        {"question_id": "x", "answer_session_ids": ["a"]},
    ]}
    raw = corpus_loader._longmemeval_raw_file("oracle")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(payload), encoding="utf-8")
    _block_network(monkeypatch)

    records = list(load_longmemeval_corpus("oracle"))
    assert records == []


def test_longmemeval_invalid_split_raises():
    with pytest.raises(ValueError, match="unknown split"):
        # Force generator to evaluate the validation.
        list(load_longmemeval_corpus("not_a_split"))


# ---------------------------------------------------------------------------
# Cache hit / miss / refresh
# ---------------------------------------------------------------------------


def test_cache_miss_then_hit_for_locomo(tmp_cache: Path, monkeypatch):
    payload = _mock_locomo_raw(["conv-A::D1:1", "conv-A::D1:2"])
    _seed_locomo_raw(tmp_cache, payload)
    _block_network(monkeypatch)

    # First call: cache MISS → builds JSONL from raw.
    first = list(load_locomo_corpus())
    assert len(first) == 2
    assert corpus_loader.LOCOMO_CACHE.exists()

    # Second call: cache HIT — modify the raw file to confirm the second
    # call doesn't re-read it.
    corpus_loader.LOCOMO_RAW_FILE.write_text("INVALID JSON", encoding="utf-8")
    second = list(load_locomo_corpus())
    assert len(second) == 2  # still 2 from cache, raw ignored


def test_cache_force_refresh_rebuilds(tmp_cache: Path, monkeypatch):
    """force_refresh=True should re-download AND rebuild the cache.

    With raw NOT seeded: download is called once during initial build, then
    again on force_refresh. Subsequent cached call without force does not.
    """
    download_calls = {"n": 0}
    # Capture the raw payload bytes so the fake_download "fetches" it on
    # demand by writing the test payload to disk.
    payload_a = _mock_locomo_raw(["conv-A::D1:1"])
    raw_bytes = json.dumps(payload_a).encode("utf-8")

    def _fake_download(url, target, *, force=False, timeout=120):
        download_calls["n"] += 1
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_bytes(raw_bytes)
        return target

    monkeypatch.setattr(corpus_loader, "_download", _fake_download)

    # Initial build — raw missing, so download is called once.
    list(load_locomo_corpus())
    assert download_calls["n"] == 1
    assert corpus_loader.LOCOMO_CACHE.exists()

    # Cached call — cache hit, no download.
    list(load_locomo_corpus())
    assert download_calls["n"] == 1

    # Force refresh — download called again, cache rebuilt.
    list(load_locomo_corpus(force_refresh=True))
    assert download_calls["n"] == 2


def test_chunk_record_jsonl_round_trip():
    """ChunkRecord must serialise to a single JSONL line and round-trip."""
    rec = ChunkRecord(
        id="conv-A::D1:1",
        text="Alice: hi",
        dataset="locomo",
        conversation_id="conv-A",
        day=1,
        metadata={"dia_id": "D1:1", "speaker": "Alice"},
    )
    line = rec.to_jsonl()
    assert "\n" not in line
    back = ChunkRecord.from_jsonl(line)
    assert back == rec


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


def test_module_public_api_exposes_loaders():
    from lib import ChunkRecord as _CR, load_locomo_corpus as _ll, load_longmemeval_corpus as _ll2

    assert _CR is ChunkRecord
    assert _ll is load_locomo_corpus
    assert _ll2 is load_longmemeval_corpus


# ---------------------------------------------------------------------------
# Optional live-network smoke (gated, slow, license-sensitive)
# ---------------------------------------------------------------------------


_NET = os.environ.get("Q4_CORPUS_LOADER_NETWORK_TESTS") == "1"


@pytest.mark.skipif(not _NET, reason="set Q4_CORPUS_LOADER_NETWORK_TESTS=1 to enable")
def test_network_locomo_ballpark():
    """LoCoMo upstream returns ~9-10k turns per the 2026-05-04 schema audit.
    A drift outside [3k, 30k] indicates an upstream regression we should
    catch BEFORE running the Q4 comparison.
    """
    n = sum(1 for _ in load_locomo_corpus())
    assert 3_000 <= n <= 30_000, f"LoCoMo chunk count out of ballpark: {n}"


@pytest.mark.skipif(not _NET, reason="set Q4_CORPUS_LOADER_NETWORK_TESTS=1 to enable")
def test_network_longmemeval_oracle_ballpark():
    """Oracle split is the smallest LongMemEval distribution (~500 questions,
    handful of sessions each). Expect ~1k-10k chunks.
    """
    n = sum(1 for _ in load_longmemeval_corpus("oracle"))
    assert 500 <= n <= 30_000, f"LongMemEval oracle chunk count out of ballpark: {n}"
