import React, { useEffect, useRef, useState } from "react";
import PasswordInput from "../components/PasswordInput.jsx";
import "../styles/admin.css";

const API_BASE = "/v1";

const formatLabel = (val) =>
  val ? val.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "\u2014";

export default function AdminPage({ onLogout }) {
  const [token, setToken] = useState(null);
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [empId, setEmpId] = useState("");
  const [password, setPassword] = useState("");

  if (!token) {
    return (
      <AdminLogin
        empId={empId}
        setEmpId={setEmpId}
        password={password}
        setPassword={setPassword}
        error={loginError}
        loading={loginLoading}
        onSubmit={async (e) => {
          e.preventDefault();
          if (!empId.trim() || !password.trim() || loginLoading) return;
          setLoginError(null);
          setLoginLoading(true);
          try {
            const res = await fetch(`${API_BASE}/auth/login`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ employee_id: empId.trim(), password }),
            });
            const data = await res.json();
            if (res.ok && data.role === "hr_admin") {
              setToken(data.access_token);
            } else if (res.ok) {
              setLoginError("This account does not have admin privileges.");
            } else {
              setLoginError(data?.error?.message || "Invalid credentials.");
            }
          } catch {
            setLoginError("Unable to reach the server.");
          } finally {
            setLoginLoading(false);
          }
        }}
        onBack={onLogout}
      />
    );
  }

  return <AdminDashboard token={token} onLogout={onLogout} />;
}

/* ------------------------------------------------------------------ */
/*  Admin Login                                                        */
/* ------------------------------------------------------------------ */

