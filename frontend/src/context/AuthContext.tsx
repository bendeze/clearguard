import * as React from "react";

import { clearTokens, getStoredTokens, saveTokens } from "@/api/client";
import { authApi } from "@/api/endpoints";
import type { UserProfileResponse } from "@/types/api";

interface AuthContextValue {
  user: UserProfileResponse | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

async function fetchAdminProfile(): Promise<UserProfileResponse | null> {
  const tokens = getStoredTokens();
  if (!tokens) return null;

  try {
    const profile = await authApi.getMe();
    if (!profile.is_admin) {
      clearTokens();
      return null;
    }
    return profile;
  } catch {
    clearTokens();
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    void fetchAdminProfile().then((profile) => {
      if (!active) return;
      setUser(profile);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const refreshProfile = React.useCallback(async () => {
    setLoading(true);
    const profile = await fetchAdminProfile();
    setUser(profile);
    setLoading(false);
  }, []);

  const login = React.useCallback(async (username: string, password: string) => {
    const tokens = await authApi.login({
      username: username.trim(),
      password,
      device_name: "ClearGuard Admin Web",
    });
    saveTokens(tokens);

    const profile = await authApi.getMe();
    if (!profile.is_admin) {
      clearTokens();
      throw new Error(
        "Access denied: this account does not have administrator privileges.",
      );
    }

    setUser(profile);
  }, []);

  const logout = React.useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({ user, loading, login, logout, refreshProfile }),
    [user, loading, login, logout, refreshProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
