"""
Ablation runner for nox-mem §5 — dispara E6/E7/E8/E9 em sequência na VPS.

⚠️  PRODUCTION IMPACT: Este script reinicia nox-mem-api e nox-mem-watch
    ~5 vezes, causando ~30s de indisponibilidade por restart.
    Rodar entre 02:00–07:00 BRT (low-traffic window).

Honesty note: as ablations alteram temporariamente o .env de produção.
O kill switch (restore_baseline_env) sempre é chamado via try/finally para
garantir que o sistema volte ao estado canônico independente de falha.

-------------------------------------------------------------------------------
VARIANTES (E6–E9 do 03-experiments-needed.md)
-------------------------------------------------------------------------------
  baseline       — tudo on (sanity check, valida ratio)
  fts_only       — NOX_HYBRID_DISABLE=1 (E6)
  no_rrf         — NOX_RRF_DISABLE=1 + NOX_FUSION_MODE=concat (E7)
  no_salience    — NOX_SALIENCE_MODE=off (E8)
  no_section_boost — NOX_SECTION_BOOST_MODE=off (E9)

-------------------------------------------------------------------------------
USO RÁPIDO
-------------------------------------------------------------------------------
  # Dry-run (inspeciona env diffs, não toca VPS):
  python ablation_runner.py --dry-run --queries /path/to/golden_queries.jsonl

  # Execução real (exige confirmação interativa):
  python ablation_runner.py \\
    --queries /path/to/golden_queries.jsonl \\
    --vps-host root@187.77.234.79 \\
    --env-path /root/.openclaw/.env

  # Usar env var no lugar de --vps-host:
  export NOX_VPS_HOST=root@187.77.234.79
  python ablation_runner.py --queries golden_queries.jsonl

-------------------------------------------------------------------------------
OUTPUTS
-------------------------------------------------------------------------------
  ablation_results.json     — métricas raw por variante
  ablation_table.md         — tabela markdown pronta pro paper §5
  ablation_runlog.txt       — audit trail completo

-------------------------------------------------------------------------------
TIMING ESTIMADO
-------------------------------------------------------------------------------
  Cada variante: restart (~30s) + health wait (~20s) + eval 50 queries (~3min)
  Total: 5 variantes × ~4min ≈ 20-25min serial
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ablation_runner")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_ENV_PATH = "/root/.openclaw/.env"
_DEFAULT_VPS_HOST = "root@187.77.234.79"
_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "results"
_HEALTH_URL = "http://127.0.0.1:18802/api/health"
_HEALTH_TIMEOUT_S = 90   # max seconds to wait for API to recover after restart
_HEALTH_POLL_INTERVAL_S = 3
_EVAL_VARIANT = "hybrid"  # nox-mem eval run --variant flag for all runs

# Services to restart (order matters: api first, then watcher)
_NOX_SERVICES = ("nox-mem-api", "nox-mem-watch")

# Ablation variants ordered: baseline first, then E6–E9
_ORDERED_VARIANTS: list[str] = [
    "baseline",
    "fts_only",
    "no_rrf",
    "no_salience",
    "no_section_boost",
]

# Human-readable labels for the markdown table
_VARIANT_LABELS: dict[str, str] = {
    "baseline": "baseline (full hybrid)",
    "fts_only": "sem semantic (FTS-only) — E6",
    "no_rrf": "sem RRF (concat scores) — E7",
    "no_salience": "sem salience boost — E8",
    "no_section_boost": "sem section_boost — E9",
}

# Experiment IDs for log tracing
_VARIANT_EXPERIMENT: dict[str, str] = {
    "baseline": "baseline",
    "fts_only": "E6",
    "no_rrf": "E7",
    "no_salience": "E8",
    "no_section_boost": "E9",
}


# ---------------------------------------------------------------------------
# 1. Env var configuration per variant
# ---------------------------------------------------------------------------


def set_env_for_variant(variant: str) -> dict[str, str]:
    """Return env var overrides required for a given ablation variant.

    Each variant disables exactly one component of the nox-mem retrieval
    pipeline.  The returned dict is *additive*: these vars are appended to
    (or override) the existing .env.  All other existing vars remain.

    Args:
        variant: One of ``baseline``, ``fts_only``, ``no_rrf``,
            ``no_salience``, ``no_section_boost``.

    Returns:
        Dict mapping env var name to value string.  Empty dict means
        no overrides (baseline = all components on).

    Raises:
        ValueError: If ``variant`` is not a recognised ablation key.

    Decision: serial ablations share the same production deploy because
    nox-mem is a single-node service on the VPS.  Parallel ablations would
    require separate processes writing to separate DBs, which is
    out-of-scope for this sprint.
    """
    env_map: dict[str, dict[str, str]] = {
        "baseline": {},  # No overrides — all components on
        "fts_only": {
            "NOX_HYBRID_DISABLE": "1",
        },
        "no_rrf": {
            "NOX_RRF_DISABLE": "1",
            "NOX_FUSION_MODE": "concat",
        },
        "no_salience": {
            "NOX_SALIENCE_MODE": "off",
        },
        "no_section_boost": {
            "NOX_SECTION_BOOST_MODE": "off",
        },
    }
    if variant not in env_map:
        raise ValueError(
            f"Unknown variant '{variant}'. "
            f"Valid options: {sorted(env_map)}"
        )
    return env_map[variant]


# ---------------------------------------------------------------------------
# 2. SSH helper
# ---------------------------------------------------------------------------


def _ssh(
    host: str,
    command: str,
    *,
    check: bool = True,
    capture_output: bool = True,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command on the remote VPS via SSH.

    Uses execFileSync-style array form (no shell string interpolation) for
    the ssh invocation itself, so the ``host`` argument cannot inject extra
    SSH flags even if it contains spaces or dashes.  The remote ``command``
    is passed as a single quoted string and executed by the remote shell.

    Args:
        host: SSH target, e.g. ``root@187.77.234.79``.
        command: Shell command to run on the remote host.
        check: If True, raise CalledProcessError on non-zero exit.
        capture_output: If True, capture stdout/stderr and return them.
        timeout: Maximum seconds before subprocess.TimeoutExpired.

    Returns:
        CompletedProcess with stdout/stderr as strings (if captured).

    Raises:
        subprocess.CalledProcessError: On non-zero exit when check=True.
        subprocess.TimeoutExpired: If the command exceeds ``timeout``.
    """
    cmd: list[str] = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        host,
        command,
    ]
    logger.debug("SSH → %s: %s", host, command)
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        check=check,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# 3. Restart services with env overrides
# ---------------------------------------------------------------------------


