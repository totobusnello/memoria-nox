"""
Stack Exchange dump adapter for nox-mem E5 cross-corpus evaluation.

This script downloads one or more Stack Exchange XML dumps from archive.org,
parses them with a memory-safe streaming parser, converts posts to the SQLite
chunk schema that nox-mem expects, curates 50 evaluation queries (title →
natural-language rewrite), and runs hybrid-search via the nox-mem HTTP API to
produce a results.jsonl suitable for the cross-corpus table in the paper §5.

Site selection trade-off (1 vs 3 sites)
----------------------------------------
Using 3 sites (cooking, scifi, meta.stackexchange/superuser for the "tech"
dimension) is the recommended path because it exercises nox-mem across three
distinct registers:
  - cooking.stackexchange.com: imperative, domain-specific vocabulary
  - scifi.stackexchange.com: narrative, pop-culture references
  - superuser.com: technical, CLI/config vocabulary (closer to internal corpus)

This mirrors the BEIR multi-collection philosophy: a retriever that generalises
must score well on all three, not just the closest domain.  The 10 K post quota
is split ~3 500 / 3 000 / 3 500 across the three sites so each contributes
roughly equally to the query pool.

A single large site (cooking ~5 GB raw) would be cheaper to download but limits
diversity.  Budget concern: the Gemini embedding cost for 10 K posts at ~500
tokens average ≈ 5 M tokens ≈ $0.50 at text-embedding-004 pricing (May 2026).
Three sites at 10 K posts total stay within the same budget while providing
richer generalisation evidence.

Limitation (documented for §5)
--------------------------------
The query curation heuristic "strip question words from title" produces queries
that are biased toward the title vocabulary already in the index.  This
inflates recall vs. a blind human curator.  We label this in the paper as
"internal-heuristic queries (SE)" and contrast with the human-curated R01b
set.  The SE queries are still valuable for generalization analysis because the
DOCUMENTS are entirely external (nox-mem has never seen SE content).

-------------------------------------------------------------------------------
HOW TO RUN
-------------------------------------------------------------------------------

  # 1. Create isolated venv
  python3.11 -m venv /tmp/se-eval-env
  source /tmp/se-eval-env/bin/activate
  pip install py7zr "beautifulsoup4>=4.12" lxml requests tqdm

  # 2. Set output paths (defaults shown)
  export STACKEXCHANGE_TEMP_DB=/tmp/se-eval/chunks.db
  export NOX_API_BASE=http://127.0.0.1:18802

  # 3. Run full pipeline (estimated times on Mac Mini M2 8 GB)
  python stackexchange_adapter.py \
      --sites cooking.stackexchange.com scifi.stackexchange.com superuser.com \
      --sample-n 10000 --min-score 2 \
      --output-dir /tmp/se-eval

  # Estimated wall-clock:
  #   Download 3 dumps    : 20-40 min (cooking ~5 GB, scifi ~800 MB, SU ~3 GB)
  #   Parse + filter      : 5-10 min  (streaming, ~2 GB peak per site)
  #   Ingest SQLite       : 2-3 min
  #   Embed via nox-mem   : 30-60 min (Gemini API, ~$0.50-2 depending on tokens)
  #   Query curation      : < 1 min
  #   Eval via HTTP API   : 5-10 min  (50 queries × HTTP round-trip)

  # Outputs:
  #   $STACKEXCHANGE_TEMP_DB           — SQLite with chunks table
  #   /tmp/se-eval/queries.jsonl       — 50 evaluation queries
  #   /tmp/se-eval/results.jsonl       — per-query nDCG/MRR/Recall@10
  #   /tmp/se-eval/eval-summary.json   — aggregate metrics for paper table

  # Integration with paper §5:
  #   Copy eval-summary.json into paper/publication/results/corpus-stackexchange-results.jsonl
  #   Add row to Table 3 (Cross-corpus generalisation) in 04-paper-arxiv-draft.md:
  #     | Stack Exchange 10 K (3 sites) | hybrid | XX.X | XX.X | XX.X |

-------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import random
import re
import sqlite3
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Iterator
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Optional heavy deps — imported lazily so the module can be imported without
# them installed (e.g. for unit testing the pure-Python parts).
# ---------------------------------------------------------------------------

logger = logging.getLogger("stackexchange_adapter")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SEPost:
    """Represents a single parsed Stack Exchange post (question or answer)."""

    post_id: int
    post_type: int          # 1 = question, 2 = answer
    parent_id: int | None   # only set for answers
    title: str              # only set for questions
    body_html: str
    body_text: str          # HTML-stripped version
    score: int
    tags: list[str]
    accepted_answer_id: int | None
    answer_ids: list[int] = field(default_factory=list)  # populated after join
    site: str = ""


@dataclass
class EvalQuery:
    """A single evaluation query with expected relevant doc IDs."""

    query_id: str
    query_text: str
    site: str
    source_post_id: int
    source_title: str
    expected_doc_ids: list[int]   # question + top-3 answer post_ids


@dataclass
class EvalResult:
    """Per-query evaluation result."""

    query_id: str
    query_text: str
    retrieved_ids: list[int]
    relevant_ids: set[int]
    ndcg_at_10: float
    mrr: float
    recall_at_10: float


# ---------------------------------------------------------------------------
# 1. Download
# ---------------------------------------------------------------------------

ARCHIVE_ORG_BASE = "https://archive.org/download/stackexchange"


def download_dump(site: str, output_dir: Path) -> Path:
    """Download a Stack Exchange XML dump (.7z) from archive.org.

    Args:
        site: Full site domain, e.g. "cooking.stackexchange.com".
              Note: "stackoverflow.com" is split into multiple files; this
              adapter is designed for smaller per-topic sites.
        output_dir: Directory where the .7z archive will be saved.

    Returns:
        Path to the downloaded .7z file.

    Raises:
        RuntimeError: If the download fails after retries.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{site}.7z"
    url = f"{ARCHIVE_ORG_BASE}/{archive_name}"
    dest = output_dir / archive_name

    if dest.exists():
        logger.info("Archive already downloaded: %s", dest)
        return dest

    logger.info("Downloading %s → %s", url, dest)
    _download_with_progress(url, dest)
    return dest


