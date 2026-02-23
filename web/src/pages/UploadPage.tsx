import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadPaper, getTask, getShelves } from "../api/client";
import type { Shelf, TaskStatusValue } from "../types/paper";
import UploadDropzone from "../components/UploadDropzone";
import ReadingProgress from "../components/ReadingProgress";

interface UploadItem {
  file: File;
  taskId: string | null;
  status: TaskStatusValue;
  message: string;
  paperId: string | null;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [reader, setReader] = useState("both");
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const pollingRef = useRef<number | null>(null);

  const [allShelves, setAllShelves] = useState<Shelf[]>([]);
  const [selectedShelves, setSelectedShelves] = useState<string[]>([]);

  useEffect(() => {
    getShelves()
      .then((s) => setAllShelves(s.filter((sh) => !sh.is_virtual)))
      .catch(console.error);
  }, []);

  const hasActiveItems = items.some(
    (it) => it.taskId !== null && it.status !== "completed" && it.status !== "failed"
  );

  const handleFilesSelected = useCallback(
    (newFiles: File[]) => {
      if (hasActiveItems || uploading) return;
      setFiles((prev) => [...prev, ...newFiles]);
    },
    [hasActiveItems, uploading]
  );

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;
    setUploading(true);

    const newItems: UploadItem[] = files.map((f) => ({
      file: f,
      taskId: null,
      status: "pending" as TaskStatusValue,
      message: "Queued...",
      paperId: null,
    }));
    setItems(newItems);
    setFiles([]);

    // Start all uploads in parallel
    const updated = [...newItems];
    await Promise.all(
      updated.map(async (item, i) => {
        try {
          const res = await uploadPaper(item.file, reader, selectedShelves);
          updated[i] = { ...updated[i], taskId: res.task_id };
        } catch (e) {
          updated[i] = {
            ...updated[i],
            status: "failed",
            message: `Upload failed: ${e}`,
          };
        }
      })
    );

    setItems([...updated]);
    setUploading(false);
  }, [files, reader, selectedShelves]);

  const toggleShelf = (shelfId: string) => {
    setSelectedShelves((prev) =>
      prev.includes(shelfId)
        ? prev.filter((s) => s !== shelfId)
        : [...prev, shelfId]
    );
  };

  // Poll task status for all active items
  useEffect(() => {
    const activeItems = items.filter(
      (it) => it.taskId && it.status !== "completed" && it.status !== "failed"
    );
    if (activeItems.length === 0) return;

    const poll = async () => {
      setItems((prev) =>
        prev.map((item) => {
          // Only poll items that have a taskId and are still active
          if (!item.taskId || item.status === "completed" || item.status === "failed") {
            return item;
          }
          // We'll update via the async call below
          return item;
        })
      );

      // Fetch all active tasks in parallel
      const updates = await Promise.all(
        items.map(async (item) => {
          if (!item.taskId || item.status === "completed" || item.status === "failed") {
            return item;
          }
          try {
            const task = await getTask(item.taskId);
            return {
              ...item,
              status: task.status,
              message: task.progress_message,
              paperId: task.paper_id || item.paperId,
            };
          } catch {
            return item;
          }
        })
      );

      setItems(updates);
    };

    pollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [
    items
      .map((it) => `${it.taskId}:${it.status}`)
      .join(","),
  ]);

  const allDone = items.length > 0 && items.every(
    (it) => it.status === "completed" || it.status === "failed"
  );

  const handleReset = () => {
    setItems([]);
    setFiles([]);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 24 }}>Upload Papers</h2>

      <UploadDropzone
        onFilesSelected={handleFilesSelected}
        disabled={hasActiveItems || uploading}
      />

      {files.length > 0 && items.length === 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 8, fontWeight: 500 }}>
            {files.length} file(s) selected:
          </p>
          <ul style={{ listStyle: "none", padding: 0, margin: "0 0 12px 0" }}>
            {files.map((f, i) => (
              <li
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 0",
                  fontSize: 14,
                }}
              >
                <span style={{ flex: 1 }}>
                  {f.name}{" "}
                  <span style={{ color: "var(--color-text-secondary)" }}>
                    ({(f.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </span>
                <button
                  className="btn btn-sm"
                  onClick={() => removeFile(i)}
                  style={{ padding: "2px 8px" }}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>

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
            {uploading
              ? "Uploading..."
              : `Start Reading (${files.length} file${files.length > 1 ? "s" : ""})`}
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div style={{ marginTop: 24 }}>
          {items.map((item, i) => (
            <div
              key={i}
              style={{
                marginBottom: 20,
                padding: 16,
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius)",
              }}
            >
              <p style={{ marginBottom: 8, fontWeight: 500, fontSize: 14 }}>
                {item.file.name}
              </p>
              <ReadingProgress status={item.status} message={item.message} />

              {item.status === "completed" && item.paperId && (
                <div style={{ marginTop: 12 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate(`/papers/${item.paperId}`)}
                  >
                    View Results
                  </button>
                </div>
              )}
            </div>
          ))}

          {allDone && (
            <button
              className="btn"
              onClick={handleReset}
              style={{ marginTop: 8 }}
            >
              Upload More
            </button>
          )}
        </div>
      )}
    </div>
  );
}
