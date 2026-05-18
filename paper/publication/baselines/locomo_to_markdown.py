#!/usr/bin/env python3
"""locomo_to_markdown.py - convert LoCoMo turns into nox-mem-ingestible Markdown.

Companion to paper/publication/baselines/locomo_production_path.md (Option A
production-path validation runbook). Reads cached LoCoMo dataset and emits
one Markdown file per turn under <output>/<sample_id>/<dia_id>.md.

Frontmatter preserves the canonical LoCoMo chunk_id (sample_id::dia_id) so
the post-search ID-resolver in eval/locomo/run.ts can map noxmem chunks back
to LoCoMo gold. retention_days=0 keeps eval corpus from being pruned.

Usage:
    python3 locomo_to_markdown.py \
        --input  /tmp/locomo10.json \
        --output /tmp/locomo-md/ \
        [--limit N] [--manifest manifest.jsonl] [--force]

Cost: zero (no API calls). Wall clock ~10-30s for full 5,882-turn corpus.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator


# Schema knowledge of locomo10.json duplicated on purpose (script must run
# self-contained on the VPS, no sibling-module imports).
def iter_turns(corpus: list[dict[str, Any]]) -> Iterator[tuple[str, str, str, str, str]]:
    """Yield (sample_id, session_id, dia_id, speaker, text) for every turn."""
    for conv in corpus:
        sid = conv.get("sample_id")
        if not sid:
            continue
        conv_body = conv.get("conversation", {})
        if not isinstance(conv_body, dict):
            continue
        for key, val in conv_body.items():
            if not key.startswith("session_") or key.endswith("_date_time"):
                continue
            if not isinstance(val, list):
                continue
            for turn in val:
                if not isinstance(turn, dict):
                    continue
                dia_id = turn.get("dia_id")
                text = turn.get("text")
                speaker = turn.get("speaker", "")
                if not dia_id or not text:
                    continue
                yield (str(sid), str(key), str(dia_id), str(speaker), str(text))


_FORBIDDEN = re.compile(r"[^A-Za-z0-9._-]")


def safe_segment(s: str) -> str:
    """Replace anything that is not [A-Za-z0-9._-] with _ so paths are POSIX-safe.

    dia_id values look like D1:7 ; the colon is illegal on Windows and awkward
    on POSIX. Use _ consistently so noxmem watcher (inotifywait) and any dev-mac
    see the same path shape."""
    cleaned = _FORBIDDEN.sub("_", s)
    return cleaned.lstrip(".") or "_"


def yaml_escape_scalar(s: str) -> str:
    """Double-quote a YAML scalar safely (handles backslash and quote)."""
    return chr(34) + s.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34)) + chr(34)


def build_markdown(
    sample_id: str,
    session_id: str,
    dia_id: str,
    speaker: str,
    text: str,
) -> str:
    """Build the .md content for one turn (frontmatter + body + trailer anchor)."""
    chunk_id = sample_id + "::" + dia_id
    fm_lines = [
        "---",
        "source: " + yaml_escape_scalar("locomo"),
        "sample_id: " + yaml_escape_scalar(sample_id),
        "session_id: " + yaml_escape_scalar(session_id),
        "dia_id: " + yaml_escape_scalar(dia_id),
        "chunk_id: " + yaml_escape_scalar(chunk_id),
        "speaker: " + yaml_escape_scalar(speaker),
        "chunk_type: " + yaml_escape_scalar("eval_locomo"),
        "retention_days: 0",
        "pain: 0.2",
        "---",
        "",
    ]
    body = (speaker + ": " + text + "\n") if speaker else (text + "\n")
    # Trailing HTML comment also embeds chunk_id so the FTS5 index has a
    # second anchor if frontmatter is stripped by an ingester variant.
    trailer = "\n<!-- locomo_chunk_id=" + chunk_id + " -->\n"
    return "\n".join(fm_lines) + body + trailer


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert LoCoMo turns to nox-mem-ingestible Markdown.")
    ap.add_argument("--input", type=Path, default=Path("/tmp/locomo10.json"),
                    help="Path to cached locomo10.json (default: /tmp/locomo10.json).")
    ap.add_argument("--output", type=Path, required=True,
                    help="Output directory. Will be created. One subdir per sample_id.")
    ap.add_argument("--limit", type=int, default=0,
                    help="If > 0, emit at most this many turns total (for dry-run).")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="Optional JSONL manifest mapping md_path to chunk_id.")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing .md files without warning.")
    args = ap.parse_args()

    if not args.input.exists():
        print("[fatal] dataset not found: " + str(args.input), file=sys.stderr)
        print("        Download via: python3 locomo_eval.py download "
              "OR npx tsx eval/locomo/download.ts", file=sys.stderr)
        return 2

    try:
        corpus = json.loads(args.input.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print("[fatal] failed to read corpus: " + str(exc), file=sys.stderr)
        return 2

    if not isinstance(corpus, list):
        print("[fatal] expected top-level list (got " + type(corpus).__name__ + ")",
              file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)

    manifest_fh = None
    if args.manifest is not None:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest_fh = args.manifest.open("w", encoding="utf-8")

    written = 0
    skipped = 0
    duplicates = 0
    seen_chunk_ids: set[str] = set()

    try:
        for (sample_id, session_id, dia_id, speaker, text) in iter_turns(corpus):
            chunk_id = sample_id + "::" + dia_id
            if chunk_id in seen_chunk_ids:
                duplicates += 1
                continue
            seen_chunk_ids.add(chunk_id)

            sample_dir = args.output / safe_segment(sample_id)
            sample_dir.mkdir(parents=True, exist_ok=True)
            md_path = sample_dir / (safe_segment(dia_id) + ".md")

            if md_path.exists() and not args.force:
                skipped += 1
                continue

            md = build_markdown(
                sample_id=sample_id,
                session_id=session_id,
                dia_id=dia_id,
                speaker=speaker,
                text=text,
            )
            md_path.write_text(md, encoding="utf-8")
            written += 1

            if manifest_fh is not None:
                manifest_fh.write(json.dumps({
                    "md_path": str(md_path),
                    "chunk_id": chunk_id,
                    "sample_id": sample_id,
                    "session_id": session_id,
                    "dia_id": dia_id,
                }, ensure_ascii=False) + "\n")

            if args.limit and written >= args.limit:
                break
    finally:
        if manifest_fh is not None:
            manifest_fh.close()

    print(
        "[ok] wrote {:,} turns (skipped {:,} existing, {:,} duplicate chunk_ids) -> {}".format(
            written, skipped, duplicates, args.output
        ),
        file=sys.stderr,
    )
    if args.manifest is not None:
        print("[ok] manifest: " + str(args.manifest), file=sys.stderr)
    if written == 0 and skipped == 0:
        print("[warn] zero turns extracted - is the corpus path correct?", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
