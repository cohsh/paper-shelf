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
  key_contributions: string[];
  methodology: string;
  main_results: string;
  limitations: string[];
  connections: string;
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
