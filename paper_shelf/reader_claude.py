from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile

from paper_shelf.exceptions import ClaudeReaderError
from paper_shelf.pdf_extractor import ExtractedPaper

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
        # Remove CLAUDECODE env var to avoid nested session error
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
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

    # Claude CLI --output-format json wraps the result in {"result": "..."}
    if isinstance(response, dict):
        text = response.get("result", "")
        if text:
            parsed = _extract_json(text)
            if parsed:
                return parsed
        # The response itself might be the structured output
        if "title" in response:
            return response

    raise ClaudeReaderError("Could not extract structured data from Claude response")


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
