export interface PaperSummary {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  read_date: string;
  tags: string[];
  readers_used: string[];
}

export interface ReadingResult {
  title: string;
  authors: string[];
  year: number;
  abstract_summary: string;
  abstract_summary_ja?: string;
  key_contributions: string[];
  key_contributions_ja?: string[];
  methodology: string;
  methodology_ja?: string;
  main_results: string;
  main_results_ja?: string;
  limitations: string[];
  limitations_ja?: string[];
  connections: string;
  connections_ja?: string;
  tags: string[];
  confidence_notes?: string;
  summary_ja?: string;
}

export interface PaperDetail {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  read_date: string;
  source_file: string;
  page_count: number;
  tags: string[];
  readers_used: string[];
  readings: {
    claude?: ReadingResult;
    codex?: ReadingResult;
  };
}

export type TaskStatusValue =
  | "pending"
  | "extracting"
  | "reading_claude"
  | "reading_codex"
  | "saving"
  | "completed"
  | "failed";

export interface TaskStatus {
  task_id: string;
  status: TaskStatusValue;
  progress_message: string;
  paper_id: string | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface PaperListResponse {
  papers: PaperSummary[];
  total: number;
}
