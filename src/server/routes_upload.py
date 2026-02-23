from __future__ import annotations

import os
import shutil
import tempfile
import threading
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, UploadFile

from src.server.tasks import TaskManager, run_reading_pipeline

router = APIRouter()


@router.post("/upload")
async def upload_paper(
    request: Request,
    file: UploadFile,
    reader: str = "both",
    shelves: str = "",
) -> dict:
    if reader not in ("claude", "codex", "both"):
        raise HTTPException(status_code=400, detail="reader must be claude, codex, or both")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(
        suffix=".pdf", prefix="upload_", delete=False
    ) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    shelf_list = (
        [s.strip() for s in shelves.split(",") if s.strip()] if shelves else None
    )

    task_manager: TaskManager = request.app.state.task_manager
    task_id = task_manager.create_task()

    thread = threading.Thread(
        target=run_reading_pipeline,
        args=(task_id, task_manager, temp_path, reader, request.app.state.output_dir),
        kwargs={"shelves": shelf_list},
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, request: Request) -> dict:
    task_manager: TaskManager = request.app.state.task_manager
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return asdict(task)


@router.get("/tasks")
def list_tasks(request: Request) -> list[dict]:
    task_manager: TaskManager = request.app.state.task_manager
    return [asdict(t) for t in task_manager.all_tasks()]
