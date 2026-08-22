"use client";
import { createContext, useContext, useEffect, useState, useMemo, ReactNode } from "react";
import api, { DISTRICT_KEY } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (mobile_no: string, password: string) => Promise<User>;
  logout: () => void;
  /** The district a District Admin is currently acting as; null for every other role.
   *  Use this anywhere you would otherwise reach for user.district_id, which is only the
   *  PRIMARY district and does not follow the switcher. */
  activeDistrictId: string | null;
  setActiveDistrict: (id: string) => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [activeDistrictId, setActiveDistrictId] = useState<string | null>(null);

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

  // Recompute whenever the user's assignments change -- login, the /auth/me refresh, or a
  // reassignment by the State Admin. Deliberately NOT gated on holding several districts:
  // an officer relieved of their additional charge drops to one, and if the stale id were
  // left in localStorage the interceptor would keep sending it and the server would refuse
  // every request, with no switcher on screen to correct it.
  useEffect(() => {
    if (!user || user.role !== "DISTRICT_ADMIN") {
      if (activeDistrictId !== null) setActiveDistrictId(null);
      localStorage.removeItem(DISTRICT_KEY);
      return;
    }
    const ids = user.district_ids && user.district_ids.length
      ? user.district_ids
      : (user.district_id ? [user.district_id] : []);
    if (!ids.length) return;
    const saved = localStorage.getItem(DISTRICT_KEY);
    const next = saved && ids.includes(saved) ? saved : ids[0];
    if (localStorage.getItem(DISTRICT_KEY) !== next) localStorage.setItem(DISTRICT_KEY, next);
    if (next !== activeDistrictId) setActiveDistrictId(next);
  }, [user?.id, user?.role, (user?.district_ids || []).join(","), user?.district_id]);

  const setActiveDistrict = (id: string) => {
    // Written to both places on purpose: React state so query keys change and every list
    // refetches, localStorage so the axios interceptor sends the matching header.
    localStorage.setItem(DISTRICT_KEY, id);
    setActiveDistrictId(id);
  };

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

  const value = useMemo(
    () => ({ user, login, logout, loading, activeDistrictId, setActiveDistrict }),
    [user, loading, activeDistrictId]);
  return <Ctx.Provider value={value}>{hydrated ? children : null}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside provider");
  return v;
}
