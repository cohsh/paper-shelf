import { useState } from "react";
import type { ReadingResult } from "../types/paper";
import ReadingSection from "./ReadingSection";

interface Props {
  readings: {
    claude?: ReadingResult;
    codex?: ReadingResult;
  };
}

type ViewMode = "side-by-side" | "claude" | "codex";

export default function ReaderComparison({ readings }: Props) {
  const hasClaudeReading = !!readings.claude;
  const hasCodexReading = !!readings.codex;
  const hasBoth = hasClaudeReading && hasCodexReading;

  const defaultMode: ViewMode = hasBoth
    ? "side-by-side"
    : hasClaudeReading
      ? "claude"
      : "codex";

  const [mode, setMode] = useState<ViewMode>(defaultMode);

  return (
    <div>
      {hasBoth && (
        <div className="reader-tabs">
          <button
            className={`reader-tab ${mode === "side-by-side" ? "active" : ""}`}
            onClick={() => setMode("side-by-side")}
          >
            Side by Side
          </button>
          <button
            className={`reader-tab ${mode === "claude" ? "active" : ""}`}
            onClick={() => setMode("claude")}
          >
            Claude
          </button>
          <button
            className={`reader-tab ${mode === "codex" ? "active" : ""}`}
            onClick={() => setMode("codex")}
          >
            Codex
          </button>
        </div>
      )}

      {mode === "side-by-side" && hasBoth ? (
        <div className="comparison-grid">
          <ReadingSection reading={readings.claude!} readerName="Claude" />
          <ReadingSection reading={readings.codex!} readerName="Codex" />
        </div>
      ) : mode === "claude" && hasClaudeReading ? (
        <ReadingSection reading={readings.claude!} readerName="Claude" />
      ) : mode === "codex" && hasCodexReading ? (
        <ReadingSection reading={readings.codex!} readerName="Codex" />
      ) : (
        <p style={{ color: "var(--color-text-secondary)" }}>
          No reading data available.
        </p>
      )}
    </div>
  );
}
