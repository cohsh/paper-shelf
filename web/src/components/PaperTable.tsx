import { useNavigate } from "react-router-dom";
import type { PaperSummary } from "../types/paper";
import TagBadge from "./TagBadge";

export type SortKey = "title" | "authors" | "year" | "read_date";
export type SortOrder = "asc" | "desc";

interface Props {
  papers: PaperSummary[];
  sortBy: SortKey;
  sortOrder: SortOrder;
  onSort: (key: SortKey) => void;
}

export default function PaperTable({ papers, sortBy, sortOrder, onSort }: Props) {
  const navigate = useNavigate();

  const renderSortIndicator = (key: SortKey) => {
    if (sortBy !== key) return null;
    return <span className="sort-indicator">{sortOrder === "asc" ? "\u25B2" : "\u25BC"}</span>;
  };

  return (
    <table className="paper-table">
      <thead>
        <tr>
          <th className="sortable" onClick={() => onSort("title")}>
            Title {renderSortIndicator("title")}
          </th>
          <th className="sortable" onClick={() => onSort("authors")}>
            Authors {renderSortIndicator("authors")}
          </th>
          <th className="sortable" onClick={() => onSort("year")}>
            Year {renderSortIndicator("year")}
          </th>
          <th>Tags</th>
          <th className="sortable" onClick={() => onSort("read_date")}>
            Read Date {renderSortIndicator("read_date")}
          </th>
          <th>Readers</th>
        </tr>
      </thead>
      <tbody>
        {papers.map((p) => (
          <tr key={p.paper_id} onClick={() => navigate(`/papers/${p.paper_id}`)}>
            <td style={{ fontWeight: 500 }}>{p.title}</td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {formatAuthors(p.authors)}
              {p.venue && (
                <div style={{ fontSize: 12, fontStyle: "italic", marginTop: 2 }}>
                  {p.venue}
                </div>
              )}
            </td>
            <td>{p.year || "-"}</td>
            <td>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {p.tags.slice(0, 3).map((t) => (
                  <TagBadge key={t} tag={t} />
                ))}
              </div>
            </td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {p.read_date}
            </td>
            <td style={{ fontSize: 13 }}>
              {p.readers_used.join(", ")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatAuthors(authors: string[]): string {
  if (authors.length === 0) return "-";
  if (authors.length <= 2) return authors.join(", ");
  return `${authors[0]} et al.`;
}
