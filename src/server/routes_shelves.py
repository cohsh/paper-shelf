from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import library
from src.exceptions import StorageError

router = APIRouter()


class ShelfCreate(BaseModel):
    name: str
    name_ja: str = ""


class ShelfUpdate(BaseModel):
    name: str
    name_ja: str | None = None


class PaperShelvesUpdate(BaseModel):
    shelf_ids: list[str]


# --- Shelf CRUD ---


@router.get("/shelves")
def list_shelves(request: Request) -> list[dict]:
    output_dir = request.app.state.output_dir
    return library.list_shelves(output_dir)


@router.post("/shelves", status_code=201)
def create_shelf(body: ShelfCreate, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        return library.create_shelf(body.name, output_dir, name_ja=body.name_ja)
    except StorageError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/shelves/{shelf_id}")
def get_shelf(shelf_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        return library.get_shelf(shelf_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Shelf not found: {shelf_id}")


@router.put("/shelves/{shelf_id}")
def update_shelf(shelf_id: str, body: ShelfUpdate, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        return library.rename_shelf(
            shelf_id, body.name, output_dir, name_ja=body.name_ja
        )
    except StorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/shelves/{shelf_id}")
def delete_shelf(shelf_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        library.delete_shelf(shelf_id, output_dir)
        return {"ok": True}
    except StorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Paper-shelf assignment ---


@router.put("/papers/{paper_id}/shelves")
def set_paper_shelves(
    paper_id: str, body: PaperShelvesUpdate, request: Request
) -> dict:
    output_dir = request.app.state.output_dir
    try:
        library.assign_paper_to_shelves(paper_id, body.shelf_ids, output_dir)
        return {"ok": True}
    except StorageError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/papers/{paper_id}/shelves/{shelf_id}")
def add_paper_to_shelf(paper_id: str, shelf_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        library.add_paper_to_shelf(paper_id, shelf_id, output_dir)
        return {"ok": True}
    except StorageError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/papers/{paper_id}/shelves/{shelf_id}")
def remove_paper_from_shelf(
    paper_id: str, shelf_id: str, request: Request
) -> dict:
    output_dir = request.app.state.output_dir
    try:
        library.remove_paper_from_shelf(paper_id, shelf_id, output_dir)
        return {"ok": True}
    except StorageError as e:
        raise HTTPException(status_code=404, detail=str(e))
