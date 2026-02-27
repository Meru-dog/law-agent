// Empty string = same-origin (routed through Next.js rewrites in dev).
// Set NEXT_PUBLIC_API_URL to a full URL when deploying separately.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface CitationInfo {
  context_number: number;
  doc_id: string;
  anchor: string;
}

export interface ChunkResult {
  chunk_id: string;
  doc_id: string;
  chunk_text: string;
  anchor_start: string;
  anchor_end: string;
  similarity_score: number;
}

export interface QueryResponse {
  matter_id: string;
  query: string;
  answer: string;
  query_id: string;
  citations: CitationInfo[];
  abstained: boolean;
  confidence: number;
  retrieval_trace: ChunkResult[];
}

export interface DocumentUploadResponse {
  doc_id: string;
  matter_id: string;
  filename: string;
  doc_type: string;
  anchors: { anchor_type: string; anchor_value: string; text_preview: string }[];
}

function headers(userId: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-User-Id": userId,
  };
}

export async function queryMatter(
  matterId: string,
  query: string,
  userId: string
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/v1/query`, {
    method: "POST",
    headers: headers(userId),
    body: JSON.stringify({ matter_id: matterId, query }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}

export async function uploadDocument(
  matterId: string,
  file: File,
  userId: string
): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/v1/documents/upload?matter_id=${encodeURIComponent(matterId)}`, {
    method: "POST",
    headers: { "X-User-Id": userId },
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}
