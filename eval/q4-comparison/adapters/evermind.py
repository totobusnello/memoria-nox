"""
EverMind-AI adapter — repo CLI (Python) OR Python module.

Repo: https://github.com/EverOS-AI/EverMind-AI  (license tracked in REQUIREMENTS.md, ~5k stars)
Note: EverOS publishes EverMemBench + papers + their own benchmark numbers,
which makes them the most-explicit "benchmark publisher competitor" of the
five (see memory: `[[everos-benchmark-publisher-competitor]]`).

Install: git clone + pip install -e . (no PyPI package as of 2026-05-21).
Pinned commit recorded in REQUIREMENTS.md once Toto clones Saturday.

INVOCATION PATHS (dual)
-----------------------
Per REQUIREMENTS.md §6: "evermind retrieve CLI assumed but not verified
against public repo as of overnight." The adapter therefore implements
TWO call paths:

  1. CLI (preferred): ``evermind retrieve --query "<q>" --k <k> --json``
     plus ``evermind add --id <id> --text "..."`` for ingestion.

  2. Python module (fallback): set ``EVERMIND_PYTHON_MODULE`` env var to
     the importable path (e.g., ``evermind.retrieval``); the adapter
     looks for ``retrieve``, ``add``/``upsert``/``insert`` callables.

setup() picks the working path via ``_resolve_path()`` and stores it in
``_path_mode``. validate() reports which path will be used. ingest_corpus()
and search() both use _path_mode. If NEITHER path works, ingest_corpus()
returns mode="none" with a clear error and the runner can document the gap.

PATH-USED reporting:
  The ingest result includes ``path_used`` so the PR write-up can record
  honestly which surface produced the numbers (per spec §6).

INGESTION MODEL
---------------
EverMind stores user-supplied ids natively in default config, so no id-map
indirection is needed (unlike Letta/Zep). search() reads .id from response
directly. Idempotency probe via ``evermind list --json`` or ``module.list()``;
if unavailable, we use --upsert / kwargs={"upsert": True}.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Iterable

NAME = "evermind"
VERSION_PIN = "EverMind-AI@git-sha-pinned-saturday (no PyPI as of 2026-05-21)"
REQUIRES_ENV: list[str] = []  # EverMind defaults to local embeddings (sentence-transformers)
INSTALL_HINT = (
    "git clone https://github.com/EverOS-AI/EverMind-AI && "
    "cd EverMind-AI && pip install -e . && evermind --version"
)

# Track which path the adapter is using (cli|python|none). Set by setup().
_path_mode: str = "none"


def _cli_path() -> str | None:
    return shutil.which(os.environ.get("EVERMIND_BIN") or "evermind")


def _python_module() -> str | None:
    return os.environ.get("EVERMIND_PYTHON_MODULE")  # e.g., "evermind.retrieval"


def _resolve_path() -> str:
    """Pick the working invocation path. Sets _path_mode and returns it."""
    global _path_mode
    cli = _cli_path()
    module = _python_module()

    # Prefer CLI when available — it's the documented surface
    if cli is not None:
        try:
            proc = subprocess.run(
                [cli, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0:
                _path_mode = "cli"
                return _path_mode
        except Exception:
            pass

    if module is not None:
        try:
            __import__(module)
            _path_mode = "python"
            return _path_mode
        except ImportError:
            pass

    _path_mode = "none"
    return _path_mode


def validate() -> dict:
    cli = _cli_path()
    module = _python_module()

    if cli is None and module is None:
        return {
            "ok": False,
            "error": "neither `evermind` CLI nor EVERMIND_PYTHON_MODULE configured",
            "version": None,
            "notes": INSTALL_HINT,
        }

    if cli is not None:
        try:
            proc = subprocess.run(
                [cli, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0:
                version = (proc.stdout.strip() or proc.stderr.strip()).splitlines()[0]
                return {
                    "ok": True,
                    "error": None,
                    "version": version,
                    "notes": "CLI mode — verify Saturday commit pinned in REQUIREMENTS.md",
                }
            error_note = proc.stderr.strip()[:200]
        except Exception as exc:  # pragma: no cover
            error_note = str(exc)
        # Fall through to module check if CLI broken
    else:
        error_note = "no CLI on PATH"

    if module is not None:
        try:
            __import__(module)
            return {
                "ok": True,
                "error": None,
                "version": "module:" + module,
                "notes": "Python module mode — confirm retrieve() signature",
            }
        except ImportError as exc:
            return {
                "ok": False,
                "error": f"EVERMIND_PYTHON_MODULE={module} import failed: {exc}",
                "version": None,
                "notes": "Set EVERMIND_PYTHON_MODULE to the importable path",
            }

    return {
        "ok": False,
        "error": f"evermind CLI present but unusable: {error_note}",
        "version": None,
        "notes": "Pin EVERMIND_BIN or EVERMIND_PYTHON_MODULE explicitly",
    }


def setup() -> None:
    _resolve_path()


def teardown() -> None:
    global _path_mode
    _path_mode = "none"


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    Add chunks via CLI (preferred) or Python module fallback.

    Args:
        chunks: iterable of dicts with at least ``id`` and ``text``. Optional
            keys ignored. Namespace pulled from env ``EVERMIND_NAMESPACE``
            (or none) and passed through if the path supports it.

    Returns:
        {ingested, skipped, total, errors, path_used}
    """
    if _path_mode == "none":
        _resolve_path()

    chunks_list = list(chunks)
    total = len(chunks_list)
    namespace = os.environ.get("EVERMIND_NAMESPACE") or None

    if total == 0:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": 0,
            "errors": 0,
            "path_used": _path_mode,
            "mode": "noop",
        }

    if _path_mode == "cli":
        result = _ingest_cli(chunks_list, namespace)
    elif _path_mode == "python":
        result = _ingest_python(chunks_list, namespace)
    else:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": total,
            "errors": total,
            "path_used": "none",
            "mode": "skip",
            "error": "EverMind unavailable — neither CLI nor module configured",
        }
    result["path_used"] = _path_mode
    return result


