import React, { useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import NavigatorPage from "./pages/NavigatorPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";

export default function App() {
  const [employeeId, setEmployeeId] = useState(null);
  const [adminMode, setAdminMode] = useState(false);

  if (adminMode) {
    return <AdminPage onLogout={() => setAdminMode(false)} />;
  }

  if (!employeeId) {
    return (
      <LoginPage
        onLogin={setEmployeeId}
        onAdminLogin={() => setAdminMode(true)}
      />
    );
  }

  return (
    <NavigatorPage
      employeeId={employeeId}
      onLogout={() => setEmployeeId(null)}
    />
  );
}
