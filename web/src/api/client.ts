import type {
  ChatMessage,
  CritiqueResult,
  DiscoveryResult,
  PaperDetail,
  PaperListResponse,
  Shelf,
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
  shelf?: string;
}): Promise<PaperListResponse> {
  const query = new URLSearchParams();
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.search) query.set("search", params.search);
  if (params?.field) query.set("field", params.field);
  if (params?.shelf) query.set("shelf", params.shelf);
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
  reader: string = "both",
  shelves: string[] = []
): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("reader", reader);
  if (shelves.length > 0) {
    form.append("shelves", shelves.join(","));
  }
  return fetchJSON(`${BASE}/upload`, { method: "POST", body: form });
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  return fetchJSON(`${BASE}/tasks/${taskId}`);
}

// --- Shelf API ---

export async function getShelves(): Promise<Shelf[]> {
  return fetchJSON(`${BASE}/shelves`);
}

export async function createShelf(
  name: string,
  name_ja: string = ""
): Promise<Shelf> {
  return fetchJSON(`${BASE}/shelves`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, name_ja }),
  });
}

export async function deleteShelf(shelfId: string): Promise<void> {
  await fetchJSON(`${BASE}/shelves/${shelfId}`, { method: "DELETE" });
}

export async function setPaperShelves(
  paperId: string,
  shelfIds: string[]
): Promise<void> {
  await fetchJSON(`${BASE}/papers/${paperId}/shelves`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shelf_ids: shelfIds }),
  });
}

// --- Critique API ---

export async function generateCritique(
  paperId: string
): Promise<{ task_id: string }> {
  return fetchJSON(`${BASE}/papers/${paperId}/critique`, {
    method: "POST",
  });
}

export async function getCritique(
  paperId: string
): Promise<CritiqueResult> {
  return fetchJSON(`${BASE}/papers/${paperId}/critique`);
}

export async function sendChatMessage(
  paperId: string,
  message: string,
  history: ChatMessage[]
): Promise<{ reply: string }> {
  return fetchJSON(`${BASE}/papers/${paperId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
}

// --- Discovery API ---

export async function discoverRelated(
  paperId: string
): Promise<{ task_id: string }> {
  return fetchJSON(`${BASE}/papers/${paperId}/discover`, {
    method: "POST",
  });
}

export async function getDiscovered(
  paperId: string
): Promise<DiscoveryResult> {
  return fetchJSON(`${BASE}/papers/${paperId}/discover`);
}

export async function discoverForLibrary(): Promise<{ task_id: string }> {
  return fetchJSON(`${BASE}/discover`, { method: "POST" });
}

export async function getLibraryDiscovery(): Promise<DiscoveryResult> {
  return fetchJSON(`${BASE}/discover`);
}
