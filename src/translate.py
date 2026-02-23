from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def translate_abstracts(papers: list[dict]) -> list[dict]:
    """Batch-translate abstracts to Japanese using Claude CLI.

    Each paper dict should have an ``"abstract"`` key.  This function
    adds an ``"abstract_ja"`` key with the Japanese translation.

    Papers without an abstract are returned unchanged.  If the Claude
    call fails, the original papers are returned without translations.
    """
    # Collect papers that have abstracts worth translating
    to_translate: list[tuple[int, str]] = []
    for i, p in enumerate(papers):
        abstract = (p.get("abstract") or "").strip()
        if abstract:
            to_translate.append((i, abstract))

    if not to_translate:
        return papers

    # Build a compact prompt with numbered abstracts
    lines = [
        "Translate each of the following academic paper abstracts into Japanese.",
        "Respond with ONLY a JSON array of translated strings, in the same order.",
        "Keep the translations accurate and natural in Japanese academic style.",
        f"There are {len(to_translate)} abstracts to translate.",
        "",
    ]
    for seq, (_, abstract) in enumerate(to_translate):
        lines.append(f"[{seq}] {abstract}")
        lines.append("")

    prompt_text = "\n".join(lines)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="translate_"
    ) as f:
        f.write(prompt_text)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            f"Read the file at {prompt_file} and follow the instructions in it. "
            "Respond ONLY with a JSON array of translated strings.",
            "--output-format",
            "json",
            "--allowedTools",
            "Read",
        ]

        logger.info("Running Claude CLI for batch translation (%d abstracts)...", len(to_translate))
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        if result.returncode != 0:
            logger.error("Claude CLI translation failed: %s", result.stderr)
            return papers

        translations = _parse_translations(result.stdout, expected=len(to_translate))

        if translations and len(translations) == len(to_translate):
            for (idx, _), ja_text in zip(to_translate, translations):
                papers[idx]["abstract_ja"] = ja_text
        else:
            logger.warning(
                "Translation count mismatch: expected %d, got %d",
                len(to_translate),
                len(translations) if translations else 0,
            )

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI translation timed out")
    except FileNotFoundError:
        logger.error("Claude CLI not found")
    finally:
        os.unlink(prompt_file)

    return papers


def _parse_translations(stdout: str, expected: int) -> list[str] | None:
    """Parse Claude CLI output to extract a list of translated strings."""
    try:
        response = json.loads(stdout)
        if isinstance(response, dict) and "result" in response:
            text = response["result"]
        elif isinstance(response, list):
            return [str(s) for s in response]
        else:
            text = stdout
    except json.JSONDecodeError:
        text = stdout

    # Try parsing as JSON array
    if isinstance(text, str):
        try:
            arr = json.loads(text)
            if isinstance(arr, list):
                return [str(s) for s in arr]
        except (json.JSONDecodeError, TypeError):
            pass

        # Try finding JSON array in text
        bracket_start = text.find("[")
        if bracket_start >= 0:
            bracket_end = text.rfind("]")
            if bracket_end > bracket_start:
                try:
                    arr = json.loads(text[bracket_start : bracket_end + 1])
                    if isinstance(arr, list):
                        return [str(s) for s in arr]
                except json.JSONDecodeError:
                    pass

    return None
