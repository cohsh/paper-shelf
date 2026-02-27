from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile

from paper_shelf.exceptions import CodexReaderError
from paper_shelf.pdf_extractor import ExtractedPaper

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "reading_prompt.txt")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "schema.json")

MAX_TEXT_LENGTH = 80000  # Truncate long papers for context window limits


def is_available() -> bool:
    """Check if Codex CLI is installed."""
    return shutil.which("codex") is not None


def read(paper: ExtractedPaper) -> dict:
    """Read an academic paper using Codex CLI."""
    if not is_available():
        raise CodexReaderError(
            "Codex CLI not found. Install it with: npm install -g @openai/codex"
        )

    prompt_template = _load_prompt()
    schema = _load_schema()
    text = paper.text
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning(
            f"Paper text ({len(text)} chars) exceeds limit. Truncating to {MAX_TEXT_LENGTH} chars."
        )
        text = text[:MAX_TEXT_LENGTH] + "\n\n[... text truncated due to length ...]"

    prompt = prompt_template.replace("{paper_text}", text)

    # Write prompt to temp file to avoid argument size limitations
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="paper_codex_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    # Write schema to temp file for --output-schema
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="schema_codex_"
    ) as f:
        json.dump(schema, f)
        schema_file = f.name

    output_file = tempfile.mktemp(suffix=".json", prefix="codex_output_")

    try:
        cmd = [
            "codex", "exec",
            f"Read the file at {prompt_file} and follow the instructions in it. "
            f"Respond ONLY with valid JSON matching the schema.",
            "--full-auto",
            "--output-schema", schema_file,
            "-o", output_file,
        ]

        logger.info("Running Codex CLI...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            raise CodexReaderError(
                f"Codex CLI failed (exit code {result.returncode}): {result.stderr}"
            )

        return _parse_output(output_file, result.stdout)
    except subprocess.TimeoutExpired:
        raise CodexReaderError("Codex CLI timed out after 600 seconds")
    except FileNotFoundError:
        raise CodexReaderError(
            "Codex CLI not found. Install it with: npm install -g @openai/codex"
        )
    finally:
        for path in (prompt_file, schema_file):
            try:
                os.unlink(path)
            except OSError:
                pass
        if os.path.exists(output_file):
            os.unlink(output_file)


def _parse_output(output_file: str, stdout: str) -> dict:
    """Parse Codex output from file or stdout."""
    # Try output file first
    if os.path.exists(output_file):
        with open(output_file) as f:
            content = f.read().strip()
        if content:
            parsed = _extract_json(content)
            if parsed:
                return parsed

    # Fallback to stdout (final agent message is printed to stdout)
    if stdout.strip():
        parsed = _extract_json(stdout.strip())
        if parsed:
            return parsed

    raise CodexReaderError("No output received from Codex CLI")


def _extract_json(text: str) -> dict | None:
    """Extract JSON from text that may contain markdown code blocks or extra text."""
    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "title" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.find("```", start)
        if end != -1:
            try:
                return json.loads(text[start:end].strip())
            except (json.JSONDecodeError, ValueError):
                pass

    if "```" in text:
        start = text.index("```") + 3
        end = text.find("```", start)
        if end != -1:
            try:
                return json.loads(text[start:end].strip())
            except (json.JSONDecodeError, ValueError):
                pass

    # Try finding JSON object in text
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        pass
                    break

    return None


def _load_prompt() -> str:
    path = os.path.normpath(PROMPT_PATH)
    with open(path) as f:
        return f.read()


def _load_schema() -> dict:
    path = os.path.normpath(SCHEMA_PATH)
    with open(path) as f:
        return json.load(f)
