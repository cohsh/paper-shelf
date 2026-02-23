import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadPaper, getTask, getShelves } from "../api/client";
import type { Shelf, TaskStatusValue } from "../types/paper";
import UploadDropzone from "../components/UploadDropzone";
import ReadingProgress from "../components/ReadingProgress";

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [reader, setReader] = useState("both");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<TaskStatusValue>("pending");
  const [message, setMessage] = useState("");
  const [paperId, setPaperId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const pollingRef = useRef<number | null>(null);

  const [allShelves, setAllShelves] = useState<Shelf[]>([]);
  const [selectedShelves, setSelectedShelves] = useState<string[]>([]);

  useEffect(() => {
    getShelves()
      .then((s) => setAllShelves(s.filter((sh) => !sh.is_virtual)))
      .catch(console.error);
  }, []);

  const isProcessing = taskId !== null && status !== "completed" && status !== "failed";

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadPaper(file, reader, selectedShelves);
      setTaskId(res.task_id);
      setStatus("pending");
      setMessage("Queued...");
    } catch (e) {
      setMessage(`Upload failed: ${e}`);
      setStatus("failed");
    } finally {
      setUploading(false);
    }
  }, [file, reader, selectedShelves]);

  const toggleShelf = (shelfId: string) => {
    setSelectedShelves((prev) =>
      prev.includes(shelfId)
        ? prev.filter((s) => s !== shelfId)
        : [...prev, shelfId]
    );
  };

  // Poll task status
  useEffect(() => {
    if (!taskId || status === "completed" || status === "failed") return;

    const poll = async () => {
      try {
        const task = await getTask(taskId);
        setStatus(task.status);
        setMessage(task.progress_message);
        if (task.paper_id) setPaperId(task.paper_id);
      } catch {
        // Ignore transient errors
      }
    };

    pollingRef.current = window.setInterval(poll, 2000);
    poll(); // immediate first call

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [taskId, status]);

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 24 }}>Upload Paper</h2>

      <UploadDropzone
        onFileSelected={setFile}
        disabled={isProcessing || uploading}
      />

      {file && !taskId && (
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 12 }}>
            Selected: <strong>{file.name}</strong> (
            {(file.size / 1024 / 1024).toFixed(1)} MB)
          </p>

          <div className="reader-selector">
            <span style={{ fontWeight: 500 }}>Reader:</span>
            {(["both", "claude", "codex"] as const).map((r) => (
              <label key={r} className="reader-option">
                <input
                  type="radio"
                  name="reader"
                  value={r}
                  checked={reader === r}
                  onChange={() => setReader(r)}
                />
                {r === "both" ? "Both" : r.charAt(0).toUpperCase() + r.slice(1)}
              </label>
            ))}
          </div>

          {allShelves.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <span style={{ fontWeight: 500, fontSize: 14 }}>Shelves (optional):</span>
              <div className="shelf-checkbox-list" style={{ marginTop: 6 }}>
                {allShelves.map((s) => (
                  <label key={s.shelf_id} className="shelf-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedShelves.includes(s.shelf_id)}
                      onChange={() => toggleShelf(s.shelf_id)}
                    />
                    {s.name}
                  </label>
                ))}
              </div>
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading}
            style={{ marginTop: 12 }}
          >
            {uploading ? "Uploading..." : "Start Reading"}
          </button>
        </div>
      )}

      {taskId && (
        <div style={{ marginTop: 24 }}>
          <ReadingProgress status={status} message={message} />

          {status === "completed" && paperId && (
            <div style={{ marginTop: 20 }}>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/papers/${paperId}`)}
              >
                View Results
              </button>
            </div>
          )}

          {status === "failed" && (
            <div style={{ marginTop: 20 }}>
              <button
                className="btn"
                onClick={() => {
                  setTaskId(null);
                  setFile(null);
                  setStatus("pending");
                  setMessage("");
                }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
