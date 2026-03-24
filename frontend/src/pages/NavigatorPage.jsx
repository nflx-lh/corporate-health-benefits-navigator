import React, { useEffect, useRef, useState } from "react";
import { queryBenefits } from "../api/client.js";
import "../styles/navigator.css";

/**
 * Lightweight markdown → HTML converter (no external dependency).
 * Handles headings, bold, italic, links, lists, code blocks, hr, paragraphs.
 */
function slugify(text) {
  return text
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

function markdownToHtml(md) {
  let html = md
    // code blocks
    .replace(/```[\s\S]*?```/g, (m) => {
      const code = m.slice(3, -3).replace(/^\w*\n/, "");
      return `<pre><code>${code.replace(/</g, "&lt;")}</code></pre>`;
    })
    // inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // headings (with id for anchor links)
    .replace(/^#### (.+)$/gm, (_, t) => `<h4 id="${slugify(t)}">${t}</h4>`)
    .replace(/^### (.+)$/gm, (_, t) => `<h3 id="${slugify(t)}">${t}</h3>`)
    .replace(/^## (.+)$/gm, (_, t) => `<h2 id="${slugify(t)}">${t}</h2>`)
    .replace(/^# (.+)$/gm, (_, t) => `<h1 id="${slugify(t)}">${t}</h1>`)
    // hr
    .replace(/^---+$/gm, "<hr/>")
    // bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    // unordered list items
    .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
    // paragraphs (double newline)
    .replace(/\n{2,}/g, "</p><p>")
    // single newlines → <br>
    .replace(/\n/g, "<br/>");

  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*?<\/li>(?:<br\/>)?)+)/g, "<ul>$1</ul>");
  // Clean up <br/> inside <ul>
  html = html.replace(/<ul>(.*?)<\/ul>/gs, (_, inner) =>
    "<ul>" + inner.replace(/<br\/>/g, "") + "</ul>"
  );

  return `<p>${html}</p>`
    .replace(/<p><\/p>/g, "")
    .replace(/<p>(<h[1-4]>)/g, "$1")
    .replace(/(<\/h[1-4]>)<\/p>/g, "$1")
    .replace(/<p>(<hr\/>)/g, "$1")
    .replace(/(<hr\/>)<\/p>/g, "$1")
    .replace(/<p>(<ul>)/g, "$1")
    .replace(/(<\/ul>)<\/p>/g, "$1")
    .replace(/<p>(<pre>)/g, "$1")
    .replace(/(<\/pre>)<\/p>/g, "$1");
}

const POLICY_GUIDES = [
  {
    id: "coverage",
    title: "Coverage & Eligibility Guide",
    href: "/guides/coverage_eligibility_guide.md",
    path: "guides/coverage_eligibility_guide.md",
  },
  {
    id: "claims",
    title: "Claims & Pre-authorization Guide",
    href: "/guides/claims_preauth_guide.md",
    path: "guides/claims_preauth_guide.md",
  },
  {
    id: "exclusions",
    title: "Clarifications & Exclusions Guide",
    href: "/guides/exclusions_clarifications_guide.md",
    path: "guides/exclusions_clarifications_guide.md",
  },
];

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function toTitleCase(str) {
  return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function DecisionBadge({ decision }) {
  const colors = {
    covered: { bg: "#dcfce7", fg: "#166534" },
    not_covered: { bg: "#fee2e2", fg: "#991b1b" },
    insufficient_info: { bg: "#fef9c3", fg: "#854d0e" },
  };
  const c = colors[decision] || { bg: "#e5e7eb", fg: "#374151" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.2rem 0.6rem",
        borderRadius: "6px",
        fontSize: "0.8rem",
        fontWeight: 600,
        background: c.bg,
        color: c.fg,
      }}
    >
      {toTitleCase(decision || "unknown")}
    </span>
  );
}

function SourceBadge({ source }) {
  const isAI = source === "llm";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.2rem 0.6rem",
        borderRadius: "6px",
        fontSize: "0.8rem",
        fontWeight: 600,
        background: isAI ? "#ede9fe" : "#f3f4f6",
        color: isAI ? "#6d28d9" : "#6b7280",
      }}
    >
      {isAI ? "AI Summary" : "System"}
    </span>
  );
}

function FieldRow({ label, value, fallback = "\u2014" }) {
  let display;
  if (value === null || value === undefined || value === "") {
    display = fallback;
  } else if (typeof value === "boolean") {
    display = value ? "Yes" : "No";
  } else {
    display = String(value);
  }
  return (
    <div style={{ display: "flex", padding: "0.35rem 0", gap: "0.5rem" }}>
      <span style={{ fontWeight: 600, minWidth: "140px", color: "#374151" }}>
        {label}
      </span>
      <span style={{ color: display === fallback ? "#9ca3af" : "#1f2937" }}>
        {display}
      </span>
    </div>
  );
}