def restart_nox_mem_services(
    host: str,
    env_path: str,
    env_overrides: dict[str, str],
    *,
    dry_run: bool = False,
) -> None:
    """Apply env overrides remotely and restart nox-mem services.

    Remote operations (in order):
    1. Backup current .env → .env.bak (idempotent — overwrites previous bak)
    2. Append/overwrite each override var in .env using sed-safe key-based
       replacement (sed on text files only — never on .db files).
    3. ``systemctl restart nox-mem-api nox-mem-watch``
    4. Wait for /api/health to return HTTP 200.

    If any step fails, the function raises and the caller's try/finally
    must call ``restore_baseline_env`` to recover.

    Args:
        host: SSH target string (e.g. ``root@187.77.234.79``).
        env_path: Absolute path to .env on the remote host.
        env_overrides: Dict of var names → values to apply.
            Empty dict = no env changes (baseline case).
        dry_run: If True, log what would happen without executing.

    Raises:
        RuntimeError: If the API fails to become healthy within timeout.
        subprocess.CalledProcessError: On any SSH command failure.
    """
    ts = _now_iso()

    if not env_overrides:
        logger.info("[%s] No env overrides for this variant — skip env edit", ts)
    else:
        logger.info("[%s] Applying env overrides: %s", ts, env_overrides)

    if dry_run:
        logger.info("[DRY-RUN] Would apply overrides: %s", env_overrides)
        logger.info("[DRY-RUN] Would restart: %s", _NOX_SERVICES)
        logger.info("[DRY-RUN] Would wait for %s to return 200", _HEALTH_URL)
        return

    # Step 1: Backup .env
    backup_cmd = f"cp -f {env_path} {env_path}.bak"
    _ssh(host, backup_cmd)
    logger.info("Backed up .env → %s.bak", env_path)

    # Step 2: Apply each override.
    # Strategy: use sed to replace existing line if key exists, else append.
    # sed operates only on .env (text file) — never on .db files (CLAUDE.md rule §7).
    for key, value in env_overrides.items():
        # Escape forward slashes in value for sed delimiter safety
        escaped_value = value.replace("/", r"\/")
        # If key exists anywhere in the file (even commented), replace the
        # uncommented assignment; otherwise append at end of file.
        sed_replace = (
            f"grep -qE '^{key}=' {env_path} "
            f"&& sed -i 's|^{key}=.*|{key}={escaped_value}|' {env_path} "
            f"|| echo '{key}={value}' >> {env_path}"
        )
        _ssh(host, sed_replace)
        logger.info("Set %s=%s in %s", key, value, env_path)

    # Step 3: Log .env hash for audit
    hash_cmd = f"md5sum {env_path} | awk '{{print $1}}'"
    result = _ssh(host, hash_cmd)
    env_hash = result.stdout.strip()
    logger.info("Post-override .env hash: %s", env_hash)

    # Step 4: Restart services
    services_str = " ".join(_NOX_SERVICES)
    restart_cmd = f"systemctl restart {services_str}"
    logger.info("Restarting services: %s", services_str)
    _ssh(host, restart_cmd, timeout=60)

    # Step 5: Wait for /api/health
    _wait_for_health(host)


