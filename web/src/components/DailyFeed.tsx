import { useCallback, useEffect, useRef, useState } from "react";
import { refreshFeed, getFeed, getTask, readFromUrl } from "../api/client";
import type { FeedResult, FeedPaper, TaskStatusValue } from "../types/paper";

interface Props {
  shelfId: string;
}

export default function DailyFeed({ shelfId }: Props) {
  const [feed, setFeed] = useState<FeedResult | null>(null);
  const [loading, setLoading] = useState(true);

  // Feed refresh state
  const [feedTaskId, setFeedTaskId] = useState<string | null>(null);
  const [feedStatus, setFeedStatus] = useState<TaskStatusValue>("pending");
  const [feedMessage, setFeedMessage] = useState("");
  const [feedRefreshing, setFeedRefreshing] = useState(false);
  const feedPollingRef = useRef<number | null>(null);

  // "Read" action state
  const [readingPaperIdx, setReadingPaperIdx] = useState<number | null>(null);
  const [readTaskId, setReadTaskId] = useState<string | null>(null);
  const [readStatus, setReadStatus] = useState<TaskStatusValue>("pending");
  const [readMessage, setReadMessage] = useState("");
  const readPollingRef = useRef<number | null>(null);

  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  // Load existing feed on mount / shelfId change
  useEffect(() => {
    setLoading(true);
    setFeed(null);
    setExpandedIdx(null);
    getFeed(shelfId)
      .then((res) => setFeed(res))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [shelfId]);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setFeedRefreshing(true);
    setFeedStatus("pending");
    setFeedMessage("Queued...");
    try {
      const res = await refreshFeed(shelfId);
      setFeedTaskId(res.task_id);
    } catch (e) {
      setFeedMessage(`Failed: ${e}`);
      setFeedRefreshing(false);
    }
  }, [shelfId]);

  // Poll feed task
  useEffect(() => {
    if (
      !feedTaskId ||
      feedStatus === "completed" ||
      feedStatus === "failed"
    )
      return;

    const poll = async () => {
      try {
        const task = await getTask(feedTaskId);
        setFeedStatus(task.status);
        setFeedMessage(task.progress_message);
        if (task.status === "completed") {
          getFeed(shelfId)
            .then((res) => {
              setFeed(res);
              setFeedRefreshing(false);
            })
            .catch(() => setFeedRefreshing(false));
        }
        if (task.status === "failed") {
          setFeedRefreshing(false);
        }
      } catch {
        // Ignore transient errors
      }
    };

    feedPollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (feedPollingRef.current) clearInterval(feedPollingRef.current);
    };
  }, [feedTaskId, feedStatus, shelfId]);

  const getPdfUrl = (paper: FeedPaper): string | null => {
    const arxivId = paper.arxiv_id || paper.external_ids?.ArXiv;
    if (arxivId) return `https://arxiv.org/pdf/${arxivId}.pdf`;
    if (paper.url && paper.url.match(/\.pdf($|\?)/i)) return paper.url;
    return null;
  };

  // Handle "Read this paper"
  const handleRead = useCallback(
    async (paper: FeedPaper, idx: number) => {
      const pdfUrl = getPdfUrl(paper);
      if (!pdfUrl) return;

      setReadingPaperIdx(idx);
      setReadStatus("pending");
      setReadMessage("Starting...");

      try {
        const res = await readFromUrl(pdfUrl, "both", [shelfId]);
        setReadTaskId(res.task_id);
      } catch (e) {
        setReadMessage(`Failed: ${e}`);
        setReadingPaperIdx(null);
      }
    },
    [shelfId]
  );

  // Poll read task
  useEffect(() => {
    if (
      !readTaskId ||
      readStatus === "completed" ||
      readStatus === "failed"
    )
      return;

    const poll = async () => {
      try {
        const task = await getTask(readTaskId);
        setReadStatus(task.status);
        setReadMessage(task.progress_message);
        if (task.status === "completed" || task.status === "failed") {
          setTimeout(() => {
            setReadingPaperIdx(null);
            setReadTaskId(null);
          }, 3000);
        }
      } catch {
        // Ignore
      }
    };

    readPollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (readPollingRef.current) clearInterval(readPollingRef.current);
    };
  }, [readTaskId, readStatus]);

  const getExternalLink = (
    externalIds: Record<string, string>
  ): { label: string; url: string } | null => {
    if (externalIds.ArXiv) {
      return {
        label: "arXiv",
        url: `https://arxiv.org/abs/${externalIds.ArXiv}`,
      };
    }
    if (externalIds.DOI) {
      return { label: "DOI", url: `https://doi.org/${externalIds.DOI}` };
    }
    return null;
  };

  if (loading) {
    return <p>Loading feed...</p>;
  }

  return (
    <div>
      <div className="controls-bar">
        <button
          className="btn btn-primary"
          onClick={handleRefresh}
          disabled={feedRefreshing}
        >
          {feedRefreshing
            ? "Refreshing..."
            : feed
              ? "Refresh Feed"
              : "Load Feed"}
        </button>
        {feed && <span className="total">{feed.papers.length} paper(s)</span>}
      </div>

      {feedRefreshing && !feed && (
        <div className="progress-steps">
          <div
            className={`progress-step ${feedStatus === "failed" ? "failed" : "active"}`}
          >
            <div
              className={`step-icon ${feedStatus === "failed" ? "failed" : "active"}`}
            >
              {feedStatus === "failed" ? "\u2717" : "1"}
            </div>
            <span>{feedMessage || "Generating feed..."}</span>
          </div>
        </div>
      )}

      {feedRefreshing && feed && (
        <p
          style={{
            marginBottom: 12,
            fontSize: 13,
            color: "var(--color-text-secondary)",
          }}
        >
          {feedMessage || "Refreshing feed..."}
        </p>
      )}

      {feed && (
        <div className="discovery-results">
          {feed.papers.map((paper, i) => {
            const extLink = getExternalLink(paper.external_ids);
            const isExpanded = expandedIdx === i;
            const isReading = readingPaperIdx === i;
            const hasPdf = !!getPdfUrl(paper);

            return (
              <div key={i} className="discovery-paper">
                <div
                  className="discovery-paper-header"
                  onClick={() =>
                    setExpandedIdx(isExpanded ? null : i)
                  }
                >
                  <div className="discovery-paper-title">
                    <span
                      className={`critique-chevron ${isExpanded ? "open" : ""}`}
                    >
                      &#9654;
                    </span>
                    {paper.title}
                  </div>
                  <div className="discovery-paper-meta">
                    {paper.authors.length > 0 && (
                      <span>
                        {paper.authors.slice(0, 3).join(", ")}
                        {paper.authors.length > 3 ? " et al." : ""}
                      </span>
                    )}
                    {(paper.published || paper.year > 0) && (
                      <span>{paper.published ? paper.published.slice(0, 10) : paper.year}</span>
                    )}
                    {paper.venue && (
                      <span className="discovery-venue">{paper.venue}</span>
                    )}
                    {extLink && (
                      <a
                        href={extLink.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="discovery-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {extLink.label}
                      </a>
                    )}
                    {hasPdf && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRead(paper, i);
                        }}
                        disabled={readingPaperIdx !== null}
                        style={{ marginLeft: 4 }}
                      >
                        {isReading ? readMessage || "Reading..." : "Read"}
                      </button>
                    )}
                  </div>
                </div>

                {isExpanded && paper.abstract && (
                  <div className="discovery-paper-abstract">
                    <p>{paper.abstract}</p>
                  </div>
                )}
              </div>
            );
          })}

          <p
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "var(--color-text-secondary)",
            }}
          >
            Generated: {new Date(feed.generated_at).toLocaleString()} |
            Sources: arXiv ({feed.source_counts.arxiv}), OpenAlex (
            {feed.source_counts.openalex})
          </p>
        </div>
      )}

      {!feed && !feedRefreshing && (
        <div className="empty-state">
          <h3>No feed yet</h3>
          <p>Click &ldquo;Load Feed&rdquo; to discover recent papers for this shelf.</p>
        </div>
      )}
    </div>
  );
}
