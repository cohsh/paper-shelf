import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getPaper, deletePaper } from "../api/client";
import type { PaperDetail } from "../types/paper";
import TagBadge from "../components/TagBadge";
import ReaderComparison from "../components/ReaderComparison";

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getPaper(id)
      .then(setPaper)
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

  if (loading) return <p>Loading...</p>;
  if (error || !paper) {
    return (
      <div className="empty-state">
        <h3>Paper not found</h3>
        <p>{error}</p>
        <Link to="/library">Back to Library</Link>
      </div>
    );
  }

  const authors = paper.authors.length > 0 ? paper.authors.join(", ") : "Unknown";

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/library">&larr; Back to Library</Link>
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
      </div>

      <ReaderComparison readings={paper.readings} />

      <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)", display: "flex", gap: 12 }}>
        <a
          className="btn"
          href={`/api/papers/${id}/pdf`}
          target="_blank"
          rel="noopener noreferrer"
        >
          View PDF
        </a>
        <button className="btn btn-danger" onClick={handleDelete}>
          Delete Paper
        </button>
      </div>
    </div>
  );
}
