from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from paper_shelf.exceptions import StorageError
from paper_shelf.storage import generate_paper_id

UNSORTED_SHELF_ID = "__unsorted__"
UNSORTED_SHELF_NAME = "Unsorted"
UNSORTED_SHELF_NAME_JA = "未分類"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _migrate_v1_to_v2(index: dict) -> dict:
    """Migrate a v1 index to v2 format in-place."""
    index["version"] = 2
    if "shelves" not in index:
        index["shelves"] = []
    for paper in index.get("papers", []):
        if "shelves" not in paper:
            paper["shelves"] = []
    return index


def _save_index(index: dict, output_dir: str) -> None:
    """Write the index to disk."""
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index_path = os.path.join(output_dir, "index.json")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write index: {e}") from e


def _find_paper(papers: list[dict], paper_id: str) -> dict | None:
    """Find a paper entry in the papers list by paper_id."""
    for paper in papers:
        if paper["paper_id"] == paper_id:
            return paper
    return None


# ---------------------------------------------------------------------------
# Index operations
# ---------------------------------------------------------------------------

def load_index(output_dir: str) -> dict:
    """Load the library index, creating it if it doesn't exist.

    Auto-migrates v1 indexes to v2 in memory. The migrated format is
    persisted on the next write operation.
    """
    index_path = os.path.join(output_dir, "index.json")
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
        except json.JSONDecodeError:
            index = None

        if index is not None:
            if index.get("version", 1) < 2:
                index = _migrate_v1_to_v2(index)
            return index

    return {
        "version": 2,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "shelves": [],
        "papers": [],
    }


def update_index(
    paper_id: str, output_dir: str, shelves: list[str] | None = None
) -> None:
    """Add or update a paper entry in the library index.

    If *shelves* is ``None`` and the paper already exists, the existing
    shelf assignments are preserved.  For new papers ``None`` means an
    empty list (i.e. Unsorted).
    """
    index = load_index(output_dir)
    paper_data = get_paper(paper_id, output_dir)

    entry = {
        "paper_id": paper_id,
        "title": paper_data.get("title", ""),
        "authors": paper_data.get("authors", []),
        "year": paper_data.get("year", 0),
        "published_date": paper_data.get("published_date", ""),
        "venue": paper_data.get("venue", ""),
        "read_date": paper_data.get("read_date", ""),
        "tags": paper_data.get("tags", []),
        "readers_used": paper_data.get("readers_used", []),
        "shelves": shelves if shelves is not None else [],
    }

    papers = index["papers"]
    existing_idx = next(
        (i for i, p in enumerate(papers) if p["paper_id"] == paper_id), None
    )
    if existing_idx is not None:
        if shelves is None:
            entry["shelves"] = papers[existing_idx].get("shelves", [])
        papers[existing_idx] = entry
    else:
        papers.append(entry)

    _save_index(index, output_dir)


