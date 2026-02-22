from __future__ import annotations

import json
import logging
import shutil

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src import library, pdf_extractor, reader_claude, reader_codex, storage
from src.exceptions import ClaudeReaderError, CodexReaderError, PaperReaderError

console = Console()
logger = logging.getLogger("paper-reader")


@click.group()
@click.option("--verbose", is_flag=True, help="Show detailed progress")
def cli(verbose: bool) -> None:
    """Paper Reading Library - Read academic papers with Claude and Codex."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--reader",
    type=click.Choice(["claude", "codex", "both"]),
    default="both",
    help="Which reader(s) to use",
)
@click.option("--output-dir", type=click.Path(), default="library", help="Output directory")
def read(pdf_path: str, reader: str, output_dir: str) -> None:
    """Read an academic paper with LLM readers."""
    # 1. Extract text from PDF
    console.print(f"[bold]Extracting text from:[/bold] {pdf_path}")
    try:
        paper = pdf_extractor.extract(pdf_path)
    except PaperReaderError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    console.print(f"  Pages: {paper.page_count}, Characters: {paper.char_count}")

    # 2. Run readers
    results: dict[str, dict] = {}

    if reader in ("claude", "both"):
        console.print("\n[bold blue]Running Claude reader...[/bold blue]")
        try:
            results["claude"] = reader_claude.read(paper)
            console.print("  [green]Claude reading complete.[/green]")
        except ClaudeReaderError as e:
            console.print(f"  [yellow]Claude reader failed:[/yellow] {e}")
            if reader == "claude":
                raise SystemExit(1)

    if reader in ("codex", "both"):
        console.print("\n[bold green]Running Codex reader...[/bold green]")
        try:
            results["codex"] = reader_codex.read(paper)
            console.print("  [green]Codex reading complete.[/green]")
        except CodexReaderError as e:
            console.print(f"  [yellow]Codex reader failed:[/yellow] {e}")
            if reader == "codex":
                raise SystemExit(1)

    if not results:
        console.print("[red]Error: No reader produced results.[/red]")
        raise SystemExit(1)

    # 3. Save results
    console.print("\n[bold]Saving results...[/bold]")
    try:
        paper_id = storage.save(
            results,
            paper.metadata,
            output_dir,
            source_path=paper.source_path,
            page_count=paper.page_count,
        )
    except PaperReaderError as e:
        console.print(f"[red]Error saving:[/red] {e}")
        raise SystemExit(1)

    # 4. Update library index
    library.update_index(paper_id, output_dir)

    # 5. Display summary
    console.print(f"\n[bold green]Done![/bold green] Paper ID: [cyan]{paper_id}[/cyan]")
    title = storage._get_title(results, paper.metadata)
    console.print(f"  Title: {title}")
    console.print(f"  Readers: {', '.join(results.keys())}")
    console.print(f"  JSON:     {output_dir}/json/{paper_id}.json")
    console.print(f"  Markdown: {output_dir}/markdown/{paper_id}.md")


@cli.command("list")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["title", "date", "year"]),
    default="date",
    help="Sort order",
)
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def list_papers(fmt: str, sort_by: str, output_dir: str) -> None:
    """List all papers in the library."""
    index = library.load_index(output_dir)
    papers = index.get("papers", [])

    if not papers:
        console.print("No papers in the library yet.")
        return

    # Sort
    if sort_by == "title":
        papers.sort(key=lambda p: p.get("title", "").lower())
    elif sort_by == "date":
        papers.sort(key=lambda p: p.get("read_date", ""), reverse=True)
    elif sort_by == "year":
        papers.sort(key=lambda p: p.get("year", 0), reverse=True)

    if fmt == "json":
        console.print(json.dumps(papers, ensure_ascii=False, indent=2))
        return

    table = Table(title="Paper Shelf")
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Authors", max_width=30)
    table.add_column("Year", justify="center")
    table.add_column("Read Date", justify="center")
    table.add_column("Readers", justify="center")

    for p in papers:
        authors = ", ".join(p.get("authors", [])[:2])
        if len(p.get("authors", [])) > 2:
            authors += " et al."
        table.add_row(
            p.get("title", ""),
            authors,
            str(p.get("year", "")),
            p.get("read_date", ""),
            ", ".join(p.get("readers_used", [])),
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option(
    "--field",
    type=click.Choice(["title", "authors", "tags", "all"]),
    default="all",
    help="Search field",
)
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def search(query: str, field: str, output_dir: str) -> None:
    """Search papers in the library."""
    results = library.search(query, field=field, output_dir=output_dir)

    if not results:
        console.print(f"No papers found for query: '{query}'")
        return

    console.print(f"Found {len(results)} paper(s):\n")
    for p in results:
        authors = ", ".join(p.get("authors", [])[:2])
        console.print(f"  [cyan]{p['paper_id']}[/cyan]")
        console.print(f"    {p.get('title', 'Untitled')} ({p.get('year', '?')})")
        console.print(f"    {authors}")
        console.print()


@cli.command()
@click.argument("paper_id")
@click.option("--raw", is_flag=True, help="Show raw markdown instead of rendered")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def show(paper_id: str, raw: bool, output_dir: str) -> None:
    """Show a paper's reading summary."""
    import os

    md_path = os.path.join(output_dir, "markdown", f"{paper_id}.md")
    if not os.path.exists(md_path):
        console.print(f"[red]Paper not found:[/red] {paper_id}")
        raise SystemExit(1)

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    if raw:
        console.print(content)
    else:
        console.print(Markdown(content))


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
@click.option("--dev", is_flag=True, help="Enable CORS for Vite dev server on port 5173")
def serve(host: str, port: int, output_dir: str, dev: bool) -> None:
    """Start the web interface."""
    import uvicorn

    from src.server.app import create_app

    app = create_app(output_dir=output_dir, dev_mode=dev)
    console.print("[bold]Starting Paper Shelf web UI[/bold]")
    console.print(f"  http://{host}:{port}")
    console.print(f"  Library: {output_dir}")
    if dev:
        console.print("  [yellow]Dev mode: CORS enabled for http://localhost:5173[/yellow]")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli()
