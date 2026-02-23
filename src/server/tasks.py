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
            results, paper.metadata, output_dir, paper.source_path, paper.page_count
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
