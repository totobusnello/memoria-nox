#!/usr/bin/env python3
"""
Q4 COMPARISON pre-flight smoke test.

Runs each adapter's `validate()` function ONLY — no external API calls,
no quota burn. Documents per-adapter expected setup (env vars, install
hints, daemons) so Toto can see at a glance what is missing Saturday
morning before kicking off the full runner.

Usage:

    python smoke_test.py                   # all adapters
    python smoke_test.py --systems mem0,zep
    python smoke_test.py --json            # machine-readable

Exit codes:
    0 — every adapter validated OK
    1 — at least one adapter failed (see report); inspect output

Per spec §4: if 3+ adapters fail validate(), Q4 is in stop-condition #1
("setup gap too wide, escalate").
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from adapters import ALL_ADAPTERS  # noqa: E402


def smoke_one(name: str) -> dict:
    try:
        mod = importlib.import_module(f"adapters.{name}")
    except ImportError as exc:
        return {
            "system": name,
            "ok": False,
            "error": f"adapter module import failed: {exc}",
            "version": None,
            "notes": None,
            "install_hint": None,
            "requires_env": [],
        }
    info = mod.validate()
    return {
        "system": getattr(mod, "NAME", name),
        "ok": bool(info.get("ok")),
        "error": info.get("error"),
        "version": info.get("version"),
        "notes": info.get("notes"),
        "install_hint": getattr(mod, "INSTALL_HINT", None),
        "requires_env": list(getattr(mod, "REQUIRES_ENV", [])),
    }


def render_text(report: list[dict]) -> str:
    lines: list[str] = []
    lines.append("Q4 COMPARISON — pre-flight smoke test")
    lines.append("=" * 60)
    for entry in report:
        status = "OK " if entry["ok"] else "FAIL"
        lines.append(f"[{status}] {entry['system']}")
        if entry["version"]:
            lines.append(f"       version: {entry['version']}")
        if entry["requires_env"]:
            lines.append(f"       env:     {', '.join(entry['requires_env'])}")
        if entry["error"]:
            lines.append(f"       error:   {entry['error']}")
        if entry["notes"]:
            lines.append(f"       notes:   {entry['notes']}")
        if not entry["ok"] and entry["install_hint"]:
            lines.append(f"       install: {entry['install_hint']}")
        lines.append("")
    total = len(report)
    failed = sum(1 for e in report if not e["ok"])
    lines.append("-" * 60)
    lines.append(f"summary: {total - failed}/{total} adapters OK ({failed} failed)")
    if failed >= 3:
        lines.append("STOP CONDITION #1: 3+ adapters failed — escalate per spec §8.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Q4 adapter smoke test")
    p.add_argument(
        "--systems",
        default="all",
        help="comma-separated adapter names (or 'all')",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = p.parse_args(argv)

    if args.systems == "all":
        names = list(ALL_ADAPTERS)
    else:
        names = [n.strip() for n in args.systems.split(",") if n.strip()]

    report = [smoke_one(n) for n in names]

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))

    failed = sum(1 for e in report if not e["ok"])
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
