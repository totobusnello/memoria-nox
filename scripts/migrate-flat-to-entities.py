#!/usr/bin/env python3
"""Parse a flat memory file (lessons.md, decisions.md) where each H2 is an event.

Input format:
    # Title
    ## 📋 Índice Rápido (ignored)
    ## YYYY-MM-DD — Titulo of event
    body...
    ## YYYY-MM-DD — Another event
    body...
    ## 🔒 Estratégicas (category group header — ignored as entity)
    ## YYYY-MM-DD — ...

Output: one entity file per H2 (slug = YYYY-MM-DD-first-words).

Usage:
    python3 migrate-flat-to-entities.py <input.md> <output_dir> \\
        --type lesson --retention 180
"""
import argparse
import re
import unicodedata
from datetime import date
from pathlib import Path

# Emoji-only H2s or markers to skip (not real events)
SKIP_PATTERNS = [
    r"^📋",
    r"^🔒",
    r"^⏳",
    r"^⭐",
    r"Índice\s+Rápido",
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9\s\-]", "", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "unnamed"


def parse_flat(content: str):
    """Yield (heading, body_lines)."""
    current_heading = None
    current_body = []

    for line in content.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            # Flush previous
            if current_heading:
                yield (current_heading, current_body)
            current_heading = line[3:].strip()
            current_body = []
        elif current_heading:
            current_body.append(line)

    if current_heading:
        yield (current_heading, current_body)


def should_skip(heading: str) -> bool:
    for p in SKIP_PATTERNS:
        if re.search(p, heading):
            return True
    return False


def make_entity_file(heading, body_lines, entity_type, retention_days):
    """Return (slug, content, event_date) tuple."""
    # Extract date + title
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+[—\-]\s+(.+)$", heading)
    if m:
        event_date = m.group(1)
        title = m.group(2).strip()
    else:
        event_date = date.today().isoformat()
        title = heading

    # Short first 5 words for slug uniqueness
    short_title = " ".join(title.split()[:6])
    slug = f"{event_date}-{slugify(short_title)}"[:80]

    # Description: first meaningful line from body
    desc = ""
    for bl in body_lines:
        bl_stripped = bl.strip()
        if bl_stripped and not bl_stripped.startswith("#"):
            desc = re.sub(r"^[-*]\s*", "", bl_stripped)
            desc = re.sub(r"^\*\*.*?\*\*:\s*", "", desc)
            desc = desc[:150]
            break
    if not desc:
        desc = title[:150]
    desc = desc.replace('"', "'").replace("\n", " ")

    # Strip stray '---' to protect parser
    safe_body_lines = [l for l in body_lines if l.strip() != "---"]
    compiled = "\n".join(safe_body_lines).strip() or title

    retention_line = f"<!-- retention: {retention_days} -->\n" if retention_days != "never" else "<!-- retention: never -->\n"

    content = f"""---
name: {title[:100]}
description: {desc}
type: {entity_type}
event_date: {event_date}
---

{retention_line}
{compiled}

---

## Timeline

- **{event_date}** — [{entity_type}] {title[:200]}
- **{date.today().isoformat()}** — [migration] Entity file created from source {entity_type}s.md
"""
    return slug, content, event_date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output_dir")
    ap.add_argument("--type", required=True, choices=["lesson", "decision"])
    ap.add_argument("--retention", default="180")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    seen_slugs = set()
    for heading, body_lines in parse_flat(content):
        if should_skip(heading):
            skipped += 1
            continue
        slug, entity_content, event_date = make_entity_file(
            heading, body_lines, args.type, args.retention
        )
        # Avoid duplicate slugs (same date+title)
        orig_slug = slug
        i = 2
        while slug in seen_slugs:
            slug = f"{orig_slug}-{i}"
            i += 1
        seen_slugs.add(slug)

        out_path = out_dir / f"{slug}.md"
        if args.dry_run:
            print(f"[DRY] {out_path} ({len(entity_content)}B) — {heading[:60]}")
        else:
            out_path.write_text(entity_content, encoding="utf-8")
        count += 1

    print(f"\nTotal: {count} entities ({'would be' if args.dry_run else 'were'}) generated, {skipped} skipped")


if __name__ == "__main__":
    main()
