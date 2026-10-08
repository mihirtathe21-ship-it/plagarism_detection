import { useState, useRef, useEffect } from "react";
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const API = "http://localhost:5000/api";

// ── Score Gauge ───────────────────────────────────────────────────────────────
function ScoreGauge({ value, color }) {
  const r = 54, cx = 70, cy = 76;
  const start = -215 * (Math.PI / 180);
  const span  = 250 * (Math.PI / 180);
  const end   = start + (value / 100) * span;
  const trackEnd = start + span;
  const pt = (a) => ({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  const arcPath = (a1, a2) => {
    const p1 = pt(a1), p2 = pt(a2);
    const lg = (a2 - a1) > Math.PI ? 1 : 0;
    return `M${p1.x},${p1.y} A${r},${r} 0 ${lg},1 ${p2.x},${p2.y}`;
  };
  return (
    <svg width="140" height="106" viewBox="0 0 140 106">
      <path d={arcPath(start, trackEnd)} fill="none" stroke="#E2E8F0" strokeWidth="10" strokeLinecap="round"/>
      {value > 0 && <path d={arcPath(start, end)} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"/>}
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize="26" fontWeight="700" fill={color}>{value}%</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fontSize="11" fill="#94A3B8">plagiarised</text>
    </svg>
  );
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
function ProgressBar({ value, color, label }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: "#64748B", fontWeight: 500 }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>{value}%</span>
      </div>
      <div style={{ height: 8, background: "#F1F5F9", borderRadius: 6, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${value}%`, background: color,
          borderRadius: 6, transition: "width 1.2s cubic-bezier(.4,0,.2,1)"
        }}/>
      </div>
    </div>
  );
}

// ── Source Card ───────────────────────────────────────────────────────────────
function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false);
  const sim = source.similarity;
  const risk = sim >= 50 ? { bg:"#FEE2E2", border:"#FCA5A5", badge:"#EF4444", text:"#991B1B" }
             : sim >= 25 ? { bg:"#FEF3C7", border:"#FCD34D", badge:"#F59E0B", text:"#92400E" }
             : { bg:"#D1FAE5", border:"#6EE7B7", badge:"#10B981", text:"#065F46" };
  const domain = source.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];

  return (
    <div style={{
      border: `1px solid ${open ? risk.border : "#E2E8F0"}`,
      borderRadius: 12, overflow: "hidden", marginBottom: 10,
      boxShadow: open ? "0 4px 12px rgba(0,0,0,.06)" : "0 1px 3px rgba(0,0,0,.04)",
      transition: "all .2s",
    }}>
      <div onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", gap: 12, padding: "14px 16px",
        cursor: "pointer", background: "#fff",
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, background: risk.bg,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 13, fontWeight: 700, color: risk.badge, flexShrink: 0,
        }}>{index + 1}</div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1E293B", marginBottom: 2 }}>{domain}</div>
          <div style={{ fontSize: 11, color: "#94A3B8", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {source.url}
          </div>
        </div>

        <div style={{
          padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 700,
          background: risk.bg, color: risk.badge, border: `1px solid ${risk.border}`, flexShrink: 0,
        }}>{sim}% match</div>

        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" strokeWidth="2.5"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .2s", flexShrink: 0 }}>
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </div>

      {open && (
        <div style={{ padding: "14px 16px", borderTop: `1px solid ${risk.border}`, background: "#FAFAFA" }}>
          {source.matched_sentence && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#64748B", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Matched sentence
              </div>
              <div style={{
                padding: "10px 14px", borderRadius: 8, borderLeft: `4px solid ${risk.badge}`,
                background: "#fff", color: "#334155", fontStyle: "italic", fontSize: 13, lineHeight: 1.6,
                boxShadow: "0 1px 3px rgba(0,0,0,.05)",
              }}>
                "{source.matched_sentence}"
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {[["TF-IDF Score", `${source.tfidf_score}%`, "#7C3AED"], ["N-gram Overlap", `${source.ngram_score}%`, "#0891B2"]].map(([k, v, c]) => (
              <div key={k} style={{
                flex: 1, padding: "10px 12px", borderRadius: 8, background: "#fff",
                border: "1px solid #E2E8F0", textAlign: "center",
              }}>
                <div style={{ fontSize: 10, color: "#94A3B8", fontWeight: 600, textTransform: "uppercase", marginBottom: 3 }}>{k}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: c }}>{v}</div>
              </div>
            ))}
          </div>

          {source.shared_terms?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#64748B", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Shared keywords
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {source.shared_terms.map(([t], i) => (
                  <span key={i} style={{
                    fontSize: 12, padding: "3px 10px", borderRadius: 20,
                    background: "#EDE9FE", color: "#5B21B6", fontWeight: 500,
                  }}>{t}</span>
                ))}
              </div>
            </div>
          )}

          <a href={source.url} target="_blank" rel="noopener noreferrer" style={{
            display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12,
            color: "#2563EB", fontWeight: 600, textDecoration: "none",
            padding: "6px 12px", borderRadius: 8, background: "#EFF6FF", border: "1px solid #BFDBFE",
          }}>
            Open source page
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/>
            </svg>
          </a>
        </div>
      )}
    </div>
  );
}

// ── Stat Box ──────────────────────────────────────────────────────────────────
function StatBox({ label, value, icon }) {
  return (
    <div style={{
      padding: "14px 16px", borderRadius: 12, background: "#fff",
      border: "1px solid #E2E8F0", textAlign: "center",
      boxShadow: "0 1px 3px rgba(0,0,0,.04)",
    }}>
      <div style={{ fontSize: 22, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: "#1E293B" }}>{value}</div>
      <div style={{ fontSize: 11, color: "#94A3B8", fontWeight: 500 }}>{label}</div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [stage, setStage] = useState("idle");
  const [progress, setProgress] = useState("");
  const [report, setReport] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");
  const [textInput, setTextInput] = useState("");
  const [inputMode, setInputMode] = useState("upload");
  const [tab, setTab] = useState("overview");
  const [progressPct, setProgressPct] = useState(0);
  const [reportHistory, setReportHistory] = useState(() => {
    try {
      const saved = localStorage.getItem("plagiarism-report-history");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const fileRef = useRef();
  const pollRef = useRef();

  const STEPS = [
    "Extracting text from document…",
    "Identifying key sentences…",
    "Searching the web for matches…",
    "Fetching matching pages…",
    "Computing similarity scores…",
    "Generating report…",
  ];

  async function submitText(text, meta = {}) {
    setStage("loading");
    setProgress(STEPS[0]);
    setProgressPct(5);
    setReport(null);
    setTab("overview");

    try {
      const res = await fetch(`${API}/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, meta }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      let pct = 10;
      pollRef.current = setInterval(async () => {
        pct = Math.min(pct + 12, 90);
        setProgressPct(pct);
        try {
          const pr = await fetch(`${API}/result/${data.job_id}`);
          const job = await pr.json();
          if (job.progress) setProgress(job.progress);
          if (job.status === "done") {
            clearInterval(pollRef.current);
            setProgressPct(100);
            setTimeout(() => {
              setReport(job.result);
              saveReportToHistory(job.result);
              setStage("done");
            }, 400);
          } else if (job.status === "error") {
            clearInterval(pollRef.current);
            setStage("error");
            setProgress(job.error || "Unknown error");
          }
        } catch {}
      }, 900);
    } catch (e) {
      setStage("error");
      setProgress(e.message);
    }
  }

  async function handleFile(file) {
    if (!file) return;
    setFileName(file.name);
    const filename = file.name.toLowerCase();

    if (file.type.startsWith("image/") || filename.endsWith(".png") || filename.endsWith(".jpg") || filename.endsWith(".jpeg") || filename.endsWith(".webp") || filename.endsWith(".tif") || filename.endsWith(".tiff")) {
      const form = new FormData();
      form.append("file", file);
      setStage("loading");
      setProgress("Running OCR on image…");
      setProgressPct(10);
      try {
        const res = await fetch(`${API}/extract`, { method: "POST", body: form });
        const { text, error, meta } = await res.json();
        if (error || !text) throw new Error(error || "OCR returned no text");
        await submitText(text, { ...meta, filename: file.name, type: "image" });
      } catch (e) {
        setStage("error"); setProgress(e.message);
      }
      return;
    }

    if (filename.endsWith(".pdf")) {
      const form = new FormData();
      form.append("file", file);
      setStage("loading");
      setProgress("Extracting text from PDF…");
      setProgressPct(10);
      try {
        const res = await fetch(`${API}/extract`, { method: "POST", body: form });
        const { text, error, meta } = await res.json();
        if (error || !text) throw new Error(error || "PDF extraction returned no text");
        await submitText(text, { ...meta, filename: file.name, type: "pdf" });
      } catch (e) {
        setStage("error"); setProgress(e.message);
      }
      return;
    }

    const text = await file.text();
    await submitText(text, { filename: file.name, type: "text" });
  }

  function reset() {
    clearInterval(pollRef.current);
    setStage("idle"); setReport(null); setFileName("");
    setTextInput(""); setProgress(""); setProgressPct(0);
  }

  function buildHighlightedSegments(text, matches) {
    const cleanMatches = [...new Set((matches || []).filter(Boolean).map((m) => String(m).trim()).filter(Boolean))]
      .sort((a, b) => b.length - a.length);

    if (!text || cleanMatches.length === 0) {
      return [{ type: "text", value: text || "" }];
    }

    const segments = [];
    let cursor = 0;

    for (const match of cleanMatches) {
      const needle = match.toLowerCase();
      const haystack = text.toLowerCase();
      const idx = haystack.indexOf(needle, cursor);

      if (idx === -1) continue;

      if (idx > cursor) {
        segments.push({ type: "text", value: text.slice(cursor, idx) });
      }

      segments.push({
        type: "match",
        value: text.slice(idx, idx + match.length),
      });

      cursor = idx + match.length;
    }

    if (cursor < text.length) {
      segments.push({ type: "text", value: text.slice(cursor) });
    }

    return segments.length > 0 ? segments : [{ type: "text", value: text }];
  }

  function printPdfReport() {
    if (typeof window !== "undefined" && window.print) {
      window.print();
    }
  }

  function downloadReportCard() {
    if (!report) return;

    const sourceList = report.sources.length > 0
      ? report.sources.map((source, index) => `
          <li style="margin-bottom: 12px; list-style: none; padding: 12px 14px; border-radius: 10px; background: #F8FAFC; border: 1px solid #E2E8F0;">
            <div style="font-weight: 700; margin-bottom: 4px;">${index + 1}. ${source.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}</div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">Similarity: ${source.similarity}%</div>
            ${source.matched_sentence ? `<div style="font-size: 12px; color: #334155; font-style: italic;">"${source.matched_sentence}"</div>` : ""}
          </li>
        `).join("")
      : "<li style='list-style: none; color: #475569;'>No matching sources found.</li>";

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8" />
        <title>Plagiarism Report</title>
        <style>
          body { font-family: Arial, sans-serif; background: #F8FAFC; margin: 0; padding: 32px; color: #0F172A; }
          .card { max-width: 900px; margin: 0 auto; background: white; border-radius: 20px; padding: 28px; box-shadow: 0 10px 30px rgba(15,23,42,0.08); border: 1px solid #E2E8F0; }
          .badge { display: inline-block; padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: bold; background: #EEF2FF; color: #4338CA; }
          .title { font-size: 30px; font-weight: 800; margin-top: 18px; }
          .meta { font-size: 13px; color: #475569; margin-top: 10px; }
          .row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 24px; }
          .stat { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; }
          .stat-label { font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase; }
          .stat-value { font-size: 24px; font-weight: 800; margin-top: 8px; }
          .section { margin-top: 28px; }
          .section h3 { margin: 0 0 12px; font-size: 18px; }
          ul { margin: 0; padding: 0; }
          .recommendations { display: grid; gap: 10px; }
          .recommendation { background: #F8FAFC; border-left: 4px solid #4F46E5; padding: 12px 14px; border-radius: 10px; }
        </style>
      </head>
      <body>
        <div class="card">
          <div class="badge">Plagiarism Report</div>
          <div class="title">${report.verdict_label}</div>
          <div class="meta">${report.document.meta?.filename || "Document"} · Overall score: ${report.overall_score}%</div>

          <div class="row">
            <div class="stat">
              <div class="stat-label">Overall Score</div>
              <div class="stat-value">${report.overall_score}%</div>
            </div>
            <div class="stat">
              <div class="stat-label">Sources Found</div>
              <div class="stat-value">${report.summary.matching_sources}</div>
            </div>
            <div class="stat">
              <div class="stat-label">Words Checked</div>
              <div class="stat-value">${(report.document.stats.word_count || 0).toLocaleString()}</div>
            </div>
            <div class="stat">
              <div class="stat-label">Top Match</div>
              <div class="stat-value">${report.summary.highest_match || 0}%</div>
            </div>
          </div>

          <div class="section">
            <h3>Recommendations</h3>
            <div class="recommendations">
              ${report.recommendations.filter(Boolean).map((rec) => `<div class="recommendation">${rec}</div>`).join("")}
            </div>
          </div>

          <div class="section">
            <h3>Matching Sources</h3>
            <ul>${sourceList}</ul>
          </div>
        </div>
      </body>
      </html>
    `;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(report.document.meta?.filename || "report").replace(/\.[^/.]+$/, "") || "report"}-plagiarism-report.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    localStorage.setItem("plagiarism-report-history", JSON.stringify(reportHistory));
  }, [reportHistory]);

  useEffect(() => () => clearInterval(pollRef.current), []);

  function saveReportToHistory(reportData) {
    const entry = {
      id: Date.now() + Math.random(),
      filename: reportData.document?.meta?.filename || "Untitled document",
      verdict: reportData.verdict,
      verdict_label: reportData.verdict_label,
      overall_score: reportData.overall_score,
      matching_sources: reportData.summary?.matching_sources || 0,
      created_at: new Date().toISOString(),
      data: reportData,
    };

    setReportHistory((prev) => [entry, ...prev].slice(0, 6));
  }

  function loadHistoryReport(entry) {
    setReport(entry.data);
    setStage("done");
    setTab("overview");
    setProgress("");
    setProgressPct(100);
  }

  const suspiciousMatches = [...new Set((report?.sources || []).map((source) => source.matched_sentence).filter(Boolean))];
  const previewSegments = buildHighlightedSegments(report?.document?.preview || "", suspiciousMatches);
  const chartData = (report?.sources || []).slice(0, 6).map((source, index) => ({
    name: source.url ? source.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0] : `Source ${index + 1}`,
    similarity: Number(source.similarity || 0),
  }));
  const averageSimilarity = chartData.length > 0
    ? Math.round(chartData.reduce((sum, item) => sum + item.similarity, 0) / chartData.length)
    : 0;

  const verdictStyle = report ? {
    plagiarism:    { gradient: "linear-gradient(135deg,#FEE2E2,#FECACA)", border: "#F87171", color: "#DC2626", icon: "🚨" },
    high_risk:     { gradient: "linear-gradient(135deg,#FEF3C7,#FDE68A)", border: "#FBBF24", color: "#D97706", icon: "⚠️" },
    moderate_risk: { gradient: "linear-gradient(135deg,#FFF7ED,#FED7AA)", border: "#FB923C", color: "#EA580C", icon: "🔍" },
    low_risk:      { gradient: "linear-gradient(135deg,#D1FAE5,#A7F3D0)", border: "#34D399", color: "#059669", icon: "✅" },
    clean:         { gradient: "linear-gradient(135deg,#ECFDF5,#D1FAE5)", border: "#6EE7B7", color: "#10B981", icon: "✅" },
  }[report.verdict] : null;

  return (
    <div style={{
      minHeight: "100vh",
      background: "radial-gradient(circle at top left, rgba(99,102,241,0.14), transparent 32%), radial-gradient(circle at bottom right, rgba(14,165,233,0.12), transparent 28%), #F8FAFC",
      fontFamily: "'Inter','Segoe UI',sans-serif",
      color: "#0F172A",
      padding: "28px 18px 64px",
    }}>
      <div style={{ maxWidth: 980, margin: "0 auto" }}>

        <header style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
          marginBottom: 24,
          padding: "22px 26px",
          borderRadius: 22,
          background: "rgba(255,255,255,0.82)",
          border: "1px solid rgba(148,163,184,0.18)",
          boxShadow: "0 14px 35px rgba(15, 23, 42, 0.08)",
          backdropFilter: "blur(12px)",
          flexWrap: "wrap",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
            <div style={{
              width: 56, height: 56, borderRadius: 18,
              background: "linear-gradient(135deg,#4F46E5,#7C3AED,#0EA5E9)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 12px 24px rgba(79,70,229,0.28)",
              flexShrink: 0,
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="6"/>
                <path d="M16 16L21 21"/>
                <path d="M11 8.5v5M8.5 11h5"/>
              </svg>
            </div>

            <div style={{ minWidth: 0 }}>
              <div style={{
                display: "inline-flex", alignItems: "center", padding: "4px 10px",
                borderRadius: 999, fontSize: 11, fontWeight: 700, letterSpacing: ".08em",
                background: "#EEF2FF", color: "#4F46E5", textTransform: "uppercase",
                border: "1px solid #C7D2FE",
                marginBottom: 8,
              }}>
                Research integrity
              </div>
              <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, color: "#0F172A", letterSpacing: "-0.6px" }}>
                Plagiarism Checker
              </h1>
              <p style={{ margin: 0, fontSize: 13, color: "#64748B", marginTop: 4 }}>
                Detect copied content across text, web sources, and image-based documents.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {['Web Search', 'AI Analysis', 'OCR'].map((f) => (
              <span key={f} style={{
                fontSize: 11, padding: "6px 10px", borderRadius: 999,
                background: "#F8FAFC", color: "#334155", border: "1px solid #E2E8F0",
                fontWeight: 700,
              }}>{f}</span>
            ))}
          </div>
        </header>

        {stage === "idle" && (
          <section style={{
            background: "#fff",
            borderRadius: 24,
            padding: 24,
            boxShadow: "0 14px 42px rgba(15, 23, 42, 0.06)",
            border: "1px solid rgba(148,163,184,0.18)",
            marginBottom: 20,
          }}>
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
              borderRadius: 14,
              padding: 5,
              marginBottom: 20,
            }}>
              {[["upload", "📁", "Upload File"], ["paste", "✏️", "Paste Text"]].map(([m, icon, label]) => (
                <button
                  type="button"
                  key={m}
                  onClick={() => setInputMode(m)}
                  style={{
                    padding: "10px 18px",
                    borderRadius: 10,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: inputMode === m ? 800 : 600,
                    background: inputMode === m ? "#fff" : "transparent",
                    color: inputMode === m ? "#4F46E5" : "#64748B",
                    boxShadow: inputMode === m ? "0 8px 18px rgba(79,70,229,0.12)" : "none",
                    transition: "all .2s ease",
                  }}
                >
                  {icon} {label}
                </button>
              ))}
            </div>

            {inputMode === "upload" ? (
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
                onClick={() => fileRef.current?.click()}
                style={{
                  border: `2px dashed ${dragOver ? "#4F46E5" : "#C7D2FE"}`,
                  borderRadius: 18,
                  padding: "54px 24px",
                  textAlign: "center",
                  cursor: "pointer",
                  transition: "all .25s ease",
                  background: dragOver
                    ? "linear-gradient(135deg,#EEF2FF,#E0E7FF)"
                    : "linear-gradient(135deg,#F8FAFF,#F3F4FF)",
                }}
              >
                <div style={{ fontSize: 58, marginBottom: 16 }}>{dragOver ? "📂" : "📄"}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", marginBottom: 8 }}>
                  {dragOver ? "Drop your file here" : "Upload a document to scan"}
                </div>
                <div style={{ fontSize: 13, color: "#64748B", marginBottom: 14 }}>
                  Supported formats: <span style={{ color: "#4338CA", fontWeight: 700 }}>TXT, PDF, DOCX, PNG, JPG</span>
                </div>
                <div style={{
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                  minWidth: 180, padding: "8px 14px", borderRadius: 999,
                  fontSize: 12, fontWeight: 700, color: "#475569",
                  background: "#fff", border: "1px solid #E2E8F0",
                }}>
                  Browse files
                </div>
                <input ref={fileRef} type="file" accept=".txt,.pdf,.doc,.docx,image/*" style={{ display: "none" }} onChange={e => handleFile(e.target.files[0])} />
              </div>
            ) : (
              <div>
                <textarea
                  value={textInput}
                  onChange={e => setTextInput(e.target.value)}
                  placeholder="Paste your essay, article, report, or any other text here…"
                  style={{
                    width: "100%",
                    minHeight: 220,
                    resize: "vertical",
                    boxSizing: "border-box",
                    border: "1.5px solid #E2E8F0",
                    borderRadius: 16,
                    padding: "16px 18px",
                    fontSize: 14,
                    lineHeight: 1.75,
                    fontFamily: "inherit",
                    background: "#FAFBFF",
                    color: "#0F172A",
                    outline: "none",
                    transition: "all .2s ease",
                    boxShadow: "inset 0 1px 2px rgba(15,23,42,0.02)",
                  }}
                  onFocus={e => e.target.style.borderColor = "#4F46E5"}
                  onBlur={e => e.target.style.borderColor = "#E2E8F0"}
                />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 14, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 12, color: "#64748B" }}>
                    {textInput.split(/\s+/).filter(Boolean).length} words · {textInput.length} characters
                  </span>
                  <button
                    type="button"
                    onClick={() => submitText(textInput, { source: "paste" })}
                    disabled={textInput.trim().length === 0}
                    style={{
                      padding: "12px 22px",
                      borderRadius: 12,
                      border: "none",
                      cursor: textInput.trim().length > 0 ? "pointer" : "not-allowed",
                      fontSize: 14,
                      fontWeight: 800,
                      transition: "all .2s ease",
                      background: textInput.trim().length > 0 ? "linear-gradient(135deg,#4F46E5,#7C3AED)" : "#E2E8F0",
                      color: textInput.trim().length > 0 ? "#fff" : "#94A3B8",
                      boxShadow: textInput.trim().length > 0 ? "0 12px 28px rgba(79,70,229,0.25)" : "none",
                    }}
                  >
                    🔍 Check for Plagiarism
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {stage === "loading" && (
          <div style={{
            background: "#fff",
            borderRadius: 24,
            padding: 36,
            textAlign: "center",
            boxShadow: "0 14px 42px rgba(15, 23, 42, 0.06)",
            border: "1px solid rgba(148,163,184,0.18)",
          }}>
            <div style={{ position: "relative", width: 86, height: 86, margin: "0 auto 24px" }}>
              <div style={{
                width: 86, height: 86, border: "4px solid #EEF2FF",
                borderTop: "4px solid #4F46E5", borderRadius: "50%",
                animation: "spin 1s linear infinite",
              }}/>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", fontSize: 28 }}>
                🔍
              </div>
            </div>

            <div style={{ fontSize: 22, fontWeight: 800, color: "#0F172A", marginBottom: 8 }}>
              Checking for Plagiarism…
            </div>
            <div style={{ fontSize: 14, color: "#64748B", marginBottom: 28, minHeight: 20 }}>
              {progress}
            </div>

            <div style={{ maxWidth: 420, margin: "0 auto 24px" }}>
              <div style={{ height: 10, background: "#EEF2FF", borderRadius: 999, overflow: "hidden" }}>
                <div style={{
                  height: "100%",
                  width: `${progressPct}%`,
                  background: "linear-gradient(90deg,#4F46E5,#7C3AED,#0EA5E9)",
                  borderRadius: 999,
                  transition: "width 1s ease",
                }}/>
              </div>
              <div style={{ fontSize: 12, color: "#64748B", marginTop: 8, fontWeight: 700 }}>{progressPct}% complete</div>
            </div>

            <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              {STEPS.map((s, i) => {
                const done = progressPct >= (i + 1) * (100 / STEPS.length);
                const active = progress === s;
                return (
                  <div key={i} style={{
                    fontSize: 11, padding: "6px 10px", borderRadius: 999, fontWeight: 700,
                    background: done || active ? "#EEF2FF" : "#F8FAFC",
                    color: done || active ? "#4338CA" : "#CBD5E1",
                    border: `1px solid ${done || active ? "#C7D2FE" : "#E2E8F0"}`,
                    transition: "all .3s",
                  }}>
                    {done ? "✓ " : active ? "⟳ " : ""}{s.replace("…", "")}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {stage === "error" && (
          <div style={{
            background: "linear-gradient(135deg,#FEF2F2,#FFF7ED)",
            borderRadius: 24,
            padding: 26,
            border: "1px solid #FECACA",
            boxShadow: "0 12px 32px rgba(239,68,68,0.08)",
          }}>
            <div style={{ fontSize: 42, marginBottom: 12 }}>⚠️</div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#B91C1C", marginBottom: 8 }}>
              Something went wrong
            </div>
            <div style={{ fontSize: 13, color: "#991B1B", marginBottom: 16, fontFamily: "monospace" }}>
              {progress}
            </div>
            <div style={{ fontSize: 13, color: "#7F1D1D", marginBottom: 18 }}>
              Make sure the backend is running with <code style={{ background: "#FEE2E2", padding: "2px 6px", borderRadius: 6 }}>python app.py</code>
            </div>
            <button type="button" onClick={reset} style={{
              padding: "11px 22px",
              borderRadius: 10,
              border: "none",
              cursor: "pointer",
              background: "#DC2626",
              color: "#fff",
              fontSize: 14,
              fontWeight: 800,
              boxShadow: "0 10px 20px rgba(220,38,38,0.22)",
            }}>
              Try Again
            </button>
          </div>
        )}

        {stage === "done" && report && verdictStyle && (
          <div>
            <div style={{
              borderRadius: 24,
              padding: "24px 24px",
              marginBottom: 20,
              background: verdictStyle.gradient,
              border: `1.5px solid ${verdictStyle.border}`,
              boxShadow: "0 18px 38px rgba(15, 23, 42, 0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 20,
              flexWrap: "wrap",
            }}>
              <div style={{ flex: 1, minWidth: 220 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                  <span style={{ fontSize: 30 }}>{verdictStyle.icon}</span>
                  <span style={{ fontSize: 24, fontWeight: 800, color: verdictStyle.color, letterSpacing: "-0.5px" }}>
                    {report.verdict_label}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#475569", marginBottom: 12 }}>
                  {report.document.meta?.filename && <span>📄 <b>{report.document.meta.filename}</b> · </span>}
                  <b>{report.summary.matching_sources}</b> matching {report.summary.matching_sources === 1 ? "source" : "sources"} found online
                </div>
                {report.domains_found?.length > 0 && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {report.domains_found.map((d, i) => (
                      <span key={i} style={{
                        fontSize: 11, padding: "4px 10px", borderRadius: 999,
                        background: "rgba(255,255,255,.72)", color: "#475569",
                        border: "1px solid rgba(15,23,42,.06)", fontWeight: 700,
                      }}>🔗 {d}</span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ textAlign: "center", flexShrink: 0 }}>
                <ScoreGauge value={report.overall_score} color={verdictStyle.color} />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginBottom: 20 }}>
              <StatBox label="Overall Score" value={`${report.overall_score}%`} icon="📊" />
              <StatBox label="Sources Found" value={report.summary.matching_sources} icon="🌐" />
              <StatBox label="Words Checked" value={(report.document.stats.word_count || 0).toLocaleString()} icon="📝" />
              <StatBox label="Top Match" value={`${report.summary.highest_match || 0}%`} icon="🎯" />
            </div>

            <div style={{
              display: "flex",
              gap: 6,
              marginBottom: 16,
              background: "rgba(255,255,255,0.9)",
              padding: 6,
              borderRadius: 14,
              border: "1px solid #E2E8F0",
              boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
              flexWrap: "wrap",
            }}>
              {[
                ["overview", "📊", "Overview"],
                ["sources", "🌐", `Sources (${report.sources.length})`],
                ["document", "📄", "Document"],
              ].map(([t, icon, label]) => (
                <button
                  type="button"
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1,
                    minWidth: 120,
                    padding: "10px 16px",
                    borderRadius: 10,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: tab === t ? 800 : 600,
                    transition: "all .2s ease",
                    background: tab === t ? "linear-gradient(135deg,#4F46E5,#7C3AED)" : "transparent",
                    color: tab === t ? "#fff" : "#64748B",
                    boxShadow: tab === t ? "0 10px 22px rgba(79,70,229,0.22)" : "none",
                  }}
                >
                  {icon} {label}
                </button>
              ))}
              <button type="button" onClick={printPdfReport} style={{
                padding: "10px 18px",
                borderRadius: 10,
                border: "1px solid #C7D2FE",
                background: "#EEF2FF",
                color: "#4338CA",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 700,
              }}>
                🖨 Save as PDF
              </button>
              <button type="button" onClick={downloadReportCard} style={{
                padding: "10px 18px",
                borderRadius: 10,
                border: "1px solid #C7D2FE",
                background: "#EEF2FF",
                color: "#4338CA",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 700,
              }}>
                ⬇ Download HTML
              </button>
              <button type="button" onClick={reset} style={{
                padding: "10px 18px",
                borderRadius: 10,
                border: "1px solid #E2E8F0",
                background: "#F8FAFC",
                color: "#475569",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 700,
              }}>
                ↩ New Check
              </button>
            </div>

            {tab === "overview" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {reportHistory.length > 0 && (
                  <div style={{
                    gridColumn: "1 / -1",
                    background: "#fff",
                    borderRadius: 18,
                    padding: 18,
                    border: "1px solid #E2E8F0",
                    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
                    marginBottom: 4,
                  }}>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 12 }}>
                      🕘 Recent Saved Reports
                    </div>
                    <div style={{ display: "grid", gap: 8 }}>
                      {reportHistory.slice(0, 3).map((item) => (
                        <button
                          type="button"
                          key={item.id}
                          onClick={() => loadHistoryReport(item)}
                          style={{
                            border: "1px solid #E2E8F0",
                            background: "#F8FAFC",
                            borderRadius: 10,
                            padding: "10px 12px",
                            textAlign: "left",
                            cursor: "pointer",
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 10,
                            flexWrap: "wrap",
                          }}
                        >
                          <span style={{ fontSize: 13, fontWeight: 700, color: "#0F172A" }}>{item.filename}</span>
                          <span style={{ fontSize: 12, color: "#64748B" }}>{new Date(item.created_at).toLocaleDateString()}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div style={{
                  background: "#fff",
                  borderRadius: 18,
                  padding: 20,
                  border: "1px solid #E2E8F0",
                  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
                }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 16 }}>
                    📈 Similarity Scores
                  </div>
                  <ProgressBar value={report.overall_score} color={verdictStyle.color} label="Overall Score" />
                  {report.sources.slice(0, 4).map((s, i) => {
                    const c = s.similarity >= 50 ? "#EF4444" : s.similarity >= 25 ? "#F59E0B" : "#10B981";
                    const dom = s.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
                    return <ProgressBar key={i} value={s.similarity} color={c} label={dom} />;
                  })}
                </div>

                <div style={{
                  gridColumn: "1 / -1",
                  background: "#fff",
                  borderRadius: 18,
                  padding: 20,
                  border: "1px solid #E2E8F0",
                  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
                }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 16 }}>
                    📊 Analytics Summary
                  </div>
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748B" }} interval={0} angle={-18} textAnchor="end" height={50} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748B" }} />
                        <Tooltip formatter={(value) => [`${value}%`, "Similarity"]} />
                        <Bar dataKey="similarity" radius={[8, 8, 0, 0]} fill="#4F46E5" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginTop: 16 }}>
                    {[
                      ["Highest Match", `${report.summary.highest_match || 0}%`, "🎯"],
                      ["Avg Similarity", `${averageSimilarity}%`, "📉"],
                      ["Matched Sources", `${report.summary.matching_sources || 0}`, "🌐"],
                      ["Risk Level", report.verdict_label, "⚠️"],
                    ].map(([label, value, icon]) => (
                      <div key={label} style={{
                        padding: "14px 12px",
                        borderRadius: 12,
                        background: "#F8FAFC",
                        border: "1px solid #E2E8F0",
                        textAlign: "center",
                      }}>
                        <div style={{ fontSize: 22, marginBottom: 4 }}>{icon}</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: "#0F172A" }}>{value}</div>
                        <div style={{ fontSize: 11, color: "#64748B", fontWeight: 700 }}>{label}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{
                  background: "#fff",
                  borderRadius: 18,
                  padding: 20,
                  border: "1px solid #E2E8F0",
                  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
                }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 16 }}>
                    💡 Recommendations
                  </div>
                  {report.recommendations.filter(Boolean).map((rec, i) => (
                    <div key={i} style={{
                      display: "flex",
                      gap: 10,
                      padding: "10px 14px",
                      borderRadius: 12,
                      background: "#F8FAFC",
                      border: `1px solid ${verdictStyle.border}`,
                      marginBottom: 10,
                      borderLeft: `4px solid ${verdictStyle.color}`,
                    }}>
                      <span style={{ fontSize: 16, flexShrink: 0 }}>
                        {i === 0 ? "🔴" : i === 1 ? "📌" : "💬"}
                      </span>
                      <span style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === "sources" && (
              <div>
                {report.sources.length === 0 ? (
                  <div style={{
                    textAlign: "center",
                    padding: 60,
                    background: "#fff",
                    borderRadius: 18,
                    border: "1px solid #E2E8F0",
                    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
                  }}>
                    <div style={{ fontSize: 54, marginBottom: 14 }}>✅</div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", marginBottom: 8 }}>
                      No matching sources found
                    </div>
                    <div style={{ fontSize: 14, color: "#64748B" }}>
                      Your document appears to be original.
                    </div>
                  </div>
                ) : (
                  report.sources.map((s, i) => <SourceCard key={i} source={s} index={i} />)
                )}
              </div>
            )}

            {tab === "document" && (
              <div style={{
                background: "#fff",
                borderRadius: 18,
                padding: 20,
                border: "1px solid #E2E8F0",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.04)",
              }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 16 }}>
                  📄 Document Information
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: 10, marginBottom: 18 }}>
                  {[
                    ["Word Count", (report.document.stats.word_count || 0).toLocaleString(), "📝"],
                    ["Sentences", (report.document.stats.sentence_count || 0).toLocaleString(), "📖"],
                    ["Unique Words", (report.document.stats.unique_words || 0).toLocaleString(), "🔤"],
                  ].map(([k, v, icon]) => (
                    <div key={k} style={{
                      padding: "16px 14px",
                      borderRadius: 12,
                      background: "#F8FAFC",
                      border: "1px solid #E2E8F0",
                      textAlign: "center",
                    }}>
                      <div style={{ fontSize: 22, marginBottom: 5 }}>{icon}</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "#0F172A" }}>{v}</div>
                      <div style={{ fontSize: 11, color: "#64748B", fontWeight: 700 }}>{k}</div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Document Preview
                </div>
                <div style={{
                  fontSize: 13,
                  lineHeight: 1.8,
                  padding: "16px 18px",
                  borderRadius: 12,
                  background: "#F8FAFC",
                  color: "#334155",
                  border: "1px solid #E2E8F0",
                  maxHeight: 240,
                  overflow: "auto",
                  fontFamily: "'Courier New', monospace",
                  whiteSpace: "pre-wrap",
                }}>
                  {previewSegments.map((segment, idx) =>
                    segment.type === "match" ? (
                      <span key={idx} style={{
                        background: "rgba(239, 68, 68, 0.18)",
                        color: "#B91C1C",
                        borderRadius: 4,
                        padding: "0 2px",
                        fontWeight: 700,
                      }}>{segment.value}</span>
                    ) : (
                      <span key={idx}>{segment.value}</span>
                    )
                  )}
                </div>

                {suspiciousMatches.length > 0 && (
                  <div style={{ marginTop: 18 }}>
                    <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Suspicious Matches
                    </div>
                    <div style={{ display: "grid", gap: 10 }}>
                      {suspiciousMatches.map((match, idx) => (
                        <div key={idx} style={{
                          padding: "12px 14px",
                          borderRadius: 12,
                          background: "#FFF7ED",
                          border: "1px solid #FCD34D",
                          color: "#7C2D12",
                          fontSize: 13,
                          lineHeight: 1.6,
                          fontStyle: "italic",
                        }}>
                          “{match}”
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #F8FAFC; }
        @keyframes spin { to { transform: rotate(360deg); } }
        button { font-family: inherit; }
        textarea { font-family: inherit; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #F1F5F9; border-radius: 8px; }
        ::-webkit-scrollbar-thumb { background: linear-gradient(180deg,#CBD5E1,#94A3B8); border-radius: 8px; }
        @media print {
          body { background: white !important; }
          header, section, button, .no-print { display: none !important; }
          div[style*="box-shadow"] { box-shadow: none !important; }
        }
        @media (max-width: 720px) {
          .results-grid { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 560px) {
          .results-grid { grid-template-columns: 1fr !important; }
          header { padding: 18px 18px !important; }
          section { padding: 18px !important; }
        }
      `}</style>
    </div>
  );
}
