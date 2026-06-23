export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Source = {
  subject: string;
  session: number;
  page: number;
  source: string;
};

export type ApiDocument = {
  subject: string;
  session: number;
  source: string;
  chunks: number;
};

export type IngestResult = {
  source: string;
  chunks: number;
};

export async function fetchDocuments(): Promise<ApiDocument[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error(`documents: ${res.status}`);
  return res.json();
}

export async function ingestPdf(
  file: File,
  subject: string,
  session: number,
): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("subject", subject);
  form.append("session", String(session));

  const res = await fetch(`${API_BASE}/api/ingest`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `ingest: ${res.status}`);
  }
  return res.json();
}

export type ChatHandlers = {
  onToken: (token: string) => void;
  onSources: (sources: Source[]) => void;
  onDone: () => void;
  onError: (message: string) => void;
};

// SSE購読。close用の関数を返す。
export function streamChat(
  question: string,
  topK: number | null,
  handlers: ChatHandlers,
): () => void {
  const params = new URLSearchParams({ question });
  if (topK != null) params.set("top_k", String(topK));

  const es = new EventSource(`${API_BASE}/api/chat?${params.toString()}`);

  es.addEventListener("token", (e) => handlers.onToken((e as MessageEvent).data));
  es.addEventListener("sources", (e) =>
    handlers.onSources(JSON.parse((e as MessageEvent).data)),
  );
  es.addEventListener("done", () => {
    handlers.onDone();
    es.close();
  });
  es.onerror = () => {
    handlers.onError("接続エラーが発生しました");
    es.close();
  };

  return () => es.close();
}
