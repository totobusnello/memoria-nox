#!/usr/bin/env python3
"""RC4 all-Gemini wrapper.

Patches adapters.mem0._build_config → Gemini embedder (3072d, collection
q4-eval-gemini) BEFORE delegating to runner.main(), so both nox_mem (hybrid,
google.generativeai) and mem0 (google.genai) run on the same Gemini model.

Run ONE system per process (thread-leak isolation for mem0; corpus > 3500):

    python runner_rc4.py --systems nox_mem --datasets locomo \
        --queries-file cache/queries-locomo-categorized.jsonl \
        --output output/rc4/locomo --limit 100000 --k 10

Required env (see lib/all_gemini_config.assert_env_ready):
    GEMINI_API_KEY / GOOGLE_API_KEY, NOX_EVAL_MODE=hybrid,
    MEM0_TELEMETRY=False, ANONYMIZED_TELEMETRY=False, MEM0_SKIP_LLM_EXTRACTION=1,
    MEM0_CHROMA_PATH, NOX_EVAL_DB_PATH.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from lib.all_gemini_config import assert_env_ready, patch_mem0_adapter  # noqa: E402

assert_env_ready()
patch_mem0_adapter()

import runner  # noqa: E402  — must import AFTER patch

if __name__ == "__main__":
    raise SystemExit(runner.main())
