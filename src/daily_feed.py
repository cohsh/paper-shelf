from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone

from src import arxiv_client, discovery, library
from src.exceptions import DiscoveryError

logger = logging.getLogger(__name__)

# Optional callback for progress updates.
_progress_callback: Callable[[str], None] | None = None


def set_progress_callback(cb: Callable[[str], None] | None) -> None:
    """Set a callback to report progress messages."""
    global _progress_callback
    _progress_callback = cb


def _notify(msg: str) -> None:
    if _progress_callback:
        _progress_callback(msg)


def generate_feed_queries(shelf_id: str, output_dir: str) -> dict:
    """Use Claude CLI to generate arXiv categories + keywords for a shelf.

    Returns:
        ``{"categories": [...], "keywords": [...]}``
    """
    context = _build_shelf_context(shelf_id, output_dir)

    prompt = (
        "Based on the following academic paper shelf, generate appropriate "
        "arXiv search parameters to find recent relevant papers.\n\n"
        f"{context}\n\n"
        "Respond with a JSON object containing:\n"
        '- "categories": array of arXiv category codes '
        '(e.g., "cond-mat.str-el", "quant-ph", "cs.AI")\n'
        '- "keywords": array of 3-5 specific search keywords/phrases '
        "relevant to this shelf\n\n"
        "Example response:\n"
        '{"categories": ["cond-mat.str-el", "cond-mat.mes-hall"], '
        '"keywords": ["topological insulator", "spin-orbit coupling", '
        '"Mott transition"]}\n\n'
        "Respond with ONLY the JSON object, nothing else."
    )

    _notify("Generating search queries for shelf...")
    return _run_claude_for_queries(prompt)


def fetch_feed(
    shelf_id: str,
    output_dir: str,
    max_results: int = 30,
) -> dict:
    """Fetch daily feed for a shelf. Returns feed data dict."""
    # Step 1: Generate queries
    _notify("Analyzing shelf to generate search queries...")
    queries = generate_feed_queries(shelf_id, output_dir)

    categories = queries.get("categories", [])
    keywords = queries.get("keywords", [])

    if not categories and not keywords:
        raise DiscoveryError("Could not generate search parameters for this shelf")

    # Step 2: Search arXiv (primary)
    _notify("Searching arXiv for recent papers...")
    arxiv_papers: list[dict] = []
    try:
        arxiv_papers = arxiv_client.search_by_category_and_keywords(
            categories, keywords, max_results=max_results
        )
    except DiscoveryError as e:
        logger.warning("arXiv search failed: %s", e)

    # Step 3: Search OpenAlex (secondary)
    _notify("Searching OpenAlex for recent publications...")
    openalex_papers: list[dict] = []
    for kw in keywords[:3]:
        try:
            results = discovery.search_papers(kw, limit=5)
            openalex_papers.extend(results)
        except DiscoveryError as e:
            logger.warning("OpenAlex search failed for '%s': %s", kw, e)

    # Step 4: Deduplicate
    _notify("Merging and deduplicating results...")
    merged = _deduplicate(arxiv_papers, openalex_papers)

    # Step 5: Exclude papers already in the shelf
    existing_titles: set[str] = set()
    try:
        shelf_papers = library.list_papers_by_shelf(shelf_id, output_dir)
        existing_titles = {
            p.get("title", "").lower().strip() for p in shelf_papers
        }
    except Exception:
        pass

    filtered = [
        p for p in merged if p["title"].lower().strip() not in existing_titles
    ]

    # Translate abstracts to Japanese
    _notify("Translating abstracts...")
    from src.translate import translate_abstracts
    filtered = translate_abstracts(filtered[:max_results])

    feed_data = {
        "shelf_id": shelf_id,
        "papers": filtered[:max_results],
        "queries": queries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_counts": {
            "arxiv": len(arxiv_papers),
            "openalex": len(openalex_papers),
            "merged": len(filtered),
        },
    }

    # Step 6: Save
    save_feed(shelf_id, feed_data, output_dir)
    return feed_data


def save_feed(shelf_id: str, feed_data: dict, output_dir: str) -> None:
    """Save feed results to ``library/feeds/{shelf_id}.json``."""
    feeds_dir = os.path.join(output_dir, "feeds")
    os.makedirs(feeds_dir, exist_ok=True)

    feed_path = os.path.join(feeds_dir, f"{shelf_id}.json")
    with open(feed_path, "w", encoding="utf-8") as f:
        json.dump(feed_data, f, ensure_ascii=False, indent=2)


