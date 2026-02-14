import React, { useState } from "react";

export default function LoginPage({ onLogin }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onLogin(trimmed);
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Corporate Health Benefits Navigator</h1>
        <p style={styles.subtitle}>Enter your Employee ID to get started.</p>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            type="text"
            placeholder="e.g. EMP001"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
          />
          <button style={styles.button} type="submit" disabled={!value.trim()}>
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f5f7fa",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  card: {
    background: "#fff",
    padding: "2.5rem 2rem",
    borderRadius: "8px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    maxWidth: "400px",
    width: "100%",
    textAlign: "center",
  },
  title: { margin: "0 0 0.25rem", fontSize: "1.4rem", color: "#1a1a2e" },
  subtitle: { margin: "0 0 1.5rem", color: "#666", fontSize: "0.95rem" },
  form: { display: "flex", flexDirection: "column", gap: "0.75rem" },
  input: {
    padding: "0.6rem 0.75rem",
    fontSize: "1rem",
    border: "1px solid #ccc",
    borderRadius: "4px",
    outline: "none",
  },
  button: {
    padding: "0.6rem",
    fontSize: "1rem",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
  },
};
