import { useState } from "react";
import type { CritiqueResult } from "../types/paper";

interface Props {
  critique: CritiqueResult;
}

type Lang = "en" | "ja";

export default function CritiqueSection({ critique }: Props) {
  const hasJa = !!(
    critique.assumptions_ja ||
    critique.weaknesses_ja ||
    critique.overall_assessment_ja
  );

  const [lang, setLang] = useState<Lang>(hasJa ? "ja" : "en");
  const [open, setOpen] = useState(false);

  const get = (en: string[], ja?: string[]) =>
    lang === "ja" && ja ? ja : en;

  const getText = (en: string, ja?: string) =>
    lang === "ja" && ja ? ja : en;

  const labels =
    lang === "ja"
      ? {
          assumptions: "暗黙の前提",
          weaknesses: "方法論上の弱点",
          unverified: "根拠の薄い主張",
          fragile: "結果の脆弱性",
          applications: "応用可能性",
          overall: "総合評価",
        }
      : {
          assumptions: "Hidden Assumptions",
          weaknesses: "Methodological Weaknesses",
          unverified: "Unsubstantiated Claims",
          fragile: "Sensitivity Points",
          applications: "Potential Applications",
          overall: "Overall Assessment",
        };

  return (
    <div className="critique-section">
      <div
        className="critique-header"
        onClick={() => setOpen(!open)}
      >
        <div className="reading-section-header" style={{ flex: 1 }}>
          <h2 style={{ color: "var(--color-warning)", cursor: "pointer" }}>
            <span className={`critique-chevron ${open ? "open" : ""}`}>&#9654;</span>
            Critical Analysis
          </h2>
          {hasJa && (
            <div className="lang-toggle" onClick={(e) => e.stopPropagation()}>
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
      </div>

      {open && (
        <div className="critique-body">
          <h3>{labels.assumptions}</h3>
          <ul>
            {get(critique.assumptions, critique.assumptions_ja).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>

          <h3>{labels.weaknesses}</h3>
          <ul>
            {get(critique.weaknesses, critique.weaknesses_ja).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>

          <h3>{labels.unverified}</h3>
          <ul>
            {get(critique.unverified_claims, critique.unverified_claims_ja).map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>

          <h3>{labels.fragile}</h3>
          <ul>
            {get(critique.fragile_points, critique.fragile_points_ja).map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>

          <h3>{labels.applications}</h3>
          <ul>
            {get(critique.applications, critique.applications_ja).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>

          <h3>{labels.overall}</h3>
          <p style={{ lineHeight: lang === "ja" ? 1.9 : 1.7 }}>
            {getText(critique.overall_assessment, critique.overall_assessment_ja)}
          </p>

          <p
            style={{
              marginTop: 16,
              fontSize: 12,
              color: "var(--color-text-secondary)",
            }}
          >
            Generated: {new Date(critique.generated_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}
