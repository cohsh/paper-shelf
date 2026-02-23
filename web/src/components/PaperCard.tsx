import { useNavigate } from "react-router-dom";
import type { PaperSummary } from "../types/paper";
import TagBadge from "./TagBadge";

interface Props {
  paper: PaperSummary;
}

export default function PaperCard({ paper }: Props) {
  const navigate = useNavigate();

  const authors =
    paper.authors.length <= 2
      ? paper.authors.join(", ")
      : `${paper.authors[0]} et al.`;

  return (
    <div className="card" onClick={() => navigate(`/papers/${paper.paper_id}`)}>
      <div className="paper-card-title">{paper.title}</div>
      <div className="paper-card-meta">
        {authors} &middot; {paper.year || "?"}
        {paper.venue && <> &middot; <em>{paper.venue}</em></>}
        &middot; {paper.read_date} &middot; {paper.readers_used.join(", ")}
      </div>
      <div className="paper-card-tags">
        {paper.tags.slice(0, 5).map((t) => (
          <TagBadge key={t} tag={t} />
        ))}
      </div>
    </div>
  );
}
