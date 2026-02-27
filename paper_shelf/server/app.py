from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from paper_shelf.server.tasks import TaskManager


def create_app(output_dir: str = "library", dev_mode: bool = False) -> FastAPI:
    app = FastAPI(title="Paper Shelf", version="0.1.0")

    app.state.output_dir = output_dir
    app.state.task_manager = TaskManager()

    if dev_mode:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register API routes
    from paper_shelf.server.routes_critique import router as critique_router
    from paper_shelf.server.routes_discovery import router as discovery_router
    from paper_shelf.server.routes_feed import router as feed_router
    from paper_shelf.server.routes_papers import router as papers_router
    from paper_shelf.server.routes_shelves import router as shelves_router
    from paper_shelf.server.routes_upload import router as upload_router

    app.include_router(papers_router, prefix="/api")
    app.include_router(shelves_router, prefix="/api")
    app.include_router(critique_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(feed_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")

    # Serve built frontend
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir) and os.listdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount(
                "/assets", StaticFiles(directory=assets_dir), name="assets"
            )

        index_html = os.path.join(static_dir, "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            # Try to serve the exact file first
            file_path = os.path.join(static_dir, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(index_html)

    return app
