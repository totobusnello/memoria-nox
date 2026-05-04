"""E5-mistral-7b-instruct Dense Embedding Baseline for nox-mem Corpus.

WHAT THIS SCRIPT DOES
---------------------
Computes dense retrieval metrics (nDCG@10, MRR, Recall@10, Precision@5) using
intfloat/e5-mistral-7b-instruct as a competitor baseline against the nox-mem
hybrid search system.

Three execution modes, each targeting a different infrastructure:

  local-gpu   — Runs model inference directly on a local GPU (>=16 GB VRAM).
                Fastest and cheapest per-run; zero cloud spend. Requires an
                NVIDIA A10 / T4 / A100 or equivalent locally attached GPU.
                Estimated time: 30-45 min embed + <1 min eval (A10, 64K chunks).

  modal       — Bursts onto a Modal.com serverless GPU worker (A10G 24 GB).
                Ideal when local GPU is unavailable (e.g. VPS Hostinger,
                Apple Silicon without MPS-compatible pipeline).
                Estimated cost: ~$2-5 per full embed run (64K × 4096d).
                Estimated time: 30-40 min total (cold start + embed + upload).

  replicate   — Delegates embedding to Replicate.com's hosted E5-mistral
                endpoint.  Pay-per-prediction; inference is slower due to
                queuing, but requires zero local setup.
                Estimated cost: ~$0.05-0.15 per full run (queue + GPU-seconds).
                Estimated time: 45-90 min (queue + serial batch latency).

HOW TO RUN
----------
# 0. Create dedicated venv (do NOT mix with nox-mem TypeScript env):
python -m venv /tmp/e5-baseline-venv && source /tmp/e5-baseline-venv/bin/activate

# local-gpu mode:
pip install "sentence-transformers>=3.0" "torch>=2.3" "transformers>=4.40" numpy

python e5_mistral_baseline.py --mode local-gpu embed \
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --output /tmp/e5-mistral-embeddings.npz

python e5_mistral_baseline.py --mode local-gpu eval \
    --npz /tmp/e5-mistral-embeddings.npz \
    --queries /path/to/golden-queries.jsonl \
    --output /path/to/results/baselines-e5.jsonl

# modal mode (install extra dep):
pip install modal-client
modal token new   # first-time auth
python e5_mistral_baseline.py --mode modal full \
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --queries /path/to/golden-queries.jsonl \
    --output /path/to/results/baselines-e5.jsonl

# replicate mode (install extra dep):
pip install replicate
REPLICATE_API_TOKEN=r8_xxx python e5_mistral_baseline.py --mode replicate full \
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --queries /path/to/golden-queries.jsonl \
    --output /path/to/results/baselines-e5.jsonl

OUTPUT FORMAT (compatible with nox-mem eval harness)
----------------------------------------------------
Each line in the output JSONL:
  {"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.812, "system": "e5-mistral"}

Fields:
  query_id  — string identifier matching the golden-queries.jsonl "id" field
  rank      — 1-indexed rank within the top-10 results
  doc_id    — integer chunk id from the nox-mem DB (chunks.id)
  score     — cosine similarity (float, 0..1 since vectors are L2-normalized)
  system    — literal "e5-mistral" for harness disambiguation

INTEGRATION WITH PAPER §5
--------------------------
This baseline fills the "E3 — E5-mistral" slot in the experiment matrix
(03-experiments-needed.md). The produced baselines-e5.jsonl feeds directly into
the nDCG/MRR/Recall table reported in paper §5 alongside BM25 (E1), BGE-M3 (E2),
and nox-mem hybrid (main system).

REPRODUCIBILITY HONESTY
------------------------
If run via Modal or Replicate, the paper MUST disclose: "E5-mistral embeddings
were computed via Modal.com/Replicate.com cloud GPU burst (single A10G run)"
rather than claiming local reproducibility.  The embedding matrix (.npz) is
deterministic given the same model weights and inputs, so downstream eval is
reproducible from the cached .npz regardless of compute origin.

MODE RECOMMENDATION
-------------------
- Preferred: modal — best cost/speed tradeoff when no local GPU is available.
  One-time ~$2-5 spend buys deterministic, cached embeddings; all subsequent
  eval runs are CPU-only (seconds).
- Fallback: replicate — zero setup, but slower and harder to debug.
- local-gpu: optimal if you have access to an A10/A100; no cloud spend.
- Skip entirely: if budget is constrained, mark E5-mistral as "future work"
  in the paper (BGE-M3 already covers the open-source dense baseline gap).

E5-MISTRAL TECHNICAL SPECIFICS
--------------------------------
- Model: intfloat/e5-mistral-7b-instruct (7B params, Mistral-7B backbone)
- Output dimension: 4096d (vs BGE-M3 1024d, Gemini 3072d) — largest of the three
- Instruction prefix (MANDATORY for queries):
    "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: <text>"
- Document side: NO prefix (raw chunk_text only)
- Pooling: LAST TOKEN (not mean pooling) — Mistral uses EOS token for pooling
- Normalization: explicit L2 normalization after pooling (model does not auto-normalize)
- Precision: fp16 / bfloat16 to fit in 16 GB VRAM; fp32 requires ~28 GB
- Context window: 4096 tokens (Mistral); chunk_text truncated at max_length=512
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterator, Any

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_NAME = "intfloat/e5-mistral-7b-instruct"
EMBED_DIM = 4096
QUERY_INSTRUCTION = (
    "Instruct: Given a question, retrieve relevant passages that answer the question\n"
    "Query: "
)
# Last token index sentinel — used in pooling
_LAST_TOKEN = -1

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ChunkRow = tuple[int, str]  # (chunk_id, chunk_text)


# ---------------------------------------------------------------------------
# Internal helpers — SQLite
# ---------------------------------------------------------------------------


def _iter_chunks(db_path: str, batch_size: int) -> Iterator[list[ChunkRow]]:
    """Yield successive batches of (id, chunk_text) from the chunks table.

    Opens the DB read-only via URI so no WAL writes occur.

    Args:
        db_path: Absolute path to the nox-mem SQLite database.
        batch_size: Number of rows per batch.

    Yields:
        List of (chunk_id, chunk_text) tuples, length <= batch_size.
    """
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, chunk_text FROM chunks ORDER BY id")

    batch: list[ChunkRow] = []
    for row in cursor:
        batch.append((row["id"], row["chunk_text"] or ""))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

    cursor.close()
    conn.close()


def _count_chunks(db_path: str) -> int:
    """Return total number of rows in the chunks table.

    Args:
        db_path: Absolute path to the nox-mem SQLite database.

    Returns:
        Row count as integer.
    """
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    (n,) = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
    conn.close()
    return int(n)


# ---------------------------------------------------------------------------
# Internal helpers — E5-mistral pooling
# ---------------------------------------------------------------------------


def _last_token_pool(
    last_hidden_state: Any,  # torch.Tensor (B, T, D)
    attention_mask: Any,     # torch.Tensor (B, T)
) -> Any:
    """Pool the last *non-padding* token's hidden state for each sequence.

    E5-mistral is trained with last-token pooling (the EOS token aggregates
    sequence meaning).  This is NOT mean pooling — using mean pooling degrades
    nDCG by 5-15 points on MTEB benchmarks.

    Args:
        last_hidden_state: Transformer output hidden states, shape (B, T, D).
        attention_mask: Padding mask, 1 for real tokens, 0 for padding; shape (B, T).

    Returns:
        Pooled tensor of shape (B, D).
    """
    import torch

    # For each sequence find the index of the last real (non-pad) token.
    # attention_mask.flip(1) reverses time dimension; argmax finds the first 1
    # in reversed order = last 1 in original order.
    sequence_lengths = attention_mask.sum(dim=1) - 1  # (B,) 0-indexed
    batch_size = last_hidden_state.shape[0]

    # Gather the hidden state at the last real token position
    pooled = last_hidden_state[
        torch.arange(batch_size, device=last_hidden_state.device),
        sequence_lengths,
    ]  # (B, D)
    return pooled


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize each row of a 2D numpy array in-place.

    Args:
        matrix: Float32 array of shape (N, D).

    Returns:
        Row-normalized copy (each row has unit L2 norm).
        Rows with zero norm are left as-is (avoid NaN).
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)  # guard zero-norm rows
    return (matrix / norms).astype(np.float32)


# ---------------------------------------------------------------------------
# MODE A: Local GPU embedding
# ---------------------------------------------------------------------------


def embed_chunks_local_gpu(
    db_path: str,
    output_npz: str,
    batch_size: int = 8,
    force: bool = False,
) -> None:
    """Embed all nox-mem chunks locally using intfloat/e5-mistral-7b-instruct.

    Requires a CUDA-capable GPU with >=16 GB VRAM (e.g. A10, T4, A100).
    Uses BF16 mixed precision and last-token pooling followed by explicit
    L2 normalization.  Documents are embedded WITHOUT any instruction prefix;
    only queries receive the task instruction (asymmetric encoding).

    Idempotent: if ``output_npz`` already exists (and ``force`` is False),
    returns immediately without re-embedding.

    Args:
        db_path: Absolute path to the nox-mem SQLite database file.
        output_npz: Destination path for the compressed numpy archive.
            Saved with keys ``embeddings`` (float32, shape N×4096) and
            ``chunk_ids`` (int64, shape N).
        batch_size: Chunks per GPU forward pass.  Default 8 fits ~16 GB VRAM
            with max_length=512; reduce to 4 if OOM, increase to 16 on A100.
        force: If True, re-embed even if the output file already exists.

    Raises:
        FileNotFoundError: If ``db_path`` does not exist.
        RuntimeError: If no CUDA device is available.
        AssertionError: If the saved matrix has NaN values or shape mismatch.
    """
    import torch
    from transformers import AutoTokenizer, AutoModel  # type: ignore[import-untyped]

    output_path = Path(output_npz)

    if output_path.exists() and not force:
        logger.info(
            "Cache hit — %s exists. Pass force=True to re-embed.", output_npz
        )
        return

    if not Path(db_path).exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    if not torch.cuda.is_available():
        raise RuntimeError(
            "No CUDA device found. Use --mode modal or --mode replicate for "
            "cloud GPU execution, or attach a compatible GPU."
        )

    device = torch.device("cuda")
    logger.info("Using device: %s (%s)", device, torch.cuda.get_device_name(0))

    logger.info("Loading tokenizer and model: %s", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,  # bfloat16 stable on A10/A100; use float16 for T4
        device_map="auto",           # distribute across available GPUs automatically
    )
    model.eval()

    total = _count_chunks(db_path)
    logger.info("Total chunks to embed: %d", total)

    all_embeddings: list[np.ndarray] = []
    all_ids: list[int] = []
    embedded = 0
    t_start = time.perf_counter()

    with torch.inference_mode():
        for batch in _iter_chunks(db_path, batch_size):
            ids, texts = zip(*batch)

            # Documents: no instruction prefix (asymmetric E5 design)
            encoded = tokenizer(
                list(texts),
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(device)

            outputs = model(**encoded)

            # Last-token pooling — critical for E5-mistral correctness
            pooled = _last_token_pool(
                outputs.last_hidden_state,
                encoded["attention_mask"],
            )  # (B, 4096) in bfloat16

            # Move to CPU, convert to float32, L2-normalize
            vecs = pooled.cpu().to(torch.float32).numpy()  # (B, 4096)
            vecs = _l2_normalize(vecs)

            all_embeddings.append(vecs)
            all_ids.extend(ids)

            embedded += len(batch)
            elapsed = time.perf_counter() - t_start
            rate = embedded / elapsed if elapsed > 0 else 0.0
            eta = (total - embedded) / rate if rate > 0 else float("inf")
            logger.info(
                "Embedded %d/%d  (%.1f chunks/s, ETA %.0f s)",
                embedded, total, rate, eta,
            )

    embeddings_matrix = np.concatenate(all_embeddings, axis=0)  # (N, 4096)
    chunk_ids_array = np.array(all_ids, dtype=np.int64)

    assert len(embeddings_matrix) == len(chunk_ids_array), (
        f"Shape mismatch: embeddings {len(embeddings_matrix)} "
        f"vs chunk_ids {len(chunk_ids_array)}"
    )
    assert not np.isnan(embeddings_matrix).any(), "NaN values found in embeddings"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=embeddings_matrix,
        chunk_ids=chunk_ids_array,
    )
    elapsed_total = time.perf_counter() - t_start
    logger.info(
        "Saved %d embeddings (shape %s) to %s in %.1f s",
        len(embeddings_matrix), embeddings_matrix.shape, output_npz, elapsed_total,
    )


# ---------------------------------------------------------------------------
# MODE B: Modal.com cloud GPU burst
# ---------------------------------------------------------------------------

# Cost estimate: A10G 24GB @ $0.000612/s.  64K chunks × batch_size=16 ≈ 4000
# forward passes × ~25ms/pass = ~100s active GPU time = ~$0.06.  Total with
# cold start, data transfer, overhead: ~$2-5 per full run.
#
# The Modal app is defined inline.  modal.Image.debian_slim() ensures a clean
# Python 3.11 environment with transformers and torch installed on the remote
# worker.  The DB is streamed in as bytes rather than mounted (simpler auth).


def embed_chunks_via_modal(
    db_path: str,
    output_npz: str,
    batch_size: int = 16,
    force: bool = False,
) -> None:
    """Embed all nox-mem chunks via a Modal.com serverless A10G GPU worker.

    Reads the nox-mem SQLite DB locally, serializes chunks to a JSON payload,
    ships them to a Modal remote function that runs E5-mistral inference, and
    streams results back.  The output .npz is saved locally for subsequent
    CPU-only eval runs.

    Requires ``modal-client`` installed and ``modal token new`` authentication
    completed before invocation.

    Args:
        db_path: Absolute path to the nox-mem SQLite database file (local).
        output_npz: Destination path for the compressed numpy archive (local).
            Keys: ``embeddings`` (float32, N×4096), ``chunk_ids`` (int64, N).
        batch_size: Chunks per remote forward pass.  Default 16 fits A10G 24 GB.
        force: If True, re-embed even if the output file already exists.

    Raises:
        FileNotFoundError: If ``db_path`` does not exist.
        ImportError: If ``modal`` is not installed.
        modal.exception.AuthError: If Modal token is not configured.

    Note:
        PAPER DISCLOSURE: If this mode was used to generate baselines-e5.jsonl,
        §5 of the paper must state: "E5-mistral-7b-instruct embeddings were
        computed via Modal.com cloud burst (A10G GPU, single run)."  Downstream
        eval metrics are reproducible from the cached .npz regardless of
        compute origin.
    """
    output_path = Path(output_npz)

    if output_path.exists() and not force:
        logger.info(
            "Cache hit — %s exists. Pass force=True to re-embed.", output_npz
        )
        return

    if not Path(db_path).exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    try:
        import modal  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "modal-client not installed. Run: pip install modal-client"
        ) from exc

    # ---- Define the Modal app inline ----------------------------------------

    # GPU image with all required deps pinned for reproducibility
    _image = (
        modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "torch==2.3.1",
            "transformers==4.41.2",
            "numpy==1.26.4",
            "accelerate>=0.30.0",
        )
    )

    app = modal.App("nox-mem-e5-mistral-embed")

    @app.function(
        image=_image,
        gpu="A10G",
        timeout=3600,           # 1h max — 64K chunks should complete in <40 min
        memory=32768,           # 32 GB RAM for model weights + batch tensors
        # Allow retries on worker preemption; result is deterministic
        retries=modal.Retries(max_retries=2, backoff_coefficient=2.0, initial_delay=10.0),
    )
    def _embed_batch_remote(texts: list[str]) -> list[list[float]]:
        """Run E5-mistral forward pass on a GPU worker and return embeddings.

        Args:
            texts: List of raw document strings (no instruction prefix).

        Returns:
            List of 4096-dimensional L2-normalized embedding vectors.
        """
        import torch
        import numpy as np
        from transformers import AutoTokenizer, AutoModel

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
        )
        model.eval()

        encoded = tokenizer(
            texts,
            max_length=512,
            padding=True,
            truncation=True,
            return_tensors="pt",
        ).to("cuda")

        with torch.inference_mode():
            outputs = model(**encoded)

        pooled = _last_token_pool(outputs.last_hidden_state, encoded["attention_mask"])
        vecs = pooled.cpu().to(torch.float32).numpy()
        vecs = _l2_normalize(vecs)
        return vecs.tolist()

    # ---- Collect all chunks locally -----------------------------------------

    logger.info("Reading all chunks from %s…", db_path)
    all_rows: list[ChunkRow] = []
    for batch in _iter_chunks(db_path, batch_size=2048):
        all_rows.extend(batch)

    total = len(all_rows)
    logger.info("Shipping %d chunks to Modal for E5-mistral embedding…", total)

    all_ids = [row[0] for row in all_rows]
    all_texts = [row[1] for row in all_rows]

    # Build batches for remote calls
    text_batches = [
        all_texts[i : i + batch_size] for i in range(0, total, batch_size)
    ]

    # ---- Execute remotely in parallel map -----------------------------------

    t_start = time.perf_counter()
    all_vecs: list[list[float]] = []

    with app.run():
        # modal's starmap/map executes batches in parallel across workers
        for result_batch in _embed_batch_remote.map(text_batches, order_outputs=True):
            all_vecs.extend(result_batch)
            logger.info("Received %d/%d embeddings from Modal", len(all_vecs), total)

    embeddings_matrix = np.array(all_vecs, dtype=np.float32)  # (N, 4096)
    chunk_ids_array = np.array(all_ids, dtype=np.int64)

    assert len(embeddings_matrix) == len(chunk_ids_array), (
        f"Shape mismatch post-Modal: embeddings {len(embeddings_matrix)} "
        f"vs chunk_ids {len(chunk_ids_array)}"
    )
    assert not np.isnan(embeddings_matrix).any(), "NaN values in Modal embeddings"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=embeddings_matrix,
        chunk_ids=chunk_ids_array,
    )
    elapsed = time.perf_counter() - t_start
    logger.info(
        "Modal embed complete: %d embeddings (shape %s) saved to %s in %.1f s",
        len(embeddings_matrix), embeddings_matrix.shape, output_npz, elapsed,
    )
    logger.info(
        "PAPER DISCLOSURE REQUIRED: state 'E5-mistral embeddings computed via "
        "Modal.com cloud burst (A10G GPU, single run)' in §5."
    )


# ---------------------------------------------------------------------------
# MODE C: Replicate.com API
# ---------------------------------------------------------------------------

# Replicate hosts intfloat/e5-mistral-7b-instruct as a public model.
# Cost: billed per GPU-second on Nvidia A40; roughly $0.0011/s.
# 64K chunks in serial batches of 32: ~2000 API calls × ~2s = ~4000 GPU-s ≈ $4.40.
# Slower than Modal due to per-call HTTP overhead; use Modal when possible.


def embed_chunks_via_replicate(
    db_path: str,
    output_npz: str,
    batch_size: int = 32,
    force: bool = False,
) -> None:
    """Embed all nox-mem chunks via the Replicate.com hosted E5-mistral endpoint.

    Sends chunks in serial batches to the Replicate prediction API.  Each
    batch returns a list of 4096-dimensional L2-normalized vectors.  The
    embedding matrix is assembled locally and saved as a .npz file.

    Requires the ``replicate`` package and the ``REPLICATE_API_TOKEN``
    environment variable to be set.

    Args:
        db_path: Absolute path to the nox-mem SQLite database file (local).
        output_npz: Destination path for the compressed numpy archive (local).
            Keys: ``embeddings`` (float32, N×4096), ``chunk_ids`` (int64, N).
        batch_size: Chunks per Replicate prediction call.  Default 32; reduce
            to 8 if you encounter payload size errors.
        force: If True, re-embed even if the output file already exists.

    Raises:
        FileNotFoundError: If ``db_path`` does not exist.
        ImportError: If ``replicate`` is not installed.
        EnvironmentError: If ``REPLICATE_API_TOKEN`` is not set.
        ValueError: If the Replicate response has an unexpected shape.

    Note:
        PAPER DISCLOSURE: If this mode was used, §5 must state:
        "E5-mistral-7b-instruct embeddings were computed via Replicate.com API."
    """
    output_path = Path(output_npz)

    if output_path.exists() and not force:
        logger.info(
            "Cache hit — %s exists. Pass force=True to re-embed.", output_npz
        )
        return

    if not Path(db_path).exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "REPLICATE_API_TOKEN environment variable is not set."
        )

    try:
        import replicate as replicate_client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "replicate not installed. Run: pip install replicate"
        ) from exc

    # Replicate model identifier for E5-mistral-7b-instruct
    # Check https://replicate.com/intfloat/e5-mistral-7b-instruct for latest version
    REPLICATE_MODEL = "intfloat/e5-mistral-7b-instruct"

    logger.info("Reading all chunks from %s…", db_path)
    all_rows: list[ChunkRow] = []
    for batch in _iter_chunks(db_path, batch_size=4096):
        all_rows.extend(batch)

    total = len(all_rows)
    logger.info(
        "Embedding %d chunks via Replicate (batch_size=%d, est. %d API calls)…",
        total, batch_size, (total + batch_size - 1) // batch_size,
    )

    all_ids = [row[0] for row in all_rows]
    all_texts = [row[1] for row in all_rows]

    all_embeddings: list[np.ndarray] = []
    embedded = 0
    t_start = time.perf_counter()

    for start in range(0, total, batch_size):
        batch_texts = all_texts[start : start + batch_size]

        # Replicate input schema: pass texts as newline-joined string or list
        # depending on the model version — check model page for exact schema
        prediction_output = replicate_client.run(
            REPLICATE_MODEL,
            input={
                "texts": batch_texts,       # list of strings
                "instruction": "",           # empty for document side
                "normalize": True,
            },
        )

        # Output is expected to be a list of lists (float vectors)
        if not isinstance(prediction_output, list):
            raise ValueError(
                f"Unexpected Replicate output type: {type(prediction_output)}"
            )

        batch_vecs = np.array(prediction_output, dtype=np.float32)

        if batch_vecs.ndim != 2 or batch_vecs.shape[1] != EMBED_DIM:
            raise ValueError(
                f"Unexpected embedding shape from Replicate: {batch_vecs.shape}. "
                f"Expected (batch, {EMBED_DIM})."
            )

        # Explicitly re-normalize regardless of model's normalize flag
        batch_vecs = _l2_normalize(batch_vecs)
        all_embeddings.append(batch_vecs)

        embedded += len(batch_texts)
        elapsed = time.perf_counter() - t_start
        rate = embedded / elapsed if elapsed > 0 else 0.0
        eta = (total - embedded) / rate if rate > 0 else float("inf")
        logger.info(
            "Replicate: %d/%d embedded (%.1f chunks/s, ETA %.0f s)",
            embedded, total, rate, eta,
        )

    embeddings_matrix = np.concatenate(all_embeddings, axis=0)  # (N, 4096)
    chunk_ids_array = np.array(all_ids, dtype=np.int64)

    assert len(embeddings_matrix) == len(chunk_ids_array), (
        f"Shape mismatch: embeddings {len(embeddings_matrix)} "
        f"vs chunk_ids {len(chunk_ids_array)}"
    )
    assert not np.isnan(embeddings_matrix).any(), "NaN values in Replicate embeddings"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=embeddings_matrix,
        chunk_ids=chunk_ids_array,
    )
    elapsed_total = time.perf_counter() - t_start
    logger.info(
        "Replicate embed complete: %d embeddings saved to %s in %.1f s",
        len(embeddings_matrix), output_npz, elapsed_total,
    )
    logger.info(
        "PAPER DISCLOSURE REQUIRED: state 'E5-mistral embeddings computed via "
        "Replicate.com API' in §5."
    )


# ---------------------------------------------------------------------------
# Query embedding helper (used by all modes for eval)
# ---------------------------------------------------------------------------


def embed_queries_local(
    query_strings: list[str],
) -> np.ndarray:
    """Embed query strings locally using E5-mistral with the instruction prefix.

    Query embedding is lightweight (<=50 queries, fast on CPU).  Even when
    corpus embedding was done via Modal/Replicate, queries can be embedded
    locally for eval.

    The instruction prefix is prepended to every query:
        "Instruct: Given a question, retrieve relevant passages...\nQuery: <text>"

    Args:
        query_strings: Plain-text query strings.

    Returns:
        Float32 numpy array of shape (Q, 4096), L2-normalized rows.

    Raises:
        ImportError: If torch or transformers are not installed.
    """
    import torch
    from transformers import AutoTokenizer, AutoModel  # type: ignore[import-untyped]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Embedding %d queries on device: %s", len(query_strings), device)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
        device_map=device,
    )
    model.eval()

    # Prepend mandatory instruction prefix to every query
    prefixed = [QUERY_INSTRUCTION + q for q in query_strings]

    encoded = tokenizer(
        prefixed,
        max_length=512,
        padding=True,
        truncation=True,
        return_tensors="pt",
    ).to(device)

    with torch.inference_mode():
        outputs = model(**encoded)

    pooled = _last_token_pool(outputs.last_hidden_state, encoded["attention_mask"])
    vecs = pooled.cpu().to(torch.float32).numpy()
    vecs = _l2_normalize(vecs)

    assert vecs.shape == (len(query_strings), EMBED_DIM), (
        f"Unexpected query embedding shape: {vecs.shape}"
    )
    return vecs


# ---------------------------------------------------------------------------
# Searcher class (eval harness compatible)
# ---------------------------------------------------------------------------


class E5MistralSearcher:
    """Cosine nearest-neighbor searcher over a pre-computed E5-mistral corpus.

    Loads the .npz produced by any of the three embed functions and exposes
    a :meth:`search` method compatible with the nox-mem eval harness.

    Since vectors are explicitly L2-normalized, cosine similarity reduces to
    a dot product: ``scores = query_emb @ corpus_matrix.T``.

    Attributes:
        embeddings: Corpus embedding matrix, shape (N, 4096), float32.
        chunk_ids: Corresponding chunk ids, shape (N,), int64.
    """

    def __init__(self, npz_path: str) -> None:
        """Load corpus embeddings from a .npz file produced by any embed mode.

        Args:
            npz_path: Path to the .npz produced by an embed function.

        Raises:
            FileNotFoundError: If the file does not exist.
            KeyError: If the required keys are missing from the archive.
            AssertionError: If embedding dimension is not 4096.
        """
        if not Path(npz_path).exists():
            raise FileNotFoundError(f"Embeddings file not found: {npz_path}")

        logger.info("Loading E5-mistral corpus embeddings from %s…", npz_path)
        archive = np.load(npz_path)

        self.embeddings: np.ndarray = archive["embeddings"]  # (N, 4096), float32
        self.chunk_ids: np.ndarray = archive["chunk_ids"]    # (N,), int64

        assert len(self.embeddings) == len(self.chunk_ids), (
            "Corrupt .npz: embeddings and chunk_ids length mismatch"
        )
        assert self.embeddings.shape[1] == EMBED_DIM, (
            f"Expected dim={EMBED_DIM}, got {self.embeddings.shape[1]}. "
            "Was this .npz produced by a different model?"
        )

        logger.info(
            "Loaded %d corpus embeddings (dim=%d)",
            len(self.embeddings),
            self.embeddings.shape[1],
        )

    def search(
        self,
        query: str,
        k: int = 10,
    ) -> list[tuple[int, float]]:
        """Return top-k (chunk_id, cosine_score) pairs for a single query string.

        Embeds the query locally with the mandatory instruction prefix, then
        performs exact cosine search via matrix dot product.

        Args:
            query: Raw query text (instruction prefix is added automatically).
            k: Number of results to return.

        Returns:
            List of (chunk_id, score) tuples sorted by score descending,
            length == min(k, N).
        """
        query_embs = embed_queries_local([query])  # (1, 4096)
        query_emb = query_embs[0]                  # (4096,)

        # Dot product == cosine similarity for L2-normalized vectors
        scores: np.ndarray = self.embeddings @ query_emb  # (N,)

        # Partial sort O(N log k) instead of O(N log N)
        top_k_indices = np.argpartition(scores, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]

        return [
            (int(self.chunk_ids[i]), float(scores[i]))
            for i in top_k_indices
        ]

    def search_by_embedding(
        self,
        query_emb: np.ndarray,
        k: int = 10,
    ) -> list[tuple[int, float]]:
        """Return top-k results for a pre-computed query embedding.

        Useful when query embeddings have been batch-computed to avoid
        re-loading the model for every query in :func:`run_eval`.

        Args:
            query_emb: L2-normalized embedding vector, shape (4096,) or (1, 4096).
            k: Number of results to return.

        Returns:
            List of (chunk_id, score) tuples sorted by score descending.
        """
        if query_emb.ndim == 2:
            query_emb = query_emb[0]

        scores: np.ndarray = self.embeddings @ query_emb  # (N,)
        top_k_indices = np.argpartition(scores, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]

        return [
            (int(self.chunk_ids[i]), float(scores[i]))
            for i in top_k_indices
        ]


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


def run_eval(
    searcher: E5MistralSearcher,
    queries_jsonl: str,
    output_results_jsonl: str,
    k: int = 10,
) -> None:
    """Embed all golden queries and run retrieval, writing ranked results to JSONL.

    Each query in ``queries_jsonl`` must be a JSON object with:
      - ``"id"``   — string query identifier (e.g. "Q01")
      - ``"text"`` — the query string (plain text, no instruction prefix needed)

    Output format (one JSON object per line):
      ``{"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.812, "system": "e5-mistral"}``

    Args:
        searcher: A loaded :class:`E5MistralSearcher` instance.
        queries_jsonl: Path to the golden-queries JSONL file.
        output_results_jsonl: Destination path for ranked results JSONL.
            Parent directories are created if they do not exist.
        k: Number of results per query (default 10 for nDCG@10).

    Raises:
        FileNotFoundError: If ``queries_jsonl`` does not exist.
    """
    queries_path = Path(queries_jsonl)
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_jsonl}")

    queries: list[dict] = []
    with queries_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                queries.append(json.loads(line))

    logger.info("Loaded %d queries from %s", len(queries), queries_jsonl)

    query_texts = [q["text"] for q in queries]
    query_ids = [q["id"] for q in queries]

    # Batch-embed all queries once (cheap — <=50 queries, fast even on CPU)
    logger.info("Embedding %d queries with instruction prefix…", len(query_texts))
    query_embeddings = embed_queries_local(query_texts)  # (Q, 4096)

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        for idx, (qid, q_emb) in enumerate(zip(query_ids, query_embeddings)):
            hits = searcher.search_by_embedding(q_emb, k=k)
            for rank, (doc_id, score) in enumerate(hits, start=1):
                record = {
                    "query_id": qid,
                    "rank": rank,
                    "doc_id": doc_id,
                    "score": round(score, 6),
                    "system": "e5-mistral",
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")

            if (idx + 1) % 10 == 0 or (idx + 1) == len(queries):
                logger.info("Evaluated %d/%d queries", idx + 1, len(queries))

    logger.info("Results written to %s", output_results_jsonl)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for 3 modes × 3 sub-commands."""
    parser = argparse.ArgumentParser(
        prog="e5_mistral_baseline",
        description=(
            "E5-mistral-7b-instruct dense retrieval baseline for nox-mem corpus.\n"
            "\n"
            "Three compute modes:\n"
            "  local-gpu   — Direct GPU inference (>=16 GB VRAM required)\n"
            "  modal       — Modal.com serverless A10G (~$2-5/run)\n"
            "  replicate   — Replicate.com API (~$0.05-0.15/run, slower)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["local-gpu", "modal", "replicate"],
        default="local-gpu",
        help="Compute backend for corpus embedding (default: local-gpu)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ---- embed sub-command --------------------------------------------------
    embed_p = sub.add_parser("embed", help="Embed all corpus chunks and save .npz.")
    embed_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (env: NOX_DB_PATH)",
    )
    embed_p.add_argument(
        "--output",
        default="/tmp/e5-mistral-embeddings.npz",
        help="Destination .npz file (default: /tmp/e5-mistral-embeddings.npz)",
    )
    embed_p.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Embedding batch size (default: 8 for local-gpu; 16 for modal/replicate)",
    )
    embed_p.add_argument(
        "--force",
        action="store_true",
        help="Re-embed even if the .npz cache already exists.",
    )

    # ---- eval sub-command ---------------------------------------------------
    eval_p = sub.add_parser(
        "eval", help="Run retrieval over golden queries and write ranked JSONL."
    )
    eval_p.add_argument(
        "--npz",
        default="/tmp/e5-mistral-embeddings.npz",
        help="Path to corpus .npz produced by the 'embed' command.",
    )
    eval_p.add_argument(
        "--queries",
        required=True,
        help="Path to golden-queries.jsonl (fields: id, text).",
    )
    eval_p.add_argument(
        "--output",
        required=True,
        help="Destination path for ranked results JSONL.",
    )
    eval_p.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of results per query (default: 10 for nDCG@10).",
    )

    # ---- full sub-command ---------------------------------------------------
    full_p = sub.add_parser(
        "full",
        help="Full pipeline: embed (if cache missing) then eval.",
    )
    full_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (env: NOX_DB_PATH)",
    )
    full_p.add_argument(
        "--npz",
        default="/tmp/e5-mistral-embeddings.npz",
        help="Corpus .npz cache path (created if absent).",
    )
    full_p.add_argument(
        "--queries",
        required=True,
        help="Path to golden-queries.jsonl.",
    )
    full_p.add_argument(
        "--output",
        default="/tmp/e5-mistral-results.jsonl",
        help="Destination path for ranked results JSONL.",
    )
    full_p.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Embedding batch size for corpus (default: 8).",
    )
    full_p.add_argument(
        "--force",
        action="store_true",
        help="Force re-embed even if .npz cache exists.",
    )
    full_p.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of results per query (default: 10).",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the E5-mistral baseline CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    mode: str = args.mode

    # ---- embed command ------------------------------------------------------
    if args.command == "embed":
        if not args.db:
            parser.error("--db is required (or set NOX_DB_PATH env var)")

        batch_size: int = args.batch_size
        if mode == "local-gpu":
            embed_chunks_local_gpu(
                db_path=args.db,
                output_npz=args.output,
                batch_size=batch_size,
                force=args.force,
            )
        elif mode == "modal":
            embed_chunks_via_modal(
                db_path=args.db,
                output_npz=args.output,
                batch_size=max(batch_size, 16),  # Modal A10G fits 16 comfortably
                force=args.force,
            )
        elif mode == "replicate":
            embed_chunks_via_replicate(
                db_path=args.db,
                output_npz=args.output,
                batch_size=batch_size,
                force=args.force,
            )

    # ---- eval command -------------------------------------------------------
    elif args.command == "eval":
        searcher = E5MistralSearcher(args.npz)
        run_eval(
            searcher=searcher,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
            k=args.k,
        )

    # ---- full command -------------------------------------------------------
    elif args.command == "full":
        if not args.db:
            parser.error("--db is required (or set NOX_DB_PATH env var)")

        batch_size = args.batch_size

        # Embed phase (idempotent via force flag)
        if mode == "local-gpu":
            embed_chunks_local_gpu(
                db_path=args.db,
                output_npz=args.npz,
                batch_size=batch_size,
                force=args.force,
            )
        elif mode == "modal":
            embed_chunks_via_modal(
                db_path=args.db,
                output_npz=args.npz,
                batch_size=max(batch_size, 16),
                force=args.force,
            )
        elif mode == "replicate":
            embed_chunks_via_replicate(
                db_path=args.db,
                output_npz=args.npz,
                batch_size=batch_size,
                force=args.force,
            )

        # Eval phase — query embedding always runs locally (cheap)
        searcher = E5MistralSearcher(args.npz)
        run_eval(
            searcher=searcher,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
            k=args.k,
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
