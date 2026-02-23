import { useCallback, useEffect, useRef, useState } from "react";
import { readFromUrl, getTask } from "../api/client";
import type { DiscoveredPaper, DiscoveryResult, TaskStatusValue } from "../types/paper";

interface Props {
  discovery: DiscoveryResult;
  shelves?: string[];
}

export default function DiscoveryResults({ discovery, shelves }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  // Read action state
  const [readingPaperIdx, setReadingPaperIdx] = useState<number | null>(null);
  const [readTaskId, setReadTaskId] = useState<string | null>(null);
  const [readStatus, setReadStatus] = useState<TaskStatusValue>("pending");
  const [readMessage, setReadMessage] = useState("");
  const readPollingRef = useRef<number | null>(null);

  const toggleExpand = (idx: number) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  const getExternalLink = (externalIds: Record<string, string>): { label: string; url: string } | null => {
    if (externalIds.ArXiv) {
      return { label: "arXiv", url: `https://arxiv.org/abs/${externalIds.ArXiv}` };
    }
    if (externalIds.DOI) {
      return { label: "DOI", url: `https://doi.org/${externalIds.DOI}` };
    }
    if (externalIds.PubMed) {
      return { label: "PubMed", url: `https://pubmed.ncbi.nlm.nih.gov/${externalIds.PubMed}` };
    }
    return null;
  };

  const getPdfUrl = (paper: DiscoveredPaper): string | null => {
    const arxivId = paper.external_ids?.ArXiv;
    if (arxivId) return `https://arxiv.org/pdf/${arxivId}.pdf`;
    // Use open access URL if it looks like a PDF
    if (paper.url && paper.url.match(/\.pdf($|\?)/i)) return paper.url;
    return null;
  };

  const handleRead = useCallback(
    async (paper: DiscoveredPaper, idx: number) => {
      const pdfUrl = getPdfUrl(paper);
      if (!pdfUrl) return;

      setReadingPaperIdx(idx);
      setReadStatus("pending");
      setReadMessage("Starting...");

      try {
        const res = await readFromUrl(pdfUrl, "both", shelves || []);
        setReadTaskId(res.task_id);
      } catch (e) {
        setReadMessage(`Failed: ${e}`);
        setReadingPaperIdx(null);
      }
    },
    [shelves]
  );

  // Poll read task
  useEffect(() => {
    if (!readTaskId || readStatus === "completed" || readStatus === "failed") return;

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
        // Ignore transient errors
      }
    };

    readPollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (readPollingRef.current) clearInterval(readPollingRef.current);
    };
  }, [readTaskId, readStatus]);

  return (
    <div className="discovery-results">
      {discovery.papers.map((paper, i) => {
        const extLink = getExternalLink(paper.external_ids);
        const isExpanded = expandedIdx === i;
        const hasPdf = !!getPdfUrl(paper);
        const isReading = readingPaperIdx === i;

        return (
          <div key={i} className="discovery-paper">
            <div className="discovery-paper-header" onClick={() => toggleExpand(i)}>
              <div className="discovery-paper-title">
                <span className={`critique-chevron ${isExpanded ? "open" : ""}`}>&#9654;</span>
                {paper.title}
              </div>
              <div className="discovery-paper-meta">
                {paper.authors.length > 0 && (
                  <span>{paper.authors.slice(0, 3).join(", ")}{paper.authors.length > 3 ? " et al." : ""}</span>
                )}
                {(paper.published_date || paper.year > 0) && <span>{paper.published_date || paper.year}</span>}
                {paper.venue && <span className="discovery-venue">{paper.venue}</span>}
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
                {paper.url && (
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="discovery-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    OpenAlex
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
        Generated: {new Date(discovery.generated_at).toLocaleString()} | Powered by OpenAlex
      </p>
    </div>
  );
}
