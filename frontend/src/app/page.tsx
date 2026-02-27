"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const DEMO_MATTERS = [
  {
    id: "matter-1",
    title: "Acme Corp — Widget Supply",
    description: "Commercial contract review, payment terms, warranty obligations.",
    tag: "Contract",
  },
  {
    id: "matter-2",
    title: "Riverside Project",
    description: "Real estate acquisition, due diligence, environmental review.",
    tag: "Real Estate",
  },
  {
    id: "matter-3",
    title: "Tech Merger (Phase I)",
    description: "M&A due diligence, IP transfer, employee agreements.",
    tag: "M&A",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [customMatter, setCustomMatter] = useState("");
  const [userId, setUserId] = useState("user-1");

  function openMatter(matterId: string) {
    router.push(`/query?matter_id=${encodeURIComponent(matterId)}&user_id=${encodeURIComponent(userId)}`);
  }

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
            maxWidth: 1200,
            margin: "0 auto",
            padding: "0 32px",
            height: 52,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              fontSize: 17,
              color: "var(--text-primary)",
              letterSpacing: "-0.03em",
            }}
          >
            LexRAG
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>User ID</span>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={{
                fontSize: 13,
                padding: "4px 10px",
                border: "1px solid var(--border)",
                borderRadius: 6,
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                width: 100,
                outline: "none",
              }}
            />
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ textAlign: "center", padding: "80px 32px 48px" }}>
        <p
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
            marginBottom: 12,
          }}
        >
          Law Firm Intelligence
        </p>
        <h1
          style={{
            fontSize: "clamp(36px, 5vw, 56px)",
            fontWeight: 700,
            letterSpacing: "-0.04em",
            lineHeight: 1.05,
            color: "var(--text-primary)",
            marginBottom: 20,
          }}
        >
          Your matters.
          <br />
          Instantly understood.
        </h1>
        <p
          style={{
            fontSize: 19,
            color: "var(--text-secondary)",
            maxWidth: 520,
            margin: "0 auto",
            lineHeight: 1.6,
          }}
        >
          Ask questions across your legal documents and get cited answers in seconds.
        </p>
      </div>

      {/* Matter cards */}
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "0 32px 80px",
        }}
      >
        <p
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text-tertiary)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            marginBottom: 20,
          }}
        >
          Select a Matter
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 20,
          }}
        >
          {DEMO_MATTERS.map((m) => (
            <MatterCard
              key={m.id}
              title={m.title}
              description={m.description}
              tag={m.tag}
              onClick={() => openMatter(m.id)}
            />
          ))}
        </div>

        {/* Custom matter input */}
        <div
          style={{
            marginTop: 40,
            background: "var(--bg-secondary)",
            borderRadius: "var(--radius-lg)",
            padding: "28px 32px",
            border: "1px solid var(--border-light)",
          }}
        >
          <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
            Open a specific matter ID
          </p>
          <div style={{ display: "flex", gap: 12 }}>
            <input
              placeholder="e.g. matter-1"
              value={customMatter}
              onChange={(e) => setCustomMatter(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && customMatter.trim() && openMatter(customMatter.trim())}
              style={{
                flex: 1,
                fontSize: 15,
                padding: "12px 16px",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--bg-primary)",
                color: "var(--text-primary)",
                outline: "none",
              }}
            />
            <button
              onClick={() => customMatter.trim() && openMatter(customMatter.trim())}
              disabled={!customMatter.trim()}
              style={{
                padding: "12px 24px",
                background: customMatter.trim() ? "var(--accent)" : "var(--border)",
                color: "white",
                border: "none",
                borderRadius: "var(--radius-sm)",
                fontSize: 15,
                fontWeight: 500,
                cursor: customMatter.trim() ? "pointer" : "not-allowed",
                transition: "background 0.15s",
              }}
            >
              Open
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MatterCard({
  title,
  description,
  tag,
  onClick,
}: {
  title: string;
  description: string;
  tag: string;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        textAlign: "left",
        background: hovered ? "var(--bg-secondary)" : "var(--bg-primary)",
        border: `1px solid ${hovered ? "var(--border)" : "var(--border-light)"}`,
        borderRadius: "var(--radius-lg)",
        padding: "28px",
        cursor: "pointer",
        transition: "all 0.2s ease",
        boxShadow: hovered ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hovered ? "translateY(-2px)" : "none",
        display: "block",
        width: "100%",
      }}
    >
      <span
        style={{
          display: "inline-block",
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--accent)",
          background: "rgba(0, 113, 227, 0.08)",
          borderRadius: 4,
          padding: "3px 8px",
          marginBottom: 16,
        }}
      >
        {tag}
      </span>
      <h3
        style={{
          fontSize: 17,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 8,
          letterSpacing: "-0.02em",
          lineHeight: 1.35,
        }}
      >
        {title}
      </h3>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
        {description}
      </p>
      <div
        style={{
          marginTop: 20,
          fontSize: 13,
          color: "var(--accent)",
          fontWeight: 500,
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        Open matter →
      </div>
    </button>
  );
}
