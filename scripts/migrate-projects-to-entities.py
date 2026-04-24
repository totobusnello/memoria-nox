#!/usr/bin/env python3
"""Parse projects.md and generate entity files in 3-section format.

Usage:
    python3 migrate-projects-to-entities.py <input.md> <output_dir> [--dry-run]

Input format assumed:
    # Title
    ## Category (✅ Concluídos, 🔄 Em andamento, etc)
    ### Project Name — STATUS (YYYY-MM-DD)
    - bullet 1
    - bullet 2
    ...

Output per project:
    <output_dir>/<slug>.md with frontmatter + compiled + timeline.
"""
import argparse
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# Categories to skip (not real project entities)
SKIP_CATEGORIES = {
    "Consolidação Automática",
    "Backlog de projetos",
}

# Category → status mapping for frontmatter
STATUS_BY_CATEGORY = {
    "✅ Concluídos": "completed",
    "🔄 Em andamento": "active",
    "🗓️ Viagens": "travel",
    "🤖 Autonomia Completa dos Agentes": "active",
    "⏸️ Backlog de projetos": "backlog",
}


def slugify(text: str) -> str:
    """Convert to lowercase ascii slug, replace spaces/special with dashes."""
    # Normalize unicode (remove accents)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Strip emoji and special markers
    text = re.sub(r"[✅🔄🗓️🤖⏸️📋⭐🚀💼🎯]", "", text)
    # Extract main name (before em-dash or parens)
    text = re.split(r"\s[—\-]\s|\s\(", text)[0]
    # Lowercase + replace non-alphanumeric with -
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "unnamed"


def extract_date(heading: str) -> str | None:
    """Extract YYYY-MM-DD from heading like '### Project (2026-03-15)'."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", heading)
    return m.group(1) if m else None


def parse_projects(content: str):
    """Yield (category, project_name, body_lines, project_date_or_none)."""
    current_category = None
    current_project = None
    current_body = []
    project_date = None

    for line in content.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            # New H2 — flush previous project if any
            if current_project:
                yield (current_category, current_project, current_body, project_date)
                current_project = None
                current_body = []
                project_date = None
            current_category = line[3:].strip()
        elif line.startswith("### "):
            # New H3 — flush previous
            if current_project:
                yield (current_category, current_project, current_body, project_date)
            current_project = line[4:].strip()
            project_date = extract_date(current_project)
            current_body = []
        else:
            if current_project:
                current_body.append(line)

    # Flush final
    if current_project:
        yield (current_category, current_project, current_body, project_date)


def make_entity_file(category, project_name, body_lines, project_date):
    """Return (slug, content) tuple for entity file."""
    slug = slugify(project_name)
    status = STATUS_BY_CATEGORY.get(category, "unknown")

    # Clean name (strip status suffix, em-dash, parens)
    clean_name = re.split(r"\s+[—\-]\s+|\s+\(", project_name)[0].strip()

    # Description: first bullet or status line
    body_text = "\n".join(body_lines).strip()
    first_desc = ""
    for bl in body_lines:
        bl = bl.strip()
        if bl.startswith("-") or bl.startswith("*"):
            first_desc = re.sub(r"^[-*]\s*", "", bl)
            first_desc = re.sub(r"^\*\*.*?:\*\*\s*", "", first_desc)  # strip **Label:** prefix
            break
    if not first_desc:
        first_desc = f"Projeto {status}"
    # Truncate description
    first_desc = first_desc[:150].replace('"', "'").replace("\n", " ")

    # Compiled: current best description based on body
    # Strip stray '---' separators that would confuse the 3-section parser.
    safe_body_lines = [l for l in body_lines if l.strip() != "---"]
    safe_body = "\n".join(safe_body_lines).strip()
    compiled = safe_body if safe_body else f"Projeto {clean_name} — status {status}."

    # Timeline: try to extract any date-tagged bullets
    timeline_entries = []
    if project_date:
        timeline_entries.append(
            f"- **{project_date}** — [migrated] {clean_name} registrado em projects.md"
        )
    # Look for inline dates in bullets
    for bl in body_lines:
        m = re.search(r"\(?(\d{4}-\d{2}-\d{2})\)?", bl)
        if m and bl.strip().startswith(("-", "*")):
            d = m.group(1)
            text = re.sub(r"^[-*]\s*", "", bl.strip())
            if not any(e.startswith(f"- **{d}**") for e in timeline_entries):
                timeline_entries.append(f"- **{d}** — [event] {text[:200]}")

    if not timeline_entries:
        timeline_entries.append(
            f"- **{date.today().isoformat()}** — [migration] Entity file created from projects.md"
        )

    # Assemble
    content = f"""---
name: {clean_name}
description: {first_desc}
type: project
status: {status}
category: {category}
---

<!-- retention: 365 -->

{compiled}

---

## Timeline

{chr(10).join(timeline_entries)}
"""
    return slug, content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output_dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    for category, project_name, body_lines, project_date in parse_projects(content):
        if category in SKIP_CATEGORIES:
            skipped += 1
            continue
        # Skip sub-headers like "Objetivos", "Sprints planejados" inside Autonomia
        if len(project_name) < 5 or project_name.lower() in {"objetivos", "sprints planejados", "pendente aprovação do totó antes de iniciar"}:
            skipped += 1
            continue
        slug, entity_content = make_entity_file(category, project_name, body_lines, project_date)
        out_path = out_dir / f"{slug}.md"

        if args.dry_run:
            print(f"[DRY-RUN] Would write {out_path} ({len(entity_content)} bytes)")
        else:
            out_path.write_text(entity_content, encoding="utf-8")
            print(f"[OK] {out_path}")
        count += 1

    print(f"\nTotal: {count} entities generated, {skipped} skipped")


if __name__ == "__main__":
    main()
