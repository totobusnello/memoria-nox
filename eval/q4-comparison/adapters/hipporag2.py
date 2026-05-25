"""
HippoRAG2 adapter — Python SDK (graph-based RAG with Personalized PageRank).

Repo:  https://github.com/OSU-NLP-Group/HippoRAG  (MIT, OSU NLP Group)
Paper: arXiv:2405.14831 (HippoRAG, NeurIPS 2024) +
       arXiv:2502.14802 (HippoRAG 2, Feb 2025) — SOTA on multi-hop reasoning
PyPI:  hipporag (>=2.0.0a3 is the HippoRAG2 line)

Why this matters for Q4
-----------------------
HippoRAG2 is a neuroscience-inspired RAG framework that builds an entity-centric
knowledge graph (OpenIE extraction) and uses Personalized PageRank to traverse
it at retrieval time. It is the state-of-the-art GRAPH-based memory paradigm
and the most direct external comparator to nox-mem's KG layer + section/entity
boosts. Including it strengthens the Q4 comparison story:
  - mem0           = LLM-extracted facts + vector store
  - Letta          = agent + archival memory
  - agentmemory    = REST API + observation store
  - Zep            = temporal KG (gated on OpenAI embed)
  - EverMind-AI    = benchmark publisher peer
  - HippoRAG2      = SOTA graph-based RAG (entity-centric + PPR)  <-- this adapter

INVOCATION MODE
---------------
Python SDK (pip-installable, no subprocess / no daemon). HippoRAG2 instantiates
a single ``HippoRAG`` object that owns:
  - the OpenIE pipeline (LLM-driven triple extraction at index time)
  - the entity KG (networkx, in-memory + on-disk pickle)
  - the embedding store (sentence-transformers or OpenAI, configurable)
  - the PPR scorer (numpy/scipy, ~ms per query)

The adapter wraps this object behind the Q4 ``search()`` contract.

ENV REQUIREMENTS
----------------
HippoRAG2's defaults are OpenAI-flavoured (gpt-4o-mini for OpenIE, text-embedding-3-small
for dense retrieval). The library also supports vLLM / Together / local sentence-transformers
via ``llm_base_url`` + ``embedding_model_name`` but we require ``OPENAI_API_KEY`` as the
default fair-comparison path (consistent with mem0 and Letta adapters).

Set ``HIPPORAG_LLM_MODEL`` / ``HIPPORAG_EMBEDDING_MODEL`` / ``HIPPORAG_LLM_BASE_URL``
to override for cost-controlled or local-stack runs.

COST ESTIMATE (full LoCoMo + LongMemEval, ~9,882 chunks)
--------------------------------------------------------
Ingest is the expensive step — HippoRAG2 runs OpenIE per chunk (1 LLM call) and
embeds the chunk + each extracted entity (multi embedding calls per chunk).

  - LLM (gpt-4o-mini, OpenIE):  ~9,882 chunks × ~$0.0008/chunk  ≈ $7.90
  - Embeddings (text-emb-3-sm): ~9,882 chunks × ~$0.00003/chunk ≈ $0.30
  - Entity embeddings:          ~3–5× chunk embed volume        ≈ $1.00–1.50

Total estimate: ~$9–11 for full corpus ingest. Set HIPPORAG_INGEST_LIMIT=N for
smoke runs (e.g. N=200 → ~$0.20). Idempotent: HippoRAG persists the graph +
embeddings under ``HIPPORAG_SAVE_DIR``; re-running setup() skips re-extraction
if the save dir already contains the indexed corpus (delta-ingest).

ID ROUND-TRIP
-------------
HippoRAG2 accepts ``passage_id`` (or equivalent) on its index API but the
exact field name shifted between 2.0.0a1 → a3. The adapter follows the same
pattern as the agentmemory adapter: each chunk is indexed with content prefix
``[nox_id:<id>]`` and the prefix is parsed back from retrieved passages so
gold matching against the canonical chunk_id (from corpus_loader) works
regardless of upstream API drift.

SEARCH MODEL
------------
HippoRAG2.retrieve(queries=[query], num_to_retrieve=k) returns a list of
``QuerySolution`` objects with:
  - .docs      : list[str] of retrieved passages
  - .doc_scores: list[float] PPR scores (descending)
  - .ranking   : optional list[int] of passage indices

We normalize to the Q4 contract {id, score, text, source}, parsing nox_id from
the content prefix and falling back to the retrieved string identifier if
HippoRAG2 surfaces one directly (post-2.0.0a3 may return passage_ids).

VALIDATE
--------
Smoke import + env-var check only (no network call). Reports which embedding /
LLM backend is configured so smoke_test.py can show capacity to the operator.

CAVEATS
-------
- Deps: hipporag depends on torch, networkx, scipy, sentence-transformers,
  openai. Heavy (~1.2 GB site-packages). Install in a dedicated venv if RAM
  is tight on the runner host.
- No Neo4j required — HippoRAG2 uses networkx in-memory + pickle persistence.
  (HippoRAG1 supported Neo4j but v2 dropped that.)
- HippoRAG2 supports incremental indexing but our setup() runs a single
  insert_to_graph call per corpus session for determinism.
- vLLM / Together backends are tested in the upstream repo but the adapter
  documents OPENAI as the fair-comparison default. Override via
  HIPPORAG_LLM_BASE_URL=http://localhost:8000/v1 to point at vLLM.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

NAME = "hipporag2"
# Pin to the first stable HippoRAG2 release line. Upstream tags drift across
# the a1/a2/a3 alpha series; the adapter is API-tolerant via getattr probes.
VERSION_PIN = "hipporag>=2.0.0a3,<2.1"
REQUIRES_ENV = ["OPENAI_API_KEY"]
INSTALL_HINT = (
    "pip install 'hipporag>=2.0.0a3,<2.1'   "
    "# then: export OPENAI_API_KEY=sk-... (gpt-4o-mini OpenIE + text-emb-3-small)"
)

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/

# Ensure lib/ is importable regardless of cwd
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

_NOX_ID_RE = re.compile(r"^\[nox_id:([^\]]+)\]\s*")
_DEFAULT_SAVE_DIR = str(HERE / ".hipporag-store")

_hippo: Any = None  # singleton HippoRAG instance, initialized in setup()
_setup_done: bool = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _build_config() -> dict[str, Any]:
    """
    Build HippoRAG2 init kwargs from env overrides (with sensible defaults).

    Env knobs (all optional):
        HIPPORAG_SAVE_DIR        — persistence dir (default: .hipporag-store)
        HIPPORAG_LLM_MODEL       — OpenIE / generation model (default: gpt-4o-mini)
        HIPPORAG_EMBEDDING_MODEL — dense retrieval model (default: text-embedding-3-small)
        HIPPORAG_LLM_BASE_URL    — override LLM endpoint (vLLM/Together/local)
    """
    cfg: dict[str, Any] = {
        "save_dir": os.environ.get("HIPPORAG_SAVE_DIR", _DEFAULT_SAVE_DIR),
        "llm_model_name": os.environ.get("HIPPORAG_LLM_MODEL", "gpt-4o-mini"),
        "embedding_model_name": os.environ.get(
            "HIPPORAG_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
    }
    base_url = os.environ.get("HIPPORAG_LLM_BASE_URL")
    if base_url:
        cfg["llm_base_url"] = base_url
    Path(cfg["save_dir"]).mkdir(parents=True, exist_ok=True)
    return cfg


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


def validate() -> dict:
    """
    Smoke import + env probe. NO network calls.

    Returns:
        {ok, error, version, notes}
    """
    try:
        import hipporag  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"hipporag not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }

    missing = [v for v in REQUIRES_ENV if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": getattr(hipporag, "__version__", "unknown"),
            "notes": (
                "export OPENAI_API_KEY=sk-... (gpt-4o-mini OpenIE + "
                "text-embedding-3-small are HippoRAG2 defaults). Override "
                "via HIPPORAG_LLM_BASE_URL=http://localhost:8000/v1 for vLLM."
            ),
        }

    # Probe the HippoRAG class exists (API name has been stable across a1-a3).
    HippoRAG = getattr(hipporag, "HippoRAG", None)
    if HippoRAG is None:
        return {
            "ok": False,
            "error": "hipporag.HippoRAG class not found — version mismatch?",
            "version": getattr(hipporag, "__version__", "unknown"),
            "notes": (
                "Expected hipporag>=2.0.0a3. Check `pip show hipporag`; "
                "if you're on an older version: pip install -U 'hipporag>=2.0.0a3,<2.1'"
            ),
        }

    return {
        "ok": True,
        "error": None,
        "version": getattr(hipporag, "__version__", "unknown"),
        "notes": (
            f"HippoRAG2 ready. Save dir: {os.environ.get('HIPPORAG_SAVE_DIR', _DEFAULT_SAVE_DIR)}. "
            f"LLM: {os.environ.get('HIPPORAG_LLM_MODEL', 'gpt-4o-mini')}, "
            f"Embed: {os.environ.get('HIPPORAG_EMBEDDING_MODEL', 'text-embedding-3-small')}. "
            "OpenIE ingest is the expensive step (~$9-11 for full Q4 corpus). "
            "Set HIPPORAG_INGEST_LIMIT=N for smoke runs."
        ),
    }


# ---------------------------------------------------------------------------
# Corpus iteration (shared loader, no adapter-private parser — see memory:
# [[shared-loader-canonical-pattern]] from Sat 2026-05-24 closure)
# ---------------------------------------------------------------------------


def _iter_corpus_chunks() -> Iterator[Any]:
    """Yield all corpus chunks from the shared corpus_loader.

    Stream order: LoCoMo first, then LongMemEval. HIPPORAG_INGEST_LIMIT caps
    the total count for cost-controlled smoke runs.
    """
    from lib.corpus_loader import load_locomo_corpus, load_longmemeval_corpus  # type: ignore[import]

    limit_raw = os.environ.get("HIPPORAG_INGEST_LIMIT", "")
    limit = int(limit_raw) if limit_raw.isdigit() else None
    count = 0
    for chunk in load_locomo_corpus():
        yield chunk
        count += 1
        if limit is not None and count >= limit:
            return
    for chunk in load_longmemeval_corpus():
        yield chunk
        count += 1
        if limit is not None and count >= limit:
            return


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def _build_passages(chunks: Iterable[Any]) -> list[str]:
    """
    Materialize the chunk stream into HippoRAG2's passage format.

    Each passage is prefixed with ``[nox_id:<id>]`` so search() can parse the
    nox-mem chunk id back, regardless of whether HippoRAG2's API surfaces
    passage_ids directly (varies across alpha versions).
    """
    passages: list[str] = []
    for chunk in chunks:
        nox_id = str(getattr(chunk, "id", "") or "")
        text = getattr(chunk, "text", "") or ""
        if not nox_id or not text:
            continue
        passages.append(f"[nox_id:{nox_id}] {text}")
    return passages


def _ingest_corpus(hippo: Any) -> int:
    """
    Index the LoCoMo + LongMemEval corpus into HippoRAG2 via insert_to_graph.

    Returns the number of passages indexed (0 if corpus empty or unavailable).

    HippoRAG2's index API varies across alpha versions:
      - 2.0.0a1/a2: ``index(passages: list[str])``
      - 2.0.0a3+ : ``insert_to_graph(docs: list[str])`` / ``index(docs)``

    We probe both via getattr and fall through to the first one that exists.
    """
    chunks = list(_iter_corpus_chunks())
    passages = _build_passages(chunks)
    if not passages:
        print(
            "[hipporag2] WARNING: corpus_loader yielded 0 chunks. "
            "Ensure eval/q4-comparison/cache/ exists or network is available "
            "for first-run download. Proceeding with empty corpus."
        )
        return 0

    print(f"[hipporag2] indexing {len(passages)} passages (OpenIE + embed)...")

    # Try API surfaces in order of preference (most recent first)
    for method_name in ("insert_to_graph", "index", "add_documents"):
        method = getattr(hippo, method_name, None)
        if callable(method):
            try:
                method(passages)
                print(f"[hipporag2] index complete via {method_name}() ({len(passages)} passages)")
                return len(passages)
            except TypeError:
                # Wrong signature — try kwarg variants
                try:
                    method(docs=passages)
                    print(f"[hipporag2] index complete via {method_name}(docs=) ({len(passages)} passages)")
                    return len(passages)
                except Exception:
                    pass
                try:
                    method(passages=passages)
                    print(f"[hipporag2] index complete via {method_name}(passages=) ({len(passages)} passages)")
                    return len(passages)
                except Exception:
                    pass
            except Exception as exc:
                print(f"[hipporag2] {method_name}() raised: {type(exc).__name__}: {exc}")
                continue

    raise RuntimeError(
        "[hipporag2] no working index method found on HippoRAG instance — "
        "tried insert_to_graph / index / add_documents. "
        "Pin a known good version: pip install 'hipporag>=2.0.0a3,<2.1'"
    )


# ---------------------------------------------------------------------------
# Setup / Teardown
# ---------------------------------------------------------------------------


def setup() -> None:
    """
    Instantiate the HippoRAG client (singleton) and index the Q4 corpus.

    Idempotent: HippoRAG persists its graph + embeddings to disk. On re-run we
    short-circuit if the save dir already contains an indexed snapshot UNLESS
    HIPPORAG_FORCE_REINGEST=1 is set.
    """
    global _hippo, _setup_done
    if _setup_done and _hippo is not None:
        return

    import hipporag

    HippoRAG = getattr(hipporag, "HippoRAG", None)
    if HippoRAG is None:
        raise RuntimeError(
            "hipporag.HippoRAG class not found. "
            "Check installed version (`pip show hipporag`) and pin to >=2.0.0a3."
        )

    cfg = _build_config()
    try:
        _hippo = HippoRAG(**cfg)
    except TypeError as exc:
        # HippoRAG2 alphas occasionally renamed kwargs (save_dir vs working_dir
        # vs storage_dir). Probe and remap.
        accepted: dict[str, Any] = {}
        try:
            import inspect

            sig = inspect.signature(HippoRAG.__init__)
            params = set(sig.parameters.keys())
            remap = {
                "save_dir": ("save_dir", "working_dir", "storage_dir", "save_directory"),
                "llm_model_name": ("llm_model_name", "llm_model", "openie_llm_model"),
                "embedding_model_name": (
                    "embedding_model_name",
                    "embedding_model",
                    "embed_model_name",
                ),
                "llm_base_url": ("llm_base_url", "llm_endpoint", "openai_base_url"),
            }
            for canonical, candidates in remap.items():
                if canonical not in cfg:
                    continue
                for candidate in candidates:
                    if candidate in params:
                        accepted[candidate] = cfg[canonical]
                        break
            _hippo = HippoRAG(**accepted)
        except Exception:
            raise RuntimeError(
                f"Failed to instantiate HippoRAG with config={cfg}: {exc}. "
                "Inspect upstream API: `python -c 'import hipporag; help(hipporag.HippoRAG)'`"
            ) from exc

    force = os.environ.get("HIPPORAG_FORCE_REINGEST", "").lower() in ("1", "true", "yes")
    save_dir = Path(cfg["save_dir"])

    # Idempotency probe: HippoRAG2 writes openie + graph artifacts under a
    # backend-specific subdir like ``gpt-4o-mini_text-embedding-3-small/``.
    # ``HippoRAG.__init__`` itself eagerly mkdir's those subdirs even when no
    # ingest has run yet, so a bare ``iterdir()`` non-empty check produces a
    # false positive on first run. We require an actual openie results file
    # (``openie_results_ner_*.json`` is what ``save_openie_results`` writes)
    # before we declare the corpus indexed.
    already_indexed = False
    if save_dir.exists():
        already_indexed = bool(list(save_dir.rglob("openie_results_*.json")))
    if already_indexed and not force:
        print(
            f"[hipporag2] openie artifacts found under {save_dir} — skipping re-ingest. "
            "Set HIPPORAG_FORCE_REINGEST=1 to force."
        )
        _setup_done = True
        return

    _ingest_corpus(_hippo)
    _setup_done = True


def teardown() -> None:
    """Release the HippoRAG handle. Disk state survives (idempotent re-setup)."""
    global _hippo, _setup_done
    _hippo = None
    _setup_done = False


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def _parse_nox_id(passage: str) -> tuple[str, str]:
    """Return (nox_id, stripped_text). Falls back to ('', passage) if no prefix."""
    m = _NOX_ID_RE.match(passage)
    if m:
        return m.group(1), passage[m.end():]
    return "", passage


def search(query: str, k: int = 10) -> list[dict]:
    """
    Retrieve top-k passages via HippoRAG2's PPR-based scorer.

    HippoRAG2's retrieve API (across alpha versions):
        retrieve(queries=[q], num_to_retrieve=k) -> list[QuerySolution]
            QuerySolution has .docs (list[str]) + .doc_scores (list[float])

    Some alpha versions expose .ranking + .passage_ids. We probe both and
    normalize to the Q4 contract: {id, score, text, source}.
    """
    if _hippo is None:
        setup()

    if _hippo is None:
        # setup() may legitimately bail (no corpus) — return empty rather than crash
        return []

    # Probe API surface
    retrieve = getattr(_hippo, "retrieve", None) or getattr(_hippo, "search", None)
    if not callable(retrieve):
        raise RuntimeError(
            "HippoRAG instance has neither .retrieve nor .search method — "
            "API drift detected. Pin: pip install 'hipporag>=2.0.0a3,<2.1'"
        )

    # Try the documented signature first, then degrade to positional
    try:
        solutions = retrieve(queries=[query], num_to_retrieve=k)
    except TypeError:
        try:
            solutions = retrieve(queries=[query], k=k)
        except TypeError:
            try:
                solutions = retrieve([query], k)
            except Exception as exc:
                raise RuntimeError(f"hipporag retrieve failed: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"hipporag retrieve failed: {exc}") from exc

    # solutions is list[QuerySolution] (one per query). We only sent one.
    if not solutions:
        return []
    sol = solutions[0] if isinstance(solutions, list) else solutions

    # NB: doc_scores is a numpy.ndarray on HippoRAG2 ≥2.0.0a3 (per QuerySolution
    # dataclass). `arr or []` raises "truth value ambiguous" — coerce explicitly.
    raw_docs = getattr(sol, "docs", None)
    raw_scores = getattr(sol, "doc_scores", None)
    raw_pids = getattr(sol, "passage_ids", None)
    docs: list[str] = list(raw_docs) if raw_docs is not None else []
    scores: list[float] = list(raw_scores) if raw_scores is not None else []
    passage_ids: list[Any] = list(raw_pids) if raw_pids is not None else []

    if not docs:
        # Fallback: some versions return a dict instead of dataclass
        if isinstance(sol, dict):
            raw_docs = sol.get("docs") or sol.get("passages")
            raw_scores = sol.get("doc_scores") or sol.get("scores")
            raw_pids = sol.get("passage_ids")
            docs = list(raw_docs) if raw_docs is not None else []
            scores = list(raw_scores) if raw_scores is not None else []
            passage_ids = list(raw_pids) if raw_pids is not None else []

    out: list[dict] = []
    for i, passage in enumerate(docs[:k]):
        score = float(scores[i]) if i < len(scores) else 0.0
        # Try passage_ids first (post 2.0.0a3) then fall back to prefix parse
        nox_id = ""
        text = passage
        if i < len(passage_ids) and passage_ids[i]:
            pid = str(passage_ids[i])
            # If the upstream id IS our nox_id prefix-content, parse it; otherwise
            # use the prefix-parsed id from the passage text itself.
            parsed_id, parsed_text = _parse_nox_id(passage)
            if parsed_id:
                nox_id = parsed_id
                text = parsed_text
            else:
                nox_id = pid
        else:
            nox_id, text = _parse_nox_id(passage)

        out.append({
            "id": nox_id,
            "score": score,
            "text": text,
            "source": None,
        })
    return out
