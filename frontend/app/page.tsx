"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ApiDocument,
  Source,
  fetchDocuments,
  ingestFile,
  streamChat,
} from "@/lib/api";

function formatTs(sec: number): string {
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(ss)}` : `${pad(m)}:${pad(ss)}`;
}

export default function Home() {
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const closeRef = useRef<(() => void) | null>(null);

  const reloadDocuments = () => {
    fetchDocuments()
      .then(setDocuments)
      .catch(() => setError("資料一覧の取得に失敗しました（APIサーバ未起動?）"));
  };

  useEffect(() => {
    reloadDocuments();
    return () => closeRef.current?.();
  }, []);

  const ask = () => {
    if (!question.trim() || streaming) return;
    setAnswer("");
    setSources([]);
    setError("");
    setStreaming(true);

    closeRef.current = streamChat(question, null, {
      onToken: (t) => setAnswer((prev) => prev + t),
      onSources: setSources,
      onDone: () => setStreaming(false),
      onError: (msg) => {
        setError(msg);
        setStreaming(false);
      },
    });
  };

  return (
    <div className="flex flex-1 min-h-screen">
      <SourcePanel documents={documents} onIngested={reloadDocuments} />

      <main className="flex flex-col flex-1">
        <header className="border-b border-black/10 dark:border-white/15 px-6 py-4">
          <h1 className="text-lg font-semibold">ayame</h1>
          <p className="text-xs opacity-60">ローカルNotebookLM — 講義資料RAG</p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {error && (
            <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          {answer ? (
            <article className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{answer}</ReactMarkdown>
            </article>
          ) : (
            !streaming && (
              <p className="opacity-50 text-sm">
                左の資料について質問してください。
              </p>
            )
          )}
          {streaming && !answer && (
            <p className="opacity-50 text-sm animate-pulse">生成中...</p>
          )}

          {sources.length > 0 && (
            <section className="mt-8">
              <h2 className="text-xs font-semibold opacity-60 mb-2">出典</h2>
              <ul className="flex flex-col gap-2">
                {sources.map((s, i) => (
                  <li
                    key={i}
                    className="text-xs border border-black/10 dark:border-white/15 rounded px-3 py-2"
                  >
                    <span className="font-medium">{s.subject}</span> 第{s.session}回{" "}
                    {s.kind === "media" ? formatTs(s.start ?? 0) : `p.${s.page}`}{" "}
                    <span className="opacity-50">({s.source})</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <div className="border-t border-black/10 dark:border-white/15 p-4">
          <div className="flex gap-2">
            <input
              className="flex-1 rounded border border-black/15 dark:border-white/20 bg-transparent px-3 py-2 text-sm"
              placeholder="質問を入力..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.nativeEvent.isComposing) ask();
              }}
              disabled={streaming}
            />
            <button
              className="rounded bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-40"
              onClick={ask}
              disabled={streaming || !question.trim()}
            >
              質問
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

function SourcePanel({
  documents,
  onIngested,
}: {
  documents: ApiDocument[];
  onIngested: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [subject, setSubject] = useState("");
  const [session, setSession] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const upload = async () => {
    if (!file || !subject || !session) return;
    setBusy(true);
    setMsg("");
    try {
      const res = await ingestFile(file, subject, Number(session));
      setMsg(`取り込み完了: ${res.source}（${res.chunks}チャンク）`);
      setFile(null);
      setSubject("");
      setSession("");
      onIngested();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "取り込みに失敗しました");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="w-72 shrink-0 border-r border-black/10 dark:border-white/15 flex flex-col">
      <div className="px-4 py-4 border-b border-black/10 dark:border-white/15">
        <h2 className="text-xs font-semibold opacity-60 mb-3">
          資料を取り込む（PDF・音声・動画）
        </h2>
        <div className="flex flex-col gap-2">
          <input
            type="file"
            accept="application/pdf,audio/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-xs"
          />
          <input
            className="rounded border border-black/15 dark:border-white/20 bg-transparent px-2 py-1 text-xs"
            placeholder="科目名"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <input
            type="number"
            className="rounded border border-black/15 dark:border-white/20 bg-transparent px-2 py-1 text-xs"
            placeholder="講義回"
            value={session}
            onChange={(e) => setSession(e.target.value)}
          />
          <button
            className="rounded bg-foreground text-background px-3 py-1.5 text-xs font-medium disabled:opacity-40"
            onClick={upload}
            disabled={busy || !file || !subject || !session}
          >
            {busy ? "取り込み中..." : "取り込む"}
          </button>
          <p className="text-[11px] opacity-50">
            音声・動画は文字起こしのため時間がかかります
          </p>
          {msg && <p className="text-[11px] opacity-70">{msg}</p>}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <h2 className="text-xs font-semibold opacity-60 mb-3">
          取り込み済み資料 ({documents.length})
        </h2>
        <ul className="flex flex-col gap-2">
          {documents.map((d) => (
            <li key={d.source} className="text-xs leading-tight">
              <p className="font-medium truncate" title={d.source}>
                {d.source}
              </p>
              <p className="opacity-50">
                {d.subject} 第{d.session}回 · {d.chunks}チャンク
              </p>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