def get_paper(paper_id: str, output_dir: str) -> dict:
    """Load full JSON record for a paper."""
    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    if not os.path.exists(json_path):
        raise StorageError(f"Paper not found: {paper_id}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def save_paper(paper_id: str, data: dict, output_dir: str) -> None:
    """Save updated paper JSON record."""
    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    if not os.path.exists(json_path):
        raise StorageError(f"Paper not found: {paper_id}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_paper_text(paper_id: str, output_dir: str) -> str:
    """Get extracted text for a paper.

    Reads from cached text file if available, otherwise falls back to
    re-extracting from the stored PDF.
    """
    # Try cached text first
    text_path = os.path.join(output_dir, "texts", f"{paper_id}.txt")
    if os.path.exists(text_path):
        with open(text_path, encoding="utf-8") as f:
            return f.read()

    # Fallback: extract from PDF
    from paper_shelf import pdf_extractor

    pdf_path = os.path.join(output_dir, "pdfs", f"{paper_id}.pdf")
    if not os.path.exists(pdf_path):
        raise StorageError(f"PDF not found: {paper_id}")
    paper = pdf_extractor.extract(pdf_path)
    return paper.text


# ---------------------------------------------------------------------------
# Search & listing
# ---------------------------------------------------------------------------

def search(
    query: str,
    field: str = "all",
    output_dir: str = "library",
    shelf: str | None = None,
) -> list[dict]:
    """Search papers by query string in specified field.

    Optionally filter by *shelf*.  Use ``UNSORTED_SHELF_ID`` to match
    papers that belong to no shelf.
    """
    index = load_index(output_dir)
    query_lower = query.lower()
    results = []

    for entry in index["papers"]:
        if shelf is not None:
            paper_shelves = entry.get("shelves", [])
            if shelf == UNSORTED_SHELF_ID:
                if paper_shelves:
                    continue
            elif shelf not in paper_shelves:
                continue
        if _matches(entry, query_lower, field, output_dir):
            results.append(entry)

    return results


def list_papers_by_shelf(
    shelf_id: str | None, output_dir: str
) -> list[dict]:
    """Return papers belonging to a specific shelf.

    ``None`` means all papers.
    """
    index = load_index(output_dir)

    if shelf_id is None:
        return index["papers"]

    papers = []
    for paper in index["papers"]:
        paper_shelves = paper.get("shelves", [])
        if shelf_id == UNSORTED_SHELF_ID:
            if not paper_shelves:
                papers.append(paper)
        elif shelf_id in paper_shelves:
            papers.append(paper)

    return papers


# ---------------------------------------------------------------------------
# Shelf CRUD
# ---------------------------------------------------------------------------

def create_shelf(
    name: str, output_dir: str, name_ja: str = ""
) -> dict:
    """Create a new shelf.  Raises ``StorageError`` on duplicate."""
    index = load_index(output_dir)
    shelf_id = generate_paper_id(name)

    if any(s["shelf_id"] == shelf_id for s in index["shelves"]):
        raise StorageError(f"Shelf already exists: {shelf_id}")

    shelf = {
        "shelf_id": shelf_id,
        "name": name,
        "name_ja": name_ja,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    index["shelves"].append(shelf)
    _save_index(index, output_dir)
    return shelf


def list_shelves(output_dir: str) -> list[dict]:
    """List all shelves with paper counts.

    The virtual *Unsorted* shelf is always included first.
    """
    index = load_index(output_dir)

    shelf_counts: dict[str, int] = {}
    unsorted_count = 0
    for paper in index["papers"]:
        paper_shelves = paper.get("shelves", [])
        if not paper_shelves:
            unsorted_count += 1
        for sid in paper_shelves:
            shelf_counts[sid] = shelf_counts.get(sid, 0) + 1

    shelves: list[dict] = [
        {
            "shelf_id": UNSORTED_SHELF_ID,
            "name": UNSORTED_SHELF_NAME,
            "name_ja": UNSORTED_SHELF_NAME_JA,
            "paper_count": unsorted_count,
            "is_virtual": True,
        }
    ]

    for s in index["shelves"]:
        shelves.append(
            {
                **s,
                "paper_count": shelf_counts.get(s["shelf_id"], 0),
                "is_virtual": False,
            }
        )

    return shelves


def get_shelf(shelf_id: str, output_dir: str) -> dict:
    """Get a single shelf by ID.  Raises ``StorageError`` if not found."""
    if shelf_id == UNSORTED_SHELF_ID:
        return {
            "shelf_id": UNSORTED_SHELF_ID,
            "name": UNSORTED_SHELF_NAME,
            "name_ja": UNSORTED_SHELF_NAME_JA,
            "is_virtual": True,
        }
    index = load_index(output_dir)
    for s in index["shelves"]:
        if s["shelf_id"] == shelf_id:
            return s
    raise StorageError(f"Shelf not found: {shelf_id}")


def rename_shelf(
    shelf_id: str,
    name: str,
    output_dir: str,
    name_ja: str | None = None,
) -> dict:
    """Rename a shelf.  Updates paper references when the ID changes."""
    if shelf_id == UNSORTED_SHELF_ID:
        raise StorageError("Cannot rename the Unsorted shelf")

    index = load_index(output_dir)
    new_shelf_id = generate_paper_id(name)

    for s in index["shelves"]:
        if s["shelf_id"] == shelf_id:
            old_id = s["shelf_id"]
            s["shelf_id"] = new_shelf_id
            s["name"] = name
            if name_ja is not None:
                s["name_ja"] = name_ja

            if old_id != new_shelf_id:
                for paper in index["papers"]:
                    paper_shelves = paper.get("shelves", [])
                    if old_id in paper_shelves:
                        paper_shelves[paper_shelves.index(old_id)] = new_shelf_id

            _save_index(index, output_dir)
            return s

    raise StorageError(f"Shelf not found: {shelf_id}")


def delete_shelf(shelf_id: str, output_dir: str) -> None:
    """Delete a shelf.  Papers lose the reference and may become Unsorted."""
    if shelf_id == UNSORTED_SHELF_ID:
        raise StorageError("Cannot delete the Unsorted shelf")

    index = load_index(output_dir)
    original_count = len(index["shelves"])
    index["shelves"] = [s for s in index["shelves"] if s["shelf_id"] != shelf_id]

    if len(index["shelves"]) == original_count:
        raise StorageError(f"Shelf not found: {shelf_id}")

    for paper in index["papers"]:
        paper_shelves = paper.get("shelves", [])
        if shelf_id in paper_shelves:
            paper_shelves.remove(shelf_id)

    _save_index(index, output_dir)


# ---------------------------------------------------------------------------
# Paper-shelf assignment
# ---------------------------------------------------------------------------

def assign_paper_to_shelves(
    paper_id: str, shelf_ids: list[str], output_dir: str
) -> None:
    """Set the shelves for a paper (replaces existing assignment)."""
    index = load_index(output_dir)

    valid_ids = {s["shelf_id"] for s in index["shelves"]}
    for sid in shelf_ids:
        if sid != UNSORTED_SHELF_ID and sid not in valid_ids:
            raise StorageError(f"Shelf not found: {sid}")

    clean_ids = [sid for sid in shelf_ids if sid != UNSORTED_SHELF_ID]

    paper = _find_paper(index["papers"], paper_id)
    if paper is None:
        raise StorageError(f"Paper not found: {paper_id}")

    paper["shelves"] = clean_ids
    _save_index(index, output_dir)


def add_paper_to_shelf(
    paper_id: str, shelf_id: str, output_dir: str
) -> None:
    """Add a single shelf to a paper without removing existing shelves."""
    index = load_index(output_dir)

    if shelf_id != UNSORTED_SHELF_ID:
        if not any(s["shelf_id"] == shelf_id for s in index["shelves"]):
            raise StorageError(f"Shelf not found: {shelf_id}")

    paper = _find_paper(index["papers"], paper_id)
    if paper is None:
        raise StorageError(f"Paper not found: {paper_id}")

    shelves = paper.get("shelves", [])
    if shelf_id not in shelves:
        shelves.append(shelf_id)
        paper["shelves"] = shelves

    _save_index(index, output_dir)


def remove_paper_from_shelf(
    paper_id: str, shelf_id: str, output_dir: str
) -> None:
    """Remove a single shelf from a paper."""
    index = load_index(output_dir)

    paper = _find_paper(index["papers"], paper_id)
    if paper is None:
        raise StorageError(f"Paper not found: {paper_id}")

    shelves = paper.get("shelves", [])
    if shelf_id in shelves:
        shelves.remove(shelf_id)
    paper["shelves"] = shelves

    _save_index(index, output_dir)


# ---------------------------------------------------------------------------
# Internal search helper
# ---------------------------------------------------------------------------

def _matches(entry: dict, query: str, field: str, output_dir: str) -> bool:
    """Check if a paper entry matches the search query."""
    if field == "title":
        return query in entry.get("title", "").lower()
    elif field == "authors":
        return any(query in a.lower() for a in entry.get("authors", []))
    elif field == "tags":
        return any(query in t.lower() for t in entry.get("tags", []))
    elif field == "all":
        if query in entry.get("title", "").lower():
            return True
        if any(query in a.lower() for a in entry.get("authors", [])):
            return True
        if any(query in t.lower() for t in entry.get("tags", [])):
            return True
        try:
            full = get_paper(entry["paper_id"], output_dir)
            readings = full.get("readings", {})
            for reader_data in readings.values():
                for v in reader_data.values():
                    if isinstance(v, str) and query in v.lower():
                        return True
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and query in item.lower():
                                return True
        except StorageError:
            pass
    return False
