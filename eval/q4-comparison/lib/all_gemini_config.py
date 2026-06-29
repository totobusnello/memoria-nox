"""
lib/all_gemini_config.py — rc4 "all-Gemini fair" embedding configuration.

Purpose:
  Control the embedding-provider confound in §6 (Q4 comparison) by forcing
  all participating systems to use the same Gemini embedder. This module
  provides constants, config builders, and a mem0 adapter patch — all
  WITHOUT touching existing adapter files.

Usage (from runner_rc4.py or a pre-run script):

    from lib.all_gemini_config import patch_mem0_adapter, assert_env_ready
    assert_env_ready()
    patch_mem0_adapter()
    # ... then import runner and run normally

Constants:
  GEMINI_EMBED_PROVIDER   — "gemini" (mem0 provider key)
  GEMINI_EMBED_MODEL      — "models/gemini-embedding-001"
  GEMINI_EMBED_DIM        — 768  (SDK default; see note below)
  GEMINI_ENV_KEY          — "GOOGLE_API_KEY" (what mem0 Gemini embedder reads)
  CHROMA_COLLECTION_RC4   — "q4-eval-gemini" (separate from OpenAI run)
  CHROMA_PATH_RC4_DEFAULT — ".mem0-chroma-gemini" (default path suffix)

Dim note:
  gemini-embedding-001 returns 768d when called without output_dimensionality.
  Prod nox-mem uses 3072d (explicit outputDimensionality in TypeScript source
  staged-A3/edits/src/providers/embedding/gemini.ts:27). rc4 uses 768d because:
    (a) nox_mem hybrid adapter does not pass output_dimensionality (nox_mem.py:84)
    (b) mem0 Gemini embedder defaults to 768 (mem0/embeddings/gemini.py)
    (c) changing to 3072d would require editing adapters (forbidden for rc4)
  This is documented in docs/rc4-all-gemini-plan.md §2.

Thread-leak warning (mem0):
  mem0 leaks threads via PostHog telemetry. Before any mem0 call:
    export MEM0_TELEMETRY=False
    export ANONYMIZED_TELEMETRY=False
  Run ingest and search in SEPARATE subprocesses. See plan §3.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEMINI_EMBED_PROVIDER: str = "gemini"
GEMINI_EMBED_MODEL: str = "models/gemini-embedding-001"
GEMINI_EMBED_DIM: int = 768  # SDK default (no output_dimensionality override)
GEMINI_ENV_KEY: str = "GOOGLE_API_KEY"

CHROMA_COLLECTION_RC4: str = "q4-eval-gemini"
CHROMA_PATH_RC4_DEFAULT: str = ".mem0-chroma-gemini"

# Env vars that must be set before mem0 processes start
_TELEMETRY_ENV: dict[str, str] = {
    "MEM0_TELEMETRY": "False",
    "ANONYMIZED_TELEMETRY": "False",
}

# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/


def gemini_api_key() -> str:
    """Return the Gemini API key from env (GOOGLE_API_KEY or GEMINI_API_KEY).

    mem0's Gemini embedder reads GOOGLE_API_KEY. nox_mem hybrid reads GEMINI_API_KEY.
    This function resolves either, with GOOGLE_API_KEY taking precedence.

    Raises:
        RuntimeError: if neither env var is set.
    """
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
    if not key:
        raise RuntimeError(
            "rc4 requires GOOGLE_API_KEY (or GEMINI_API_KEY as fallback). "
            "Set: export GOOGLE_API_KEY=$GEMINI_API_KEY"
        )
    return key


def ensure_telemetry_off() -> None:
    """Set mem0 telemetry env vars in the current process.

    Call this before importing or calling any mem0 code. mem0 spawns PostHog
    telemetry threads on every add()/search() which exhausts PID limits at scale.
    See memory [[feedback_mem0_thread_leak_telemetry_faiss_architecture]].
    """
    for k, v in _TELEMETRY_ENV.items():
        os.environ.setdefault(k, v)


def assert_env_ready() -> None:
    """Raise RuntimeError if required env vars for rc4 are missing.

    Checks:
      - GOOGLE_API_KEY or GEMINI_API_KEY (at least one must be set)
      - NOX_EVAL_MODE == "hybrid" (nox_mem must run in hybrid/Gemini mode)
    Does NOT check OPENAI_API_KEY — assumed not needed when MEM0_SKIP_LLM_EXTRACTION=1.
    """
    gemini_api_key()  # raises if missing

    nox_mode = os.environ.get("NOX_EVAL_MODE", "eval")
    if nox_mode != "hybrid":
        raise RuntimeError(
            f"NOX_EVAL_MODE must be 'hybrid' for rc4 (got {nox_mode!r}). "
            "Set: export NOX_EVAL_MODE=hybrid"
        )

    ensure_telemetry_off()


# ---------------------------------------------------------------------------
# mem0 Gemini config builder
# ---------------------------------------------------------------------------


def get_mem0_gemini_config(chroma_path: str | None = None) -> dict[str, Any]:
    """Return a mem0 Memory.from_config() config dict using Gemini embedder.

    The config:
      - Replaces the default OpenAI embedder with GoogleGenAIEmbedding
        (provider="gemini", model=gemini-embedding-001, dim=768)
      - Points Chroma at a NEW collection (q4-eval-gemini) to avoid a
        dimension mismatch with the existing OpenAI 1536d collection
      - Does NOT include an LLM section → mem0 keeps its OpenAI LLM default,
        but with MEM0_SKIP_LLM_EXTRACTION=1 (adapter default) it is never called

    Args:
        chroma_path: Absolute or relative path for the Chroma persistent dir.
            Defaults to MEM0_CHROMA_PATH env var or HERE/.mem0-chroma-gemini.

    Returns:
        dict: config suitable for mem0.Memory.from_config(config).
    """
    if chroma_path is None:
        chroma_path = os.environ.get(
            "MEM0_CHROMA_PATH",
            str(HERE / CHROMA_PATH_RC4_DEFAULT),
        )
    Path(chroma_path).mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or None

    config: dict[str, Any] = {
        "embedder": {
            "provider": GEMINI_EMBED_PROVIDER,
            "config": {
                "model": GEMINI_EMBED_MODEL,
                "embedding_dims": GEMINI_EMBED_DIM,
                **({"api_key": api_key} if api_key else {}),
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": CHROMA_COLLECTION_RC4,
                "path": str(chroma_path),
            },
        },
    }
    return config


# ---------------------------------------------------------------------------
# mem0 adapter monkeypatch
# ---------------------------------------------------------------------------


def patch_mem0_adapter() -> bool:
    """Monkeypatch adapters.mem0._build_config to inject Gemini embedder config.

    This is the zero-adapter-edit approach for rc4: replaces _build_config on
    the already-imported (or not-yet-imported) adapters.mem0 module so that
    Memory.from_config() receives the Gemini embedder section.

    Call this BEFORE the runner imports adapters.mem0, or before setup() is called.
    The patch is idempotent: repeated calls replace the same attribute.

    Returns:
        True if patch was applied, False if adapters.mem0 is not importable.
    """
    try:
        # Insert lib path so corpus_loader works when adapters.mem0 is imported
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))

        import importlib
        mod = importlib.import_module("adapters.mem0")
    except ImportError as exc:
        print(
            f"[all_gemini_config] WARNING: cannot import adapters.mem0 — {exc}. "
            "Patch not applied.",
            file=sys.stderr,
        )
        return False

    # Capture the new config builder (closure captures current env at call time)
    def _build_config_gemini() -> dict[str, Any]:
        return get_mem0_gemini_config()

    # Replace _build_config on the module object
    mod._build_config = _build_config_gemini  # type: ignore[attr-defined]

    print(
        f"[all_gemini_config] patched adapters.mem0._build_config → Gemini embedder "
        f"({GEMINI_EMBED_MODEL}, {GEMINI_EMBED_DIM}d, collection={CHROMA_COLLECTION_RC4})",
        file=sys.stderr,
    )
    return True


# ---------------------------------------------------------------------------
# Quick self-check (not a full test, just import validation)
# ---------------------------------------------------------------------------


def _self_check() -> None:
    """Verify constants are consistent and config dict has expected shape."""
    cfg = get_mem0_gemini_config(chroma_path="/tmp/rc4-selfcheck-chroma")
    assert cfg["embedder"]["provider"] == GEMINI_EMBED_PROVIDER, "provider mismatch"
    assert cfg["embedder"]["config"]["model"] == GEMINI_EMBED_MODEL, "model mismatch"
    assert cfg["embedder"]["config"]["embedding_dims"] == GEMINI_EMBED_DIM, "dim mismatch"
    assert cfg["vector_store"]["config"]["collection_name"] == CHROMA_COLLECTION_RC4
    assert GEMINI_EMBED_DIM == 768, "dim must be 768 (SDK default; see docstring)"


_self_check()