def _wait_for_health(host: str) -> None:
    """Poll /api/health until it returns 200 or timeout is exceeded.

    Args:
        host: SSH target for polling (health endpoint is localhost-only).

    Raises:
        RuntimeError: If the health endpoint does not respond OK within
            ``_HEALTH_TIMEOUT_S`` seconds.
    """
    deadline = time.monotonic() + _HEALTH_TIMEOUT_S
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            result = _ssh(
                host,
                f"curl -sf {_HEALTH_URL} | jq -r '.status // \"unknown\"'",
                check=False,
                timeout=15,
            )
            status = result.stdout.strip()
            if result.returncode == 0 and status == "ok":
                logger.info(
                    "API healthy after %d poll(s) — status=%s", attempt, status
                )
                return
            logger.debug(
                "Health poll %d: returncode=%d status=%s stderr=%s",
                attempt,
                result.returncode,
                status,
                result.stderr.strip()[:120],
            )
        except subprocess.TimeoutExpired:
            logger.debug("Health poll %d timed out", attempt)

        time.sleep(_HEALTH_POLL_INTERVAL_S)

    raise RuntimeError(
        f"nox-mem-api did not become healthy within {_HEALTH_TIMEOUT_S}s "
        f"after {attempt} poll attempts. Check: ssh {host} "
        f"'journalctl -u nox-mem-api -n 20 --no-pager'"
    )


# ---------------------------------------------------------------------------
# 4. Run eval for one variant
# ---------------------------------------------------------------------------