def _download_with_progress(url: str, dest: Path, retries: int = 3) -> None:
    """Download URL to dest with retry logic and progress logging."""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "nox-mem-research/1.0 (academic evaluation)"},
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1 << 20  # 1 MB
                with dest.open("wb") as fh:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded / total * 100
                            logger.debug(
                                "  %.1f%% (%d / %d MB)",
                                pct,
                                downloaded >> 20,
                                total >> 20,
                            )
            logger.info("Download complete: %s (%d MB)", dest, downloaded >> 20)
            return
        except Exception as exc:
            logger.warning("Download attempt %d/%d failed: %s", attempt, retries, exc)
            if dest.exists():
                dest.unlink()
            if attempt < retries:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Failed to download {url} after {retries} attempts")


def extract_dump(archive_path: Path, output_dir: Path) -> Path:
    """Extract a .7z dump archive using py7zr.

    Only extracts Posts.xml (the file we need); other XML files in the dump
    (Users, Comments, Badges, etc.) are skipped to save disk space.

    Args:
        archive_path: Path to the downloaded .7z file.
        output_dir: Directory where Posts.xml will be extracted.

    Returns:
        Path to the extracted Posts.xml file.

    Raises:
        ImportError: If py7zr is not installed.
        FileNotFoundError: If Posts.xml was not found in the archive.
    """
    try:
        import py7zr  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("py7zr required: pip install py7zr") from exc

    posts_xml = output_dir / "Posts.xml"
    if posts_xml.exists():
        logger.info("Posts.xml already extracted: %s", posts_xml)
        return posts_xml

    logger.info("Extracting Posts.xml from %s → %s", archive_path, output_dir)
    with py7zr.SevenZipFile(archive_path, mode="r") as archive:
        names = archive.getnames()
        if "Posts.xml" not in names:
            raise FileNotFoundError(
                f"Posts.xml not found in {archive_path}. "
                f"Available: {names[:10]}"
            )
        archive.extract(targets=["Posts.xml"], path=output_dir)

    if not posts_xml.exists():
        raise FileNotFoundError(f"Extraction succeeded but Posts.xml missing: {output_dir}")
    logger.info("Extracted Posts.xml (%d MB)", posts_xml.stat().st_size >> 20)
    return posts_xml


# ---------------------------------------------------------------------------
# 2. Parse
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<([^>]+)>")
_MULTI_SPACE = re.compile(r"\s+")
_CODE_BLOCK_RE = re.compile(r"<pre[^>]*>.*?</pre>", re.DOTALL | re.IGNORECASE)