def _existing_count_cli(cli: str) -> int | None:
    try:
        proc = subprocess.run(
            [cli, "list", "--json"], capture_output=True, text=True, timeout=10, check=False
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("count", "total", "memories", "items"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, list):
                return len(value)
    return None


def _ingest_cli(chunks_list: list[dict], namespace: str | None) -> dict:
    cli = _cli_path()
    if cli is None:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": len(chunks_list),
            "errors": len(chunks_list),
            "mode": "skip",
        }

    total = len(chunks_list)
    existing = _existing_count_cli(cli)
    if existing is not None and existing >= total:
        return {
            "ingested": 0,
            "skipped": total,
            "total": total,
            "errors": 0,
            "mode": "idempotent-skip",
            "note": f"idempotent: existing={existing} >= total={total}",
        }

    ingested = 0
    errors = 0
    base_args = [cli, "add"]
    if namespace:
        base_args += ["--namespace", namespace]

    for chunk in chunks_list:
        nox_id = str(chunk.get("id") or "")
        text = chunk.get("text") or ""
        if not nox_id or not text:
            errors += 1
            continue
        argv = base_args + ["--id", nox_id, "--text", text, "--upsert"]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        except Exception:
            errors += 1
            continue
        if proc.returncode != 0:
            # Retry without --upsert in case of older CLI
            try:
                proc2 = subprocess.run(
                    [a for a in argv if a != "--upsert"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if proc2.returncode != 0:
                    errors += 1
                    continue
            except Exception:
                errors += 1
                continue
        ingested += 1

    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "mode": "subprocess",
    }


def _ingest_python(chunks_list: list[dict], namespace: str | None) -> dict:
    module_name = _python_module()
    if module_name is None:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": len(chunks_list),
            "errors": len(chunks_list),
            "mode": "skip",
        }

    total = len(chunks_list)
    mod = __import__(module_name, fromlist=["add", "list", "upsert", "insert"])
    add_fn = (
        getattr(mod, "add", None)
        or getattr(mod, "upsert", None)
        or getattr(mod, "insert", None)
    )
    list_fn = getattr(mod, "list", None) or getattr(mod, "list_all", None)

    if add_fn is None:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": total,
            "errors": total,
            "mode": "skip",
            "error": f"{module_name} has no add/upsert/insert function",
        }

    # Idempotency probe via module
    if callable(list_fn):
        try:
            existing = list_fn()
            existing_count = len(existing) if hasattr(existing, "__len__") else None
            if existing_count is not None and existing_count >= total:
                return {
                    "ingested": 0,
                    "skipped": total,
                    "total": total,
                    "errors": 0,
                    "mode": "idempotent-skip",
                    "note": f"idempotent: existing={existing_count} >= total={total}",
                }
        except Exception:
            pass

    ingested = 0
    errors = 0
    for chunk in chunks_list:
        nox_id = str(chunk.get("id") or "")
        text = chunk.get("text") or ""
        if not nox_id or not text:
            errors += 1
            continue
        try:
            kwargs: dict[str, Any] = {"id": nox_id, "text": text, "upsert": True}
            if namespace:
                kwargs["namespace"] = namespace
            add_fn(**kwargs)
            ingested += 1
        except TypeError:
            # Older signature: try positional or strip upsert
            try:
                add_fn(nox_id, text)
                ingested += 1
            except Exception:
                errors += 1
        except Exception:
            errors += 1

    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "mode": "module",
    }


def search(query: str, k: int = 10) -> list[dict]:
    if _path_mode == "none":
        _resolve_path()

    if _path_mode == "cli":
        cli = _cli_path()
        if cli is not None:
            return _search_cli(cli, query, k)
    if _path_mode == "python":
        module = _python_module()
        if module is not None:
            return _search_module(module, query, k)
    raise RuntimeError("EverMind-AI not configured — run smoke_test.py")


def _search_cli(cli: str, query: str, k: int) -> list[dict]:
    proc = subprocess.run(
        [cli, "retrieve", "--query", query, "--k", str(k), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"evermind retrieve exit {proc.returncode}: {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"evermind output not JSON: {exc}") from exc
    raw: list[dict[str, Any]] = (
        payload if isinstance(payload, list) else payload.get("results", [])
    )
    return _normalize(raw, k)


def _search_module(module: str, query: str, k: int) -> list[dict]:
    mod = __import__(module, fromlist=["retrieve"])
    retrieve = getattr(mod, "retrieve", None)
    if retrieve is None:
        raise RuntimeError(f"{module}.retrieve not found")
    raw = retrieve(query=query, k=k)
    return _normalize(raw, k)


def _normalize(raw: list[dict[str, Any]], k: int) -> list[dict]:
    return [
        {
            "id": str(item.get("id") or item.get("doc_id") or ""),
            "score": float(item.get("score") or item.get("similarity") or 0.0),
            "text": item.get("text") or item.get("content") or "",
            "source": item.get("source") or None,
        }
        for item in (raw or [])[:k]
    ]
