from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile

from src.exceptions import ClaudeReaderError
from src.pdf_extractor import ExtractedPaper

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "reading_prompt.txt")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "schema.json")


def read(paper: ExtractedPaper) -> dict:
    """Read an academic paper using Claude Code CLI."""
    prompt_template = _load_prompt()
    schema = _load_schema()
    prompt = prompt_template.replace("{paper_text}", paper.text)

    # Write prompt to temp file to avoid stdin size limitations
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="paper_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            f"Read the file at {prompt_file} and follow the instructions in it. "
            f"Respond ONLY with valid JSON matching this schema: {json.dumps(schema)}",
            "--output-format", "json",
            "--allowedTools", "Read",
        ]

        logger.info("Running Claude CLI...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            raise ClaudeReaderError(
                f"Claude CLI failed (exit code {result.returncode}): {result.stderr}"
            )

        return _parse_response(result.stdout)
    except subprocess.TimeoutExpired:
        raise ClaudeReaderError("Claude CLI timed out after 600 seconds")
    except FileNotFoundError:
        raise ClaudeReaderError(
            "Claude CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
        )
    finally:
        os.unlink(prompt_file)


def _parse_response(stdout: str) -> dict:
    """Parse the Claude CLI JSON output."""
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError:
        raise ClaudeReaderError(f"Failed to parse Claude response as JSON: {stdout[:500]}")

    # Claude CLI --output-format json wraps the result
    if isinstance(response, dict):
        # Try to extract the structured content from the response
        if "result" in response:
            text = response["result"]
            # The result may be a JSON string inside the text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                pass
        # The response itself might be the structured output
        if "title" in response:
            return response

    raise ClaudeReaderError("Could not extract structured data from Claude response")


def _load_prompt() -> str:
    path = os.path.normpath(PROMPT_PATH)
    with open(path) as f:
        return f.read()


def _load_schema() -> dict:
    path = os.path.normpath(SCHEMA_PATH)
    with open(path) as f:
        return json.load(f)
