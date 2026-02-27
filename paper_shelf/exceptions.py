class PaperReaderError(Exception):
    """Base exception for paper-reader."""


class PDFExtractionError(PaperReaderError):
    """Error during PDF text extraction."""


class ReaderError(PaperReaderError):
    """Error during LLM reading."""


class ClaudeReaderError(ReaderError):
    """Error specific to Claude reader."""


class CodexReaderError(ReaderError):
    """Error specific to Codex reader."""


class StorageError(PaperReaderError):
    """Error during result storage."""


class DiscoveryError(PaperReaderError):
    """Error during paper discovery."""
