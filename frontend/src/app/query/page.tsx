"use client";

import { Suspense, useCallback, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { queryMatter, uploadDocument, type QueryResponse } from "@/lib/api";

function QueryPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const matterId = params.get("matter_id") ?? "";
  const userId = params.get("user_id") ?? "user-1";

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);

  // Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ filename: string; anchors: number } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function handleQuery() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await queryMatter(matterId, query.trim(), userId);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const res = await uploadDocument(matterId, file, userId);
      setUploadResult({ filename: res.filename, anchors: res.anchors.length });
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [matterId, userId]
  );

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* Nav */}
      <nav
        style={{
          borderBottom: "1px solid var(--border-light)",
          background: "rgba(255,255,255,0.85)",
          backdropFilter: "saturate(180%) blur(20px)",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0 32px",
            height: 52,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <button
            onClick={() => router.push("/")}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 17,
              color: "var(--accent)",
              padding: "4px 0",
              fontWeight: 400,
            }}
          >
            ← LexRAG
          </button>
          <span style={{ color: "var(--border)", fontSize: 17 }}>|</span>
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text-secondary)",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-light)",
              borderRadius: 6,
              padding: "3px 10px",
            }}
          >
            {matterId}
          </span>
          <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--text-tertiary)" }}>
            {userId}
          </span>
        </div>
      </nav>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 32px 80px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 32 }}>
          {/* Left column: Query + Results */}
          <div>
            {/* Query input */}
            <div
              style={{
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border-light)",
                overflow: "hidden",
                marginBottom: 32,
              }}
            >
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleQuery();
                }}
                placeholder="Ask a question about this matter… (⌘↵ to submit)"
                rows={4}
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  padding: "20px 24px",
                  fontSize: 17,
                  color: "var(--text-primary)",
                  resize: "none",
                  outline: "none",
                  fontFamily: "inherit",
                  lineHeight: 1.5,
                }}
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  padding: "12px 16px",
                  borderTop: "1px solid var(--border-light)",
                }}
              >
                <button
                  onClick={handleQuery}
                  disabled={!query.trim() || loading}
                  style={{
                    padding: "10px 22px",
                    background: query.trim() && !loading ? "var(--accent)" : "var(--border)",
                    color: "white",
                    border: "none",
                    borderRadius: "var(--radius-sm)",
                    fontSize: 15,
                    fontWeight: 500,
                    cursor: query.trim() && !loading ? "pointer" : "not-allowed",
                    transition: "background 0.15s",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  {loading ? <Spinner /> : null}
                  {loading ? "Thinking…" : "Ask"}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div
                style={{
                  background: "rgba(192, 57, 43, 0.06)",
                  border: "1px solid rgba(192, 57, 43, 0.3)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px 20px",
                  marginBottom: 24,
                  color: "var(--error)",
                  fontSize: 14,
                }}
              >
                {error}
              </div>
            )}

            {/* Result */}
            {result && (
              <div>
                {/* Confidence + abstain */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                  <ConfidenceBadge confidence={result.confidence} abstained={result.abstained} />
                  {result.abstained && (
                    <span style={{ fontSize: 13, color: "var(--warning)", fontWeight: 500 }}>
                      Model abstained from answering
                    </span>
                  )}
                </div>

                {/* Answer */}
                <div
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-light)",
                    borderRadius: "var(--radius-lg)",
                    padding: "28px 32px",
                    marginBottom: 24,
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  <p
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      letterSpacing: "0.09em",
                      textTransform: "uppercase",
                      color: "var(--text-tertiary)",
                      marginBottom: 14,
                    }}
                  >
                    Answer
                  </p>
                  <AnswerText text={result.answer} citations={result.citations} />
                </div>

                {/* Citations */}
                {result.citations.length > 0 && (
                  <div
                    style={{
                      background: "var(--bg-secondary)",
                      borderRadius: "var(--radius-md)",
                      padding: "20px 24px",
                      marginBottom: 16,
                      border: "1px solid var(--border-light)",
                    }}
                  >
                    <p
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: "0.09em",
                        textTransform: "uppercase",
                        color: "var(--text-tertiary)",
                        marginBottom: 14,
                      }}
                    >
                      Citations
                    </p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {result.citations.map((c) => (
                        <div
                          key={c.context_number}
                          style={{ display: "flex", alignItems: "baseline", gap: 10, fontSize: 14 }}
                        >
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              width: 20,
                              height: 20,
                              borderRadius: "50%",
                              background: "var(--accent)",
                              color: "white",
                              fontSize: 11,
                              fontWeight: 700,
                              flexShrink: 0,
                            }}
                          >
                            {c.context_number}
                          </span>
                          <span style={{ color: "var(--text-secondary)" }}>
                            Doc{" "}
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: 12,
                                color: "var(--text-primary)",
                              }}
                            >
                              {c.doc_id.slice(0, 8)}…
                            </span>{" "}
                            · ¶{c.anchor}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Retrieval trace toggle */}
                <button
                  onClick={() => setTraceOpen((o) => !o)}
                  style={{
                    background: "none",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)",
                    padding: "8px 16px",
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {traceOpen ? "▾" : "▸"} Retrieval trace ({result.retrieval_trace.length} chunks)
                </button>

                {traceOpen && (
                  <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                    {result.retrieval_trace.map((chunk) => (
                      <div
                        key={chunk.chunk_id}
                        style={{
                          background: "var(--bg-secondary)",
                          borderRadius: "var(--radius-sm)",
                          padding: "14px 18px",
                          border: "1px solid var(--border-light)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 8,
                            gap: 8,
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: 11,
                              color: "var(--text-tertiary)",
                            }}
                          >
                            {chunk.doc_id.slice(0, 8)}… · ¶{chunk.anchor_start}
                            {chunk.anchor_end !== chunk.anchor_start ? `–${chunk.anchor_end}` : ""}
                          </span>
                          <ScoreBar score={chunk.similarity_score} />
                        </div>
                        <p
                          style={{
                            fontSize: 13,
                            color: "var(--text-secondary)",
                            lineHeight: 1.6,
                            margin: 0,
                            display: "-webkit-box",
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {chunk.chunk_text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right column: Upload panel */}
          <div>
            <div
              style={{
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border-light)",
                padding: "24px",
                position: "sticky",
                top: 72,
              }}
            >
              <p
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.09em",
                  textTransform: "uppercase",
                  color: "var(--text-tertiary)",
                  marginBottom: 16,
                }}
              >
                Add Document
              </p>

              {/* Drop zone */}
              <div
                onDrop={onDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed var(--border)",
                  borderRadius: "var(--radius-md)",
                  padding: "32px 16px",
                  textAlign: "center",
                  cursor: "pointer",
                  background: "var(--bg-primary)",
                  transition: "border-color 0.15s",
                  marginBottom: 12,
                }}
              >
                <p style={{ fontSize: 32, margin: "0 0 8px" }}>📄</p>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                  Drop PDF or DOCX here
                  <br />
                  <span style={{ color: "var(--accent)", fontWeight: 500 }}>or click to browse</span>
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc"
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />

              {uploading && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    padding: "8px 0",
                  }}
                >
                  <Spinner /> Processing document…
                </div>
              )}

              {uploadResult && (
                <div
                  style={{
                    background: "rgba(29, 131, 72, 0.08)",
                    border: "1px solid rgba(29, 131, 72, 0.25)",
                    borderRadius: "var(--radius-sm)",
                    padding: "10px 14px",
                    fontSize: 13,
                    color: "var(--success)",
                    lineHeight: 1.5,
                  }}
                >
                  ✓ <strong>{uploadResult.filename}</strong> ingested
                  <br />
                  {uploadResult.anchors} anchors extracted
                </div>
              )}

              {uploadError && (
                <div
                  style={{
                    background: "rgba(192, 57, 43, 0.06)",
                    border: "1px solid rgba(192, 57, 43, 0.3)",
                    borderRadius: "var(--radius-sm)",
                    padding: "10px 14px",
                    fontSize: 13,
                    color: "var(--error)",
                  }}
                >
                  {uploadError}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Renders answer text with citation markers highlighted
function AnswerText({
  text,
  citations,
}: {
  text: string;
  citations: { context_number: number }[];
}) {
  const citNums = citations.map((c) => c.context_number);

  // Split on [N] citation markers
  const parts = text.split(/(\[\d+\])/g);

  return (
    <p style={{ fontSize: 17, lineHeight: 1.7, color: "var(--text-primary)", margin: 0 }}>
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const num = Number(match[1]);
          const isValid = citNums.includes(num);
          return (
            <sup
              key={i}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 18,
                height: 18,
                borderRadius: "50%",
                background: isValid ? "var(--accent)" : "var(--border)",
                color: "white",
                fontSize: 10,
                fontWeight: 700,
                verticalAlign: "super",
                margin: "0 1px",
                lineHeight: 1,
              }}
            >
              {num}
            </sup>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}

function ConfidenceBadge({ confidence, abstained }: { confidence: number; abstained: boolean }) {
  const pct = Math.round(confidence * 100);
  const color = abstained
    ? "var(--warning)"
    : pct >= 70
    ? "var(--success)"
    : pct >= 40
    ? "var(--warning)"
    : "var(--error)";

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border-light)",
        borderRadius: "var(--radius-sm)",
        padding: "4px 10px",
        fontSize: 12,
        fontWeight: 600,
        color,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {pct}% confidence
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score));
  const color = pct >= 0.7 ? "var(--success)" : pct >= 0.4 ? "var(--warning)" : "var(--border)";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          width: 60,
          height: 4,
          background: "var(--border-light)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct * 100}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
          }}
        />
      </div>
      <span style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
        {Math.round(pct * 100)}%
      </span>
    </div>
  );
}

function Spinner() {
  return (
    <span
      style={{
        display: "inline-block",
        width: 14,
        height: 14,
        border: "2px solid rgba(255,255,255,0.4)",
        borderTopColor: "white",
        borderRadius: "50%",
        animation: "spin 0.7s linear infinite",
      }}
    />
  );
}

export default function QueryPage() {
  return (
    <Suspense>
      <QueryPageInner />
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Suspense>
  );
}
