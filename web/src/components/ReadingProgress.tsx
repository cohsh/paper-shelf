import type { TaskStatusValue } from "../types/paper";

interface Props {
  status: TaskStatusValue;
  message: string;
}

const STEPS: { key: TaskStatusValue[]; label: string }[] = [
  { key: ["extracting"], label: "Extracting text from PDF" },
  { key: ["reading_claude"], label: "Claude is reading the paper" },
  { key: ["reading_codex"], label: "Codex is reading the paper" },
  { key: ["saving"], label: "Saving results" },
  { key: ["completed"], label: "Done!" },
];

const ORDER: TaskStatusValue[] = [
  "pending",
  "extracting",
  "reading_claude",
  "reading_codex",
  "saving",
  "completed",
];

export default function ReadingProgress({ status, message }: Props) {
  const currentIdx = ORDER.indexOf(status);
  const isFailed = status === "failed";

  return (
    <div className="progress-steps">
      {STEPS.map((step, i) => {
        const stepIdx = ORDER.indexOf(step.key[0]);
        const isCompleted = !isFailed && currentIdx > stepIdx;
        const isActive = !isFailed && step.key.includes(status);
        const stepClass = isFailed
          ? i === STEPS.length - 1
            ? "failed"
            : currentIdx >= stepIdx
              ? "completed"
              : ""
          : isCompleted
            ? "completed"
            : isActive
              ? "active"
              : "";

        return (
          <div key={i} className={`progress-step ${stepClass}`}>
            <div className={`step-icon ${stepClass}`}>
              {isCompleted ? "\u2713" : isFailed && i === STEPS.length - 1 ? "\u2717" : i + 1}
            </div>
            <span>
              {isFailed && isActive ? message : step.label}
            </span>
          </div>
        );
      })}

      {isFailed && (
        <div
          className="progress-step failed"
          style={{ marginTop: 8, fontWeight: 500 }}
        >
          Error: {message}
        </div>
      )}
    </div>
  );
}