function TagList({ items, emptyText }) {
  if (!Array.isArray(items) || items.length === 0) {
    return emptyText ? (
      <span style={{ color: "#9ca3af", fontStyle: "italic" }}>{emptyText}</span>
    ) : null;
  }
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
      {items.map((item, i) => (
        <span
          key={i}
          style={{
            padding: "0.15rem 0.5rem",
            background: "#f3f4f6",
            borderRadius: "4px",
            fontSize: "0.85rem",
            color: "#374151",
          }}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function CitationBadge({ citation }) {
  return (
    <span
      title={`${citation.source_file}${citation.section ? ` — ${citation.section}` : ""}`}
      style={{
        display: "inline-block",
        padding: "0.2rem 0.55rem",
        background: "#e0e7ff",
        border: "1px solid #c7d2fe",
        borderRadius: "6px",
        fontSize: "0.8rem",
        fontWeight: 600,
        color: "#4338ca",
        cursor: "default",
      }}
    >
      {citation.clause_id}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Action zone – required docs & pre-auth                             */
/* ------------------------------------------------------------------ */

function ActionZone({ data }) {
  const hasActions =
    (Array.isArray(data.required_docs) && data.required_docs.length > 0) ||
    data.preauth_required === true;

  if (!hasActions) return null;

  return (
    <div style={styles.actionZone}>
      <div style={styles.actionHeader}>Action Required</div>
      {data.preauth_required === true && (
        <div style={styles.actionItem}>Pre-authorization is required before treatment.</div>
      )}
      {Array.isArray(data.required_docs) && data.required_docs.length > 0 && (
        <div style={styles.actionItem}>
          Required documents: {data.required_docs.join(", ")}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Decision result panel                                              */
/* ------------------------------------------------------------------ */

function ResultPanel({ data }) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  // Primary zone: AI summary or fallback reason_summary
  const summaryText = data.ai_summary || data.reason_summary || "\u2014";

  return (
    <div style={styles.resultCard}>
      {/* Primary zone: Summary + decision badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <DecisionBadge decision={data.decision} />
        <SourceBadge source={data.ai_summary_source || "fallback"} />
        <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>
          {data.benefit_type || "—"} / {data.service_category || "—"}
        </span>
      </div>

      {/* Summary text */}
      <div style={{ marginBottom: "1rem", color: "#1f2937", lineHeight: 1.6, whiteSpace: "pre-line" }}>
        {summaryText}
      </div>

      {/* Source references for employees */}
      {Array.isArray(data.policy_citations) && data.policy_citations.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.35rem", marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.8rem", color: "#6b7280", fontWeight: 500 }}>Sources:</span>
          {data.policy_citations.map((c, i) => (
            <CitationBadge key={i} citation={c} />
          ))}
        </div>
      )}

      {/* Action zone */}
      <ActionZone data={data} />

      {/* Financial zone */}
      <div style={styles.fieldGroup}>
        <FieldRow label="Coverage" value={data.coverage_percent != null ? `${data.coverage_percent}%` : null} />
        <FieldRow label="Annual Limit" value={(() => { const v = data.annual_limit ?? data.annual_limit_sgd ?? null; return v != null ? `SGD ${v}` : null; })()} />
        <FieldRow label="Remaining Limit" value={data.remaining_limit != null ? `SGD ${data.remaining_limit}` : null} />
        <FieldRow label="Estimated Payout" value={data.estimated_payout != null ? `SGD ${data.estimated_payout}` : null} />
        <FieldRow label="Co-pay" value={data.co_pay_sgd != null ? `SGD ${data.co_pay_sgd}` : null} />
      </div>

      {/* Collapsible details zone */}
      <div style={{ marginTop: "1rem" }}>
        <button
          onClick={() => setDetailsOpen(!detailsOpen)}
          style={styles.detailsToggle}
        >
          {detailsOpen ? "Hide" : "Show"} Technical Details
        </button>

        {detailsOpen && (
          <div style={styles.detailsZone}>
            {/* Reason codes */}
            <div style={{ marginBottom: "0.75rem" }}>
              <div style={styles.sectionLabel}>Reason Codes</div>
              <TagList items={data.reason_codes} emptyText="None" />
            </div>

            {/* Matched rules */}
            <div style={{ marginBottom: "0.75rem" }}>
              <div style={styles.sectionLabel}>Matched Rules</div>
              <TagList items={data.matched_rule_ids} emptyText="None" />
            </div>

            {/* Raw explanation (backward compat) */}
            {data.explanation && (
              <div style={{ marginBottom: "0.75rem" }}>
                <div style={styles.sectionLabel}>Raw Citation</div>
                <div style={{ fontSize: "0.85rem", color: "#374151" }}>
                  {data.explanation
                    .replace(/\*\*([^*]+)\*\*/g, "$1")
                    .replace(/#{1,6}\s+/g, "")
                    .replace(/__([^_]+)__/g, "$1")
                  }
                </div>
              </div>
            )}

            {/* Citations */}
            {Array.isArray(data.policy_citations) && data.policy_citations.length > 0 && (
              <div>
                <div style={{ ...styles.sectionLabel, marginBottom: "0.5rem" }}>
                  Policy Citations
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                  {data.policy_citations.map((c, i) => (
                    <CitationBadge key={i} citation={c} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function NavigatorPage({ employeeId, onLogout }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeGuide, setActiveGuide] = useState(null);
  const [guideContent, setGuideContent] = useState("");
  const [guideLoading, setGuideLoading] = useState(false);
  const [guideError, setGuideError] = useState("");
  const queryInputRef = useRef(null);
  const drawerCloseBtnRef = useRef(null);

  useEffect(() => {
    queryInputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!activeGuide) return;

    drawerCloseBtnRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setActiveGuide(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeGuide]);

  const openGuide = async (guide) => {
    setActiveGuide(guide);
    setGuideContent("");
    setGuideError("");
    setGuideLoading(true);
    try {
      const response = await fetch(guide.href, {
        headers: { Accept: "text/plain, text/markdown" },
        redirect: "follow",
      });
      if (!response.ok) {
        throw new Error("Failed guide fetch");
      }
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("text/html")) {
        throw new Error("Got HTML instead of markdown");
      }
      const text = await response.text();
      if (
        !text.trim() ||
        text.trimStart().startsWith("<!") ||
        text.trimStart().startsWith("<html")
      ) {
        throw new Error("Guide content not available");
      }
      setGuideContent(text);
    } catch {
      setGuideError("Unable to load guide.");
    } finally {
      setGuideLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await queryBenefits(employeeId, q);
      setResult(data);
    } catch (err) {
      if (err.status === 404 && err.code === "EMPLOYEE_NOT_FOUND") {
        setError(`Employee "${employeeId}" was not found. Please check your ID.`);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="navigator-page">
      {/* Top bar */}
      <header className="navigator-header">
        <span className="navigator-header__title">Employee Policies</span>
        <div className="navigator-header__actions">
          <span className="navigator-header__employee">
            {employeeId}
          </span>
          <button onClick={onLogout} className="navigator-logout-btn">
            Logout
          </button>
        </div>
      </header>

      <main className="navigator-main navigator-layout">
        <aside className="navigator-sidebar" aria-label="Policy Library">
          <h2 className="navigator-sidebar__title">Policy Library</h2>
          <p className="navigator-sidebar__helper">
            Guides for manual references
          </p>
          <ul className="navigator-library-list">
            {POLICY_GUIDES.map((guide) => (
              <li key={guide.id}>
                <button
                  type="button"
                  className="navigator-library-link"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); openGuide(guide); }}
                >
                  {guide.title}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <section className="navigator-panel">
          {/* Query form at the top */}
          <form onSubmit={handleSubmit} className="navigator-query-form">
            <input
              className="navigator-query-input"
              ref={queryInputRef}
              type="text"
              placeholder="Ask a benefits question, e.g. 'Am I covered for dental cleaning?'"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="navigator-ask-btn"
              disabled={loading || !question.trim()}
            >
              {loading ? "Checking..." : "Search"}
            </button>
          </form>

          {/* Results area */}
          <div className="navigator-results">
            {loading && (
              <div className="navigator-spinner-wrap">
                <div className="navigator-radial-spinner">
                  {[...Array(8)].map((_, i) => (
                    <span key={i} className="navigator-radial-spinner__segment" />
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div style={styles.errorBox}>{error}</div>
            )}

            {result?.decision === "insufficient_info" && (
              <div style={styles.infoBox}>
                Your query cannot be found in database.
              </div>
            )}

            {result && (
              <ResultPanel data={result} />
            )}
          </div>
        </section>
      </main>
      {activeGuide && (
        <div className="navigator-guide-drawer-backdrop" onClick={() => setActiveGuide(null)}>
          <aside
            className="navigator-guide-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="navigator-guide-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="navigator-guide-drawer__header">
              <h2 id="navigator-guide-title" className="navigator-guide-drawer__title">
                {activeGuide.title}
              </h2>
              <div className="navigator-guide-drawer__actions">
                <button
                  type="button"
                  className="navigator-guide-drawer__newwin"
                  title="Open in new window"
                  onClick={() => {
                    const w = window.open("", "_blank", "width=860,height=700");
                    if (w) {
                      w.document.write(
                        `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${activeGuide.title}</title>` +
                        `<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;` +
                        `max-width:780px;margin:2rem auto;padding:0 1.5rem;color:#0f172a;line-height:1.6;` +
                        `min-height:100vh;background-color:#fef0e8;` +
                        `background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='60' viewBox='0 0 120 60'%3E%3Cpath d='M0 30 Q15 10 30 30 Q45 50 60 30 Q75 10 90 30 Q105 50 120 30' fill='none' stroke='%23d4856a' stroke-opacity='0.12' stroke-width='1.2'/%3E%3Cpath d='M0 50 Q15 30 30 50 Q45 70 60 50 Q75 30 90 50 Q105 70 120 50' fill='none' stroke='%23d4856a' stroke-opacity='0.08' stroke-width='1'/%3E%3Cpath d='M0 10 Q15 -10 30 10 Q45 30 60 10 Q75 -10 90 10 Q105 30 120 10' fill='none' stroke='%23d4856a' stroke-opacity='0.08' stroke-width='1'/%3E%3C/svg%3E")}` +
                        `h1,h2,h3,h4{color:#0f172a;line-height:1.25}a{color:#0f766e}code{background:#f1f5f9;` +
                        `padding:0.15em 0.35em;border-radius:3px;font-size:0.9em}pre{background:#f1f5f9;` +
                        `padding:1rem;border-radius:6px;overflow-x:auto}ul{padding-left:1.25rem}</style>` +
                        `</head><body>${markdownToHtml(guideContent)}</body></html>`
                      );
                      w.document.close();
                    }
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" />
                    <path d="M9 2h5v5" />
                    <path d="M14 2L7 9" />
                  </svg>
                </button>
                <button
                  ref={drawerCloseBtnRef}
                  type="button"
                  className="navigator-guide-drawer__close"
                  onClick={() => setActiveGuide(null)}
                >
                  Close
                </button>
              </div>
            </div>
            <div
              className="navigator-guide-drawer__body"
              onClick={(e) => {
                const anchor = e.target.closest("a[href^='#']");
                if (!anchor) return;
                e.preventDefault();
                const id = anchor.getAttribute("href").slice(1);
                const target = e.currentTarget.querySelector(`#${CSS.escape(id)}`);
                if (target) target.scrollIntoView({ behavior: "smooth" });
              }}
            >
              {guideLoading && <p>Loading guide...</p>}
              {!guideLoading && guideError && <p>{guideError}</p>}
              {!guideLoading && !guideError && guideContent && (
                <div
                  className="navigator-guide-markdown"
                  dangerouslySetInnerHTML={{ __html: markdownToHtml(guideContent) }}
                />
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = {
  errorBox: {
    padding: "0.75rem 1rem",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "6px",
    color: "#991b1b",
    marginBottom: "1rem",
  },
  infoBox: {
    padding: "0.75rem 1rem",
    background: "#fefce8",
    border: "1px solid #fde68a",
    borderRadius: "6px",
    color: "#854d0e",
    marginBottom: "1rem",
    fontSize: "0.9rem",
  },
  resultCard: {
    background: "#f8fafc",
    padding: "1.5rem",
    borderRadius: "12px",
    border: "1px solid rgba(15, 23, 42, 0.08)",
    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.12)",
  },
  fieldGroup: {
    marginBottom: "1rem",
    padding: "0.75rem",
    background: "#f9fafb",
    borderRadius: "6px",
  },
  sectionLabel: {
    fontSize: "0.8rem",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    color: "#6b7280",
    marginBottom: "0.35rem",
  },
  actionZone: {
    marginBottom: "1rem",
    padding: "0.75rem 1rem",
    background: "#fefce8",
    border: "1px solid #fde68a",
    borderRadius: "6px",
  },
  actionHeader: {
    fontSize: "0.85rem",
    fontWeight: 700,
    color: "#854d0e",
    marginBottom: "0.5rem",
  },
  actionItem: {
    fontSize: "0.9rem",
    color: "#713f12",
    marginBottom: "0.25rem",
  },
  detailsToggle: {
    background: "none",
    border: "1px solid #d1d5db",
    borderRadius: "4px",
    padding: "0.35rem 0.75rem",
    fontSize: "0.85rem",
    color: "#6b7280",
    cursor: "pointer",
  },
  detailsZone: {
    marginTop: "0.75rem",
    padding: "1rem",
    background: "#f9fafb",
    borderRadius: "6px",
    border: "1px solid #e5e7eb",
  },
};
