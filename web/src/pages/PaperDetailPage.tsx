import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getPaper, deletePaper, getShelves, setPaperShelves, generateCritique, discoverRelated, getTask } from "../api/client";
import type { CritiqueResult, DiscoveryResult, PaperDetail, Shelf, TaskStatusValue } from "../types/paper";
import TagBadge from "../components/TagBadge";
import ReaderComparison from "../components/ReaderComparison";
import CritiqueSection from "../components/CritiqueSection";
import CritiqueChat from "../components/CritiqueChat";
import DiscoveryResults from "../components/DiscoveryResults";

function DiscoverySection({
  discovery,
  onRefresh,
  refreshing,
}: {
  discovery: DiscoveryResult;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <div className="collapsible-header" onClick={() => setOpen(!open)}>
        <div className="reading-section-header" style={{ flex: 1 }}>
          <h2 style={{ cursor: "pointer" }}>
            <span className={`critique-chevron ${open ? "open" : ""}`}>&#9654;</span>
            Related Papers
          </h2>
          <button
            className="btn btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              onRefresh();
            }}
            disabled={refreshing}
            style={{ marginLeft: 8 }}
          >
            {refreshing ? "Searching..." : "Refresh"}
          </button>
        </div>
      </div>
      {open && <DiscoveryResults discovery={discovery} />}
    </div>
  );
}

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPdf, setShowPdf] = useState(false);

  const [allShelves, setAllShelves] = useState<Shelf[]>([]);
  const [editingShelves, setEditingShelves] = useState(false);
  const [selectedShelfIds, setSelectedShelfIds] = useState<string[]>([]);

  const [critique, setCritique] = useState<CritiqueResult | null>(null);
  const [critiqueTaskId, setCritiqueTaskId] = useState<string | null>(null);
  const [critiqueStatus, setCritiqueStatus] = useState<TaskStatusValue>("pending");
  const [critiqueMessage, setCritiqueMessage] = useState("");
  const [critiqueGenerating, setCritiqueGenerating] = useState(false);
  const critiquePollingRef = useRef<number | null>(null);

  const [discovered, setDiscovered] = useState<DiscoveryResult | null>(null);
  const [discoveryTaskId, setDiscoveryTaskId] = useState<string | null>(null);
  const [discoveryStatus, setDiscoveryStatus] = useState<TaskStatusValue>("pending");
  const [discoveryMessage, setDiscoveryMessage] = useState("");
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const discoveryPollingRef = useRef<number | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([getPaper(id), getShelves()])
      .then(([p, s]) => {
        setPaper(p);
        setAllShelves(s);
        setSelectedShelfIds(p.shelves || []);
        if (p.critique) {
          setCritique(p.critique);
        }
        if (p.discovered) {
          setDiscovered(p.discovered);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleGenerateCritique = useCallback(async () => {
    if (!id) return;
    setCritiqueGenerating(true);
    try {
      const res = await generateCritique(id);
      setCritiqueTaskId(res.task_id);
      setCritiqueStatus("pending");
      setCritiqueMessage("Queued...");
    } catch (e) {
      setCritiqueMessage(`Failed: ${e}`);
      setCritiqueGenerating(false);
    }
  }, [id]);

  // Poll critique task status
  useEffect(() => {
    if (!critiqueTaskId || critiqueStatus === "completed" || critiqueStatus === "failed") return;

    const poll = async () => {
      try {
        const task = await getTask(critiqueTaskId);
        setCritiqueStatus(task.status);
        setCritiqueMessage(task.progress_message);
        if (task.status === "completed" && task.paper_id) {
          // Reload paper to get critique data
          getPaper(task.paper_id).then((p) => {
            if (p.critique) {
              setCritique(p.critique);
            }
            setCritiqueGenerating(false);
          });
        }
        if (task.status === "failed") {
          setCritiqueGenerating(false);
        }
      } catch {
        // Ignore transient errors
      }
    };

    critiquePollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (critiquePollingRef.current) clearInterval(critiquePollingRef.current);
    };
  }, [critiqueTaskId, critiqueStatus]);

  const handleDiscover = useCallback(async () => {
    if (!id) return;
    setDiscoveryRunning(true);
    try {
      const res = await discoverRelated(id);
      setDiscoveryTaskId(res.task_id);
      setDiscoveryStatus("pending");
      setDiscoveryMessage("Queued...");
    } catch (e) {
      setDiscoveryMessage(`Failed: ${e}`);
      setDiscoveryRunning(false);
    }
  }, [id]);

  // Poll discovery task status
  useEffect(() => {
    if (!discoveryTaskId || discoveryStatus === "completed" || discoveryStatus === "failed") return;

    const poll = async () => {
      try {
        const task = await getTask(discoveryTaskId);
        setDiscoveryStatus(task.status);
        setDiscoveryMessage(task.progress_message);
        if (task.status === "completed" && task.paper_id) {
          getPaper(task.paper_id).then((p) => {
            if (p.discovered) {
              setDiscovered(p.discovered);
            }
            setDiscoveryRunning(false);
          });
        }
        if (task.status === "failed") {
          setDiscoveryRunning(false);
        }
      } catch {
        // Ignore transient errors
      }
    };

    discoveryPollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (discoveryPollingRef.current) clearInterval(discoveryPollingRef.current);
    };
  }, [discoveryTaskId, discoveryStatus]);

  const handleDelete = async () => {
    if (!id || !confirm("Are you sure you want to delete this paper?")) return;
    try {
      await deletePaper(id);
      navigate("/library");
    } catch (e) {
      alert(`Failed to delete: ${e}`);
    }
  };

  const handleSaveShelves = async () => {
    if (!id) return;
    try {
      await setPaperShelves(id, selectedShelfIds);
      setPaper((prev) => (prev ? { ...prev, shelves: selectedShelfIds } : prev));
      setEditingShelves(false);
    } catch (e) {
      alert(`Failed to update shelves: ${e}`);
    }
  };

  const toggleShelf = (shelfId: string) => {
    setSelectedShelfIds((prev) =>
      prev.includes(shelfId)
        ? prev.filter((s) => s !== shelfId)
        : [...prev, shelfId]
    );
  };

  if (loading) return <p>Loading...</p>;
  if (error || !paper) {
    return (
      <div className="empty-state">
        <h3>Paper not found</h3>
        <p>{error}</p>
        <Link to="/library">Back to Shelf</Link>
      </div>
    );
  }

  const authors = paper.authors.length > 0 ? paper.authors.join(", ") : "Unknown";
  const pdfUrl = `/api/papers/${id}/pdf`;
  const paperShelves = paper.shelves || [];
  const userShelves = allShelves.filter((s) => !s.is_virtual);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/library">&larr; Back to Shelf</Link>
      </div>

      <div className="paper-header">
        <h1>{paper.title}</h1>
        <div className="paper-meta">
          <span>{authors}</span>
          <span>{paper.published_date || paper.year || "?"}</span>
          {paper.venue && <span>{paper.venue}</span>}
          <span>{paper.page_count} pages</span>
          <span>Read: {paper.read_date}</span>
          <span>Readers: {paper.readers_used.join(", ")}</span>
        </div>
        <div className="paper-tags">
          {paper.tags.map((t) => (
            <TagBadge key={t} tag={t} />
          ))}
        </div>

        <div className="paper-shelves">
          <span className="paper-shelves-label">Shelves:</span>
          {paperShelves.length === 0 ? (
            <span className="shelf-badge">Unsorted</span>
          ) : (
            paperShelves.map((sid) => {
              const shelf = allShelves.find((s) => s.shelf_id === sid);
              return (
                <span key={sid} className="shelf-badge">
                  {shelf ? shelf.name : sid}
                </span>
              );
            })
          )}
          <button
            className="btn btn-sm"
            onClick={() => {
              setSelectedShelfIds(paperShelves);
              setEditingShelves(!editingShelves);
            }}
            style={{ marginLeft: 8 }}
          >
            {editingShelves ? "Cancel" : "Edit"}
          </button>
        </div>

        {editingShelves && (
          <div className="shelf-edit-panel">
            {userShelves.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                No shelves created yet. Create one from the library page.
              </p>
            ) : (
              <div className="shelf-checkbox-list">
                {userShelves.map((s) => (
                  <label key={s.shelf_id} className="shelf-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedShelfIds.includes(s.shelf_id)}
                      onChange={() => toggleShelf(s.shelf_id)}
                    />
                    {s.name}
                  </label>
                ))}
              </div>
            )}
            <button
              className="btn btn-primary btn-sm"
              onClick={handleSaveShelves}
              style={{ marginTop: 8 }}
            >
              Save
            </button>
          </div>
        )}
      </div>

      <ReaderComparison readings={paper.readings} />

      <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
        {critique ? (
          <>
            <CritiqueSection critique={critique} />
            <CritiqueChat paperId={paper.paper_id} />
          </>
        ) : critiqueGenerating ? (
          <div>
            <h2 style={{ color: "var(--color-warning)", marginBottom: 16 }}>
              Critical Analysis
            </h2>
            <div className="progress-steps">
              <div className={`progress-step ${critiqueStatus === "completed" ? "completed" : critiqueStatus === "failed" ? "failed" : "active"}`}>
                <div className={`step-icon ${critiqueStatus === "completed" ? "completed" : critiqueStatus === "failed" ? "failed" : "active"}`}>
                  {critiqueStatus === "completed" ? "\u2713" : critiqueStatus === "failed" ? "\u2717" : "1"}
                </div>
                <span>{critiqueMessage || "Generating critical analysis..."}</span>
              </div>
            </div>
          </div>
        ) : (
          <button
            className="btn btn-primary"
            onClick={handleGenerateCritique}
          >
            Generate Critique
          </button>
        )}
      </div>

      <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
        {discovered ? (
          <DiscoverySection discovery={discovered} onRefresh={handleDiscover} refreshing={discoveryRunning} />
        ) : discoveryRunning ? (
          <div>
            <h2 style={{ marginBottom: 16 }}>
              Related Papers
            </h2>
            <div className="progress-steps">
              <div className={`progress-step ${discoveryStatus === "completed" ? "completed" : discoveryStatus === "failed" ? "failed" : "active"}`}>
                <div className={`step-icon ${discoveryStatus === "completed" ? "completed" : discoveryStatus === "failed" ? "failed" : "active"}`}>
                  {discoveryStatus === "completed" ? "\u2713" : discoveryStatus === "failed" ? "\u2717" : "1"}
                </div>
                <span>{discoveryMessage || "Finding related papers..."}</span>
              </div>
            </div>
          </div>
        ) : (
          <button
            className="btn btn-primary"
            onClick={handleDiscover}
          >
            Find Related Papers
          </button>
        )}
      </div>

      <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
        <button
          className="btn"
          onClick={() => setShowPdf((v) => !v)}
        >
          {showPdf ? "Hide PDF" : "Show PDF"}
        </button>
      </div>

      {showPdf && (
        <div style={{ marginTop: 16 }}>
          <iframe
            src={pdfUrl}
            title="Paper PDF"
            style={{
              width: "100%",
              height: "80vh",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius)",
            }}
          />
        </div>
      )}

      <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
        <button className="btn btn-danger" onClick={handleDelete}>
          Delete Paper
        </button>
      </div>
    </div>
  );
}
