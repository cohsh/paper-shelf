from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from collections.abc import Callable

from src.exceptions import DiscoveryError

logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds before retrying

# Optional callback for progress updates.
_progress_callback: Callable[[str], None] | None = None


def set_progress_callback(cb: Callable[[str], None] | None) -> None:
    """Set a callback to report progress messages."""
    global _progress_callback
    _progress_callback = cb


def _notify(msg: str) -> None:
    if _progress_callback:
        _progress_callback(msg)


def _api_get(url: str) -> dict:
    """Make a GET request to the OpenAlex API with retry."""
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PaperShelf/1.0 (mailto:paper-shelf@example.com)")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (attempt + 1)
                logger.warning("Rate limited (429), retrying in %ds (attempt %d/%d)", delay, attempt + 1, MAX_RETRIES)
                _notify(f"Rate limited. Retrying in {delay}s...")
                import time
                time.sleep(delay)
                continue
            raise DiscoveryError(f"OpenAlex API error ({e.code}): {e.reason}")
        except urllib.error.URLError as e:
            raise DiscoveryError(f"Failed to connect to OpenAlex: {e.reason}")
        except TimeoutError:
            raise DiscoveryError("OpenAlex API request timed out")
    raise DiscoveryError("Unexpected error in API request")


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def _normalize_paper(work: dict) -> dict:
    """Normalize an OpenAlex work record to our format."""
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append(name)

    # Extract external IDs
    external_ids: dict[str, str] = {}
    doi = work.get("doi") or ""
    if doi:
        # OpenAlex returns full URL like "https://doi.org/10.1234/..."
        doi_str = doi.replace("https://doi.org/", "")
        external_ids["DOI"] = doi_str
        # Extract arXiv ID from DOI (e.g. "10.48550/arxiv.1706.03762")
        doi_lower = doi_str.lower()
        if "arxiv." in doi_lower:
            parts = doi_lower.split("arxiv.")
            if len(parts) > 1:
                external_ids["ArXiv"] = parts[1]

    ids = work.get("ids") or {}
    if ids.get("pmid"):
        external_ids["PubMed"] = ids["pmid"].replace("https://pubmed.ncbi.nlm.nih.gov/", "")
    if ids.get("openalex"):
        external_ids["OpenAlex"] = ids["openalex"].replace("https://openalex.org/", "")

    # Extract venue (journal / conference name)
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    venue = source.get("display_name") or primary_loc.get("raw_source_name") or ""

    # Check for open access URL
    oa = work.get("open_access") or {}
    url = oa.get("oa_url") or work.get("id") or ""

    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    return {
        "title": work.get("display_name") or work.get("title") or "",
        "authors": authors,
        "year": work.get("publication_year") or 0,
        "published_date": work.get("publication_date") or "",
        "abstract": abstract,
        "venue": venue,
        "url": url,
        "external_ids": external_ids,
    }


def search_papers(query: str, limit: int = 10) -> list[dict]:
    """Search for papers by keyword query."""
    encoded_query = urllib.parse.quote(query)
    url = (
        f"{OPENALEX_API}/works?search={encoded_query}"
        f"&per_page={limit}"
        f"&select=id,display_name,publication_year,publication_date,authorships,doi,ids,"
        f"primary_location,abstract_inverted_index,open_access"
    )
    logger.info("Searching OpenAlex: %s", query)

    result = _api_get(url)
    works = result.get("results") or []
    papers = [p for p in (_normalize_paper(w) for w in works) if p["title"]]
    papers.sort(key=lambda p: p["year"], reverse=True)
    return papers


def get_recommendations(paper_title: str, limit: int = 10) -> list[dict]:
    """Get related papers based on a paper title.

    Resolves the title to an OpenAlex work ID, then fetches
    the related_works for that paper.
    """
    # Step 1: Find work by title
    encoded_title = urllib.parse.quote(paper_title)
    search_url = (
        f"{OPENALEX_API}/works?search={encoded_title}"
        f"&per_page=1&select=id,display_name,related_works"
    )
    logger.info("Resolving OpenAlex work for: %s", paper_title)
    _notify("Searching for paper on OpenAlex...")

    search_result = _api_get(search_url)
    candidates = search_result.get("results") or []
    if not candidates:
        logger.warning("Could not find paper on OpenAlex: %s", paper_title)
        _notify("Paper not found, falling back to keyword search...")
        return search_papers(paper_title, limit=limit)

    work = candidates[0]
    related_ids = work.get("related_works") or []
    if not related_ids:
        logger.warning("No related_works for paper, falling back to search")
        _notify("No related papers found, falling back to keyword search...")
        return search_papers(paper_title, limit=limit)

    # Step 2: Fetch details of related works (batch by IDs)
    # Request more than needed to account for entries with empty titles
    fetch_count = min(len(related_ids), limit * 2)
    batch_ids = related_ids[:fetch_count]
    openalex_ids = [rid.replace("https://openalex.org/", "") for rid in batch_ids]
    ids_filter = "|".join(openalex_ids)
    details_url = (
        f"{OPENALEX_API}/works?filter=openalex:{ids_filter}"
        f"&per_page={fetch_count}"
        f"&select=id,display_name,publication_year,publication_date,authorships,doi,ids,"
        f"primary_location,abstract_inverted_index,open_access"
    )
    logger.info("Fetching %d related works", len(batch_ids))
    _notify("Fetching related papers...")

    details_result = _api_get(details_url)
    works = details_result.get("results") or []
    papers = [p for p in (_normalize_paper(w) for w in works) if p["title"]]
    logger.info("Got %d related works (%d with titles)", len(works), len(papers))

    if papers:
        # Keep top-N by relevance (order from OpenAlex), then sort by year
        top = papers[:limit]
        top.sort(key=lambda p: p["year"], reverse=True)
        return top

    # Fallback
    logger.warning("Related works fetch returned 0 results, falling back to search")
    _notify("Falling back to keyword search...")
    return search_papers(paper_title, limit=limit)


