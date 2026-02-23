from __future__ import annotations

import json
import logging
import os
import re
import shutil
import unicodedata
from datetime import datetime, timezone

from src.exceptions import StorageError

logger = logging.getLogger(__name__)


def save(
    results: dict[str, dict],
    metadata: dict,
    output_dir: str,
    source_path: str = "",
    page_count: int = 0,
    paper_text: str = "",
) -> str:
    """Save reading results to markdown and JSON files. Returns paper_id."""
    # Determine title from results or metadata
    title = _get_title(results, metadata)
    paper_id = generate_paper_id(title)

    json_dir = os.path.join(output_dir, "json")
    md_dir = os.path.join(output_dir, "markdown")
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(md_dir, exist_ok=True)

    # Handle filename conflicts
    paper_id = _resolve_conflict(paper_id, json_dir)

    # Build and save JSON record
    record = _build_json_record(results, metadata, paper_id, source_path, page_count)
    json_path = os.path.join(json_dir, f"{paper_id}.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write JSON file: {e}") from e

    # Render and save Markdown
    md_content = _render_markdown(record)
    md_path = os.path.join(md_dir, f"{paper_id}.md")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    except OSError as e:
        raise StorageError(f"Failed to write Markdown file: {e}") from e

    # Save source PDF
    if source_path and os.path.exists(source_path):
        pdf_dir = os.path.join(output_dir, "pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_dest = os.path.join(pdf_dir, f"{paper_id}.pdf")
        try:
            shutil.copy2(source_path, pdf_dest)
            record["source_file"] = pdf_dest
            # Update JSON with the saved PDF path
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("Failed to save source PDF: %s", e)

    # Save extracted paper text for later use (e.g. critique)
    if paper_text:
        text_dir = os.path.join(output_dir, "texts")
        os.makedirs(text_dir, exist_ok=True)
        text_path = os.path.join(text_dir, f"{paper_id}.txt")
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(paper_text)
        except OSError as e:
            logger.warning("Failed to save paper text: %s", e)

    return paper_id


def generate_paper_id(title: str) -> str:
    """Create URL-safe slug from paper title."""
    if not title:
        return "untitled"
    # Normalize unicode
    normalized = unicodedata.normalize("NFKD", title)
    # Keep only alphanumeric, spaces, hyphens
    cleaned = re.sub(r"[^\w\s-]", "", normalized).strip().lower()
    # Replace whitespace with hyphens
    slug = re.sub(r"[\s_]+", "-", cleaned)
    # Limit length
    slug = slug[:80].rstrip("-")
    return slug or "untitled"


def _resolve_conflict(paper_id: str, json_dir: str) -> str:
    """Append numeric suffix if paper_id already exists."""
    if not os.path.exists(os.path.join(json_dir, f"{paper_id}.json")):
        return paper_id
    i = 2
    while os.path.exists(os.path.join(json_dir, f"{paper_id}-{i}.json")):
        i += 1
    return f"{paper_id}-{i}"


def _get_title(results: dict[str, dict], metadata: dict) -> str:
    """Extract title from reader results or PDF metadata."""
    for reader_name in ("claude", "codex"):
        if reader_name in results and results[reader_name].get("title"):
            return results[reader_name]["title"]
    return metadata.get("title", "Untitled Paper")


def _build_json_record(
    results: dict[str, dict],
    metadata: dict,
    paper_id: str,
    source_path: str,
    page_count: int,
) -> dict:
    """Build structured JSON record for storage."""
    title = _get_title(results, metadata)

    # Get authors, year, venue from first available reader
    authors = []
    year = 0
    venue = ""
    tags = []
    for reader_name in ("claude", "codex"):
        if reader_name in results:
            r = results[reader_name]
            if not authors and r.get("authors"):
                authors = r["authors"]
            if not year and r.get("year"):
                year = r["year"]
            if not venue and r.get("venue"):
                venue = r["venue"]
            if not tags and r.get("tags"):
                tags = r["tags"]

    return {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "read_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source_file": source_path,
        "page_count": page_count,
        "tags": tags,
        "readers_used": list(results.keys()),
        "readings": results,
    }


def _render_markdown(record: dict) -> str:
    """Render combined reading results as Markdown."""
    lines = []
    lines.append(f"# {record['title']}")
    lines.append("")

    authors_str = ", ".join(record["authors"]) if record["authors"] else "Unknown"
    lines.append(f"**Authors:** {authors_str}  ")
    lines.append(f"**Year:** {record['year'] or 'Unknown'}  ")
    if record.get("venue"):
        lines.append(f"**Venue:** {record['venue']}  ")
    lines.append(f"**Read on:** {record['read_date']}  ")
    lines.append(f"**Paper ID:** {record['paper_id']}  ")
    lines.append(f"**Readers:** {', '.join(record['readers_used'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

    readings = record.get("readings", {})

    # For each reader, output a section
    for reader_name in ("claude", "codex"):
        if reader_name not in readings:
            continue
        r = readings[reader_name]
        reader_label = reader_name.capitalize()
        lines.append(f"## {reader_label}'s Reading")
        lines.append("")

        if r.get("abstract_summary"):
            lines.append("### Abstract Summary")
            lines.append(r["abstract_summary"])
            lines.append("")

        if r.get("abstract_summary_ja"):
            lines.append("### 概要 (Abstract Summary)")
            lines.append(r["abstract_summary_ja"])
            lines.append("")

        if r.get("key_contributions"):
            lines.append("### Key Contributions")
            for item in r["key_contributions"]:
                lines.append(f"- {item}")
            lines.append("")

        if r.get("key_contributions_ja"):
            lines.append("### 主要な貢献 (Key Contributions)")
            for item in r["key_contributions_ja"]:
                lines.append(f"- {item}")
            lines.append("")

        if r.get("methodology"):
            lines.append("### Methodology")
            lines.append(r["methodology"])
            lines.append("")

        if r.get("methodology_ja"):
            lines.append("### 手法 (Methodology)")
            lines.append(r["methodology_ja"])
            lines.append("")

        if r.get("main_results"):
            lines.append("### Main Results")
            lines.append(r["main_results"])
            lines.append("")

        if r.get("main_results_ja"):
            lines.append("### 主な結果 (Main Results)")
            lines.append(r["main_results_ja"])
            lines.append("")

        if r.get("limitations"):
            lines.append("### Limitations")
            for item in r["limitations"]:
                lines.append(f"- {item}")
            lines.append("")

        if r.get("limitations_ja"):
            lines.append("### 限界・課題 (Limitations)")
            for item in r["limitations_ja"]:
                lines.append(f"- {item}")
            lines.append("")

        if r.get("connections"):
            lines.append("### Connections")
            lines.append(r["connections"])
            lines.append("")

        if r.get("connections_ja"):
            lines.append("### 関連研究 (Connections)")
            lines.append(r["connections_ja"])
            lines.append("")

        if r.get("confidence_notes"):
            lines.append("### Confidence Notes")
            lines.append(r["confidence_notes"])
            lines.append("")

        lines.append("---")
        lines.append("")

    # Tags
    if record.get("tags"):
        lines.append("## Tags")
        lines.append(", ".join(f"`{tag}`" for tag in record["tags"]))
        lines.append("")

    return "\n".join(lines)