def _strip_html(html_text: str) -> str:
    """Strip HTML tags from a Stack Exchange post body.

    Design decisions:
    - Code blocks (<pre><code>…</code></pre>) are PRESERVED as plain text
      because they are semantically important for tech sites (superuser.com).
      We extract their text content rather than removing them.
    - <a> tags and <img> tags are removed (link URLs and images add noise).
    - HTML entities are decoded (e.g. &amp; → &).
    - Runs of whitespace are collapsed to single space.

    Args:
        html_text: Raw HTML body from a Stack Exchange XML dump.

    Returns:
        Plain-text representation suitable for chunking.
    """
    if not html_text:
        return ""
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("beautifulsoup4 required: pip install beautifulsoup4") from exc

    soup = BeautifulSoup(html_text, "lxml")

    # Remove purely decorative elements (images, link hrefs)
    for tag in soup.find_all(["img"]):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()  # keep link text, drop href

    text = soup.get_text(separator=" ")
    text = html.unescape(text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


def _parse_tags(tags_attr: str) -> list[str]:
    """Parse the pipe-delimited tag string from SE XML.

    Example: '<python><django><orm>' → ['python', 'django', 'orm']

    Args:
        tags_attr: Raw Tags attribute value from Posts.xml.

    Returns:
        List of tag strings (may be empty).
    """
    if not tags_attr:
        return []
    return [t.strip("<>") for t in tags_attr.split("><") if t.strip("<>")]


def parse_posts_xml(
    xml_path: Path,
    site: str = "",
    sample_n: int = 10_000,
    min_score: int = 2,
    seed: int = 42,
) -> list[SEPost]:
    """Parse a Stack Exchange Posts.xml file using streaming ElementTree.

    Uses iterparse to avoid loading multi-GB XML into memory.  Peak memory is
    bounded by the number of elements buffered (cleared after each row element).

    Quality filter: ``min_score >= 2``
    Posts with Score 0 or 1 are frequently: duplicate questions, low-effort
    answers, outdated information, or outright spam.  Score ≥ 2 is a community
    signal that at least two users found the content useful.  This keeps the
    eval corpus realistic (a retriever should surface useful content, not noise).

    Args:
        xml_path: Path to Posts.xml (may be several GB).
        site: Site identifier attached to each post for provenance.
        sample_n: Maximum number of posts to return (random sample after filter).
            The full qualifying set may be much larger; we sample to control cost.
        min_score: Minimum community score to include a post.
        seed: Random seed for reproducible sampling.

    Returns:
        List of at most ``sample_n`` SEPost objects, shuffled randomly.

    Raises:
        AssertionError: If the number of qualifying posts is 0 (bad filter or
            wrong XML).
    """
    logger.info("Streaming parse: %s (site=%s, min_score=%d)", xml_path, site, min_score)

    all_posts: list[SEPost] = []
    context = ET.iterparse(str(xml_path), events=("start", "end"))

    n_rows_seen = 0
    n_accepted = 0

    for event, elem in context:
        if event != "end" or elem.tag != "row":
            continue

        n_rows_seen += 1
        if n_rows_seen % 100_000 == 0:
            logger.debug("  rows seen: %d, accepted: %d", n_rows_seen, n_accepted)

        try:
            score = int(elem.get("Score", "0"))
        except ValueError:
            elem.clear()
            continue

        if score < min_score:
            elem.clear()
            continue

        try:
            post_id = int(elem.get("Id", "-1"))
            post_type = int(elem.get("PostTypeId", "0"))
        except ValueError:
            elem.clear()
            continue

        # Only questions (1) and answers (2)
        if post_type not in (1, 2):
            elem.clear()
            continue

        body_html = elem.get("Body", "")
        body_text = _strip_html(body_html)

        # Skip empty bodies after stripping
        if len(body_text) < 20:
            elem.clear()
            continue

        try:
            parent_id_str = elem.get("ParentId")
            parent_id = int(parent_id_str) if parent_id_str else None

            accepted_str = elem.get("AcceptedAnswerId")
            accepted_answer_id = int(accepted_str) if accepted_str else None
        except ValueError:
            parent_id = None
            accepted_answer_id = None

        tags = _parse_tags(elem.get("Tags", ""))
        title = elem.get("Title", "")

        post = SEPost(
            post_id=post_id,
            post_type=post_type,
            parent_id=parent_id,
            title=title,
            body_html=body_html,
            body_text=body_text,
            score=score,
            tags=tags,
            accepted_answer_id=accepted_answer_id,
            site=site,
        )
        all_posts.append(post)
        n_accepted += 1

        # Free element memory immediately
        elem.clear()

    logger.info(
        "Parse complete: %d rows seen, %d qualifying (score≥%d), site=%s",
        n_rows_seen,
        n_accepted,
        min_score,
        site,
    )

    assert n_accepted > 0, (
        f"No posts qualified from {xml_path} with min_score={min_score}. "
        "Check XML path and filter parameters."
    )

    if len(all_posts) <= sample_n:
        logger.info("Returning all %d posts (< sample_n=%d)", len(all_posts), sample_n)
        return all_posts

    rng = random.Random(seed)
    sampled = rng.sample(all_posts, sample_n)
    logger.info("Sampled %d from %d qualifying posts", len(sampled), len(all_posts))
    return sampled


def _join_answers(posts: list[SEPost]) -> list[SEPost]:
    """Attach answer IDs to their parent question posts (in-place).

    Args:
        posts: Mixed list of questions and answers.

    Returns:
        Same list with answer_ids populated on question posts.
    """
    question_map: dict[int, SEPost] = {
        p.post_id: p for p in posts if p.post_type == 1
    }
    for post in posts:
        if post.post_type == 2 and post.parent_id in question_map:
            question_map[post.parent_id].answer_ids.append(post.post_id)
    return posts


# ---------------------------------------------------------------------------
# 3. Ingest to SQLite
# ---------------------------------------------------------------------------

_CHUNK_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_text  TEXT NOT NULL,
    source_file TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    -- nox-mem schema v10 fields
    importance  REAL NOT NULL DEFAULT 0.5,
    pain        REAL NOT NULL DEFAULT 0.2,
    recency     REAL NOT NULL DEFAULT 1.0,
    retention_days INTEGER,
    section     TEXT,
    section_boost REAL NOT NULL DEFAULT 1.0,
    -- SE-specific metadata stored as JSON in extra_meta
    extra_meta  TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS se_post_map (
    chunk_id    INTEGER PRIMARY KEY REFERENCES chunks(id),
    site        TEXT NOT NULL,
    post_id     INTEGER NOT NULL,
    post_type   INTEGER NOT NULL,
    parent_id   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_se_post_map_post ON se_post_map(site, post_id);
"""


def posts_to_chunks_db(
    posts: list[SEPost],
    target_db_path: Path,
) -> int:
    """Convert parsed SE posts to the nox-mem SQLite chunks schema.

    Each post becomes exactly ONE chunk.  The chunk_text is:
        ``{title}\\n\\n{body_text}`` for questions (title + body)
        ``{body_text}``             for answers (no title)

    This "post = 1 chunk" design is intentional:
    - SE posts are already paragraph-sized (median ~400 tokens)
    - Sub-chunking adds complexity without benefit at 10 K scale
    - The eval queries map to full post IDs, so chunk/doc boundaries align

    The section field is set to "compiled" for questions (they contain the
    canonical problem statement + answer) and NULL for pure answers.
    section_boost follows nox-mem conventions: compiled=2.0.

    Args:
        posts: Parsed SE posts (questions and answers mixed).
        target_db_path: Path to the output SQLite database.
            Created if it does not exist; chunks table is appended.

    Returns:
        Number of chunks inserted.
    """
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_db_path))
    conn.executescript(_CHUNK_SCHEMA)
    conn.commit()

    inserted = 0
    batch: list[tuple] = []
    map_batch: list[tuple] = []

    for post in posts:
        if post.post_type == 1:
            chunk_text = f"{post.title}\n\n{post.body_text}".strip()
            section = "compiled"
            section_boost = 2.0
        else:
            chunk_text = post.body_text.strip()
            section = None
            section_boost = 1.0

        if not chunk_text:
            continue

        source_file = f"stackexchange/{post.site}/post-{post.post_id}.md"
        token_count = len(chunk_text.split())  # rough word count as proxy

        extra_meta = json.dumps({
            "site": post.site,
            "post_id": post.post_id,
            "post_type": post.post_type,
            "score": post.score,
            "tags": post.tags,
            "accepted_answer_id": post.accepted_answer_id,
        })

        batch.append((
            chunk_text,
            source_file,
            0,               # chunk_index
            token_count,
            0.5,             # importance (neutral for external corpus)
            0.2,             # pain (neutral)
            1.0,             # recency
            None,            # retention_days
            section,
            section_boost,
            extra_meta,
        ))

    conn.executemany(
        """
        INSERT INTO chunks
            (chunk_text, source_file, chunk_index, token_count,
             importance, pain, recency, retention_days,
             section, section_boost, extra_meta)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        batch,
    )
    conn.commit()

    # Build the post-map in a second pass using last-inserted rowids
    # We re-query by source_file to get the assigned IDs.
    for post in posts:
        source_file = f"stackexchange/{post.site}/post-{post.post_id}.md"
        row = conn.execute(
            "SELECT id FROM chunks WHERE source_file = ? LIMIT 1",
            (source_file,),
        ).fetchone()
        if row:
            map_batch.append((row[0], post.site, post.post_id, post.post_type, post.parent_id))

    conn.executemany(
        "INSERT OR IGNORE INTO se_post_map (chunk_id, site, post_id, post_type, parent_id) VALUES (?,?,?,?,?)",
        map_batch,
    )
    conn.commit()

    inserted = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    logger.info("Inserted %d chunks into %s", inserted, target_db_path)
    conn.close()
    return inserted


def lookup_chunk_id_for_post(
    conn: sqlite3.Connection,
    site: str,
    post_id: int,
) -> int | None:
    """Return the chunk.id for a given SE post_id from the se_post_map.

    Args:
        conn: Open SQLite connection to the chunks DB.
        site: Site domain string (e.g. "cooking.stackexchange.com").
        post_id: Stack Exchange post integer ID.

    Returns:
        chunk_id if found, None otherwise.
    """
    row = conn.execute(
        "SELECT chunk_id FROM se_post_map WHERE site=? AND post_id=?",
        (site, post_id),
    ).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# 4. Query curation
# ---------------------------------------------------------------------------

_QUESTION_WORD_RE = re.compile(
    r"^(how (do|does|can|to|would|should|did|is|are|was|were)|"
    r"what (is|are|was|were|does|should)|"
    r"why (is|are|does|do|would|should|did)|"
    r"when (is|are|does|do|would|should|did)|"
    r"where (is|are|does|do|can|should|did)|"
    r"which|who|whom|is (there|it|this|that|a|an|the)|"
    r"can (i|you|we|it)|should (i|you|we)|"
    r"does (it|this|that)|do (i|you|we))\b",
    re.IGNORECASE,
)


def _title_to_query(title: str) -> str:
    """Convert a SE question title into a natural-language search query.

    Heuristic (documented limitation for paper §5):
    1. Strip trailing '?' and leading/trailing whitespace
    2. If the title starts with a WH-word or auxiliary verb pattern, keep as-is
       (already a natural language query)
    3. Otherwise, prefix with "How to " as a default interrogative frame

    This heuristic is weak by design — it does not paraphrase, so queries
    share vocabulary with the indexed title.  We document this as a bias
    in §5: "SE title-derived queries overestimate recall vs blind queries."

    Args:
        title: Raw Stack Exchange question title.

    Returns:
        Query string (no trailing '?').
    """
    title = title.strip().rstrip("?").strip()
    if not title:
        return ""

    if _QUESTION_WORD_RE.match(title):
        return title

    # Noun-phrase titles: "Best practices for X" → keep as-is (still retrieval-natural)
    # Short titles < 5 words: prefix with "How to"
    if len(title.split()) < 5:
        return f"How to {title.lower()}"

    return title


def curate_queries(
    posts: list[SEPost],
    n: int = 50,
    seed: int = 42,
) -> list[EvalQuery]:
    """Generate evaluation queries from question posts.

    Strategy:
    - Filter to questions only (post_type == 1) with at least 1 answer in our
      sample (so expected_doc_ids is non-empty beyond the question itself).
    - Prefer questions with Tags populated (richer for retrieval diversity).
    - Convert title to NL query via _title_to_query heuristic.
    - expected_doc_ids = [question_post_id] + up to 3 answer_ids (by insertion
      order, which correlates with score in SE dumps — accepted answer is
      stored first).

    Args:
        posts: Mixed list of questions and answers (all sites).
        n: Number of queries to produce.  Must be ≤ number of eligible questions.
        seed: Random seed for reproducible selection.

    Returns:
        List of EvalQuery objects.

    Raises:
        AssertionError: If fewer than n eligible questions are found.
    """
    posts = _join_answers(posts)

    eligible: list[SEPost] = [
        p for p in posts
        if p.post_type == 1
        and p.title
        and len(p.answer_ids) >= 1
        and len(_title_to_query(p.title)) >= 10
    ]

    logger.info("Eligible questions for query curation: %d", len(eligible))

    # Sort by number of answers desc (more answers = more expected docs = richer eval)
    eligible.sort(key=lambda p: len(p.answer_ids), reverse=True)

    # Stratify by site to avoid single-site domination
    sites = list({p.site for p in eligible})
    per_site = max(1, n // len(sites)) if sites else n
    stratified: list[SEPost] = []
    rng = random.Random(seed)

    for site in sorted(sites):
        site_posts = [p for p in eligible if p.site == site]
        take = min(per_site, len(site_posts))
        stratified.extend(rng.sample(site_posts, take))

    # Top-up if we're short (due to uneven site sizes)
    remaining_ids = {p.post_id for p in stratified}
    extras = [p for p in eligible if p.post_id not in remaining_ids]
    rng.shuffle(extras)
    while len(stratified) < n and extras:
        stratified.append(extras.pop(0))

    assert len(stratified) >= n, (
        f"Not enough eligible questions: have {len(stratified)}, need {n}. "
        "Reduce --queries-n or lower --min-score."
    )

    selected = stratified[:n]

    queries: list[EvalQuery] = []
    for q in selected:
        query_text = _title_to_query(q.title)
        if not query_text:
            continue
        # expected_doc_ids: question itself + up to 3 answers
        expected = [q.post_id] + q.answer_ids[:3]
        queries.append(
            EvalQuery(
                query_id=f"{q.site}-{q.post_id}",
                query_text=query_text,
                site=q.site,
                source_post_id=q.post_id,
                source_title=q.title,
                expected_doc_ids=expected,
            )
        )

    assert len(queries) >= n, (
        f"Query list shorter than expected: {len(queries)} < {n}"
    )

    logger.info("Curated %d evaluation queries across %d sites", len(queries), len(sites))
    return queries


def save_queries_jsonl(queries: list[EvalQuery], path: Path) -> None:
    """Write queries to a JSONL file.

    Args:
        queries: List of EvalQuery objects.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for q in queries:
            fh.write(
                json.dumps(
                    {
                        "query_id": q.query_id,
                        "query_text": q.query_text,
                        "site": q.site,
                        "source_post_id": q.source_post_id,
                        "source_title": q.source_title,
                        "expected_doc_ids": q.expected_doc_ids,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    logger.info("Saved %d queries to %s", len(queries), path)


def load_queries_jsonl(path: Path) -> list[EvalQuery]:
    """Load queries from a JSONL file produced by save_queries_jsonl.

    Args:
        path: Path to queries.jsonl.

    Returns:
        List of EvalQuery objects.
    """
    queries: list[EvalQuery] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            data = json.loads(line)
            queries.append(
                EvalQuery(
                    query_id=data["query_id"],
                    query_text=data["query_text"],
                    site=data["site"],
                    source_post_id=data["source_post_id"],
                    source_title=data["source_title"],
                    expected_doc_ids=data["expected_doc_ids"],
                )
            )
    return queries


# ---------------------------------------------------------------------------
# 5. Evaluate via nox-mem HTTP API
# ---------------------------------------------------------------------------


def _chunk_ids_to_post_ids(
    chunk_ids: list[int],
    conn: sqlite3.Connection,
) -> list[int]:
    """Map chunk IDs (nox-mem internal) back to SE post IDs.

    Args:
        chunk_ids: List of chunk.id integers from search results.
        conn: Open SQLite connection.

    Returns:
        List of post_ids in the same order (unknowns are skipped).
    """
    if not chunk_ids:
        return []
    placeholders = ",".join("?" * len(chunk_ids))
    rows = conn.execute(
        f"SELECT chunk_id, post_id FROM se_post_map WHERE chunk_id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    chunk_to_post = {r[0]: r[1] for r in rows}
    return [chunk_to_post[cid] for cid in chunk_ids if cid in chunk_to_post]


def _ndcg_at_k(retrieved: list[int], relevant: set[int], k: int = 10) -> float:
    """Compute nDCG@k.

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        relevant: Set of relevant doc IDs.
        k: Cutoff.

    Returns:
        nDCG@k score in [0, 1].
    """
    import math

    def dcg(ids: list[int], rel: set[int], k: int) -> float:
        score = 0.0
        for rank, doc_id in enumerate(ids[:k], start=1):
            if doc_id in rel:
                score += 1.0 / math.log2(rank + 1)
        return score

    actual_dcg = dcg(retrieved, relevant, k)
    ideal_ids = list(relevant)[:k]
    ideal_dcg = dcg(ideal_ids, relevant, k)
    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def _mrr(retrieved: list[int], relevant: set[int]) -> float:
    """Compute Mean Reciprocal Rank (single query).

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        relevant: Set of relevant doc IDs.

    Returns:
        Reciprocal rank (0 if no relevant doc in top-10).
    """
    for rank, doc_id in enumerate(retrieved[:10], start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[int], relevant: set[int], k: int = 10) -> float:
    """Compute Recall@k.

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        relevant: Set of relevant doc IDs.
        k: Cutoff.

    Returns:
        Recall@k in [0, 1].
    """
    if not relevant:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / len(relevant)


def _search_via_http(
    query_text: str,
    api_base: str,
    system: str = "hybrid",
    k: int = 10,
    timeout: int = 30,
) -> list[int]:
    """Run a search query against the nox-mem HTTP API.

    The nox-mem /api/search endpoint accepts:
        POST /api/search
        Content-Type: application/json
        {"query": "...", "limit": 10, "mode": "hybrid"|"fts"|"semantic"}

    Args:
        query_text: The search query string.
        api_base: Base URL of the nox-mem API (e.g. "http://127.0.0.1:18802").
        system: Search mode — "hybrid", "fts", or "semantic".
        k: Number of results to request.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of chunk IDs (internal nox-mem integers) in ranked order.
    """
    import urllib.error

    url = f"{api_base}/api/search"
    payload = json.dumps({
        "query": query_text,
        "limit": k,
        "mode": system,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP %d for query %r: %s", exc.code, query_text[:50], exc)
        return []
    except Exception as exc:
        logger.warning("Search failed for query %r: %s", query_text[:50], exc)
        return []

    # nox-mem /api/search returns: {"results": [{"id": int, "score": float, ...}, ...]}
    results = data.get("results", [])
    return [int(r["id"]) for r in results if "id" in r]


def evaluate_all(
    queries: list[EvalQuery],
    db_path: Path,
    api_base: str,
    system: str = "hybrid",
    k: int = 10,
) -> list[EvalResult]:
    """Evaluate all queries against nox-mem and compute IR metrics.

    For each query:
    1. POST to /api/search → list of chunk IDs (nox-mem internal)
    2. Map chunk IDs → SE post IDs via se_post_map
    3. Compute nDCG@10, MRR, Recall@10 against expected_doc_ids

    Args:
        queries: List of EvalQuery objects from curate_queries().
        db_path: Path to the SQLite DB containing se_post_map.
        api_base: nox-mem HTTP API base URL.
        system: Search mode ("hybrid", "fts", "semantic").
        k: Evaluation cutoff.

    Returns:
        List of EvalResult objects (one per query).
    """
    conn = sqlite3.connect(str(db_path))
    results: list[EvalResult] = []

    for idx, query in enumerate(queries, start=1):
        logger.debug(
            "[%d/%d] Searching: %r (expected: %s)",
            idx,
            len(queries),
            query.query_text[:60],
            query.expected_doc_ids,
        )

        chunk_ids = _search_via_http(query.query_text, api_base, system=system, k=k)
        post_ids = _chunk_ids_to_post_ids(chunk_ids, conn)

        relevant = set(query.expected_doc_ids)
        ndcg = _ndcg_at_k(post_ids, relevant, k=k)
        mrr = _mrr(post_ids, relevant)
        recall = _recall_at_k(post_ids, relevant, k=k)

        results.append(
            EvalResult(
                query_id=query.query_id,
                query_text=query.query_text,
                retrieved_ids=post_ids,
                relevant_ids=relevant,
                ndcg_at_10=ndcg,
                mrr=mrr,
                recall_at_10=recall,
            )
        )

        if idx % 10 == 0:
            running_ndcg = sum(r.ndcg_at_10 for r in results) / len(results)
            logger.info(
                "Progress: %d/%d queries, running nDCG@10=%.3f",
                idx, len(queries), running_ndcg,
            )

    conn.close()
    logger.info(
        "Eval complete: %d queries, mean nDCG@10=%.3f, MRR=%.3f, Recall@10=%.3f",
        len(results),
        sum(r.ndcg_at_10 for r in results) / len(results),
        sum(r.mrr for r in results) / len(results),
        sum(r.recall_at_10 for r in results) / len(results),
    )
    return results


def save_results_jsonl(results: list[EvalResult], path: Path) -> None:
    """Write eval results to JSONL.

    Args:
        results: List of EvalResult objects.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(
                json.dumps(
                    {
                        "query_id": r.query_id,
                        "query_text": r.query_text,
                        "retrieved_ids": r.retrieved_ids,
                        "relevant_ids": list(r.relevant_ids),
                        "ndcg_at_10": r.ndcg_at_10,
                        "mrr": r.mrr,
                        "recall_at_10": r.recall_at_10,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    logger.info("Saved %d results to %s", len(results), path)


def save_summary_json(results: list[EvalResult], path: Path, system: str, sites: list[str]) -> None:
    """Write aggregate summary JSON for the paper table.

    Args:
        results: Full list of EvalResult objects.
        path: Output path for eval-summary.json.
        system: Search system name used.
        sites: List of sites evaluated.
    """
    n = len(results)
    if n == 0:
        logger.warning("No results to summarise")
        return

    summary = {
        "corpus": "Stack Exchange 10K (3 sites)",
        "sites": sites,
        "system": system,
        "n_queries": n,
        "ndcg_at_10": round(sum(r.ndcg_at_10 for r in results) / n, 4),
        "mrr": round(sum(r.mrr for r in results) / n, 4),
        "recall_at_10": round(sum(r.recall_at_10 for r in results) / n, 4),
        "per_query": [
            {
                "query_id": r.query_id,
                "ndcg_at_10": round(r.ndcg_at_10, 4),
                "mrr": round(r.mrr, 4),
                "recall_at_10": round(r.recall_at_10, 4),
            }
            for r in results
        ],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    logger.info(
        "Summary: nDCG@10=%.4f MRR=%.4f Recall@10=%.4f → %s",
        summary["ndcg_at_10"],
        summary["mrr"],
        summary["recall_at_10"],
        path,
    )


# ---------------------------------------------------------------------------
# 6. Main pipeline
# ---------------------------------------------------------------------------

DEFAULT_SITES = [
    "cooking.stackexchange.com",
    "scifi.stackexchange.com",
    "superuser.com",
]


def run_pipeline(
    sites: list[str],
    output_dir: Path,
    db_path: Path,
    sample_n: int = 10_000,
    min_score: int = 2,
    queries_n: int = 50,
    system: str = "hybrid",
    api_base: str = "http://127.0.0.1:18802",
    skip_download: bool = False,
    skip_eval: bool = False,
    seed: int = 42,
) -> None:
    """Run the full Stack Exchange evaluation pipeline.

    Phases:
    1. Download dumps (one per site)
    2. Extract Posts.xml from each .7z
    3. Parse and filter posts (streaming, min_score filter)
    4. Ingest all posts into a shared SQLite chunks DB
    5. Curate 50 evaluation queries (stratified across sites)
    6. Evaluate via nox-mem HTTP API
    7. Save results + summary

    Args:
        sites: List of SE site domains to download.
        output_dir: Working directory for downloads and extractions.
        db_path: Path to the output chunks SQLite database.
        sample_n: Total post sample across all sites (split equally).
        min_score: Minimum post Score filter.
        queries_n: Number of evaluation queries to generate.
        system: nox-mem search mode ("hybrid", "fts", "semantic").
        api_base: nox-mem HTTP API base URL.
        skip_download: If True, assume archives are already in output_dir.
        skip_eval: If True, stop after ingest + query curation (no HTTP eval).
        seed: Random seed.
    """
    per_site_n = max(1, sample_n // len(sites))
    logger.info(
        "Pipeline: %d sites, %d posts/site, min_score=%d, queries_n=%d",
        len(sites), per_site_n, min_score, queries_n,
    )

    all_posts: list[SEPost] = []

    for site in sites:
        site_dir = output_dir / site.replace(".", "_")
        site_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1: Download
        if not skip_download:
            archive_path = download_dump(site, site_dir)
        else:
            archive_path = site_dir / f"{site}.7z"
            if not archive_path.exists():
                logger.warning("Archive not found, attempting download: %s", archive_path)
                archive_path = download_dump(site, site_dir)

        # Phase 2: Extract
        posts_xml = extract_dump(archive_path, site_dir)

        # Phase 3: Parse
        site_posts = parse_posts_xml(
            posts_xml,
            site=site,
            sample_n=per_site_n,
            min_score=min_score,
            seed=seed,
        )
        all_posts.extend(site_posts)
        logger.info("Site %s: %d posts loaded", site, len(site_posts))

    logger.info("Total posts across all sites: %d", len(all_posts))

    # Phase 4: Ingest
    n_inserted = posts_to_chunks_db(all_posts, db_path)
    logger.info("Chunks DB ready: %d rows in %s", n_inserted, db_path)

    # Phase 5: Curate queries
    queries = curate_queries(all_posts, n=queries_n, seed=seed)
    queries_path = output_dir / "queries.jsonl"
    save_queries_jsonl(queries, queries_path)

    if skip_eval:
        logger.info("--skip-eval set: stopping before HTTP eval. DB and queries saved.")
        return

    # Phase 6: Evaluate
    results = evaluate_all(queries, db_path, api_base=api_base, system=system)

    # Phase 7: Save
    results_path = output_dir / "results.jsonl"
    save_results_jsonl(results, results_path)

    summary_path = output_dir / "eval-summary.json"
    save_summary_json(results, summary_path, system=system, sites=sites)

    logger.info("Pipeline complete. Outputs:")
    logger.info("  DB:       %s", db_path)
    logger.info("  Queries:  %s", queries_path)
    logger.info("  Results:  %s", results_path)
    logger.info("  Summary:  %s", summary_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stackexchange_adapter",
        description=(
            "Download, parse, ingest, and evaluate Stack Exchange dumps "
            "for nox-mem cross-corpus evaluation (E5)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sites",
        nargs="+",
        default=DEFAULT_SITES,
        metavar="SITE",
        help=(
            "Stack Exchange site domains to download. "
            "Defaults to cooking + scifi + superuser (3-site diversity set)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("STACKEXCHANGE_TEMP_DIR", "/tmp/se-eval")),
        help="Directory for downloads, extractions, and results.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("STACKEXCHANGE_TEMP_DB", "/tmp/se-eval/chunks.db")),
        metavar="PATH",
        help="Output SQLite database path.",
    )
    parser.add_argument(
        "--sample-n",
        type=int,
        default=10_000,
        help="Total number of posts to sample across all sites.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=2,
        help="Minimum SE post Score to include (quality filter).",
    )
    parser.add_argument(
        "--queries-n",
        type=int,
        default=50,
        help="Number of evaluation queries to curate.",
    )
    parser.add_argument(
        "--system",
        choices=["hybrid", "fts", "semantic"],
        default="hybrid",
        help="nox-mem search mode to evaluate.",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("NOX_API_BASE", "http://127.0.0.1:18802"),
        help="nox-mem HTTP API base URL.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Assume archives are already present in output-dir. Skip download.",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help=(
            "Stop after ingest + query curation. "
            "Use this to prepare the corpus without running the nox-mem API."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling and stratification.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity.",
    )
    return parser


if __name__ == "__main__":
    _parser = _build_arg_parser()
    _args = _parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, _args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_pipeline(
        sites=_args.sites,
        output_dir=_args.output_dir,
        db_path=_args.db,
        sample_n=_args.sample_n,
        min_score=_args.min_score,
        queries_n=_args.queries_n,
        system=_args.system,
        api_base=_args.api_base,
        skip_download=_args.skip_download,
        skip_eval=_args.skip_eval,
        seed=_args.seed,
    )
