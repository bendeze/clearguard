import * as React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { BlocklistDetailPage } from "@/pages/BlocklistDetailPage";
import { BlocklistsPage } from "@/pages/BlocklistsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { OverridesPage } from "@/pages/OverridesPage";
import { PartnerVerifyPage } from "@/pages/PartnerVerifyPage";
import { SecurityKeysPage } from "@/pages/SecurityKeysPage";

function ProtectedAdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="text-muted-foreground flex min-h-screen items-center justify-center text-sm">
        Verifying session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <AppShell>{children}</AppShell>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/verify" element={<PartnerVerifyPage />} />
      <Route
        path="/"
        element={
          <ProtectedAdminRoute>
            <DashboardPage />
          </ProtectedAdminRoute>
        }
      />
      <Route
        path="/overrides"
        element={
          <ProtectedAdminRoute>
            <OverridesPage />
          </ProtectedAdminRoute>
        }
      />
      <Route
        path="/blocklists"
        element={
          <ProtectedAdminRoute>
            <BlocklistsPage />
          </ProtectedAdminRoute>
        }
      />
      <Route
        path="/blocklists/:id"
        element={
          <ProtectedAdminRoute>
            <BlocklistDetailPage />
          </ProtectedAdminRoute>
        }
      />
      <Route
        path="/keys"
        element={
          <ProtectedAdminRoute>
            <SecurityKeysPage />
          </ProtectedAdminRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
