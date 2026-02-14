import React, { useState } from "react";
import { queryBenefits } from "../api/client.js";

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

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
        padding: "0.25rem 0.75rem",
        borderRadius: "9999px",
        fontSize: "0.85rem",
        fontWeight: 600,
        background: c.bg,
        color: c.fg,
      }}
    >
      {(decision || "unknown").replace(/_/g, " ")}
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

function CitationCard({ citation }) {
  return (
    <div
      style={{
        padding: "0.75rem",
        background: "#f0f4ff",
        borderLeft: "3px solid #6366f1",
        borderRadius: "4px",
        marginBottom: "0.5rem",
        fontSize: "0.9rem",
      }}
    >
      <div style={{ fontWeight: 600, color: "#4338ca", marginBottom: "0.25rem" }}>
        {citation.clause_id}{" "}
        <span style={{ fontWeight: 400, color: "#6b7280" }}>
          — {citation.source_file}
          {citation.section ? `, ${citation.section}` : ""}
        </span>
      </div>
      <div style={{ color: "#374151" }}>{citation.text}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Decision result panel                                              */
/* ------------------------------------------------------------------ */

function ResultPanel({ data }) {
  return (
    <div style={styles.resultCard}>
      {/* Decision header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        <DecisionBadge decision={data.decision} />
        <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>
          {data.benefit_type || "—"} / {data.service_category || "—"}
        </span>
      </div>

      {/* Reason */}
      <div style={{ marginBottom: "1rem", color: "#1f2937" }}>
        {data.reason_summary || "\u2014"}
      </div>

      {/* Deterministic fields */}
      <div style={styles.fieldGroup}>
        <FieldRow label="Coverage" value={data.coverage_percent != null ? `${data.coverage_percent}%` : null} />
        <FieldRow label="Annual Limit" value={(() => { const v = data.annual_limit ?? data.annual_limit_sgd ?? null; return v != null ? `SGD ${v}` : null; })()} />
        <FieldRow label="Remaining Limit" value={data.remaining_limit != null ? `SGD ${data.remaining_limit}` : null} />
        <FieldRow label="Estimated Payout" value={data.estimated_payout != null ? `SGD ${data.estimated_payout}` : null} />
        <FieldRow label="Pre-auth Required" value={typeof data.preauth_required === "boolean" ? data.preauth_required : null} />
      </div>

      {/* Reason codes */}
      <div style={{ marginBottom: "0.75rem" }}>
        <div style={styles.sectionLabel}>Reason Codes</div>
        <TagList items={data.reason_codes} emptyText="None" />
      </div>

      {/* Required docs */}
      <div style={{ marginBottom: "0.75rem" }}>
        <div style={styles.sectionLabel}>Required Documents</div>
        <TagList items={data.required_docs} emptyText="None" />
      </div>

      {/* Matched rules */}
      <div style={{ marginBottom: "0.75rem" }}>
        <div style={styles.sectionLabel}>Matched Rules</div>
        <TagList items={data.matched_rule_ids} emptyText="None" />
      </div>

      {/* --- Enrichment section (visually separated) --- */}
      {(data.explanation || (Array.isArray(data.policy_citations) && data.policy_citations.length > 0)) && (
        <div style={styles.enrichment}>
          <div style={styles.enrichmentHeader}>Policy Explanation</div>

          {data.explanation && (
            <div style={{ marginBottom: "0.75rem", color: "#374151" }}>
              {data.explanation}
            </div>
          )}

          {Array.isArray(data.policy_citations) && data.policy_citations.length > 0 && (
            <>
              <div style={{ ...styles.sectionLabel, marginBottom: "0.5rem" }}>
                Citations
              </div>
              {data.policy_citations.map((c, i) => (
                <CitationCard key={i} citation={c} />
              ))}
            </>
          )}
        </div>
      )}
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
    <div style={styles.page}>
      {/* Top bar */}
      <header style={styles.header}>
        <span style={{ fontWeight: 600 }}>Benefits Navigator</span>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "0.9rem", color: "#6b7280" }}>
            {employeeId}
          </span>
          <button onClick={onLogout} style={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </header>

      {/* Query form */}
      <main style={styles.main}>
        <form onSubmit={handleSubmit} style={styles.queryForm}>
          <input
            style={styles.queryInput}
            type="text"
            placeholder="Ask a benefits question, e.g. 'Am I covered for dental cleaning?'"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            style={{
              ...styles.submitBtn,
              opacity: loading || !question.trim() ? 0.6 : 1,
            }}
            disabled={loading || !question.trim()}
          >
            {loading ? "Checking..." : "Ask"}
          </button>
        </form>

        {/* Error display */}
        {error && <div style={styles.errorBox}>{error}</div>}

        {/* Insufficient-info hint */}
        {result?.decision === "insufficient_info" && (
          <div style={styles.infoBox}>
            More details may be required (e.g., treatment type/date/provider).
          </div>
        )}

        {/* Result display */}
        {result && <ResultPanel data={result} />}
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f5f7fa",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.75rem 1.5rem",
    background: "#fff",
    borderBottom: "1px solid #e5e7eb",
  },
  logoutBtn: {
    padding: "0.3rem 0.75rem",
    fontSize: "0.85rem",
    background: "transparent",
    border: "1px solid #d1d5db",
    borderRadius: "4px",
    cursor: "pointer",
    color: "#374151",
  },
  main: {
    maxWidth: "720px",
    margin: "2rem auto",
    padding: "0 1rem",
  },
  queryForm: {
    display: "flex",
    gap: "0.5rem",
    marginBottom: "1.5rem",
  },
  queryInput: {
    flex: 1,
    padding: "0.6rem 0.75rem",
    fontSize: "1rem",
    border: "1px solid #ccc",
    borderRadius: "4px",
    outline: "none",
  },
  submitBtn: {
    padding: "0.6rem 1.25rem",
    fontSize: "1rem",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
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
    background: "#fff",
    padding: "1.5rem",
    borderRadius: "8px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
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
  enrichment: {
    marginTop: "1.25rem",
    padding: "1rem",
    background: "#f5f3ff",
    borderRadius: "6px",
    borderTop: "2px solid #8b5cf6",
  },
  enrichmentHeader: {
    fontSize: "0.9rem",
    fontWeight: 700,
    color: "#5b21b6",
    marginBottom: "0.75rem",
  },
};