def discover_for_library(
    papers: list[dict], limit: int = 10, existing_titles: set[str] | None = None
) -> list[dict]:
    """Discover papers for the whole library using Claude to generate search queries.

    Args:
        papers: List of paper summaries from the library index.
        limit: Max number of results to return.
        existing_titles: Titles already in the library (for dedup).
    """
    if not papers:
        raise DiscoveryError("No papers in the library to base recommendations on")

    if existing_titles is None:
        existing_titles = {p.get("title", "").lower() for p in papers}

    # Build context from library
    paper_info_lines = []
    for p in papers[:30]:  # Limit to avoid overly long prompts
        title = p.get("title", "")
        tags = ", ".join(p.get("tags", []))
        line = f"- {title}"
        if tags:
            line += f" [{tags}]"
        paper_info_lines.append(line)

    paper_info = "\n".join(paper_info_lines)

    # Use Claude to generate search queries
    prompt = (
        "Based on the following academic paper library, generate 3-5 search queries "
        "to find related or complementary papers that would be valuable additions. "
        "Consider the research themes, methodologies, and gaps in the collection.\n\n"
        "Papers in library:\n"
        f"{paper_info}\n\n"
        "Respond with a JSON array of search query strings, nothing else. "
        'Example: ["query one", "query two", "query three"]'
    )

    queries = _generate_search_queries(prompt)
    if not queries:
        raise DiscoveryError("Failed to generate search queries")

    # Search for each query and collect results
    all_results: list[dict] = []
    seen_titles: set[str] = set()

    for query in queries:
        try:
            results = search_papers(query, limit=5)
            for paper in results:
                title_lower = paper["title"].lower()
                # Skip duplicates and papers already in library
                if title_lower in seen_titles or title_lower in existing_titles:
                    continue
                seen_titles.add(title_lower)
                all_results.append(paper)
        except DiscoveryError as e:
            logger.warning("Search query failed (%s): %s", query, e)

        if len(all_results) >= limit:
            break

    all_results.sort(key=lambda p: p["year"], reverse=True)
    return all_results[:limit]


def _generate_search_queries(prompt: str) -> list[str]:
    """Use Claude CLI to generate search queries."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="discovery_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            f"Read the file at {prompt_file} and follow the instructions in it. "
            "Respond ONLY with a JSON array of search query strings.",
            "--output-format", "json",
            "--allowedTools", "Read",
        ]

        logger.info("Running Claude CLI for query generation...")
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
            return []

        return _parse_queries(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return []
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        return []
    finally:
        os.unlink(prompt_file)


def _parse_queries(stdout: str) -> list[str]:
    """Parse Claude CLI output to extract a list of search queries."""
    # Try parsing the JSON output directly
    try:
        response = json.loads(stdout)
        if isinstance(response, dict) and "result" in response:
            text = response["result"]
        elif isinstance(response, list):
            return [q for q in response if isinstance(q, str)]
        else:
            text = stdout
    except json.JSONDecodeError:
        text = stdout

    # Try extracting JSON array from text
    try:
        queries = json.loads(text)
        if isinstance(queries, list):
            return [q for q in queries if isinstance(q, str)]
    except (json.JSONDecodeError, TypeError):
        pass

    # Try finding JSON array in text
    bracket_start = text.find("[") if isinstance(text, str) else -1
    if bracket_start >= 0:
        bracket_end = text.rfind("]")
        if bracket_end > bracket_start:
            try:
                queries = json.loads(text[bracket_start:bracket_end + 1])
                if isinstance(queries, list):
                    return [q for q in queries if isinstance(q, str)]
            except json.JSONDecodeError:
                pass

    return []
