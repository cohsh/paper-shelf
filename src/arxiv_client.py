from __future__ import annotations

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from src.exceptions import DiscoveryError

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 3  # seconds between requests per arXiv guidelines

_last_request_time: float = 0.0

# XML namespaces
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def _rate_limit() -> None:
    """Enforce 3-second gap between arXiv API requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _api_get(url: str) -> str:
    """Make a GET request to arXiv API, returning raw XML string."""
    _rate_limit()
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "PaperShelf/1.0")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise DiscoveryError(f"arXiv API error ({e.code}): {e.reason}") from e
    except urllib.error.URLError as e:
        raise DiscoveryError(f"Failed to connect to arXiv: {e.reason}") from e
    except TimeoutError as e:
        raise DiscoveryError("arXiv API request timed out") from e


def _parse_feed(xml_text: str) -> list[dict]:
    """Parse Atom XML feed into normalized paper dicts."""
    root = ET.fromstring(xml_text)

    papers = []
    for entry in root.findall(f"{_ATOM_NS}entry"):
        title_el = entry.find(f"{_ATOM_NS}title")
        title = (
            title_el.text.strip().replace("\n", " ")
            if title_el is not None and title_el.text
            else ""
        )
        if not title:
            continue

        # Authors
        authors = []
        for author_el in entry.findall(f"{_ATOM_NS}author"):
            name_el = author_el.find(f"{_ATOM_NS}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        # Abstract / summary
        summary_el = entry.find(f"{_ATOM_NS}summary")
        abstract = (
            summary_el.text.strip().replace("\n", " ")
            if summary_el is not None and summary_el.text
            else ""
        )

        # Published date -> year
        published_el = entry.find(f"{_ATOM_NS}published")
        published = ""
        year = 0
        if published_el is not None and published_el.text:
            published = published_el.text.strip()
            try:
                year = int(published[:4])
            except (ValueError, IndexError):
                pass

        # Entry URL and arXiv ID
        entry_url = ""
        id_el = entry.find(f"{_ATOM_NS}id")
        if id_el is not None and id_el.text:
            entry_url = id_el.text.strip()

        arxiv_id = ""
        if entry_url:
            parts = entry_url.split("/abs/")
            if len(parts) == 2:
                arxiv_id = parts[1].split("v")[0]

        # Primary category as venue
        primary_cat_el = entry.find(f"{_ARXIV_NS}primary_category")
        venue = ""
        if primary_cat_el is not None:
            venue = primary_cat_el.get("term", "")
        if not venue:
            venue = "arXiv"

        # External IDs
        external_ids: dict[str, str] = {}
        if arxiv_id:
            external_ids["ArXiv"] = arxiv_id

        doi_el = entry.find(f"{_ARXIV_NS}doi")
        if doi_el is not None and doi_el.text:
            external_ids["DOI"] = doi_el.text.strip()

        papers.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "abstract": abstract,
                "venue": venue,
                "url": entry_url,
                "external_ids": external_ids,
                "arxiv_id": arxiv_id,
                "published": published,
            }
        )

    return papers


def search_recent(query: str, max_results: int = 20) -> list[dict]:
    """Search arXiv for recent papers matching a query string.

    The query can include category filters like ``cat:cond-mat``
    and keyword filters like ``abs:superconductivity``.
    """
    encoded_query = urllib.parse.quote(query, safe=":()+")
    url = (
        f"{ARXIV_API}?search_query={encoded_query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&start=0&max_results={max_results}"
    )

    logger.info("Searching arXiv: %s", query)
    xml_text = _api_get(url)
    return _parse_feed(xml_text)


def search_by_category_and_keywords(
    categories: list[str],
    keywords: list[str],
    max_results: int = 20,
) -> list[dict]:
    """Search arXiv with a combination of categories and keywords."""
    parts = []
    if categories:
        cat_query = "+OR+".join(f"cat:{cat}" for cat in categories)
        if len(categories) > 1:
            parts.append(f"({cat_query})")
        else:
            parts.append(cat_query)

    if keywords:
        kw_parts = []
        for kw in keywords:
            safe_kw = kw.replace('"', "")
            kw_parts.append(f"abs:{safe_kw}")
        kw_query = "+OR+".join(kw_parts)
        if len(keywords) > 1:
            parts.append(f"({kw_query})")
        else:
            parts.append(kw_query)

    if not parts:
        return []

    search_query = "+AND+".join(parts)
    return search_recent(search_query, max_results=max_results)


def get_pdf_url(arxiv_id: str) -> str:
    """Get the PDF download URL for an arXiv paper."""
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
