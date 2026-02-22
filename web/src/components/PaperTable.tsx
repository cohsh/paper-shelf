import { useNavigate } from "react-router-dom";
import type { PaperSummary } from "../types/paper";
import TagBadge from "./TagBadge";

interface Props {
  papers: PaperSummary[];
}

export default function PaperTable({ papers }: Props) {
  const navigate = useNavigate();

  return (
    <table className="paper-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Authors</th>
          <th>Year</th>
          <th>Tags</th>
          <th>Read Date</th>
          <th>Readers</th>
        </tr>
      </thead>
      <tbody>
        {papers.map((p) => (
          <tr key={p.paper_id} onClick={() => navigate(`/papers/${p.paper_id}`)}>
            <td style={{ fontWeight: 500 }}>{p.title}</td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {formatAuthors(p.authors)}
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
