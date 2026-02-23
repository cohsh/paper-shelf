import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { getPapers, discoverForLibrary, getLibraryDiscovery, getTask } from "../api/client";
import type { DiscoveryResult, PaperSummary, TaskStatusValue } from "../types/paper";
import PaperTable from "../components/PaperTable";
import type { SortKey, SortOrder } from "../components/PaperTable";
import PaperCard from "../components/PaperCard";
import ShelfSidebar from "../components/ShelfSidebar";
import DiscoveryResults from "../components/DiscoveryResults";
import DailyFeed from "../components/DailyFeed";

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
  const [activeTab, setActiveTab] = useState<"papers" | "feed">("papers");

  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null);
  const [discoveryOpen, setDiscoveryOpen] = useState(false);
  const [discoveryTaskId, setDiscoveryTaskId] = useState<string | null>(null);
  const [discoveryStatus, setDiscoveryStatus] = useState<TaskStatusValue>("pending");
  const [discoveryMessage, setDiscoveryMessage] = useState("");
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const discoveryPollingRef = useRef<number | null>(null);

  // Reset tab when shelf changes
  useEffect(() => {
    setActiveTab("papers");
  }, [activeShelfId]);

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

  // Load existing library discovery results when shelf changes
  useEffect(() => {
    setDiscoveryResult(null);
    setDiscoveryOpen(false);
    getLibraryDiscovery(activeShelfId)
      .then((res) => setDiscoveryResult(res))
      .catch(() => {});
  }, [activeShelfId]);

  const handleLibraryDiscover = useCallback(async () => {
    setDiscoveryRunning(true);
    setDiscoveryOpen(true);
    try {
      const res = await discoverForLibrary(activeShelfId);
      setDiscoveryTaskId(res.task_id);
      setDiscoveryStatus("pending");
      setDiscoveryMessage("Queued...");
    } catch (e) {
      setDiscoveryMessage(`Failed: ${e}`);
      setDiscoveryRunning(false);
    }
  }, [activeShelfId]);

  // Poll library discovery task status
  useEffect(() => {
    if (!discoveryTaskId || discoveryStatus === "completed" || discoveryStatus === "failed") return;

    const poll = async () => {
      try {
        const task = await getTask(discoveryTaskId);
        setDiscoveryStatus(task.status);
        setDiscoveryMessage(task.progress_message);
        if (task.status === "completed") {
          getLibraryDiscovery(activeShelfId)
            .then((res) => {
              setDiscoveryResult(res);
              setDiscoveryRunning(false);
            })
            .catch(() => setDiscoveryRunning(false));
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
  }, [discoveryTaskId, discoveryStatus, activeShelfId]);

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

        {activeShelfId && activeShelfId !== "__unsorted__" && (
          <div className="reader-tabs" style={{ marginBottom: 16 }}>
            <button
              className={`reader-tab ${activeTab === "papers" ? "active" : ""}`}
              onClick={() => setActiveTab("papers")}
            >
              Papers
            </button>
            <button
              className={`reader-tab ${activeTab === "feed" ? "active" : ""}`}
              onClick={() => setActiveTab("feed")}
            >
              Daily Feed
            </button>
          </div>
        )}

        {(!activeShelfId || activeShelfId === "__unsorted__" || activeTab === "papers") ? (
          <>
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

              <button
                className="btn"
                onClick={handleLibraryDiscover}
                disabled={discoveryRunning || total === 0}
              >
                {discoveryRunning ? "Discovering..." : "Discover"}
              </button>

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

            {(discoveryOpen || discoveryResult) && (
              <div style={{ marginTop: 32, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
                <div
                  className="collapsible-header"
                  onClick={() => setDiscoveryOpen(!discoveryOpen)}
                >
                  <div className="reading-section-header" style={{ flex: 1 }}>
                    <h2 style={{ cursor: "pointer" }}>
                      <span className={`critique-chevron ${discoveryOpen ? "open" : ""}`}>&#9654;</span>
                      Suggested Papers
                    </h2>
                    {discoveryResult && (
                      <button
                        className="btn btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLibraryDiscover();
                        }}
                        disabled={discoveryRunning}
                        style={{ marginLeft: 8 }}
                      >
                        {discoveryRunning ? "Searching..." : "Refresh"}
                      </button>
                    )}
                  </div>
                </div>
                {discoveryOpen && (
                  <div className="collapsible-body">
                    {discoveryRunning && !discoveryResult ? (
                      <div className="progress-steps">
                        <div className={`progress-step ${discoveryStatus === "failed" ? "failed" : "active"}`}>
                          <div className={`step-icon ${discoveryStatus === "failed" ? "failed" : "active"}`}>
                            {discoveryStatus === "failed" ? "\u2717" : "1"}
                          </div>
                          <span>{discoveryMessage || "Analyzing library and searching for papers..."}</span>
                        </div>
                      </div>
                    ) : discoveryResult ? (
                      <DiscoveryResults discovery={discoveryResult} />
                    ) : null}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <DailyFeed shelfId={activeShelfId!} />
        )}
      </div>
    </div>
  );
}
