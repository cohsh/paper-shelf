import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getPaper, deletePaper, getShelves, setPaperShelves } from "../api/client";
import type { PaperDetail, Shelf } from "../types/paper";
import TagBadge from "../components/TagBadge";
import ReaderComparison from "../components/ReaderComparison";

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

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([getPaper(id), getShelves()])
      .then(([p, s]) => {
        setPaper(p);
        setAllShelves(s);
        setSelectedShelfIds(p.shelves || []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

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
          <span>{paper.year || "?"}</span>
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
