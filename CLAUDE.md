# Paper Shelf

Python 3.11+ project. A personal academic paper library powered by LLMs.

## Structure
- `paper_shelf/` - Source code
- `prompts/` - Prompt templates and JSON schema
- `library/` - Output directory (gitignored)
- `papers/` - Input PDFs (gitignored)
- `tests/` - Test files

## Commands
- Run tests: `pytest`
- Install: `pip install -e ".[dev]"`
- CLI: `paper-shelf read <pdf_path>`
