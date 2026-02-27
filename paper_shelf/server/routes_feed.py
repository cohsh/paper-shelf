from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from paper_shelf import library
from paper_shelf.exceptions import StorageError
from paper_shelf.server.tasks import run_feed_pipeline, run_url_reading_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Daily Feed
# ---------------------------------------------------------------------------


@router.post("/shelves/{shelf_id}/feed")
def start_feed_refresh(shelf_id: str, request: Request) -> dict:
    """Start async daily feed refresh for a shelf."""
    output_dir = request.app.state.output_dir
    task_manager = request.app.state.task_manager

    try:
        library.get_shelf(shelf_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Shelf not found: {shelf_id}")

    task_id = task_manager.create_task()
    thread = threading.Thread(
        target=run_feed_pipeline,
        args=(task_id, task_manager, shelf_id, output_dir),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/shelves/{shelf_id}/feed")
def get_feed(shelf_id: str, request: Request) -> dict:
    """Get saved feed results for a shelf."""
    output_dir = request.app.state.output_dir

    from paper_shelf import daily_feed

    feed = daily_feed.load_feed(shelf_id, output_dir)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not generated yet")

    return feed


# ---------------------------------------------------------------------------
# Read from URL
# ---------------------------------------------------------------------------


class ReadFromUrlRequest(BaseModel):
    url: str
    reader: str = "both"
    shelves: list[str] = []


@router.post("/read-url")
def read_from_url(body: ReadFromUrlRequest, request: Request) -> dict:
    """Download a PDF from URL and run through the reading pipeline."""
    if body.reader not in ("claude", "codex", "both"):
        raise HTTPException(
            status_code=400, detail="reader must be claude, codex, or both"
        )

    task_manager = request.app.state.task_manager
    task_id = task_manager.create_task()

    thread = threading.Thread(
        target=run_url_reading_pipeline,
        args=(
            task_id,
            task_manager,
            body.url,
            body.reader,
            request.app.state.output_dir,
        ),
        kwargs={"shelves": body.shelves if body.shelves else None},
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}
