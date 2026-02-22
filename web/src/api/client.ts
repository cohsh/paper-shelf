import type {
  PaperDetail,
  PaperListResponse,
  TaskStatus,
} from "../types/paper";

const BASE = "/api";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function getPapers(params?: {
  sort_by?: string;
  search?: string;
  field?: string;
}): Promise<PaperListResponse> {
  const query = new URLSearchParams();
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.search) query.set("search", params.search);
  if (params?.field) query.set("field", params.field);
  const qs = query.toString();
  return fetchJSON(`${BASE}/papers${qs ? `?${qs}` : ""}`);
}

export async function getPaper(paperId: string): Promise<PaperDetail> {
  return fetchJSON(`${BASE}/papers/${paperId}`);
}

export async function getPaperMarkdown(
  paperId: string
): Promise<{ markdown: string }> {
  return fetchJSON(`${BASE}/papers/${paperId}/markdown`);
}

export async function deletePaper(paperId: string): Promise<void> {
  await fetchJSON(`${BASE}/papers/${paperId}`, { method: "DELETE" });
}

export async function uploadPaper(
  file: File,
  reader: string = "both"
): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("reader", reader);
  return fetchJSON(`${BASE}/upload`, { method: "POST", body: form });
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  return fetchJSON(`${BASE}/tasks/${taskId}`);
}
