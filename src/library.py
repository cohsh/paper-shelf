from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from src.exceptions import StorageError


def update_index(paper_id: str, output_dir: str) -> None:
    """Add or update a paper entry in the library index."""
    index = load_index(output_dir)
    paper_data = get_paper(paper_id, output_dir)

    entry = {
        "paper_id": paper_id,
        "title": paper_data.get("title", ""),
        "authors": paper_data.get("authors", []),
        "year": paper_data.get("year", 0),
        "read_date": paper_data.get("read_date", ""),
        "tags": paper_data.get("tags", []),
        "readers_used": paper_data.get("readers_used", []),
    }

    # Update existing or append
    papers = index["papers"]
    existing_idx = next(
        (i for i, p in enumerate(papers) if p["paper_id"] == paper_id), None
    )
    if existing_idx is not None:
        papers[existing_idx] = entry
    else:
        papers.append(entry)

    index["updated_at"] = datetime.now(timezone.utc).isoformat()

    index_path = os.path.join(output_dir, "index.json")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write index: {e}") from e


def load_index(output_dir: str) -> dict:
    """Load the library index, creating it if it doesn't exist."""
    index_path = os.path.join(output_dir, "index.json")
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupted index, start fresh
            pass

    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "papers": [],
    }


def get_paper(paper_id: str, output_dir: str) -> dict:
    """Load full JSON record for a paper."""
    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    if not os.path.exists(json_path):
        raise StorageError(f"Paper not found: {paper_id}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def search(query: str, field: str = "all", output_dir: str = "library") -> list[dict]:
    """Search papers by query string in specified field."""
    index = load_index(output_dir)
    query_lower = query.lower()
    results = []

    for entry in index["papers"]:
        if _matches(entry, query_lower, field, output_dir):
            results.append(entry)

    return results


def _matches(entry: dict, query: str, field: str, output_dir: str) -> bool:
    """Check if a paper entry matches the search query."""
    if field == "title":
        return query in entry.get("title", "").lower()
    elif field == "authors":
        return any(query in a.lower() for a in entry.get("authors", []))
    elif field == "tags":
        return any(query in t.lower() for t in entry.get("tags", []))
    elif field == "all":
        # Search index fields
        if query in entry.get("title", "").lower():
            return True
        if any(query in a.lower() for a in entry.get("authors", [])):
            return True
        if any(query in t.lower() for t in entry.get("tags", [])):
            return True
        # Also search full record
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
