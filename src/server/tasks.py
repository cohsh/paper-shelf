from __future__ import annotations

import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: str
    status: str = "pending"
    progress_message: str = "Queued"
    paper_id: str | None = None
    error: str | None = None
    started_at: str = ""
    completed_at: str | None = None


class TaskManager:
    """In-memory task tracker. Thread-safe via GIL."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        self._tasks[task_id] = Task(
            task_id=task_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        return task_id

    def update(self, task_id: str, **kwargs: object) -> None:
        task = self._tasks.get(task_id)
        if task:
            for k, v in kwargs.items():
                setattr(task, k, v)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())


def run_reading_pipeline(
    task_id: str,
    task_manager: TaskManager,
    pdf_path: str,
    reader_choice: str,
    output_dir: str,
    shelves: list[str] | None = None,
) -> None:
    """Run the full extract -> read -> save pipeline in a background thread."""
    from src import library, pdf_extractor, reader_claude, reader_codex, storage
    from src.exceptions import PaperReaderError

    try:
        task_manager.update(
            task_id, status="extracting", progress_message="Extracting text from PDF..."
        )
        paper = pdf_extractor.extract(pdf_path)

        results: dict[str, dict] = {}

        if reader_choice in ("claude", "both"):
            task_manager.update(
                task_id,
                status="reading_claude",
                progress_message="Claude is reading the paper...",
            )
            try:
                results["claude"] = reader_claude.read(paper)
            except PaperReaderError as e:
                logger.error("Claude reader failed: %s", e)
                if reader_choice == "claude":
                    raise

        if reader_choice in ("codex", "both"):
            task_manager.update(
                task_id,
                status="reading_codex",
                progress_message="Codex is reading the paper...",
            )
            try:
                results["codex"] = reader_codex.read(paper)
            except PaperReaderError as e:
                logger.error("Codex reader failed: %s", e)
                if reader_choice == "codex":
                    raise

        if not results:
            raise PaperReaderError("No reader produced results")

        task_manager.update(
            task_id, status="saving", progress_message="Saving results..."
        )
        paper_id = storage.save(
            results, paper.metadata, output_dir, paper.source_path, paper.page_count,
            paper_text=paper.text,
        )
        library.update_index(paper_id, output_dir, shelves=shelves)

        task_manager.update(
            task_id,
            status="completed",
            progress_message="Done!",
            paper_id=paper_id,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Reading pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def run_critique_pipeline(
    task_id: str,
    task_manager: TaskManager,
    paper_id: str,
    output_dir: str,
) -> None:
    """Run the critique generation pipeline in a background thread."""
    from src import critique as critique_mod
    from src import library

    try:
        task_manager.update(
            task_id,
            status="analyzing",
            progress_message="Generating critical analysis...",
            paper_id=paper_id,
        )

        paper = library.get_paper(paper_id, output_dir)
        paper_text = library.get_paper_text(paper_id, output_dir)
        readings = paper.get("readings", {})

        result = critique_mod.generate_critique(paper_text, readings)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()

        # Save critique to paper JSON
        paper["critique"] = result
        library.save_paper(paper_id, paper, output_dir)

        task_manager.update(
            task_id,
            status="completed",
            progress_message="Critique complete!",
            paper_id=paper_id,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Critique pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


def run_discovery_pipeline(
    task_id: str,
    task_manager: TaskManager,
    paper_id: str,
    output_dir: str,
) -> None:
    """Run discovery of related papers in a background thread."""
    from src import discovery, library

    try:
        task_manager.update(
            task_id,
            status="discovering",
            progress_message="Finding related papers...",
            paper_id=paper_id,
        )

        # Wire up progress callback so rate-limit waits appear in the UI
        def _on_progress(msg: str) -> None:
            task_manager.update(task_id, progress_message=msg)

        discovery.set_progress_callback(_on_progress)

        paper = library.get_paper(paper_id, output_dir)
        title = paper.get("title", "")
        if not title:
            raise Exception("Paper has no title")

        results = discovery.get_recommendations(title, limit=20)

        result_data = {
            "papers": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save to paper JSON
        paper["discovered"] = result_data
        library.save_paper(paper_id, paper, output_dir)

        task_manager.update(
            task_id,
            status="completed",
            progress_message="Discovery complete!",
            paper_id=paper_id,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Discovery pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        discovery.set_progress_callback(None)


def run_library_discovery_pipeline(
    task_id: str,
    task_manager: TaskManager,
    output_dir: str,
    shelf_id: str | None = None,
) -> None:
    """Run paper discovery in a background thread.

    When *shelf_id* is provided, only papers on that shelf are used as
    context and results are saved per-shelf.  Otherwise, the entire
    library is used.
    """
    import json

    from src import discovery, library

    try:
        label = "shelf" if shelf_id else "library"
        task_manager.update(
            task_id,
            status="discovering",
            progress_message=f"Analyzing {label} and searching for papers...",
        )

        def _on_progress(msg: str) -> None:
            task_manager.update(task_id, progress_message=msg)

        discovery.set_progress_callback(_on_progress)

        if shelf_id:
            papers = library.list_papers_by_shelf(shelf_id, output_dir)
        else:
            index = library.load_index(output_dir)
            papers = index.get("papers", [])
        existing_titles = {p.get("title", "").lower() for p in papers}

        results = discovery.discover_for_library(
            papers, limit=20, existing_titles=existing_titles
        )

        result_data = {
            "papers": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save per-shelf or library-wide
        if shelf_id:
            discovery_path = os.path.join(output_dir, f"discovery_{shelf_id}.json")
        else:
            discovery_path = os.path.join(output_dir, "discovery.json")
        with open(discovery_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        task_manager.update(
            task_id,
            status="completed",
            progress_message="Discovery complete!",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Library discovery pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        discovery.set_progress_callback(None)


def run_feed_pipeline(
    task_id: str,
    task_manager: TaskManager,
    shelf_id: str,
    output_dir: str,
) -> None:
    """Run daily feed generation for a shelf in a background thread."""
    from src import daily_feed

    try:
        task_manager.update(
            task_id,
            status="discovering",
            progress_message="Generating feed for shelf...",
        )

        def _on_progress(msg: str) -> None:
            task_manager.update(task_id, progress_message=msg)

        daily_feed.set_progress_callback(_on_progress)

        result = daily_feed.fetch_feed(shelf_id, output_dir)

        task_manager.update(
            task_id,
            status="completed",
            progress_message=f"Feed complete! Found {len(result.get('papers', []))} papers.",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Feed pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        daily_feed.set_progress_callback(None)


def run_url_reading_pipeline(
    task_id: str,
    task_manager: TaskManager,
    url: str,
    reader_choice: str,
    output_dir: str,
    shelves: list[str] | None = None,
) -> None:
    """Download PDF from URL and run through reading pipeline."""
    import tempfile
    import urllib.error
    import urllib.request

    temp_path = ""
    try:
        task_manager.update(
            task_id,
            status="downloading",
            progress_message="Downloading PDF...",
        )

        with tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix="feed_dl_", delete=False
        ) as tmp:
            temp_path = tmp.name
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "PaperShelf/1.0")
            with urllib.request.urlopen(req, timeout=60) as resp:
                tmp.write(resp.read())

        # Delegate to existing reading pipeline (same thread).
        # run_reading_pipeline handles its own status updates and
        # cleans up the temp file in its finally block.
        run_reading_pipeline(
            task_id, task_manager, temp_path, reader_choice, output_dir,
            shelves=shelves,
        )
    except Exception as e:
        logger.error("URL reading pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        # Clean up temp file on download error
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
