import React, { useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import NavigatorPage from "./pages/NavigatorPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import ChangePasswordPage from "./pages/ChangePasswordPage.jsx";

export default function App() {
  const [employeeId, setEmployeeId] = useState(null);
  const [token, setToken] = useState(null);
  const [mustResetPassword, setMustResetPassword] = useState(false);
  const [adminMode, setAdminMode] = useState(false);

  if (adminMode) {
    return <AdminPage onLogout={() => setAdminMode(false)} />;
  }

  if (!employeeId) {
    return (
      <LoginPage
        onLogin={(id, tok, mustReset) => {
          setEmployeeId(id);
          setToken(tok);
          setMustResetPassword(!!mustReset);
        }}
        onAdminLogin={() => setAdminMode(true)}
      />
    );
  }

  if (mustResetPassword) {
    return (
      <ChangePasswordPage
        token={token}
        onPasswordChanged={() => setMustResetPassword(false)}
      />
    );
  }

  return (
    <NavigatorPage
      employeeId={employeeId}
      onLogout={() => {
        setEmployeeId(null);
        setToken(null);
        setMustResetPassword(false);
      }}
    />
  );
}
