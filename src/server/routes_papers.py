from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src import library
from src.exceptions import StorageError

router = APIRouter()


@router.get("/papers")
def list_papers(
    request: Request,
    sort_by: str = "date",
    search: str | None = None,
    field: str = "all",
    shelf: str | None = None,
) -> dict:
    output_dir = request.app.state.output_dir

    if search:
        papers = library.search(search, field=field, output_dir=output_dir, shelf=shelf)
    else:
        papers = library.list_papers_by_shelf(shelf, output_dir)

    if sort_by == "title":
        papers.sort(key=lambda p: p.get("title", "").lower())
    elif sort_by == "date":
        papers.sort(key=lambda p: p.get("read_date", ""), reverse=True)
    elif sort_by == "year":
        papers.sort(key=lambda p: p.get("year", 0), reverse=True)

    return {"papers": papers, "total": len(papers)}


@router.get("/papers/{paper_id}")
def get_paper(paper_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        paper = library.get_paper(paper_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    # Enrich with shelves from index
    index = library.load_index(output_dir)
    for entry in index["papers"]:
        if entry["paper_id"] == paper_id:
            paper["shelves"] = entry.get("shelves", [])
            break
    else:
        paper["shelves"] = []
    return paper


@router.get("/papers/{paper_id}/markdown")
def get_paper_markdown(paper_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    md_path = os.path.join(output_dir, "markdown", f"{paper_id}.md")
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    with open(md_path, encoding="utf-8") as f:
        return {"markdown": f.read()}


@router.get("/papers/{paper_id}/pdf")
def get_paper_pdf(paper_id: str, request: Request) -> StreamingResponse:
    output_dir = request.app.state.output_dir
    pdf_path = os.path.join(output_dir, "pdfs", f"{paper_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {paper_id}")
    return StreamingResponse(
        open(pdf_path, "rb"),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{paper_id}.pdf"'},
    )


@router.delete("/papers/{paper_id}")
def delete_paper(paper_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir

    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    md_path = os.path.join(output_dir, "markdown", f"{paper_id}.md")
    pdf_path = os.path.join(output_dir, "pdfs", f"{paper_id}.pdf")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    for path in (json_path, md_path, pdf_path):
        if os.path.exists(path):
            os.unlink(path)

    # Update index
    index = library.load_index(output_dir)
    index["papers"] = [p for p in index["papers"] if p["paper_id"] != paper_id]
    library._save_index(index, output_dir)

    return {"ok": True}
