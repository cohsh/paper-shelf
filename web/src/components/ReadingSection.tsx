import type { ReadingResult } from "../types/paper";

interface Props {
  reading: ReadingResult;
  readerName: string;
}

export default function ReadingSection({ reading, readerName }: Props) {
  return (
    <div className="reading-section">
      <h2 style={{ marginBottom: 20, color: "var(--color-primary)" }}>
        {readerName}'s Reading
      </h2>

      <h3>Abstract Summary</h3>
      <p>{reading.abstract_summary}</p>

      <h3>Key Contributions</h3>
      <ul>
        {reading.key_contributions.map((c, i) => (
          <li key={i}>{c}</li>
        ))}
      </ul>

      <h3>Methodology</h3>
      <p>{reading.methodology}</p>

      <h3>Main Results</h3>
      <p>{reading.main_results}</p>

      <h3>Limitations</h3>
      <ul>
        {reading.limitations.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>

      <h3>Connections</h3>
      <p>{reading.connections}</p>

      {reading.confidence_notes && (
        <>
          <h3>Confidence Notes</h3>
          <p style={{ color: "var(--color-text-secondary)", fontStyle: "italic" }}>
            {reading.confidence_notes}
          </p>
        </>
      )}
    </div>
  );
}
