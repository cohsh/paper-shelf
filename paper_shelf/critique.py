from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile

from paper_shelf.exceptions import ClaudeReaderError

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "critique_prompt.txt")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "critique_schema.json")


def generate_critique(paper_text: str, readings: dict) -> dict:
    """Generate a critical analysis of a paper using Claude CLI."""
    prompt_template = _load_prompt()
    schema = _load_schema()

    # Build reading summary from available readings
    reading_summary = _build_reading_summary(readings)

    prompt = prompt_template.replace("{paper_text}", paper_text)
    prompt = prompt.replace("{reading_summary}", reading_summary)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="critique_"
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

        logger.info("Running Claude CLI for critique...")
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

        return _parse_response(result.stdout, expected_key="assumptions")
    except subprocess.TimeoutExpired:
        raise ClaudeReaderError("Claude CLI timed out after 600 seconds")
    except FileNotFoundError:
        raise ClaudeReaderError(
            "Claude CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
        )
    finally:
        os.unlink(prompt_file)


def generate_chat_response(
    paper_text: str,
    readings: dict,
    critique: dict,
    messages: list[dict],
) -> str:
    """Generate a chat response about the paper using Claude CLI."""
    reading_summary = _build_reading_summary(readings)
    critique_summary = _build_critique_summary(critique)

    # Build conversation context
    conversation = []
    conversation.append(
        "You are a critical research dialogue partner. You have deeply analyzed "
        "the following academic paper. Answer the user's questions with precision, "
        "always grounding your responses in the paper's actual content. "
        "Be direct, critical, and intellectually honest. "
        "Respond in the same language as the user's question."
    )
    conversation.append("")
    conversation.append("=== PAPER TEXT ===")
    conversation.append(paper_text[:40000])  # Truncate for context window
    conversation.append("")
    conversation.append("=== READING SUMMARY ===")
    conversation.append(reading_summary)
    conversation.append("")
    conversation.append("=== CRITICAL ANALYSIS ===")
    conversation.append(critique_summary)
    conversation.append("")
    conversation.append("=== CONVERSATION ===")

    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation.append(f"{role}: {msg['content']}")

    conversation.append("")
    conversation.append("Respond to the user's latest message. Be concise but thorough.")

    prompt_text = "\n".join(conversation)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="chat_"
    ) as f:
        f.write(prompt_text)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            f"Read the file at {prompt_file} and follow the instructions in it.",
            "--output-format", "json",
            "--allowedTools", "Read",
        ]

        logger.info("Running Claude CLI for chat...")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        if result.returncode != 0:
            raise ClaudeReaderError(
                f"Claude CLI failed (exit code {result.returncode}): {result.stderr}"
            )

        # Parse the JSON response to get the text
        try:
            response = json.loads(result.stdout)
            if isinstance(response, dict) and "result" in response:
                return response["result"]
            return result.stdout
        except json.JSONDecodeError:
            return result.stdout
    except subprocess.TimeoutExpired:
        raise ClaudeReaderError("Claude CLI timed out after 300 seconds")
    except FileNotFoundError:
        raise ClaudeReaderError(
            "Claude CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
        )
    finally:
        os.unlink(prompt_file)


def _build_reading_summary(readings: dict) -> str:
    """Build a text summary from reading results."""
    parts = []
    for reader_name, reading in readings.items():
        parts.append(f"--- {reader_name.upper()} READING ---")
        if reading.get("abstract_summary"):
            parts.append(f"Abstract: {reading['abstract_summary']}")
        if reading.get("key_contributions"):
            parts.append("Key Contributions:")
            for c in reading["key_contributions"]:
                parts.append(f"  - {c}")
        if reading.get("methodology"):
            parts.append(f"Methodology: {reading['methodology']}")
        if reading.get("main_results"):
            parts.append(f"Main Results: {reading['main_results']}")
        if reading.get("limitations"):
            parts.append("Limitations:")
            for lim in reading["limitations"]:
                parts.append(f"  - {lim}")
        if reading.get("connections"):
            parts.append(f"Connections: {reading['connections']}")
        parts.append("")
    return "\n".join(parts)


def _build_critique_summary(critique: dict) -> str:
    """Build a text summary from critique results."""
    parts = []
    if critique.get("assumptions"):
        parts.append("Hidden Assumptions:")
        for a in critique["assumptions"]:
            parts.append(f"  - {a}")
    if critique.get("weaknesses"):
        parts.append("Methodological Weaknesses:")
        for w in critique["weaknesses"]:
            parts.append(f"  - {w}")
    if critique.get("unverified_claims"):
        parts.append("Unsubstantiated Claims:")
        for u in critique["unverified_claims"]:
            parts.append(f"  - {u}")
    if critique.get("fragile_points"):
        parts.append("Sensitivity Points:")
        for fp in critique["fragile_points"]:
            parts.append(f"  - {fp}")
    if critique.get("applications"):
        parts.append("Potential Applications:")
        for app in critique["applications"]:
            parts.append(f"  - {app}")
    if critique.get("overall_assessment"):
        parts.append(f"Overall Assessment: {critique['overall_assessment']}")
    return "\n".join(parts)


def _parse_response(stdout: str, expected_key: str = "assumptions") -> dict:
    """Parse the Claude CLI JSON output."""
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError:
        raise ClaudeReaderError(f"Failed to parse Claude response as JSON: {stdout[:500]}")

    if isinstance(response, dict):
        text = response.get("result", "")
        if text:
            parsed = _extract_json(text, expected_key)
            if parsed:
                return parsed
        if expected_key in response:
            return response

    raise ClaudeReaderError("Could not extract structured data from Claude response")


def _extract_json(text: str, expected_key: str = "assumptions") -> dict | None:
    """Extract JSON from text that may contain markdown code blocks."""
    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and expected_key in data:
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