def load_feed(shelf_id: str, output_dir: str) -> dict | None:
    """Load saved feed for a shelf. Returns ``None`` if not found."""
    feed_path = os.path.join(output_dir, "feeds", f"{shelf_id}.json")
    if not os.path.exists(feed_path):
        return None

    with open(feed_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_shelf_context(shelf_id: str, output_dir: str) -> str:
    """Build context string from a shelf's papers for query generation."""
    shelf = library.get_shelf(shelf_id, output_dir)
    shelf_name = shelf.get("name", "")
    papers = library.list_papers_by_shelf(shelf_id, output_dir)

    lines = [f"Shelf name: {shelf_name}"]
    if shelf.get("name_ja"):
        lines.append(f"Shelf name (Japanese): {shelf['name_ja']}")

    lines.append(f"\nPapers on this shelf ({len(papers)} total):")
    for p in papers[:20]:
        title = p.get("title", "")
        tags = ", ".join(p.get("tags", []))
        line = f"- {title}"
        if tags:
            line += f" [{tags}]"
        lines.append(line)

    return "\n".join(lines)


def _run_claude_for_queries(prompt: str) -> dict:
    """Call Claude CLI and parse structured query output."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="feed_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            f"Read the file at {prompt_file} and follow the instructions in it. "
            "Respond ONLY with a JSON object.",
            "--output-format",
            "json",
            "--allowedTools",
            "Read",
        ]

        logger.info("Running Claude CLI for feed query generation...")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        if result.returncode != 0:
            logger.error("Claude CLI failed: %s", result.stderr)
            return {"categories": [], "keywords": []}

        return _parse_query_result(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return {"categories": [], "keywords": []}
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        return {"categories": [], "keywords": []}
    finally:
        os.unlink(prompt_file)


def _parse_query_result(stdout: str) -> dict:
    """Parse Claude CLI output to extract categories and keywords."""
    try:
        response = json.loads(stdout)
        if isinstance(response, dict) and "result" in response:
            text = response["result"]
        elif isinstance(response, dict) and "categories" in response:
            return {
                "categories": [
                    c for c in response.get("categories", []) if isinstance(c, str)
                ],
                "keywords": [
                    k for k in response.get("keywords", []) if isinstance(k, str)
                ],
            }
        else:
            text = stdout
    except json.JSONDecodeError:
        text = stdout

    # Try extracting JSON object from text
    if isinstance(text, str):
        brace_start = text.find("{")
        if brace_start >= 0:
            brace_end = text.rfind("}")
            if brace_end > brace_start:
                try:
                    obj = json.loads(text[brace_start : brace_end + 1])
                    if isinstance(obj, dict):
                        return {
                            "categories": [
                                c
                                for c in obj.get("categories", [])
                                if isinstance(c, str)
                            ],
                            "keywords": [
                                k
                                for k in obj.get("keywords", [])
                                if isinstance(k, str)
                            ],
                        }
                except json.JSONDecodeError:
                    pass

    return {"categories": [], "keywords": []}


def _deduplicate(
    arxiv_papers: list[dict],
    openalex_papers: list[dict],
) -> list[dict]:
    """Merge two paper lists, deduplicating by title and DOI."""
    seen_titles: set[str] = set()
    seen_dois: set[str] = set()
    merged: list[dict] = []

    # arXiv papers take priority
    for p in arxiv_papers:
        title_key = p["title"].lower().strip()
        doi = p.get("external_ids", {}).get("DOI", "")

        if title_key in seen_titles:
            continue
        if doi and doi in seen_dois:
            continue

        seen_titles.add(title_key)
        if doi:
            seen_dois.add(doi)
        merged.append(p)

    # Add OpenAlex papers that are not duplicates
    for p in openalex_papers:
        title_key = p["title"].lower().strip()
        doi = p.get("external_ids", {}).get("DOI", "")

        if title_key in seen_titles:
            continue
        if doi and doi in seen_dois:
            continue

        seen_titles.add(title_key)
        if doi:
            seen_dois.add(doi)
        merged.append(p)

    # Sort by year descending
    merged.sort(key=lambda p: p.get("year", 0), reverse=True)
    return merged