def run_eval_for_variant(
    host: str,
    env_path: str,
    variant: str,
    queries_jsonl: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Invoke ``nox-mem eval run`` on the VPS and parse the JSON output.

    Uses a tag ``ablation-<variant>`` to distinguish these runs from normal
    eval runs in the eval_runs table.  Parses the stdout JSON block that
    nox-mem eval run emits after ``## Eval Run #N``.

    The command sources .env before invocation (CLAUDE.md rule §1: required
    for Gemini embeddings to be available during vector eval steps).

    Args:
        host: SSH target.
        env_path: Path to .env on remote (sourced before nox-mem invocation).
        variant: Ablation variant name (used as note tag).
        queries_jsonl: Absolute path to golden_queries.jsonl on remote host.
        dry_run: If True, return a placeholder result without SSH execution.

    Returns:
        Dict with keys: ``ndcg_at_10``, ``mrr``, ``recall_at_10``,
        ``precision_at_5``, ``query_count``, ``duration_ms``, ``run_id``,
        ``variant``, ``note``, ``raw_output`` (truncated stderr).

    Raises:
        RuntimeError: If the eval command fails or produces unparseable output.
        subprocess.CalledProcessError: On SSH failure.
    """
    note = f"ablation-{variant}"
    experiment_id = _VARIANT_EXPERIMENT.get(variant, variant)

    if dry_run:
        logger.info(
            "[DRY-RUN] Would run: nox-mem eval run "
            "--variant=hybrid --note=%s --queries=%s",
            note,
            queries_jsonl,
        )
        return _placeholder_metrics(variant)

    logger.info(
        "Running eval for variant=%s (experiment=%s) note=%s",
        variant,
        experiment_id,
        note,
    )

    # Source .env for Gemini creds (CLAUDE.md critical rule §1)
    # --queries flag passes the golden queries file path
    eval_cmd = (
        f"set -a; source {env_path}; set +a; "
        f"nox-mem eval run "
        f"--variant={_EVAL_VARIANT} "
        f"--note={note} "
        f"--queries={queries_jsonl} "
        f"--format=json"
    )

    t0 = time.monotonic()
    try:
        result = _ssh(host, eval_cmd, timeout=360)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"nox-mem eval run failed for variant={variant}: {exc.stderr[:500]}"
        ) from exc

    elapsed_ms = int((time.monotonic() - t0) * 1_000)
    logger.info(
        "Eval finished for variant=%s in %.1fs", variant, elapsed_ms / 1_000
    )

    metrics = _parse_eval_output(result.stdout, variant)
    metrics["duration_ms"] = elapsed_ms
    metrics["raw_output"] = result.stdout[:2_000]
    return metrics


def _parse_eval_output(stdout: str, variant: str) -> dict[str, Any]:
    """Parse JSON metrics block from ``nox-mem eval run --format=json`` output.

    nox-mem eval run with --format=json emits a single JSON object on stdout.
    Falls back to regex extraction if the full output contains prose before
    the JSON block.

    Args:
        stdout: Full stdout from the SSH command.
        variant: Ablation variant name (for error context).

    Returns:
        Dict with metric fields extracted from the JSON block.

    Raises:
        RuntimeError: If no parseable JSON block is found.
    """
    # Try direct JSON parse first (clean output)
    raw = stdout.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            return _normalize_eval_json(data, variant)
        except json.JSONDecodeError:
            pass

    # Fallback: find first { ... } block in mixed prose output
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            data = json.loads(raw[brace_start : brace_end + 1])
            return _normalize_eval_json(data, variant)
        except json.JSONDecodeError:
            pass

    logger.warning(
        "Could not parse JSON from eval output for variant=%s. "
        "Raw output (first 500 chars): %s",
        variant,
        raw[:500],
    )
    # Return NaN-equivalent placeholder so the table still renders
    return _placeholder_metrics(variant, note="parse_failed")


def _normalize_eval_json(data: dict[str, Any], variant: str) -> dict[str, Any]:
    """Normalise field names from nox-mem eval JSON to our internal schema.

    nox-mem eval may use camelCase (ndcgAt10) or snake_case (ndcg_at_10).
    This function accepts both and normalises to snake_case.

    Args:
        data: Parsed JSON dict from eval output.
        variant: Ablation variant name.

    Returns:
        Normalised dict with ``ndcg_at_10``, ``mrr``, ``recall_at_10``,
        ``precision_at_5``, ``query_count``, ``run_id``.
    """

    def _get(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in data:
                return data[k]
        return default

    return {
        "variant": variant,
        "ndcg_at_10": float(_get("ndcg_at_10", "ndcgAt10", default=float("nan"))),
        "mrr": float(_get("mrr", default=float("nan"))),
        "recall_at_10": float(_get("recall_at_10", "recallAt10", default=float("nan"))),
        "precision_at_5": float(_get("precision_at_5", "precisionAt5", default=float("nan"))),
        "query_count": int(_get("query_count", "queryCount", default=0)),
        "run_id": _get("run_id", "runId", "id", default=None),
        "note": _get("notes", "note", default=f"ablation-{variant}"),
    }


def _placeholder_metrics(variant: str, note: str = "dry_run") -> dict[str, Any]:
    """Return a placeholder metrics dict for dry-run or parse-failure cases.

    Args:
        variant: Ablation variant name.
        note: Reason for placeholder (``dry_run`` or ``parse_failed``).

    Returns:
        Dict with NaN metric values and the given note.
    """
    return {
        "variant": variant,
        "ndcg_at_10": float("nan"),
        "mrr": float("nan"),
        "recall_at_10": float("nan"),
        "precision_at_5": float("nan"),
        "query_count": 0,
        "run_id": None,
        "note": note,
        "duration_ms": 0,
        "raw_output": "",
    }


# ---------------------------------------------------------------------------
# 5. Restore baseline env (kill switch)
# ---------------------------------------------------------------------------


def restore_baseline_env(
    host: str,
    env_path: str,
    *,
    dry_run: bool = False,
) -> None:
    """Restore the .env from .env.bak and restart services.

    This is the kill switch called in every try/finally block to guarantee
    the production environment returns to its canonical state regardless of
    what happened during a variant run.

    Strategy: restore from .env.bak (created at the start of each variant
    run by ``restart_nox_mem_services``).  If .env.bak does not exist
    (e.g., first run or bak was never created), log a warning but do not
    raise — the env may already be clean.

    Args:
        host: SSH target.
        env_path: Absolute path to .env on remote host.
        dry_run: If True, log intent without executing.

    Raises:
        RuntimeError: If the API fails to recover after restore.
        subprocess.CalledProcessError: On SSH failure.
    """
    ts = _now_iso()
    logger.info("[%s] RESTORE baseline .env from %s.bak", ts, env_path)

    if dry_run:
        logger.info("[DRY-RUN] Would restore %s from .bak and restart services", env_path)
        return

    # Check if .bak exists; if not, warn but continue (may already be clean)
    check_bak = _ssh(
        host,
        f"test -f {env_path}.bak && echo exists || echo missing",
        check=False,
    )
    bak_status = check_bak.stdout.strip()

    if bak_status == "missing":
        logger.warning(
            "No .env.bak found at %s.bak — .env may already be canonical. "
            "Restarting services as precaution.",
            env_path,
        )
    else:
        restore_cmd = f"cp -f {env_path}.bak {env_path}"
        _ssh(host, restore_cmd)
        # Log hash of restored .env for audit trail
        hash_result = _ssh(host, f"md5sum {env_path} | awk '{{print $1}}'")
        logger.info(
            "Restored %s from .bak. Hash: %s", env_path, hash_result.stdout.strip()
        )

    # Always restart after restore to ensure clean state
    services_str = " ".join(_NOX_SERVICES)
    logger.info("Restarting services after restore: %s", services_str)
    _ssh(host, f"systemctl restart {services_str}", timeout=60)

    _wait_for_health(host)
    logger.info("Baseline restore complete — services healthy")


# ---------------------------------------------------------------------------
# 6. Idempotency check
# ---------------------------------------------------------------------------


def verify_env_is_baseline(
    host: str,
    env_path: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Check whether the remote .env contains any ablation overrides.

    Called at script startup to verify the environment is clean before
    the first run.  If ablation vars are found (e.g., from a previous
    interrupted run), logs a warning and returns False.

    Args:
        host: SSH target.
        env_path: Absolute path to .env on remote host.
        dry_run: If True, skip check and return True.

    Returns:
        True if the .env appears to be in baseline state (no ablation vars
        set to override values).  False if leftover ablation vars are found.
    """
    if dry_run:
        return True

    # Check for each ablation-specific var in the .env
    ablation_vars = [
        "NOX_HYBRID_DISABLE",
        "NOX_RRF_DISABLE",
        "NOX_FUSION_MODE",
        "NOX_SALIENCE_MODE",
        "NOX_SECTION_BOOST_MODE",
    ]

    # Build a grep pattern for problematic values
    suspicious_patterns = [
        "NOX_HYBRID_DISABLE=1",
        "NOX_RRF_DISABLE=1",
        "NOX_FUSION_MODE=concat",
        "NOX_SALIENCE_MODE=off",
        "NOX_SECTION_BOOST_MODE=off",
    ]
    pattern = "|".join(suspicious_patterns)
    grep_cmd = f"grep -E '{pattern}' {env_path} || true"
    result = _ssh(host, grep_cmd, check=False)
    found = result.stdout.strip()

    if found:
        logger.warning(
            "⚠️  DETECTED leftover ablation vars in %s:\n%s\n"
            "This suggests a previous run was interrupted. "
            "Run restore_baseline_env() before proceeding.",
            env_path,
            found,
        )
        return False

    logger.info("Env baseline check: OK (no leftover ablation vars)")
    return True


def _env_hash(host: str, env_path: str) -> str:
    """Return MD5 hash of the remote .env file for audit logging.

    Args:
        host: SSH target.
        env_path: Absolute path to .env on remote host.

    Returns:
        MD5 hex digest string, or ``"unavailable"`` on error.
    """
    try:
        result = _ssh(host, f"md5sum {env_path} | awk '{{print $1}}'")
        return result.stdout.strip()
    except Exception:
        return "unavailable"


# ---------------------------------------------------------------------------
# 7. Markdown table generation
# ---------------------------------------------------------------------------


def generate_ablation_table(results: dict[str, dict[str, Any]]) -> str:
    """Generate a markdown ablation table for inclusion in paper §5.

    The table shows each variant's nDCG@10, MRR, Recall@10, and its delta
    vs. the baseline.  Variants with NaN metrics (dry-run or parse failure)
    are shown with ``??.???`` placeholders.

    Args:
        results: Dict mapping variant name to its metrics dict
            (as returned by ``run_eval_for_variant``).

    Returns:
        Multi-line markdown string with the ablation table plus
        a timestamp footer.

    Example output::

        | Variant | nDCG@10 | MRR | Recall@10 | Δ nDCG vs baseline |
        |---|---|---|---|---|
        | baseline (full hybrid) | 0.714 | 0.698 | 0.821 | — |
        | sem semantic (FTS-only) — E6 | 0.000 | 0.000 | 0.000 | **-0.714** |
        ...
    """
    baseline = results.get("baseline", {})
    baseline_ndcg = baseline.get("ndcg_at_10", float("nan"))

    def _fmt(val: float) -> str:
        if val != val:  # NaN check
            return "?.???"
        return f"{val:.3f}"

    def _fmt_delta(val: float, base: float) -> str:
        if val != val or base != base:
            return "?.???"
        delta = val - base
        sign = "+" if delta >= 0 else ""
        return f"**{sign}{delta:.3f}**" if abs(delta) > 0.001 else "—"

    header = (
        "| Variant | nDCG@10 | MRR | Recall@10 | Δ nDCG vs baseline |\n"
        "|---|---|---|---|---|\n"
    )

    rows: list[str] = []
    for variant in _ORDERED_VARIANTS:
        if variant not in results:
            continue
        m = results[variant]
        ndcg = m.get("ndcg_at_10", float("nan"))
        mrr = m.get("mrr", float("nan"))
        recall = m.get("recall_at_10", float("nan"))
        label = _VARIANT_LABELS.get(variant, variant)

        if variant == "baseline":
            delta_str = "—"
        else:
            delta_str = _fmt_delta(ndcg, baseline_ndcg)

        rows.append(
            f"| {label} | {_fmt(ndcg)} | {_fmt(mrr)} | {_fmt(recall)} | {delta_str} |"
        )

    generated_at = _now_iso()
    table = (
        "## Ablation Study — Component Contribution (§5)\n\n"
        "_Table generated by `ablation_runner.py` — "
        f"nox-mem corpus, 50 golden queries (R01b)_\n\n"
        + header
        + "\n".join(rows)
        + f"\n\n_Generated: {generated_at}_\n"
    )
    return table


# ---------------------------------------------------------------------------
# 8. Utilities
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format.

    Returns:
        String like ``2026-05-03T14:32:01Z``.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _setup_file_logging(log_path: Path) -> None:
    """Add a file handler to the root logger for the audit trail.

    Args:
        log_path: Absolute path to the log file.  Parent dir created if needed.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logging.getLogger().addHandler(fh)
    logger.info("Audit trail → %s", log_path)


# ---------------------------------------------------------------------------
# 9. CLI argument parser
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="ablation_runner",
        description=(
            "Run nox-mem ablation experiments E6–E9 sequentially on the VPS "
            "and generate a markdown table for paper §5.\n\n"
            "⚠️  Restarts nox-mem services ~5 times (~30s downtime each). "
            "Run during low-traffic window (02:00–07:00 BRT)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--queries",
        required=True,
        metavar="REMOTE_PATH",
        help=(
            "Absolute path to golden_queries.jsonl ON THE VPS "
            "(e.g. /root/paper-experiments/golden_queries.jsonl)."
        ),
    )
    parser.add_argument(
        "--vps-host",
        default=os.environ.get("NOX_VPS_HOST", _DEFAULT_VPS_HOST),
        metavar="SSH_TARGET",
        help=(
            f"SSH target for the VPS (default: {_DEFAULT_VPS_HOST}). "
            "Override via $NOX_VPS_HOST env var."
        ),
    )
    parser.add_argument(
        "--env-path",
        default=_DEFAULT_ENV_PATH,
        metavar="REMOTE_PATH",
        help=f"Absolute path to .env on the VPS (default: {_DEFAULT_ENV_PATH}).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        metavar="LOCAL_DIR",
        help=(
            f"Local directory for output files (default: {_DEFAULT_OUTPUT_DIR}). "
            "Created if it does not exist."
        ),
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=_ORDERED_VARIANTS,
        default=_ORDERED_VARIANTS,
        metavar="VARIANT",
        help=(
            "Which variants to run (default: all). "
            f"Choices: {_ORDERED_VARIANTS}. "
            "Always runs in the canonical order regardless of input order."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show what would happen (env diffs, SSH commands) without "
            "actually touching the VPS or restarting services."
        ),
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the interactive confirmation prompt (for CI/cron use).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


# ---------------------------------------------------------------------------
# 10. Main pipeline
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Full ablation pipeline: baseline → E6 → E7 → E8 → E9.

    Pipeline per variant:
    1. Verify env is baseline
    2. Apply env overrides + restart services
    3. Run eval, capture metrics
    4. Restore baseline env (try/finally — runs even on failure)
    5. Move to next variant

    Final: write ablation_results.json, ablation_table.md, ablation_runlog.txt.

    Args:
        argv: CLI argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Setup output dir and file logging
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runlog_path = output_dir / "ablation_runlog.txt"
    _setup_file_logging(runlog_path)

    host: str = args.vps_host
    env_path: str = args.env_path
    dry_run: bool = args.dry_run

    # Canonical order: only run selected variants, preserving _ORDERED_VARIANTS order
    variants_to_run = [v for v in _ORDERED_VARIANTS if v in args.variants]

    # -----------------------------------------------------------------------
    # Pre-flight: show what env vars each variant will set
    # -----------------------------------------------------------------------
    logger.info("=" * 70)
    logger.info("ABLATION RUNNER — nox-mem E6/E7/E8/E9")
    logger.info("VPS target: %s", host)
    logger.info("Env file:   %s", env_path)
    logger.info("Queries:    %s", args.queries)
    logger.info("Output dir: %s", output_dir)
    logger.info("Variants:   %s", variants_to_run)
    logger.info("Dry-run:    %s", dry_run)
    logger.info("=" * 70)

    for v in variants_to_run:
        overrides = set_env_for_variant(v)
        label = _VARIANT_LABELS.get(v, v)
        if overrides:
            kv_str = ", ".join(f"{k}={val}" for k, val in overrides.items())
            logger.info("  %-20s → %s", label, kv_str)
        else:
            logger.info("  %-20s → (no overrides — baseline)", label)

    # -----------------------------------------------------------------------
    # Confirmation prompt (skip if --dry-run or --yes)
    # -----------------------------------------------------------------------
    n_restarts = len(variants_to_run) * 2  # restart per variant + restore
    estimated_min = len(variants_to_run) * 5

    if not dry_run and not args.yes:
        print()
        print("⚠️  WARNING: Will restart nox-mem services "
              f"~{n_restarts} times (2 per variant: apply + restore).")
        print(f"   Estimated downtime: ~30s × {n_restarts} restarts = "
              f"~{n_restarts * 30 // 60}min downtime spread over ~{estimated_min}min total.")
        print("   Production traffic will be affected during each restart window.")
        print("   Recommended window: 02:00–07:00 BRT (low-traffic).")
        print()
        answer = input("Continue? [y/N] ").strip().lower()
        if answer != "y":
            logger.info("Aborted by user.")
            return 0

    # -----------------------------------------------------------------------
    # Idempotency: verify baseline state before starting
    # -----------------------------------------------------------------------
    if not dry_run:
        is_clean = verify_env_is_baseline(host, env_path, dry_run=dry_run)
        if not is_clean:
            logger.warning(
                "Leftover ablation vars detected. Attempting baseline restore first."
            )
            restore_baseline_env(host, env_path, dry_run=dry_run)
            # Re-check
            is_clean = verify_env_is_baseline(host, env_path, dry_run=dry_run)
            if not is_clean:
                logger.error(
                    "Could not restore baseline env. Aborting to avoid "
                    "corrupting ablation results."
                )
                return 1

    # -----------------------------------------------------------------------
    # Main loop: one variant at a time, serial
    # -----------------------------------------------------------------------
    results: dict[str, dict[str, Any]] = {}
    pipeline_start = time.monotonic()

    for variant in variants_to_run:
        label = _VARIANT_LABELS.get(variant, variant)
        experiment_id = _VARIANT_EXPERIMENT.get(variant, variant)
        variant_start = time.monotonic()

        logger.info("-" * 60)
        logger.info("VARIANT: %s (%s)", label, experiment_id)
        logger.info("Started: %s", _now_iso())

        overrides = set_env_for_variant(variant)
        env_hash_before = _env_hash(host, env_path) if not dry_run else "dry-run"
        logger.info("Pre-variant .env hash: %s", env_hash_before)

        try:
            # Step A: apply env overrides and restart
            restart_nox_mem_services(
                host,
                env_path,
                overrides,
                dry_run=dry_run,
            )

            # Step B: run eval and capture metrics
            metrics = run_eval_for_variant(
                host,
                env_path,
                variant,
                args.queries,
                dry_run=dry_run,
            )
            results[variant] = metrics

            elapsed_variant = time.monotonic() - variant_start
            logger.info(
                "Variant %s complete in %.1fs — "
                "nDCG@10=%s MRR=%s Recall@10=%s",
                variant,
                elapsed_variant,
                f"{metrics['ndcg_at_10']:.4f}"
                if metrics["ndcg_at_10"] == metrics["ndcg_at_10"]
                else "NaN",
                f"{metrics['mrr']:.4f}"
                if metrics["mrr"] == metrics["mrr"]
                else "NaN",
                f"{metrics['recall_at_10']:.4f}"
                if metrics["recall_at_10"] == metrics["recall_at_10"]
                else "NaN",
            )

        except Exception as exc:
            logger.error(
                "VARIANT %s FAILED: %s — will restore baseline and continue",
                variant,
                exc,
            )
            results[variant] = _placeholder_metrics(variant, note=f"FAILED: {exc!s}")

        finally:
            # CRITICAL SAFETY: always restore baseline, even on failure
            try:
                restore_baseline_env(host, env_path, dry_run=dry_run)
                env_hash_after = (
                    _env_hash(host, env_path) if not dry_run else "dry-run"
                )
                logger.info(
                    "Post-restore .env hash: %s (pre was: %s)",
                    env_hash_after,
                    env_hash_before,
                )
            except Exception as restore_exc:
                logger.critical(
                    "🚨 BASELINE RESTORE FAILED for variant=%s: %s\n"
                    "MANUAL RECOVERY REQUIRED:\n"
                    "  ssh %s 'cp -f %s.bak %s && systemctl restart %s'",
                    variant,
                    restore_exc,
                    host,
                    env_path,
                    env_path,
                    " ".join(_NOX_SERVICES),
                )
                # Do not abort the loop — try remaining variants if restore
                # is a transient network issue; log is the audit trail

    # -----------------------------------------------------------------------
    # Final: ensure baseline is restored one more time (belt and suspenders)
    # -----------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("All variants complete. Final baseline restore for safety.")
    try:
        restore_baseline_env(host, env_path, dry_run=dry_run)
    except Exception as exc:
        logger.warning("Final restore warning (non-fatal): %s", exc)

    total_elapsed = time.monotonic() - pipeline_start
    logger.info("Total pipeline time: %.1fs (%.1f min)", total_elapsed, total_elapsed / 60)

    # -----------------------------------------------------------------------
    # Write outputs
    # -----------------------------------------------------------------------
    _write_outputs(results, output_dir, dry_run=dry_run)

    logger.info("Done. Outputs written to: %s", output_dir)
    return 0


def _write_outputs(
    results: dict[str, dict[str, Any]],
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Write ablation_results.json and ablation_table.md.

    Args:
        results: Dict mapping variant name to metrics dict.
        output_dir: Local directory to write files into.
        dry_run: If True, log file contents instead of writing.
    """
    # ablation_results.json — raw metrics
    results_path = output_dir / "ablation_results.json"
    results_payload = {
        "generated_at": _now_iso(),
        "note": "nox-mem ablation study E6–E9, 50 golden queries",
        "variants": results,
    }
    if dry_run:
        logger.info(
            "[DRY-RUN] Would write ablation_results.json:\n%s",
            json.dumps(results_payload, indent=2, default=str)[:1_000],
        )
    else:
        results_path.write_text(
            json.dumps(results_payload, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Wrote: %s", results_path)

    # ablation_table.md — markdown table for paper §5
    table_path = output_dir / "ablation_table.md"
    table_md = generate_ablation_table(results)
    if dry_run:
        logger.info("[DRY-RUN] Would write ablation_table.md:\n%s", table_md)
    else:
        table_path.write_text(table_md, encoding="utf-8")
        logger.info("Wrote: %s", table_path)
        # Print table to stdout for immediate inspection
        print("\n" + table_md)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
