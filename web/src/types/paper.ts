export interface Shelf {
  shelf_id: string;
  name: string;
  name_ja: string;
  paper_count: number;
  is_virtual: boolean;
  created_at?: string;
}

export interface PaperSummary {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  venue?: string;
  read_date: string;
  tags: string[];
  readers_used: string[];
  shelves?: string[];
}

export interface ReadingResult {
  title: string;
  authors: string[];
  year: number;
  venue?: string;
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

export interface CritiqueResult {
  assumptions: string[];
  assumptions_ja?: string[];
  weaknesses: string[];
  weaknesses_ja?: string[];
  unverified_claims: string[];
  unverified_claims_ja?: string[];
  fragile_points: string[];
  fragile_points_ja?: string[];
  applications: string[];
  applications_ja?: string[];
  overall_assessment: string;
  overall_assessment_ja?: string;
  generated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface DiscoveredPaper {
  title: string;
  authors: string[];
  year: number;
  abstract: string;
  venue: string;
  url: string;
  external_ids: Record<string, string>;
}

export interface DiscoveryResult {
  papers: DiscoveredPaper[];
  generated_at: string;
}

export interface PaperDetail {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  venue?: string;
  read_date: string;
  source_file: string;
  page_count: number;
  tags: string[];
  readers_used: string[];
  shelves?: string[];
  readings: {
    claude?: ReadingResult;
    codex?: ReadingResult;
  };
  critique?: CritiqueResult;
  discovered?: DiscoveryResult;
}

export type TaskStatusValue =
  | "pending"
  | "extracting"
  | "reading_claude"
  | "reading_codex"
  | "saving"
  | "analyzing"
  | "discovering"
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
