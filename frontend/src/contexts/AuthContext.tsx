/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, UserResponse, OrganizationMemberResponse } from "@/services/api";

interface AuthContextType {
  user: UserResponse | null;
  activeOrg: OrganizationMemberResponse | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    full_name: string,
    organization_name?: string
  ) => Promise<void>;
  logout: () => void;
  setActiveOrg: (org: OrganizationMemberResponse) => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("dcp_access_token"));
  const [user, setUser] = useState<UserResponse | null>(null);
  const [activeOrg, setActiveOrgState] = useState<OrganizationMemberResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfile = useCallback(async () => {
    const currentToken = localStorage.getItem("dcp_access_token");
    if (!currentToken) {
      setUser(null);
      setActiveOrgState(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.auth.getMe();
      setUser(profile);

      // Select active organization
      const storedOrgId = localStorage.getItem("dcp_active_org_id");
      if (profile.memberships && profile.memberships.length > 0) {
        const found = profile.memberships.find((m) => m.organization_id === storedOrgId);
        const selected = found || profile.memberships[0];
        setActiveOrgState(selected);
        localStorage.setItem("dcp_active_org_id", selected.organization_id);
      }
    } catch {
      // Token expired or invalid
      localStorage.removeItem("dcp_access_token");
      localStorage.removeItem("dcp_refresh_token");
      localStorage.removeItem("dcp_active_org_id");
      setToken(null);
      setUser(null);
      setActiveOrgState(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.auth.login({ email, password });
      localStorage.setItem("dcp_access_token", res.access_token);
      localStorage.setItem("dcp_refresh_token", res.refresh_token);
      setToken(res.access_token);
      await fetchProfile();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    email: string,
    password: string,
    full_name: string,
    organization_name?: string
  ) => {
    setIsLoading(true);
    try {
      const res = await api.auth.register({ email, password, full_name, organization_name });
      localStorage.setItem("dcp_access_token", res.access_token);
      localStorage.setItem("dcp_refresh_token", res.refresh_token);
      setToken(res.access_token);
      await fetchProfile();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.auth.logout();
    setToken(null);
    setUser(null);
    setActiveOrgState(null);
  };

  const setActiveOrg = (org: OrganizationMemberResponse) => {
    setActiveOrgState(org);
    localStorage.setItem("dcp_active_org_id", org.organization_id);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        login,
        register,
        logout,
        setActiveOrg,
        refreshProfile: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