function AdminLogin({ empId, setEmpId, password, setPassword, error, loading, onSubmit, onBack }) {
  const idRef = useRef(null);
  useEffect(() => { idRef.current?.focus(); }, []);

  return (
    <>
      <header className="app-header">
        <a className="brand" href="/" aria-label="AnovaGreen home">
          <img className="brand__logo" src="/images/logo-transparent.png" alt="" aria-hidden="true" />
        </a>
      </header>
      <div className="admin-login">
        <div className="admin-login__card">
          <h1 className="admin-login__title">Admin Login</h1>
          <p className="admin-login__subtitle">Sign in with your HR admin credentials.</p>
          <form onSubmit={onSubmit} className="admin-login__form">
            <label className="admin-login__label" htmlFor="admin-emp-id">Employee ID</label>
            <input
              className="admin-login__input"
              id="admin-emp-id"
              type="text"
              placeholder="e.g. HR001"
              value={empId}
              onChange={(e) => setEmpId(e.target.value)}
              ref={idRef}
            />
            <label className="admin-login__label" htmlFor="admin-password">Password</label>
            <PasswordInput
              className="admin-login__input"
              id="admin-password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div className="admin-login__error">{error}</div>}
            <button
              className="admin-login__button"
              type="submit"
              disabled={!empId.trim() || !password.trim() || loading}
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
          <button className="admin-login__back" type="button" onClick={onBack}>
            Back to Employee Login
          </button>
        </div>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Admin Dashboard                                                    */
/* ------------------------------------------------------------------ */

function AdminDashboard({ token, onLogout }) {
  const [activeTab, setActiveTab] = useState("employees");
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [tempPasswordModal, setTempPasswordModal] = useState(null);
  const [pendingResetCount, setPendingResetCount] = useState(0);

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  const fetchPendingResetCount = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/password-reset-requests?status=pending`, { headers });
      if (res.ok) {
        const data = await res.json();
        setPendingResetCount(data.length);
      }
    } catch {
      // silent — badge is non-critical
    }
  };

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/employees`, { headers });
      if (!res.ok) throw new Error("Failed to load employees");
      setEmployees(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchEmployees(); fetchPendingResetCount(); }, []);

  const handleCreate = async (data) => {
    const res = await fetch(`${API_BASE}/admin/employees`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json();
      throw new Error(body?.error?.message || "Create failed");
    }
    const result = await res.json();
    await fetchEmployees();
    setFormOpen(false);
    if (result.temp_password) {
      setTempPasswordModal({ employeeId: result.employee_id, tempPassword: result.temp_password });
    }
  };

  const handleUpdate = async (employeeId, data) => {
    const res = await fetch(`${API_BASE}/admin/employees/${encodeURIComponent(employeeId)}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json();
      throw new Error(body?.error?.message || "Update failed");
    }
    await fetchEmployees();
    setEditing(null);
  };

  const handleDelete = async (employeeId) => {
    const res = await fetch(`${API_BASE}/admin/employees/${encodeURIComponent(employeeId)}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) {
      const body = await res.json();
      throw new Error(body?.error?.message || "Delete failed");
    }
    await fetchEmployees();
    setDeleteTarget(null);
  };

  return (
    <div className="admin-page">
      <header className="admin-header">
        <span className="admin-header__title">Admin Dashboard</span>
        <button className="admin-header__logout" onClick={onLogout}>Logout</button>
      </header>

      <main className="admin-main">
        <div className="admin-tabs">
          <button
            className={`admin-tabs__tab ${activeTab === "employees" ? "admin-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab("employees")}
          >
            Employee Management
          </button>
          <button
            className={`admin-tabs__tab ${activeTab === "resets" ? "admin-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab("resets")}
          >
            Reset Requests
            {pendingResetCount > 0 && (
              <span className="admin-tabs__badge">!</span>
            )}
          </button>
          <button
            className={`admin-tabs__tab ${activeTab === "analytics" ? "admin-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab("analytics")}
          >
            Analytics
          </button>
        </div>

        {activeTab === "employees" && (
          <>
            <div className="admin-toolbar">
              <h2 className="admin-toolbar__title">Employee Management</h2>
              <button
                className="admin-toolbar__create-btn"
                onClick={() => { setEditing(null); setFormOpen(true); }}
              >
                + New Employee
              </button>
            </div>

            {error && <div className="admin-error">{error}</div>}

            {formOpen && !editing && (
              <EmployeeForm
                initial={null}
                onSave={handleCreate}
                onCancel={() => setFormOpen(false)}
              />
            )}

            {editing && (
              <div className="admin-modal-overlay" onClick={() => setEditing(null)}>
                <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
                  <EmployeeForm
                    initial={editing}
                    onSave={(data) => handleUpdate(editing.employee_id, data)}
                    onCancel={() => setEditing(null)}
                  />
                </div>
              </div>
            )}

            {deleteTarget && (
              <div className="admin-modal-overlay" onClick={() => setDeleteTarget(null)}>
                <div className="admin-modal admin-modal--narrow" onClick={(e) => e.stopPropagation()}>
                  <div className="admin-confirm">
                    <p>Delete employee <strong>{deleteTarget}</strong>?</p>
                    <p className="admin-confirm__warning">This action cannot be undone.</p>
                    <div className="admin-confirm__actions">
                      <button className="admin-confirm__yes" onClick={() => handleDelete(deleteTarget)}>
                        Yes, Delete
                      </button>
                      <button className="admin-confirm__no" onClick={() => setDeleteTarget(null)}>
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {loading ? (
              <p className="admin-loading">Loading employees...</p>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Age</th>
                      <th>Type</th>
                      <th>Plan</th>
                      <th>Tenure</th>
                      <th>Deps</th>
                      <th>Active</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {employees.length === 0 ? (
                      <tr><td colSpan="9" className="admin-table__empty">No employees found.</td></tr>
                    ) : (
                      employees.map((emp) => (
                        <tr key={emp.employee_id}>
                          <td>{emp.employee_id}</td>
                          <td>{emp.name || "\u2014"}</td>
                          <td>{emp.age ?? "\u2014"}</td>
                          <td>{formatLabel(emp.employment_type)}</td>
                          <td>{formatLabel(emp.plan_tier)}</td>
                          <td>{emp.tenure_months ?? "\u2014"}</td>
                          <td>{emp.dependents_count}</td>
                          <td>{emp.is_active ? "Yes" : "No"}</td>
                          <td className="admin-table__actions">
                            <button className="admin-action-btn admin-action-btn--edit" onClick={() => { setFormOpen(false); setEditing(emp); }}>Edit</button>
                            <button className="admin-action-btn admin-action-btn--delete" onClick={() => setDeleteTarget(emp.employee_id)}>Delete</button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {activeTab === "resets" && (
          <ResetRequests token={token} headers={headers} onTempPassword={setTempPasswordModal} onCountChange={setPendingResetCount} />
        )}

        {activeTab === "analytics" && (
          <AnalyticsDashboard headers={headers} />
        )}

        {tempPasswordModal && (
          <TempPasswordModal
            employeeId={tempPasswordModal.employeeId}
            tempPassword={tempPasswordModal.tempPassword}
            onClose={() => setTempPasswordModal(null)}
          />
        )}
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Reset Requests Section                                             */
/* ------------------------------------------------------------------ */

function ResetRequests({ token, headers, onTempPassword, onCountChange }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/password-reset-requests?status=pending`, { headers });
      if (!res.ok) throw new Error("Failed to load reset requests");
      const data = await res.json();
      setRequests(data);
      if (onCountChange) onCountChange(data.length);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRequests(); }, []);

  const handleReset = async (requestId, employeeId) => {
    setActionLoading(requestId);
    try {
      const res = await fetch(`${API_BASE}/admin/password-reset-requests/${requestId}/reset`, {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body?.error?.message || "Reset failed");
      }
      const data = await res.json();
      onTempPassword({ employeeId, tempPassword: data.temp_password });
      await fetchRequests();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (requestId) => {
    setActionLoading(requestId);
    try {
      const res = await fetch(`${API_BASE}/admin/password-reset-requests/${requestId}/reject`, {
        method: "POST",
        headers,
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body?.error?.message || "Reject failed");
      }
      await fetchRequests();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <>
      <div className="admin-toolbar">
        <h2 className="admin-toolbar__title">Password Reset Requests</h2>
        <button className="admin-toolbar__create-btn" onClick={fetchRequests}>
          Refresh
        </button>
      </div>

      {error && <div className="admin-error">{error}</div>}

      {loading ? (
        <p className="admin-loading">Loading reset requests...</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Employee</th>
                <th>Status</th>
                <th>Requested</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.length === 0 ? (
                <tr><td colSpan="5" className="admin-table__empty">No pending reset requests.</td></tr>
              ) : (
                requests.map((req) => (
                  <tr key={req.id}>
                    <td>{req.id}</td>
                    <td>{req.employee_id}</td>
                    <td>{req.status}</td>
                    <td>{req.requested_at ? new Date(req.requested_at).toLocaleString() : "\u2014"}</td>
                    <td className="admin-table__actions">
                      <button
                        className="admin-action-btn admin-action-btn--edit"
                        onClick={() => handleReset(req.id, req.employee_id)}
                        disabled={actionLoading === req.id}
                      >
                        {actionLoading === req.id ? "..." : "Reset"}
                      </button>
                      <button
                        className="admin-action-btn admin-action-btn--delete"
                        onClick={() => handleReject(req.id)}
                        disabled={actionLoading === req.id}
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Temp Password Modal                                                */
/* ------------------------------------------------------------------ */

function TempPasswordModal({ employeeId, tempPassword, onClose }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(tempPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for HTTP (non-secure context) where clipboard API is blocked
      const el = document.createElement('textarea');
      el.value = tempPassword;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="temp-pw-overlay" onClick={onClose}>
      <div className="temp-pw-modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="temp-pw-modal__title">Temporary Password</h3>
        <p className="temp-pw-modal__info">
          Employee <strong>{employeeId}</strong> has been assigned a temporary password.
          They will be required to change it on first login.
        </p>
        <div className="temp-pw-modal__password-row">
          <code className="temp-pw-modal__password">{tempPassword}</code>
          <button className="temp-pw-modal__copy" onClick={handleCopy}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <button className="temp-pw-modal__close" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Analytics Dashboard (B-1703)                                       */
/* ------------------------------------------------------------------ */

function AnalyticsDashboard({ headers }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/analytics`, { headers });
      if (!res.ok) throw new Error("Failed to load analytics");
      setData(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAnalytics(); }, []);

  if (loading) return <p className="admin-loading">Loading analytics...</p>;
  if (error) return <div className="admin-error">{error}</div>;
  if (!data) return null;

  return (
    <>
      <div className="admin-toolbar">
        <h2 className="admin-toolbar__title">Query Analytics</h2>
        <button className="admin-toolbar__create-btn" onClick={fetchAnalytics}>Refresh</button>
      </div>

      <div className="analytics-grid">
        <div className="analytics-card">
          <div className="analytics-card__label">Total Queries</div>
          <div className="analytics-card__value">{data.total_queries}</div>
        </div>
        <div className="analytics-card">
          <div className="analytics-card__label">Last 7 Days</div>
          <div className="analytics-card__value">{data.recent_7_days}</div>
        </div>
      </div>

      <div className="analytics-tables">
        <AnalyticsTable title="By Decision" rows={data.by_decision} />
        <AnalyticsTable title="By Benefit Type" rows={data.by_benefit_type} />
      </div>
    </>
  );
}

function AnalyticsTable({ title, rows }) {
  const entries = Object.entries(rows || {}).sort((a, b) => b[1] - a[1]);
  return (
    <div className="analytics-section">
      <h3 className="analytics-section__title">{title}</h3>
      {entries.length === 0 ? (
        <p className="admin-loading">No data yet.</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr><th>Category</th><th>Count</th></tr>
            </thead>
            <tbody>
              {entries.map(([key, count]) => (
                <tr key={key}>
                  <td>{formatLabel(key)}</td>
                  <td>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Employee Form (Create / Edit)                                      */
/* ------------------------------------------------------------------ */

function EmployeeForm({ initial, onSave, onCancel }) {
  const isEdit = !!initial;
  const [formData, setFormData] = useState({
    employee_id: initial?.employee_id || "",
    name: initial?.name || "",
    age: initial?.age ?? "",
    employment_type: initial?.employment_type || "",
    plan_tier: initial?.plan_tier || "",
    tenure_months: initial?.tenure_months ?? "",
    dependents_count: initial?.dependents_count ?? 0,
    is_active: initial?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const set = (field) => (e) => setFormData({ ...formData, [field]: e.target.value });

  const validate = () => {
    const errors = [];
    if (!isEdit && !formData.employee_id.trim()) errors.push("Employee ID is required.");
    if (!formData.name.trim()) errors.push("Name is required.");
    if (!formData.employment_type) errors.push("Employment Type is required.");
    if (!formData.plan_tier) errors.push("Plan Tier is required.");
    if (formData.age === "" || formData.age === null) errors.push("Age is required.");
    else if (Number(formData.age) < 16 || Number(formData.age) > 100) errors.push("Age must be between 16 and 100.");
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    const errors = validate();
    if (errors.length) {
      setFormError(errors.join(" "));
      return;
    }
    setSaving(true);
    try {
      const payload = { ...formData };
      // Convert numeric fields
      payload.age = payload.age === "" ? null : Number(payload.age);
      payload.tenure_months = payload.tenure_months === "" ? null : Number(payload.tenure_months);
      payload.dependents_count = Number(payload.dependents_count) || 0;
      payload.is_active = formData.is_active === true || formData.is_active === "true";
      // For edit, don't send employee_id in body
      if (isEdit) delete payload.employee_id;
      // For create/edit, strip empty strings to null
      if (!payload.name) payload.name = null;
      if (!payload.employment_type) payload.employment_type = null;
      if (!payload.plan_tier) payload.plan_tier = null;
      await onSave(payload);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-form">
      <h3 className="admin-form__title">{isEdit ? "Edit Employee" : "New Employee"}</h3>
      <form onSubmit={handleSubmit} className="admin-form__grid">
        <label className="admin-form__field">
          <span>Employee ID</span>
          <input type="text" value={formData.employee_id} onChange={set("employee_id")} disabled={isEdit} placeholder="e.g. TST001" required />
        </label>
        <label className="admin-form__field">
          <span>Name</span>
          <input type="text" value={formData.name} onChange={set("name")} placeholder="Full name" required />
        </label>
        <label className="admin-form__field">
          <span>Age</span>
          <input type="number" value={formData.age} onChange={set("age")} min="16" max="100" required />
        </label>
        <label className="admin-form__field">
          <span>Employment Type</span>
          <select value={formData.employment_type} onChange={set("employment_type")} required>
            <option value="">-- Select --</option>
            <option value="full_time">Full Time</option>
            <option value="part_time">Part Time</option>
            <option value="contract">Contract</option>
          </select>
        </label>
        <label className="admin-form__field">
          <span>Plan Tier</span>
          <select value={formData.plan_tier} onChange={set("plan_tier")} required>
            <option value="">-- Select --</option>
            <option value="basic">Basic</option>
            <option value="standard">Standard</option>
            <option value="premium">Premium</option>
          </select>
        </label>
        <label className="admin-form__field">
          <span>Tenure (months)</span>
          <input type="number" value={formData.tenure_months} onChange={set("tenure_months")} min="0" />
        </label>
        <label className="admin-form__field">
          <span>Dependents</span>
          <input type="number" value={formData.dependents_count} onChange={set("dependents_count")} min="0" />
        </label>
        <label className="admin-form__field admin-form__field--checkbox">
          <input
            type="checkbox"
            checked={formData.is_active === true || formData.is_active === "true"}
            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
          />
          <span>Active</span>
        </label>
        {formError && <div className="admin-form__error">{formError}</div>}
        <div className="admin-form__actions">
          <button className="admin-form__save" type="submit" disabled={saving}>
            {saving ? "Saving..." : isEdit ? "Update" : "Create"}
          </button>
          <button className="admin-form__cancel" type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
