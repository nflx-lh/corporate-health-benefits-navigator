import React, { useEffect, useRef, useState } from "react";
import "../styles/login.css";

export default function LoginPage({ onLogin }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const employeeInputRef = useRef(null);

  useEffect(() => {
    employeeInputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`/v1/employees/${encodeURIComponent(trimmed)}/verify`);
      if (res.ok) {
        onLogin(trimmed);
      } else {
        const body = await res.json();
        const code = body?.error?.code;
        if (code === "EMPLOYEE_NOT_FOUND") {
          setError("Employee not found. Please check your ID.");
        } else if (code === "VALIDATION_ERROR") {
          setError("Invalid Employee ID format (e.g. EMP001).");
        } else {
          setError("Something went wrong. Please try again.");
        }
      }
    } catch {
      setError("Unable to reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <header className="app-header">
        <a className="brand" href="/" aria-label="AnovaGreen home">
          <img className="brand__logo" src="/images/logo-transparent.png" alt="" aria-hidden="true" />
        </a>
      </header>
      <div className="login-page">
        <aside className="login-page__media" aria-hidden="true">
          <img
            className="login-page__image"
            src="/images/ui-front.jpg"
            alt=""
          />
        </aside>
        <main className="login-page__content">
          <div className="login-page__card">
            <h1 className="login-page__title">Employee Health Benefits Platform</h1>
            <p className="login-page__subtitle">
              Enter your Employee Credentials to get started.
            </p>
            <form onSubmit={handleSubmit} className="login-page__form">
              <label className="login-page__label" htmlFor="employee-id-input">
                Employee ID
              </label>
              <input
                className="login-page__input login-input"
                id="employee-id-input"
                type="text"
                placeholder="e.g. EMP001"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                ref={employeeInputRef}
              />
              {error && <div className="login-page__error">{error}</div>}
              <button
                className="login-page__button login-button"
                type="submit"
                disabled={!value.trim() || loading}
              >
                {loading ? "Checking..." : "Continue"}
              </button>
            </form>
          </div>
        </main>
      </div>
    </>
  );
}
