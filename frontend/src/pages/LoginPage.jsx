import React, { useEffect, useRef, useState } from "react";
import PasswordInput from "../components/PasswordInput.jsx";
import "../styles/login.css";

export default function LoginPage({ onLogin, onAdminLogin }) {
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [resetMode, setResetMode] = useState(false);
  const [resetId, setResetId] = useState("");
  const [resetMsg, setResetMsg] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const employeeInputRef = useRef(null);

  useEffect(() => {
    employeeInputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedId = employeeId.trim();
    const trimmedPw = password.trim();
    if (!trimmedId || !trimmedPw || loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: trimmedId, password: trimmedPw }),
      });
      const data = await res.json();

      if (res.ok) {
        onLogin(trimmedId, data.access_token, data.must_reset_password);
      } else {
        const code = data?.error?.code;
        if (code === "INVALID_CREDENTIALS") {
          setError("Invalid Employee ID or password.");
        } else {
          setError(data?.error?.message || "Something went wrong. Please try again.");
        }
      }
    } catch {
      setError("Unable to reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetRequest = async (e) => {
    e.preventDefault();
    const trimmed = resetId.trim();
    if (!trimmed || resetLoading) return;

    setResetMsg(null);
    setResetLoading(true);

    try {
      const res = await fetch("/v1/auth/employee/request-password-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: trimmed }),
      });
      if (res.ok) {
        setResetMsg("Password reset request submitted. HR admin will be in touch shortly.");
      } else {
        setResetMsg("Something went wrong. Please try again.");
      }
    } catch {
      setResetMsg("Unable to reach the server. Please try again.");
    } finally {
      setResetLoading(false);
    }
  };

  const handleAdminLogin = () => {
    if (onAdminLogin) onAdminLogin();
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

            {!resetMode ? (
              <>
                <form onSubmit={handleSubmit} className="login-page__form">
                  <label className="login-page__label" htmlFor="employee-id-input">
                    Employee ID
                  </label>
                  <input
                    className="login-page__input login-input"
                    id="employee-id-input"
                    type="text"
                    placeholder="e.g. EMP001"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    ref={employeeInputRef}
                  />
                  <label className="login-page__label" htmlFor="password-input">
                    Password
                  </label>
                  <PasswordInput
                    className="login-page__input login-input"
                    id="password-input"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  {error && <div className="login-page__error">{error}</div>}
                  <button
                    className="login-page__button login-button"
                    type="submit"
                    disabled={!employeeId.trim() || !password.trim() || loading}
                  >
                    {loading ? "Signing in..." : "Sign In"}
                  </button>
                </form>
                <button
                  className="login-page__forgot"
                  type="button"
                  onClick={() => { setResetMode(true); setResetMsg(null); setResetId(""); }}
                >
                  Forgot password?
                </button>
              </>
            ) : (
              <>
                <form onSubmit={handleResetRequest} className="login-page__form">
                  <label className="login-page__label" htmlFor="reset-id-input">
                    Employee ID
                  </label>
                  <input
                    className="login-page__input login-input"
                    id="reset-id-input"
                    type="text"
                    placeholder="e.g. EMP001"
                    value={resetId}
                    onChange={(e) => setResetId(e.target.value)}
                  />
                  {resetMsg && <div className="login-page__info">{resetMsg}</div>}
                  <button
                    className="login-page__button login-button"
                    type="submit"
                    disabled={!resetId.trim() || resetLoading}
                  >
                    {resetLoading ? "Submitting..." : "Request Password Reset"}
                  </button>
                </form>
                <button
                  className="login-page__forgot"
                  type="button"
                  onClick={() => { setResetMode(false); setError(null); }}
                >
                  Back to login
                </button>
              </>
            )}
          </div>
        </main>
      </div>
      <button
        className="login-page__admin-fab"
        type="button"
        onClick={handleAdminLogin}
        title="Admin Access"
        aria-label="Admin Access"
      >
        <img src="/images/admin-icon.png" alt="Admin" className="login-page__admin-fab-icon" />
      </button>
    </>
  );
}
