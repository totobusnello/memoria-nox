"""
test_smoke.py — local smoke test for HotPotQA harness modules.

Runs without VPS, without nox-mem CLI, without API keys. Validates:
    - lib/corpus_loader.py parses dev-distractor shape
    - lib/scorer.py matches hotpot_evaluate_v1.py reference values
    - lib/aggregate.py composes per-type and per-level summaries
    - adapter helpers (refuse_if_prod, predict_supporting_facts,
      paragraph_title_from_chunk, _tokenize, build_answer_prompt)

Usage:
    python3 eval/hotpotqa/test_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "lib"))

from lib.corpus_loader import (  # noqa: E402
    HotpotQuestion,
    load_questions,
    paragraph_text,
    question_to_markdown,
)
from lib.scorer import (  # noqa: E402
    _normalize_answer,
    exact_match_score,
    f1_score,
    score_record,
    supporting_facts_metrics,
)
from lib.aggregate import aggregate  # noqa: E402


def _fake_dataset_path() -> Path:
    fake = [
        {
            "_id": "q-001",
            "question": "Where was the lead singer of Queen born?",
            "answer": "Zanzibar",
            "type": "bridge",
            "level": "medium",
            "context": [
                ["Queen (band)", ["Queen are a British rock band.", "Their lead singer was Freddie Mercury."]],
                ["Freddie Mercury", ["Freddie Mercury was born in Zanzibar.", "He moved to England as a teenager."]],
                ["Brian May", ["Brian May was the guitarist of Queen.", "He has a PhD in astrophysics."]],
                ["Roger Taylor", ["Roger Taylor was the drummer.", "He sang co-lead on some tracks."]],
                ["John Deacon", ["John Deacon was the bassist.", "He left the band in 1997."]],
                ["Live Aid 1985", ["Queen's Live Aid set is famous.", "Held at Wembley Stadium."]],
                ["Wembley Stadium", ["Wembley is in London.", "It hosts the FA Cup Final."]],
                ["London", ["London is the capital of the UK.", "It has many landmarks."]],
                ["UK", ["The UK is in Europe.", "It is a constitutional monarchy."]],
                ["Europe", ["Europe is a continent.", "It contains 44 countries."]],
            ],
            "supporting_facts": [["Queen (band)", 1], ["Freddie Mercury", 0]],
        },
        {
            "_id": "q-002",
            "question": "Is Mount Everest higher than Kilimanjaro?",
            "answer": "yes",
            "type": "comparison",
            "level": "easy",
            "context": [
                ["Mount Everest", ["Mount Everest is 8848m tall.", "Located in Nepal and China."]],
                ["Kilimanjaro", ["Mount Kilimanjaro is 5895m tall.", "Located in Tanzania."]],
                ["Africa", ["Africa is a continent.", "It contains Tanzania."]],
                ["Asia", ["Asia is a continent.", "It contains Nepal and China."]],
                ["Tanzania", ["Tanzania is in East Africa.", "Its capital is Dodoma."]],
                ["Nepal", ["Nepal is in South Asia.", "Its capital is Kathmandu."]],
                ["China", ["China is in East Asia.", "Its capital is Beijing."]],
                ["Mountains", ["Mountains are landforms.", "Many are over 4000m."]],
                ["Climbing", ["Mountain climbing is a sport.", "Everest summit takes weeks."]],
                ["Geography", ["Geography studies the Earth.", "It includes physical features."]],
            ],
            "supporting_facts": [["Mount Everest", 0], ["Kilimanjaro", 0]],
        },
    ]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(fake, tmp)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def test_corpus_loader() -> None:
    p = _fake_dataset_path()
    try:
        qs = load_questions(p)
        assert len(qs) == 2, f"expected 2 questions, got {len(qs)}"
        q1 = qs[0]
        assert q1.question_id == "q-001"
        assert q1.type == "bridge"
        assert q1.gold_titles == {"Queen (band)", "Freddie Mercury"}
        assert len(q1.paragraphs) == 10
        # paragraph_text
        assert "British rock band" in paragraph_text(q1, "Queen (band)")
        assert paragraph_text(q1, "DoesNotExist") is None
        # markdown rendering
        md = question_to_markdown(q1)
        assert "paragraph_title: Queen (band)" in md
        assert "paragraph_title: Freddie Mercury" in md
        # Distractors also included (10 paragraphs total)
        assert md.count("paragraph_title:") == 10
        print("[corpus_loader] OK")
    finally:
        try:
            os.unlink(p)
        except OSError:
            pass


def test_scorer() -> None:
    # Normalization
    assert _normalize_answer("The Beatles!") == "beatles"
    assert _normalize_answer("A B C") == "b c"
    assert _normalize_answer("  Hello   World  ") == "hello world"

    # EM
    assert exact_match_score("Yes", "yes") == 1.0
    assert exact_match_score("No", "yes") == 0.0
    assert exact_match_score("The Beatles", "beatles") == 1.0

    # F1
    f1, _, _ = f1_score("beatles", "the beatles")
    assert f1 == 1.0
    f1, _, _ = f1_score("paul mccartney", "john lennon")
    assert f1 == 0.0
    f1, p, r = f1_score("paul mccartney lennon", "john lennon paul")
    assert 0 < f1 < 1

    # Supporting facts
    em, f1, _, _ = supporting_facts_metrics(
        [("A", 0), ("B", 1)],
        [("A", 0), ("B", 1)],
    )
    assert em == 1.0 and f1 == 1.0
    em, f1, _, _ = supporting_facts_metrics([("A", 0)], [("A", 0), ("B", 1)])
    assert em == 0.0 and 0 < f1 < 1

    # Joint
    m = score_record("Yes", "yes", [("A", 0), ("B", 0)], [("A", 0), ("B", 0)])
    assert m["joint_em"] == 1.0 and m["joint_f1"] == 1.0
    m = score_record("Yes", "no", [("A", 0)], [("A", 0)])
    assert m["joint_em"] == 0.0
    print("[scorer] OK")


def test_aggregate() -> None:
    records = [
        {
            "question_id": "a",
            "type": "bridge",
            "level": "easy",
            "predicted_answer": "Zanzibar",
            "gold_answer": "Zanzibar",
            "predicted_supporting_facts": [["Q", 1], ["F", 0]],
            "gold_supporting_facts": [["Q", 1], ["F", 0]],
            "retrieval_ms": 200, "generation_ms": 500, "ingest_ms": 1500,
            "error": None,
        },
        {
            "question_id": "b",
            "type": "comparison",
            "level": "hard",
            "predicted_answer": "no",
            "gold_answer": "yes",
            "predicted_supporting_facts": [["X", 0]],
            "gold_supporting_facts": [["X", 0], ["Y", 1]],
            "retrieval_ms": 300, "generation_ms": 600, "ingest_ms": 2000,
            "error": None,
        },
        {
            "question_id": "c",
            "type": "bridge",
            "level": "medium",
            "predicted_answer": "",
            "gold_answer": "42",
            "predicted_supporting_facts": [],
            "gold_supporting_facts": [["Z", 0]],
            "retrieval_ms": 150, "generation_ms": 0, "ingest_ms": 1200,
            "error": None,
        },
        {
            "question_id": "d", "type": "bridge", "level": "easy",
            "predicted_answer": "", "gold_answer": "foo",
            "predicted_supporting_facts": [], "gold_supporting_facts": [["A", 0]],
            "retrieval_ms": 100, "generation_ms": 0, "ingest_ms": 1000,
            "error": "sim",
        },
    ]
    agg = aggregate(records)
    assert agg["n_total"] == 4
    assert agg["n_errors"] == 1
    assert agg["n_scored"] == 3
    assert agg["answer"]["n"] == 3
    assert agg["answer"]["em"] > 0
    assert "by_type" in agg and "bridge" in agg["by_type"]
    assert "by_level" in agg and "easy" in agg["by_level"]
    assert agg["latency_ms"]["retrieval_p50"] > 0
    print("[aggregate] OK")


def test_adapter_helpers() -> None:
    from adapter_nox_mem import (
        refuse_if_prod, predict_supporting_facts, paragraph_title_from_chunk,
        build_answer_prompt, _tokenize,
    )

    # refuse_if_prod
    try:
        refuse_if_prod("/root/.openclaw/workspace/tools/nox-mem/nox-mem.db",
                       "http://127.0.0.1:18900")
        raise AssertionError("should have refused prod DB")
    except SystemExit:
        pass

    try:
        refuse_if_prod("/root/.openclaw/x/q.db", "http://127.0.0.1:18802")
        raise AssertionError("should have refused prod port 18802")
    except SystemExit:
        pass

    try:
        refuse_if_prod("/tmp/x/q.db", "http://127.0.0.1:18900")
        raise AssertionError("should have refused /tmp path")
    except SystemExit:
        pass

    refuse_if_prod("/root/.openclaw/hotpot/q.db", "http://127.0.0.1:18900")

    # Tokenize
    assert _tokenize("It's Mount Everest!") == ["it", "s", "mount", "everest"]

    # SP prediction
    q = HotpotQuestion(
        question_id="t1",
        question="What is the height of Mount Everest?",
        answer="8848m",
        type="bridge",
        level="easy",
        paragraphs=[
            ("Mount Everest", ["Mount Everest is high.", "Its height is 8848m.", "It is in Nepal."]),
            ("Nepal", ["Nepal is a country.", "Many mountains."]),
            ("Random", ["Distractor.", "Nothing."]),
        ],
        supporting_facts=[("Mount Everest", 1)],
    )
    preds = predict_supporting_facts(q, ["Mount Everest", "Nepal"], q.question)
    assert any(p[0] == "Mount Everest" for p in preds), preds

    # Paragraph title extract
    assert paragraph_title_from_chunk(
        {"chunk_text": "## Mount Everest\n\nparagraph_title: Mount Everest\n\nbody"}
    ) == "Mount Everest"
    assert paragraph_title_from_chunk(
        {"chunk_text": "## Nepal\n\nbody"}
    ) == "Nepal"
    assert paragraph_title_from_chunk({"chunk_text": "no header"}) == ""

    # Prompt
    prompt = build_answer_prompt(q, ["Mount Everest is 8848m high."])
    assert "Question: What is the height" in prompt
    assert "Short answer:" in prompt
    print("[adapter helpers] OK")


def main() -> int:
    test_corpus_loader()
    test_scorer()
    test_aggregate()
    test_adapter_helpers()
    print("ALL HOTPOTQA SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
