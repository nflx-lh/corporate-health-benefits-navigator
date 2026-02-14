import React, { useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import NavigatorPage from "./pages/NavigatorPage.jsx";

export default function App() {
  const [employeeId, setEmployeeId] = useState(null);

  if (!employeeId) {
    return <LoginPage onLogin={setEmployeeId} />;
  }

  return (
    <NavigatorPage
      employeeId={employeeId}
      onLogout={() => setEmployeeId(null)}
    />
  );
}
