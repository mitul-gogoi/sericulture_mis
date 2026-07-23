"use client";
import { createContext, useContext, useEffect, useState, useMemo, ReactNode } from "react";
import api from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (mobile_no: string, password: string) => Promise<User>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const u = localStorage.getItem("seri_user");
      if (u) setUser(JSON.parse(u));
    } catch {
      // ignore corrupt localStorage payload
    }
    setHydrated(true);
    const t = localStorage.getItem("seri_token");
    if (t) {
      api.get("/auth/me").then((r) => {
        setUser(r.data);
        localStorage.setItem("seri_user", JSON.stringify(r.data));
      }).catch(() => {});
    }
  }, []);

  const login = async (mobile_no: string, password: string) => {
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { mobile_no, password });
      localStorage.setItem("seri_token", data.access_token);
      localStorage.setItem("seri_refresh", data.refresh_token);
      localStorage.setItem("seri_user", JSON.stringify(data.user));
      setUser(data.user);
      return data.user;
    } finally { setLoading(false); }
  };

  const logout = () => {
    localStorage.removeItem("seri_token");
    localStorage.removeItem("seri_refresh");
    localStorage.removeItem("seri_user");
    setUser(null);
    if (typeof window !== "undefined") window.location.href = "/login";
  };

  const value = useMemo(() => ({ user, login, logout, loading }), [user, loading]);
  return <Ctx.Provider value={value}>{hydrated ? children : null}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside provider");
  return v;
}
