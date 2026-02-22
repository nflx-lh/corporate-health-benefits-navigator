import React, { useState } from "react";
import PasswordInput from "../components/PasswordInput.jsx";
import "../styles/login.css";

export default function ChangePasswordPage({ token, onPasswordChanged }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    setError(null);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/v1/auth/employee/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (res.ok) {
        onPasswordChanged();
      } else {
        const data = await res.json();
        const code = data?.error?.code;
        if (code === "INVALID_CREDENTIALS") {
          setError("Current password is incorrect.");
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

  return (
    <>
      <header className="app-header">
        <a className="brand" href="/" aria-label="AnovaGreen home">
          <img className="brand__logo" src="/images/logo-transparent.png" alt="" aria-hidden="true" />
        </a>
      </header>
      <div className="change-password-page">
        <div className="change-password-card">
          <h1 className="change-password-card__title">Change Your Password</h1>
          <p className="change-password-card__subtitle">
            You must set a new password before continuing.
          </p>
          <form onSubmit={handleSubmit} className="change-password-card__form">
            <label className="change-password-card__label" htmlFor="current-pw">
              Current Password
            </label>
            <PasswordInput
              className="change-password-card__input"
              id="current-pw"
              placeholder="Enter current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <label className="change-password-card__label" htmlFor="new-pw">
              New Password
            </label>
            <PasswordInput
              className="change-password-card__input"
              id="new-pw"
              placeholder="Min. 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <label className="change-password-card__label" htmlFor="confirm-pw">
              Confirm New Password
            </label>
            <PasswordInput
              className="change-password-card__input"
              id="confirm-pw"
              placeholder="Re-enter new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {error && <div className="change-password-card__error">{error}</div>}
            <button
              className="change-password-card__button"
              type="submit"
              disabled={!currentPassword || !newPassword || !confirmPassword || loading}
            >
              {loading ? "Updating..." : "Update Password"}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
