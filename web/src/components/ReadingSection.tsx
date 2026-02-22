import { useState } from "react";
import type { ReadingResult } from "../types/paper";

interface Props {
  reading: ReadingResult;
  readerName: string;
}

type Lang = "en" | "ja";

export default function ReadingSection({ reading, readerName }: Props) {
  const hasJa = !!(
    reading.abstract_summary_ja ||
    reading.key_contributions_ja ||
    reading.methodology_ja ||
    reading.main_results_ja ||
    reading.limitations_ja ||
    reading.connections_ja
  );

  const [lang, setLang] = useState<Lang>(hasJa ? "ja" : "en");

  const abstractSummary =
    lang === "ja" && reading.abstract_summary_ja
      ? reading.abstract_summary_ja
      : reading.abstract_summary;

  const keyContributions =
    lang === "ja" && reading.key_contributions_ja
      ? reading.key_contributions_ja
      : reading.key_contributions;

  const methodology =
    lang === "ja" && reading.methodology_ja
      ? reading.methodology_ja
      : reading.methodology;

  const mainResults =
    lang === "ja" && reading.main_results_ja
      ? reading.main_results_ja
      : reading.main_results;

  const limitations =
    lang === "ja" && reading.limitations_ja
      ? reading.limitations_ja
      : reading.limitations;

  const connections =
    lang === "ja" && reading.connections_ja
      ? reading.connections_ja
      : reading.connections;

  const sectionLabels =
    lang === "ja"
      ? {
          abstract: "概要",
          contributions: "主要な貢献",
          methodology: "手法",
          results: "主な結果",
          limitations: "限界・課題",
          connections: "関連研究",
          confidence: "信頼性に関する注記",
        }
      : {
          abstract: "Abstract Summary",
          contributions: "Key Contributions",
          methodology: "Methodology",
          results: "Main Results",
          limitations: "Limitations",
          connections: "Connections",
          confidence: "Confidence Notes",
        };

  return (
    <div className="reading-section">
      <div className="reading-section-header">
        <h2 style={{ color: "var(--color-primary)" }}>
          {readerName}'s Reading
        </h2>
        {hasJa && (
          <div className="lang-toggle">
            <button
              className={`lang-btn ${lang === "en" ? "active" : ""}`}
              onClick={() => setLang("en")}
            >
              En
            </button>
            <button
              className={`lang-btn ${lang === "ja" ? "active" : ""}`}
              onClick={() => setLang("ja")}
            >
              Ja
            </button>
          </div>
        )}
      </div>

      <h3>{sectionLabels.abstract}</h3>
      <p style={{ lineHeight: lang === "ja" ? 1.9 : 1.7 }}>{abstractSummary}</p>

      <h3>{sectionLabels.contributions}</h3>
      <ul>
        {keyContributions.map((c, i) => (
          <li key={i}>{c}</li>
        ))}
      </ul>

      <h3>{sectionLabels.methodology}</h3>
      <p style={{ lineHeight: lang === "ja" ? 1.9 : 1.7 }}>{methodology}</p>

      <h3>{sectionLabels.results}</h3>
      <p style={{ lineHeight: lang === "ja" ? 1.9 : 1.7 }}>{mainResults}</p>

      <h3>{sectionLabels.limitations}</h3>
      <ul>
        {limitations.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>

      <h3>{sectionLabels.connections}</h3>
      <p style={{ lineHeight: lang === "ja" ? 1.9 : 1.7 }}>{connections}</p>

      {reading.confidence_notes && (
        <>
          <h3>{sectionLabels.confidence}</h3>
          <p style={{ color: "var(--color-text-secondary)", fontStyle: "italic" }}>
            {reading.confidence_notes}
          </p>
        </>
      )}
    </div>
  );
}
