# Paper Reading via LLM

Python 3.11+ project. CLI tool that reads academic papers with Claude and Codex.

## Structure
- `src/` - Source code
- `prompts/` - Prompt templates and JSON schema
- `library/` - Output directory (gitignored)
- `papers/` - Input PDFs (gitignored)
- `tests/` - Test files

## Commands
- Run tests: `pytest`
- Install: `pip install -e ".[dev]"`
- CLI: `paper-reader read <pdf_path>`
