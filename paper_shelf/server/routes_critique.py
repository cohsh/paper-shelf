from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from paper_shelf import critique, library
from paper_shelf.exceptions import ClaudeReaderError, StorageError
from paper_shelf.server.tasks import run_critique_pipeline

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/papers/{paper_id}/critique")
def start_critique(paper_id: str, request: Request) -> dict:
    """Start async critique generation for a paper."""
    output_dir = request.app.state.output_dir
    task_manager = request.app.state.task_manager

    # Verify paper exists
    try:
        library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    task_id = task_manager.create_task()
    thread = threading.Thread(
        target=run_critique_pipeline,
        args=(task_id, task_manager, paper_id, output_dir),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/papers/{paper_id}/critique")
def get_critique(paper_id: str, request: Request) -> dict:
    """Get saved critique for a paper."""
    output_dir = request.app.state.output_dir
    try:
        paper = library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    critique_data = paper.get("critique")
    if not critique_data:
        raise HTTPException(status_code=404, detail="Critique not generated yet")

    return critique_data


@router.post("/papers/{paper_id}/chat")
def chat(paper_id: str, body: ChatRequest, request: Request) -> dict:
    """Send a chat message about a paper."""
    output_dir = request.app.state.output_dir
    try:
        paper = library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    readings = paper.get("readings", {})
    critique_data = paper.get("critique", {})

    # Get paper text from PDF
    paper_text = library.get_paper_text(paper_id, output_dir)

    # Build message history including new message
    messages = list(body.history)
    messages.append({"role": "user", "content": body.message})

    try:
        reply = critique.generate_chat_response(
            paper_text=paper_text,
            readings=readings,
            critique=critique_data,
            messages=messages,
        )
        return {"reply": reply}
    except ClaudeReaderError as e:
        raise HTTPException(status_code=500, detail=str(e))
