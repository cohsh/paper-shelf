import { useState } from "react";
import type { DiscoveryResult } from "../types/paper";

interface Props {
  discovery: DiscoveryResult;
}

export default function DiscoveryResults({ discovery }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

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

  return (
    <div className="discovery-results">
      {discovery.papers.map((paper, i) => {
        const extLink = getExternalLink(paper.external_ids);
        const isExpanded = expandedIdx === i;

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
              </div>
            </div>

            {isExpanded && (paper.abstract || paper.abstract_ja) && (
              <div className="discovery-paper-abstract">
                {paper.abstract_ja && (
                  <p style={{ fontFamily: "'Noto Sans JP', sans-serif" }}>{paper.abstract_ja}</p>
                )}
                {paper.abstract && (
                  <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{paper.abstract}</p>
                )}
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
