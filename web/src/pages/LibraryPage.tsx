import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { getPapers } from "../api/client";
import type { PaperSummary } from "../types/paper";
import PaperTable from "../components/PaperTable";
import PaperCard from "../components/PaperCard";

type ViewMode = "table" | "cards";

export default function LibraryPage() {
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState("date");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getPapers({
      sort_by: sortBy,
      search: searchQuery || undefined,
    })
      .then((res) => {
        setPapers(res.papers);
        setTotal(res.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [sortBy, searchQuery]);

  if (loading) {
    return <p>Loading...</p>;
  }

  if (total === 0 && !searchQuery) {
    return (
      <div className="empty-state">
        <h3>No papers in the library yet</h3>
        <p>
          <Link to="/upload">Upload a PDF</Link> to get started.
        </p>
      </div>
    );
  }

  return (
    <div>
      {searchQuery && (
        <p style={{ marginBottom: 16, color: "var(--color-text-secondary)" }}>
          Search results for "{searchQuery}"
        </p>
      )}

      <div className="controls-bar">
        <label>
          Sort by:{" "}
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="date">Date</option>
            <option value="title">Title</option>
            <option value="year">Year</option>
          </select>
        </label>

        <div>
          <button
            className={`btn ${viewMode === "table" ? "btn-primary" : ""}`}
            onClick={() => setViewMode("table")}
            style={{ borderRadius: "var(--radius) 0 0 var(--radius)" }}
          >
            Table
          </button>
          <button
            className={`btn ${viewMode === "cards" ? "btn-primary" : ""}`}
            onClick={() => setViewMode("cards")}
            style={{ borderRadius: "0 var(--radius) var(--radius) 0", marginLeft: -1 }}
          >
            Cards
          </button>
        </div>

        <span className="total">{total} paper(s)</span>
      </div>

      {total === 0 ? (
        <div className="empty-state">
          <h3>No papers found</h3>
          <p>Try a different search query.</p>
        </div>
      ) : viewMode === "table" ? (
        <PaperTable papers={papers} />
      ) : (
        <div className="card-grid">
          {papers.map((p) => (
            <PaperCard key={p.paper_id} paper={p} />
          ))}
        </div>
      )}
    </div>
  );
}
