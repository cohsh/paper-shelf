import { useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { getPapers } from "../api/client";
import type { PaperSummary } from "../types/paper";
import PaperTable from "../components/PaperTable";
import type { SortKey, SortOrder } from "../components/PaperTable";
import PaperCard from "../components/PaperCard";
import ShelfSidebar from "../components/ShelfSidebar";

type ViewMode = "table" | "cards";

export default function LibraryPage() {
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState<SortKey>("read_date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [loading, setLoading] = useState(true);
  const [activeShelfId, setActiveShelfId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getPapers({
      search: searchQuery || undefined,
      shelf: activeShelfId || undefined,
    })
      .then((res) => {
        setPapers(res.papers);
        setTotal(res.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [searchQuery, activeShelfId]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder(key === "title" || key === "authors" ? "asc" : "desc");
    }
  };

  const sortedPapers = useMemo(() => {
    const sorted = [...papers];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case "title":
          cmp = a.title.toLowerCase().localeCompare(b.title.toLowerCase());
          break;
        case "authors": {
          const aa = a.authors[0]?.toLowerCase() ?? "";
          const bb = b.authors[0]?.toLowerCase() ?? "";
          cmp = aa.localeCompare(bb);
          break;
        }
        case "year":
          cmp = (a.year || 0) - (b.year || 0);
          break;
        case "read_date":
          cmp = (a.read_date || "").localeCompare(b.read_date || "");
          break;
      }
      return sortOrder === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [papers, sortBy, sortOrder]);

  if (loading) {
    return <p>Loading...</p>;
  }

  if (total === 0 && !searchQuery && activeShelfId === null) {
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
    <div className="library-layout">
      <ShelfSidebar
        activeShelfId={activeShelfId}
        onSelectShelf={setActiveShelfId}
      />
      <div className="library-main">
        {searchQuery && (
          <p style={{ marginBottom: 16, color: "var(--color-text-secondary)" }}>
            Search results for &ldquo;{searchQuery}&rdquo;
          </p>
        )}

        <div className="controls-bar">
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
            <p>Try a different search query or shelf.</p>
          </div>
        ) : viewMode === "table" ? (
          <PaperTable
            papers={sortedPapers}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
        ) : (
          <div className="card-grid">
            {sortedPapers.map((p) => (
              <PaperCard key={p.paper_id} paper={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
