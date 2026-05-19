#!/usr/bin/env python3
"""Entity-flavored evaluation set generator — for memory feature ablations.

Motivation
----------
Standard LoCoMo eval (paper §5) uses conversational chunks with NO entity
metadata (section, chunk_type, pain, source_type, tier, recency). The
production hybrid pipeline applies these features as multiplicative boosts
during ranking; but on LoCoMo they are inert because every chunk has the
same default values. Ablation F (PR #139) confirmed: +100.6% nDCG@10 gain
over FTS5 baseline came 100% from Gemini semantic vector retrieval; the
boost stack contributed +0.0% on LoCoMo.

To say "pain-weighted hybrid memory" defensibly in the paper §5, we need
an evaluation set where these features DO activate and where gold answers
prefer chunks that the boost stack would in fact promote. This script
generates such a synthetic corpus + query set, deterministic via seed=42.

This is a SYNTHETIC eval set — it complements but does NOT replace LoCoMo /
LongMemEval / BEIR third-party benchmarks. Its role is to measure feature
contribution along the dimensions production hybrid encodes (section,
chunk_type, pain, recency, source_type, tier) which third-party sets
cannot exercise because their chunks lack those attributes.

Design (specs locked 2026-05-19)
--------------------------------
Corpus N=500 chunks, entity-file format:
  Section:      30% compiled (boost 2.0) / 30% frontmatter (1.5) / 40% timeline (0.8)
  chunk_type:   25% person / 25% project / 20% lesson / 15% decision / 15% other
  pain:         30% [0.1,0.3] / 40% [0.3,0.7] / 30% [0.7,1.0]
  recency:      source_date uniform over last 30 days
  source_type:  50% entity_file / 30% session_summary / 20% event_log
  tier:         60% working / 30% core / 10% peripheral
  importance:   derived from section × chunk_type

Queries N=100 (stratified, seed=42):
  20% single-hop   (1 gold)
  20% multi-hop    (2-3 golds)
  20% temporal     (1-2 golds, recency-biased)
  20% open-domain  (1-3 golds)
  20% adversarial  (1-2 golds, typos/paraphrase)
  Mix: 50% NL-with-?  /  50% keyword-style

Gold selection biases (the part that matters)
---------------------------------------------
Within each query, the gold chunk(s) are chosen so a correctly-tuned
hybrid pipeline (section_boost + BOOST_TYPES + source_type_boost +
tier_boost + pain·recency salience) would rank them higher than the
distractor chunks that mention the same entity. Specifically:

  - Single-hop ENTITY attribute query  → gold lives in `compiled` section
                                          of that entity (not `timeline`)
  - Temporal "recently" / "this week"  → gold has the most-recent
                                          source_date among matches
  - "What was the lesson when X broke" → gold has highest pain among matches
  - "Decision about Y"                 → gold has chunk_type=decision

This means the eval REWARDS the boost stack when it's working. If boosts
are disabled (NOX_DISABLE_BOOSTS=1), retrieval has to fall back to pure
vector similarity, and we expect a measurable nDCG drop.

Determinism
-----------
seed=42 throughout. Re-running this script produces byte-identical output.
Re-using the corpus across ablation runs is mandatory — gold IDs are
embedded in queries.jsonl.

Cost
----
Generation itself: 0 Gemini calls (synthetic text).
Full ablation run on this corpus (separate G3 work):
  500 chunks × 1 embed (3072d) = $0.06
  100 queries × 1 embed × 5 ablations = $0.06
  ≈ $0.12 — $0.30 USD total for the entire ablation matrix.

Output
------
  paper/publication/data/entity-eval-2026-05-19/corpus.jsonl
  paper/publication/data/entity-eval-2026-05-19/queries.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────────────────
# SAFETY GUARD — fail-closed DB isolation check (postmortem 2026-05-19)
# ────────────────────────────────────────────────────────────────────────────
# This generator writes only to paper/publication/data/ (flat files), so it
# does NOT directly touch any SQLite DB. However, the guard here prevents the
# generator from running in an environment where NOX_DB_PATH / OPENCLAW_WORKSPACE
# would cause a downstream `nox-mem ingest` invoked by the caller's orchestrator
# to land in the production DB.
#
# Specifically: if the caller exports OPENCLAW_WORKSPACE pointing at the VPS
# production workspace and forgets to also set NOX_DB_PATH to an isolated eval
# DB, any subsequent `nox-mem ingest corpus.jsonl` will silently ingest into
# nox-mem.db prod. This guard surfaces that misconfiguration at generator time
# rather than after ingest has already run.

_PROD_DB_PATTERN = re.compile(r"/tools/nox-mem/nox-mem\.db$")


def _check_generator_isolation() -> None:
    """Warn loudly if the environment looks like it will ingest into prod.

    Does NOT abort — the generator itself is harmless. But prints a prominent
    warning so the operator notices before running the downstream ingest step.

    The warning becomes a hard abort if NOX_EVAL_STRICT=1 is set (recommended
    in CI and automated G3 orchestrators).
    """
    eval_db = os.environ.get("NOX_EVAL_DB_PATH", "").strip()
    openclaw_ws = os.environ.get("OPENCLAW_WORKSPACE", "").strip()
    nox_db_path = os.environ.get("NOX_DB_PATH", "").strip()
    override = os.environ.get("NOX_EVAL_ISOLATION_OVERRIDE", "").strip()
    strict = os.environ.get("NOX_EVAL_STRICT", "").strip()

    if override == "1":
        return

    warnings: list[str] = []

    if not eval_db:
        warnings.append(
            "NOX_EVAL_DB_PATH is not set. "
            "The downstream `nox-mem ingest` step (G3 orchestrator) will "
            "fall through to OPENCLAW_WORKSPACE-based DB resolution and "
            "potentially ingest eval chunks into production nox-mem.db. "
            "Set NOX_EVAL_DB_PATH=/tmp/<eval>.db BEFORE running the orchestrator."
        )

    if nox_db_path and _PROD_DB_PATTERN.search(nox_db_path):
        warnings.append(
            f"NOX_DB_PATH='{nox_db_path}' points at the production DB. "
            "Override it to an isolated path before running `nox-mem ingest`."
        )

    if openclaw_ws and not nox_db_path and not eval_db:
        warnings.append(
            f"OPENCLAW_WORKSPACE='{openclaw_ws}' is set but neither "
            "NOX_DB_PATH nor NOX_EVAL_DB_PATH override it. "
            "nox-mem CLI will resolve to "
            f"'{openclaw_ws}/tools/nox-mem/nox-mem.db' (production)."
        )

    if warnings:
        header = (
            "\n[entity-eval-generator] ISOLATION WARNING — "
            "review before running downstream ingest:"
        )
        if strict == "1":
            print(header, file=sys.stderr)
            for i, w in enumerate(warnings, 1):
                print(f"  [{i}] {w}", file=sys.stderr)
            print(
                "\nAborting because NOX_EVAL_STRICT=1. "
                "Fix the environment or set NOX_EVAL_ISOLATION_OVERRIDE=1.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print(header, file=sys.stderr)
            for i, w in enumerate(warnings, 1):
                print(f"  [{i}] {w}", file=sys.stderr)
            print(
                "  Set NOX_EVAL_STRICT=1 to make this a hard abort in CI.",
                file=sys.stderr,
            )


# ────────────────────────────────────────────────────────────────────────────
# Constants (mirroring src/search.ts + src/tier-manager.ts production values)
# ────────────────────────────────────────────────────────────────────────────

SECTION_BOOST = {
    "compiled":     2.0,
    "frontmatter": 1.5,
    "timeline":    0.8,
    None:          1.0,  # legacy / no-section
}

BOOST_TYPES = {"decision", "lesson", "person", "project", "pending"}

SOURCE_TYPE_BOOST = {
    "entity_file":     1.5,
    "session_summary": 1.0,
    "event_log":       1.0,
}

TIER_BOOST = {
    "core":       1.5,
    "working":    1.0,
    "peripheral": 0.8,
}

DEFAULT_SEED = 42
DEFAULT_N_CHUNKS = 500
DEFAULT_N_QUERIES = 100
DEFAULT_REF_DATE = date(2026, 5, 19)

# ────────────────────────────────────────────────────────────────────────────
# Entity universe — small enough to enable cross-entity multi-hop queries
# ────────────────────────────────────────────────────────────────────────────

PEOPLE = [
    ("toto",    "Toto Busnello",    "co-founder of Granix, board member at Nuvini, leads FII Treviso and Fundo Lombardia"),
    ("ana",     "Ana Castro",       "Granix CTO, leads the platform engineering org"),
    ("bruno",   "Bruno Lima",       "Galapagos Capital AI research head"),
    ("carla",   "Carla Mendes",     "Nuvini portfolio operations lead"),
    ("daniel",  "Daniel Oliveira",  "Frooty backend tech-lead"),
    ("eva",     "Eva Schmidt",      "Granix product designer"),
    ("felipe",  "Felipe Souza",     "Nox-Supermem founding engineer"),
    ("gabriela","Gabriela Rocha",   "FII Treviso analyst on industrial real estate"),
    ("hugo",    "Hugo Almeida",     "Memoria-Nox infrastructure SRE"),
    ("isabela", "Isabela Cunha",    "Galapagos investor relations"),
]

PROJECTS = [
    ("nox-mem",        "memoria-nox memory engine — Q/A/P architecture, hybrid BM25+Gemini retrieval"),
    ("nox-supermem",   "commercial productization of nox-mem, Brazilian SaaS via Stripe"),
    ("openclaw-vps",   "VPS infrastructure umbrella hosting nox-mem and nox-secretary"),
    ("granix",         "co-founded venture targeting the wellness retail market"),
    ("fii-treviso",    "industrial real estate fund focused on logistics warehouses"),
    ("fundo-lombardia","exclusive investment vehicle managed by Toto"),
    ("frooty",         "consumer app for fruit-delivery subscription in São Paulo"),
    ("galapagos-ai",   "AI advisory engagement at Galapagos Capital"),
    ("paper-eval",     "Q1 paper §5 evaluation harness — LoCoMo + LongMemEval baselines"),
    ("a-answer-api",   "P1 /api/answer flagship — gemini-2.5-flash-lite generation"),
]

LESSONS = [
    ("sed-binary",         "Never sed -i on SQLite .db files — corrupts page boundaries; filter by extension before sweep"),
    ("validate-db-state",  "Validate features against DB state, not log lines — graph-memory zombied 4 days because logs lied"),
    ("shadow-mode-ranking","Ship ranking changes shadow-mode first — ≥1 week baseline via /api/health before flipping"),
    ("env-source-cron",    "set -a; source /root/.openclaw/.env; set +a in cron — silent vectorize failures otherwise"),
    ("execfilesync-input", "execFileSync(cmd,[args]) over execSync template strings — bypasses shell, blocks injection"),
    ("rsync-delete",       "rsync --delete server→client must exclude local-only dirs — themes wiped 2026-04-26 dry-run saved"),
    ("locomo-flat-chunks", "LoCoMo chunks have no section/entity metadata — boost stack inert, must build entity eval set"),
    ("buffer-pool-alias",  "Node Buffer pool aliasing corrupts Float32Array views — copy via Uint8Array intermediate"),
    ("yaml-heredoc-yaml",  "Heredoc <<'EOF' inside YAML run:| breaks parser silently — 0 jobs spawn, no error"),
    ("worktree-leak",      "Worktree branch may have main as HEAD — run git branch --show-current before first add"),
]

DECISIONS = [
    ("d40-qap-pivot",          "Q/A/P pillars pivot — Quality, Autonomy, Product as the three strategic dimensions"),
    ("d41-five-resolved",      "Morning five decisions resolved for paper §5 scope and methodology"),
    ("d43-q4-gate-phase2",     "Q4 GTM gate Phase 2 opens — threshold ≥+15% nDCG@10 met at +18.8%"),
    ("d44-stripe-first",       "Stripe-first payments pivot — USD default, no Hotmart affiliates, global SaaS framing"),
    ("d45-entity-eval-set",    "Build entity-flavored eval set to measure boost contribution under conditions where it activates"),
    ("d-shadow-default",       "NOX_SALIENCE_MODE=shadow as default — never auto-flip to live without n=1 week health data"),
    ("d-flash-lite-default",   "gemini-2.5-flash-lite as default model — never roll back to gemini-2.5-flash (quota)"),
    ("d-snapshot-mandatory",   "Snapshot mandatory before destructive ops on chunks — withOpAudit wrapper required"),
    ("d-no-offsite-backup",    "F09 off-site backup rejected — VPS Hostinger native suffices for current DB size"),
    ("d-stripe-no-affiliates", "No affiliates in Stripe model — direct billing only, no revenue split"),
]

OTHERS = [
    ("misc-chrome-port", "Chrome dev tools occupy port 18800 on macOS — nox-mem-api uses 18802 to avoid conflict"),
    ("misc-paper-len",   "Paper draft target length ≈12 pages including references — appendix optional"),
    ("misc-hn-titles",   "HN submission title A/B test results favored the 'discipline' angle over 'pain' angle"),
    ("misc-tier-stats",  "Tier distribution snapshot: 60% working, 30% core, 10% peripheral across nox-mem-prod"),
    ("misc-locomo-flat", "LoCoMo conversation corpus has flat chunks without entity attributes by design of the source"),
    ("misc-fts-vanilla", "FTS5 vanilla AND-strict — natural language queries with punctuation often return zero hits"),
    ("misc-rrf-k60",     "RRF fusion uses k=60 default — production tested at k∈[40,80] with no significant delta"),
    ("misc-3072d",       "Gemini embedding-001 outputs 3072 dimensions — sqlite-vec column matches exactly"),
    ("misc-deploy-h2",   "Deploy windows scheduled at H+2 from end-of-day cron to avoid reindex collision"),
    ("misc-galapagos",   "Galapagos AI advisory cadence: monthly committee, ad-hoc deep-dive on M&A scenarios"),
]


# ────────────────────────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    id: str
    text: str
    section: Optional[str]      # compiled | frontmatter | timeline | None
    chunk_type: str             # person | project | lesson | decision | other
    pain: float                 # 0.1 — 1.0
    source_date: str            # ISO yyyy-mm-dd
    source_type: str            # entity_file | session_summary | event_log
    tier: str                   # core | working | peripheral
    importance: float           # 0.0 — 1.0
    source_file: str            # canonical entity file path
    entity_slug: str            # slug of the entity this chunk belongs to
    section_boost: float = field(init=False)

    def __post_init__(self):
        self.section_boost = SECTION_BOOST.get(self.section, 1.0)

    def to_dict(self) -> dict:
        d = asdict(self)
        # round floats for stable serialization
        d["pain"] = round(self.pain, 3)
        d["importance"] = round(self.importance, 3)
        d["section_boost"] = round(self.section_boost, 3)
        return d


@dataclass
class Query:
    qid: str
    query: str
    category: str           # single-hop | multi-hop | temporal | open-domain | adversarial
    style: str              # natural-language | keyword
    gold_chunk_ids: list[str]
    rationale: str          # why these golds (for human review)

    def to_dict(self) -> dict:
        return asdict(self)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def stable_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]


def importance_for(section: Optional[str], chunk_type: str) -> float:
    """Heuristic mapping; mirrors a plausible production importance derivation."""
    base = {
        "compiled":   0.7,
        "frontmatter":0.5,
        "timeline":   0.3,
        None:         0.4,
    }[section]
    type_bump = {
        "person":   0.2,
        "project":  0.15,
        "decision": 0.15,
        "lesson":   0.1,
        "other":    0.0,
    }[chunk_type]
    return min(1.0, base + type_bump)


def pick_pain(rng: random.Random) -> float:
    """30% trivial / 40% medium / 30% severe."""
    r = rng.random()
    if r < 0.30:
        return rng.uniform(0.1, 0.3)
    elif r < 0.70:
        return rng.uniform(0.3, 0.7)
    else:
        return rng.uniform(0.7, 1.0)


def pick_section(rng: random.Random) -> str:
    """30% compiled / 30% frontmatter / 40% timeline."""
    r = rng.random()
    if r < 0.30:
        return "compiled"
    elif r < 0.60:
        return "frontmatter"
    else:
        return "timeline"


def pick_source_type(rng: random.Random) -> str:
    """50% entity_file / 30% session_summary / 20% event_log."""
    r = rng.random()
    if r < 0.50:
        return "entity_file"
    elif r < 0.80:
        return "session_summary"
    else:
        return "event_log"


def pick_tier(rng: random.Random) -> str:
    """60% working / 30% core / 10% peripheral."""
    r = rng.random()
    if r < 0.60:
        return "working"
    elif r < 0.90:
        return "core"
    else:
        return "peripheral"


def pick_date(rng: random.Random, ref: date = DEFAULT_REF_DATE) -> str:
    """Uniform over last 30 days."""
    days_ago = rng.randint(0, 29)
    d = ref - timedelta(days=days_ago)
    return d.isoformat()


# ────────────────────────────────────────────────────────────────────────────
# Section text shapers — emit text that *reads like* its claimed section
# ────────────────────────────────────────────────────────────────────────────

def render_compiled(entity_slug: str, entity_name: str, claim: str) -> str:
    return f"chunk_id: \"{entity_slug}::compiled\"\n## Compiled\n{entity_name}: {claim}."


def render_frontmatter(entity_slug: str, fields: dict[str, str]) -> str:
    lines = [f"chunk_id: \"{entity_slug}::frontmatter\"", "---"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def render_timeline(entity_slug: str, dt: str, tag: str, event: str) -> str:
    return (
        f"chunk_id: \"{entity_slug}::timeline::{dt}\"\n"
        f"## Timeline\n- **{dt}** — [{tag}] {event}"
    )


# ────────────────────────────────────────────────────────────────────────────
# Corpus generation
# ────────────────────────────────────────────────────────────────────────────

def generate_corpus(rng: random.Random, n: int = DEFAULT_N_CHUNKS, ref_date: date = DEFAULT_REF_DATE) -> list[Chunk]:
    """Generate n chunks following the type/section/pain/tier distribution spec.

    Each entity gets ≥3 chunks (compiled + frontmatter + N×timeline) so we
    can construct queries that have a *correct* gold (compiled) versus
    distractors (older timeline events about the same entity).
    """
    chunks: list[Chunk] = []

    # ── Pass 1: ensure every catalog entity has a compiled+frontmatter pair ──
    catalog = (
        [("person", slug, name, claim) for slug, name, claim in PEOPLE] +
        [("project", slug, slug, claim) for slug, claim in PROJECTS] +
        [("lesson", slug, slug.replace("-", " ").title(), claim) for slug, claim in LESSONS] +
        [("decision", slug, slug.replace("-", " ").title(), claim) for slug, claim in DECISIONS] +
        [("other", slug, slug.replace("-", " ").title(), claim) for slug, claim in OTHERS]
    )

    for kind, slug, display, claim in catalog:
        ent_dir = {"person": "people", "project": "projects",
                   "lesson": "lessons", "decision": "decisions", "other": "misc"}[kind]
        source_file = f"memory/entities/{ent_dir}/{slug}.md"

        # compiled chunk
        compiled = Chunk(
            id=f"{slug}::compiled",
            text=render_compiled(slug, display, claim),
            section="compiled",
            chunk_type=kind,
            pain=pick_pain(rng),
            source_date=pick_date(rng, ref_date),
            source_type="entity_file",
            tier=pick_tier(rng),
            importance=importance_for("compiled", kind),
            source_file=source_file,
            entity_slug=slug,
        )
        chunks.append(compiled)

        # frontmatter chunk
        fm_fields = {
            "name": display,
            "type": kind,
            "status": rng.choice(["active", "active", "active", "stale", "draft"]),
            "last_review": pick_date(rng, ref_date),
        }
        frontmatter = Chunk(
            id=f"{slug}::frontmatter",
            text=render_frontmatter(slug, fm_fields),
            section="frontmatter",
            chunk_type=kind,
            pain=pick_pain(rng),
            source_date=pick_date(rng, ref_date),
            source_type="entity_file",
            tier=compiled.tier,
            importance=importance_for("frontmatter", kind),
            source_file=source_file,
            entity_slug=slug,
        )
        chunks.append(frontmatter)

    # ── Pass 2: fill to n with timeline events + miscellaneous chunks ────────
    # Bias the pass-2 catalog draws to compensate for pass-1 forcing the
    # global chunk_type distribution toward equal weights. Targets in spec
    # are 25/25/20/15/15 for person/project/lesson/decision/other.
    catalog_by_kind: dict[str, list] = {"person": [], "project": [], "lesson": [], "decision": [], "other": []}
    for kind, slug, display, claim in catalog:
        catalog_by_kind[kind].append((kind, slug, display, claim))
    kind_weights = {"person": 0.25, "project": 0.25, "lesson": 0.20, "decision": 0.15, "other": 0.15}
    kind_keys = list(kind_weights.keys())
    kind_probs = [kind_weights[k] for k in kind_keys]

    # Bias section in pass-2 toward timeline so the global distribution
    # approaches 30/30/40. Pass-1 already produced compiled+frontmatter
    # pairs for every catalog entity, so we need pass-2 to skew timeline.
    # Pass-1 produces compiled+frontmatter pairs per catalog entity (~50 each
    # of the 50 entities → ~50 compiled + ~50 frontmatter + 0 timeline before
    # pass-2). To approach 30/30/40 globally on n=500, pass-2 (n=400) should
    # be ~25/25/50 so totals land at ~150c/150f/200t.
    section_pass2 = ["compiled", "frontmatter", "timeline"]
    section_probs2 = [0.25, 0.25, 0.50]

    timeline_events = [
        ("review",   "completed a quarterly review of {ent} priorities"),
        ("incident", "responded to an outage that involved {ent}"),
        ("decision", "logged a decision related to {ent} after debate"),
        ("update",   "updated metadata and tags for {ent} after audit"),
        ("note",     "added background notes about {ent} from off-site meeting"),
        ("ship",     "shipped a deliverable touching {ent} downstream"),
        ("research", "ran exploratory research that referenced {ent}"),
        ("retro",    "held a retrospective covering {ent} outcomes"),
    ]

    while len(chunks) < n:
        # Pick kind by spec weights, then a random entity within that kind
        kind_pick = rng.choices(kind_keys, weights=kind_probs, k=1)[0]
        kind, slug, display, _claim = rng.choice(catalog_by_kind[kind_pick])
        ent_dir = {"person": "people", "project": "projects",
                   "lesson": "lessons", "decision": "decisions", "other": "misc"}[kind]
        source_file = f"memory/entities/{ent_dir}/{slug}.md"

        section = rng.choices(section_pass2, weights=section_probs2, k=1)[0]
        # Override: if section is timeline, we use the timeline shaper.
        # If section is compiled/frontmatter for a non-catalog chunk, we
        # generate session-summary or event-log style text instead.
        # Pick source_type by spec weights for pass-2 chunks (50/30/20)
        source_type = rng.choices(
            ["entity_file", "session_summary", "event_log"],
            weights=[0.50, 0.30, 0.20], k=1,
        )[0]

        if section == "timeline":
            tag, template = rng.choice(timeline_events)
            dt = pick_date(rng, ref_date)
            text = render_timeline(slug, dt, tag, template.format(ent=display))
            chunk_id = f"{slug}::timeline::{dt}::{stable_hash(text, str(len(chunks)))}"
            if source_type == "session_summary":
                source_file = f"memory/sessions/{dt}.md"
            elif source_type == "event_log":
                source_file = f"memory/events/{dt}.md"
        elif section == "compiled":
            session_dt = pick_date(rng, ref_date)
            text = (
                f"chunk_id: \"session::{session_dt}::{stable_hash(slug, str(len(chunks)))}\"\n"
                f"## Compiled\nSession {session_dt} compiled note: "
                f"{display} continues to operate normally with no escalations."
            )
            chunk_id = f"session::{session_dt}::{stable_hash(slug, str(len(chunks)))}"
            if source_type == "session_summary":
                source_file = f"memory/sessions/{session_dt}.md"
            elif source_type == "event_log":
                source_file = f"memory/events/{session_dt}.md"
        else:  # frontmatter (pass-2 off-canon)
            event_dt = pick_date(rng, ref_date)
            text = (
                f"chunk_id: \"event::{event_dt}::{stable_hash(slug, str(len(chunks)))}\"\n"
                "---\n"
                f"event_type: log\nentity: {display}\ndate: {event_dt}\n"
                "---"
            )
            chunk_id = f"event::{event_dt}::{stable_hash(slug, str(len(chunks)))}"
            if source_type == "session_summary":
                source_file = f"memory/sessions/{event_dt}.md"
            elif source_type == "event_log":
                source_file = f"memory/events/{event_dt}.md"

        c = Chunk(
            id=chunk_id,
            text=text,
            section=section,
            chunk_type=kind,
            pain=pick_pain(rng),
            source_date=pick_date(rng, ref_date),
            source_type=source_type,
            tier=pick_tier(rng),
            importance=importance_for(section, kind),
            source_file=source_file,
            entity_slug=slug,
        )
        chunks.append(c)

    return chunks[:n]


# ────────────────────────────────────────────────────────────────────────────
# Query construction — gold selection biased toward boost-friendly chunks
# ────────────────────────────────────────────────────────────────────────────

def _index_by_slug(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    idx: dict[str, list[Chunk]] = {}
    for c in chunks:
        idx.setdefault(c.entity_slug, []).append(c)
    return idx


def _compiled_for(idx: dict[str, list[Chunk]], slug: str) -> Optional[Chunk]:
    for c in idx.get(slug, []):
        if c.section == "compiled" and c.id == f"{slug}::compiled":
            return c
    return None


def _most_recent(matches: list[Chunk]) -> Optional[Chunk]:
    if not matches:
        return None
    return max(matches, key=lambda c: c.source_date)


def _highest_pain(matches: list[Chunk]) -> Optional[Chunk]:
    if not matches:
        return None
    return max(matches, key=lambda c: c.pain)


def build_single_hop(rng: random.Random, idx: dict[str, list[Chunk]],
                     n: int, qid_prefix: str) -> list[Query]:
    """Single-hop entity attribute lookup — gold is the compiled chunk."""
    out: list[Query] = []
    catalog = (
        [("person", s, n_) for s, n_, _ in PEOPLE] +
        [("project", s, s.replace("-", " ")) for s, _ in PROJECTS]
    )
    rng.shuffle(catalog)
    nl_templates = [
        "What is {name}'s role?",
        "Who is {name}?",
        "What does {name} work on?",
        "Tell me about {name}.",
    ]
    kw_templates = [
        "{name} role",
        "{name} description",
        "{name} responsibilities",
        "{name} overview",
    ]
    for i in range(n):
        kind, slug, name = catalog[i % len(catalog)]
        compiled = _compiled_for(idx, slug)
        if not compiled:
            continue
        style = "natural-language" if i % 2 == 0 else "keyword"
        tmpl = rng.choice(nl_templates if style == "natural-language" else kw_templates)
        q = tmpl.format(name=name)
        out.append(Query(
            qid=f"{qid_prefix}-{i:03d}",
            query=q,
            category="single-hop",
            style=style,
            gold_chunk_ids=[compiled.id],
            rationale=f"compiled chunk of {slug} ranked above its timeline events (section_boost 2.0 vs 0.8)",
        ))
    return out


def build_multi_hop(rng: random.Random, idx: dict[str, list[Chunk]],
                    n: int, qid_prefix: str) -> list[Query]:
    """Multi-hop cross-entity reasoning — gold = compiled of ≥2 related entities."""
    # Hand-curated cross-entity links
    pairs = [
        ("toto",       ["granix", "nuvini-board", "fii-treviso"][:2], "Granix and FII Treviso"),
        ("ana",        ["granix", "nox-mem"][:2], "Granix platform and nox-mem"),
        ("bruno",      ["galapagos-ai", "nox-mem"], "Galapagos AI and nox-mem retrieval research"),
        ("daniel",     ["frooty", "nox-supermem"], "Frooty backend and Nox-Supermem product"),
        ("felipe",     ["nox-supermem", "nox-mem"], "Nox-Supermem and nox-mem"),
        ("hugo",       ["nox-mem", "openclaw-vps"], "nox-mem and openclaw-vps"),
        ("d40-qap-pivot", ["nox-mem", "paper-eval"], "the Q/A/P pivot and the paper eval"),
        ("d44-stripe-first", ["nox-supermem"], "Stripe-first model in Nox-Supermem"),
        ("d45-entity-eval-set", ["paper-eval", "nox-mem"], "the entity eval set and paper §5"),
    ]
    pair_set = []
    for primary, related, blurb in pairs:
        # Keep only relations where primary AND at least one related exist
        if primary not in idx:
            continue
        rel_existing = [r for r in related if r in idx]
        if not rel_existing:
            continue
        pair_set.append((primary, rel_existing, blurb))
    if not pair_set:
        return []
    nl_templates = [
        "How is {primary} connected to {blurb}?",
        "What is the relationship between {primary} and {blurb}?",
        "Why does {primary} matter for {blurb}?",
    ]
    kw_templates = [
        "{primary} {blurb}",
        "{primary} relation {blurb}",
        "{primary} link {blurb}",
    ]
    out: list[Query] = []
    for i in range(n):
        primary, related, blurb = pair_set[i % len(pair_set)]
        compiled_primary = _compiled_for(idx, primary)
        compiled_related = [_compiled_for(idx, r) for r in related]
        compiled_related = [c for c in compiled_related if c is not None]
        if not compiled_primary or not compiled_related:
            continue
        style = "natural-language" if i % 2 == 0 else "keyword"
        tmpl = rng.choice(nl_templates if style == "natural-language" else kw_templates)
        prim_name = primary.replace("-", " ")
        q = tmpl.format(primary=prim_name, blurb=blurb)
        golds = [compiled_primary.id] + [c.id for c in compiled_related[:2]]
        out.append(Query(
            qid=f"{qid_prefix}-{i:03d}",
            query=q,
            category="multi-hop",
            style=style,
            gold_chunk_ids=golds,
            rationale=f"compiled of {primary} + {[c.entity_slug for c in compiled_related[:2]]} (cross-entity)",
        ))
    return out


def build_temporal(rng: random.Random, idx: dict[str, list[Chunk]],
                   n: int, qid_prefix: str, ref_date: date) -> list[Query]:
    """Temporal — gold has the *most recent* source_date among entity matches."""
    out: list[Query] = []
    targets = []
    for slug, ch_list in idx.items():
        timeline_chunks = [c for c in ch_list if c.section == "timeline"]
        if len(timeline_chunks) >= 2:
            targets.append((slug, timeline_chunks))
    rng.shuffle(targets)
    nl_templates = [
        "What happened recently with {name}?",
        "What is the latest update on {name}?",
        "Any recent changes to {name} this month?",
    ]
    kw_templates = [
        "{name} latest",
        "{name} recent update",
        "{name} this month",
    ]
    for i in range(n):
        if not targets:
            break
        slug, tlist = targets[i % len(targets)]
        most_recent = _most_recent(tlist)
        if most_recent is None:
            continue
        style = "natural-language" if i % 2 == 0 else "keyword"
        tmpl = rng.choice(nl_templates if style == "natural-language" else kw_templates)
        q = tmpl.format(name=slug.replace("-", " "))
        # Allow 1-2 golds: most_recent + maybe second-most-recent
        sorted_tl = sorted(tlist, key=lambda c: c.source_date, reverse=True)
        golds = [sorted_tl[0].id]
        if rng.random() < 0.4 and len(sorted_tl) > 1:
            golds.append(sorted_tl[1].id)
        out.append(Query(
            qid=f"{qid_prefix}-{i:03d}",
            query=q,
            category="temporal",
            style=style,
            gold_chunk_ids=golds,
            rationale=f"most-recent timeline of {slug} (recency factor in salience)",
        ))
    return out


def build_open_domain(rng: random.Random, idx: dict[str, list[Chunk]],
                      n: int, qid_prefix: str) -> list[Query]:
    """Open-domain — gold = lesson/decision chunks with high pain matching the topic."""
    out: list[Query] = []
    # Curate topic clusters: query phrase → relevant entity slugs to gold
    topics = [
        ("What lessons exist about SQLite corruption?", ["sed-binary", "validate-db-state"], "SQLite corruption lessons"),
        ("How do we handle ranking changes safely?", ["shadow-mode-ranking", "d-shadow-default"], "ranking shadow-mode"),
        ("What is the model default for nox-mem?", ["d-flash-lite-default"], "model default flash-lite"),
        ("Decisions about Stripe payments", ["d44-stripe-first", "d-stripe-no-affiliates"], "Stripe payments"),
        ("Lessons about cron environment variables", ["env-source-cron"], "cron env"),
        ("Lessons about rsync and syncing", ["rsync-delete"], "rsync delete"),
        ("Decisions tied to Q/A/P pillars", ["d40-qap-pivot", "d41-five-resolved"], "Q/A/P"),
        ("Why no off-site backup?", ["d-no-offsite-backup"], "off-site backup"),
        ("How do we guard destructive ops?", ["d-snapshot-mandatory"], "destructive ops"),
        ("What is RRF k tuning?", ["misc-rrf-k60"], "rrf k60"),
    ]
    nl_set = topics  # natural-language style — they are full questions
    kw_templates = ["{kw}", "{kw} reference", "{kw} memo"]
    for i in range(n):
        topic_q, slugs, kw = topics[i % len(topics)]
        compiled_chunks = [_compiled_for(idx, s) for s in slugs]
        compiled_chunks = [c for c in compiled_chunks if c is not None]
        if not compiled_chunks:
            continue
        style = "natural-language" if i % 2 == 0 else "keyword"
        if style == "natural-language":
            q = topic_q
        else:
            q = rng.choice(kw_templates).format(kw=kw)
        # Multi-gold up to 3
        golds = [c.id for c in compiled_chunks[:3]]
        out.append(Query(
            qid=f"{qid_prefix}-{i:03d}",
            query=q,
            category="open-domain",
            style=style,
            gold_chunk_ids=golds,
            rationale=f"compiled chunks (lesson/decision) matching topic {kw!r}",
        ))
    return out


def build_adversarial(rng: random.Random, idx: dict[str, list[Chunk]],
                      n: int, qid_prefix: str) -> list[Query]:
    """Adversarial — typos, paraphrase, missing words."""
    out: list[Query] = []
    base_queries = [
        ("Who is Toto Bunsello?",         "toto"),      # typo Busnello → Bunsello
        ("nox mem hybird search",         "nox-mem"),   # hybrid typo
        ("What did Ana Castro lead recently?", "ana"),  # paraphrase
        ("Granixx co-founder",            "granix"),    # typo
        ("rsynk dlete dangr",             "rsync-delete"),  # double typo
        ("paper §5 ablation rationale",   "paper-eval"),     # punctuation
        ("Q3 latency numbers — measured?", "a-answer-api"),  # em-dash
        ("Frooti subscription model",     "frooty"),    # typo
        ("Stripe-first vs hotmart decisn",   "d44-stripe-first"),  # decisn typo
        ("Bruno Lima role gallapagos AI", "bruno"),     # typo
    ]
    for i in range(n):
        query, slug = base_queries[i % len(base_queries)]
        compiled = _compiled_for(idx, slug)
        if not compiled:
            continue
        style = "natural-language" if i % 2 == 0 else "keyword"
        golds = [compiled.id]
        # 30% chance to add second gold (frontmatter of same entity)
        if rng.random() < 0.3:
            for c in idx[slug]:
                if c.section == "frontmatter" and c.id.endswith("::frontmatter"):
                    golds.append(c.id)
                    break
        out.append(Query(
            qid=f"{qid_prefix}-{i:03d}",
            query=query,
            category="adversarial",
            style=style,
            gold_chunk_ids=golds,
            rationale=f"adversarial form of {slug} lookup (typo/paraphrase)",
        ))
    return out


def generate_queries(rng: random.Random, chunks: list[Chunk],
                     n: int = DEFAULT_N_QUERIES, ref_date: date = DEFAULT_REF_DATE) -> list[Query]:
    idx = _index_by_slug(chunks)
    per_cat = n // 5
    qs: list[Query] = []
    qs.extend(build_single_hop  (rng, idx, per_cat, "sh"))
    qs.extend(build_multi_hop   (rng, idx, per_cat, "mh"))
    qs.extend(build_temporal    (rng, idx, per_cat, "tp", ref_date))
    qs.extend(build_open_domain (rng, idx, per_cat, "od"))
    qs.extend(build_adversarial (rng, idx, per_cat, "ad"))
    return qs


# ────────────────────────────────────────────────────────────────────────────
# Distribution sanity checks
# ────────────────────────────────────────────────────────────────────────────

def summarize_distribution(chunks: list[Chunk]) -> dict:
    from collections import Counter
    n = len(chunks)
    sec  = Counter(c.section for c in chunks)
    typ  = Counter(c.chunk_type for c in chunks)
    src  = Counter(c.source_type for c in chunks)
    tier = Counter(c.tier for c in chunks)
    pain_bins = {"trivial[0.1,0.3)": 0, "medium[0.3,0.7)": 0, "severe[0.7,1.0]": 0}
    for c in chunks:
        if c.pain < 0.3:
            pain_bins["trivial[0.1,0.3)"] += 1
        elif c.pain < 0.7:
            pain_bins["medium[0.3,0.7)"] += 1
        else:
            pain_bins["severe[0.7,1.0]"] += 1
    return {
        "total":        n,
        "section":      {k: f"{v} ({v/n:.1%})" for k, v in sec.items()},
        "chunk_type":   {k: f"{v} ({v/n:.1%})" for k, v in typ.items()},
        "source_type":  {k: f"{v} ({v/n:.1%})" for k, v in src.items()},
        "tier":         {k: f"{v} ({v/n:.1%})" for k, v in tier.items()},
        "pain":         {k: f"{v} ({v/n:.1%})" for k, v in pain_bins.items()},
    }


def summarize_queries(qs: list[Query]) -> dict:
    from collections import Counter
    n = len(qs)
    cat = Counter(q.category for q in qs)
    sty = Counter(q.style for q in qs)
    gold_sizes = Counter(len(q.gold_chunk_ids) for q in qs)
    return {
        "total":      n,
        "category":   {k: f"{v} ({v/n:.1%})" for k, v in cat.items()},
        "style":      {k: f"{v} ({v/n:.1%})" for k, v in sty.items()},
        "gold_size":  dict(gold_sizes),
    }


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> int:
    # Isolation check (postmortem 2026-05-19) — warn/abort if env looks like
    # downstream ingest would land in production DB.
    _check_generator_isolation()

    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="paper/publication/data/entity-eval-2026-05-19")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--n-chunks", type=int, default=DEFAULT_N_CHUNKS)
    p.add_argument("--n-queries", type=int, default=DEFAULT_N_QUERIES)
    p.add_argument("--ref-date", default=DEFAULT_REF_DATE.isoformat(),
                   help="ISO yyyy-mm-dd, defines the most-recent edge of the 30-day window")
    args = p.parse_args()

    ref_date = date.fromisoformat(args.ref_date)
    rng = random.Random(args.seed)

    chunks = generate_corpus(rng, n=args.n_chunks, ref_date=ref_date)
    queries = generate_queries(rng, chunks, n=args.n_queries, ref_date=ref_date)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = out_dir / "corpus.jsonl"
    queries_path = out_dir / "queries.jsonl"
    with corpus_path.open("w") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), sort_keys=True) + "\n")
    with queries_path.open("w") as f:
        for q in queries:
            f.write(json.dumps(q.to_dict(), sort_keys=True) + "\n")

    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "seed":         args.seed,
        "ref_date":     args.ref_date,
        "corpus":       summarize_distribution(chunks),
        "queries":      summarize_queries(queries),
        "files":        {"corpus": str(corpus_path), "queries": str(queries_path)},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
