from __future__ import annotations

import json
import os
import threading

from fastapi import APIRouter, HTTPException, Request

from paper_shelf import library
from paper_shelf.exceptions import StorageError
from paper_shelf.server.tasks import run_discovery_pipeline, run_library_discovery_pipeline

router = APIRouter()


@router.post("/papers/{paper_id}/discover")
def start_discovery(paper_id: str, request: Request) -> dict:
    """Start async discovery of related papers."""
    output_dir = request.app.state.output_dir
    task_manager = request.app.state.task_manager

    try:
        library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    task_id = task_manager.create_task()
    thread = threading.Thread(
        target=run_discovery_pipeline,
        args=(task_id, task_manager, paper_id, output_dir),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/papers/{paper_id}/discover")
def get_discovered(paper_id: str, request: Request) -> dict:
    """Get saved discovery results for a paper."""
    output_dir = request.app.state.output_dir
    try:
        paper = library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    discovered = paper.get("discovered")
    if not discovered:
        raise HTTPException(status_code=404, detail="Discovery not run yet")

    return discovered


@router.post("/discover")
def start_library_discovery(request: Request, shelf: str | None = None) -> dict:
    """Start async paper discovery.

    Pass ``?shelf=<shelf_id>`` to scope discovery to a specific shelf.
    """
    output_dir = request.app.state.output_dir
    task_manager = request.app.state.task_manager

    task_id = task_manager.create_task()
    thread = threading.Thread(
        target=run_library_discovery_pipeline,
        args=(task_id, task_manager, output_dir),
        kwargs={"shelf_id": shelf},
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/discover")
def get_library_discovery(request: Request, shelf: str | None = None) -> dict:
    """Get saved discovery results.

    Pass ``?shelf=<shelf_id>`` to get per-shelf results.
    """
    output_dir = request.app.state.output_dir
    if shelf:
        discovery_path = os.path.join(output_dir, f"discovery_{shelf}.json")
    else:
        discovery_path = os.path.join(output_dir, "discovery.json")

    if not os.path.exists(discovery_path):
        raise HTTPException(status_code=404, detail="Discovery not run yet")

    with open(discovery_path, encoding="utf-8") as f:
        return json.load(f)
