"use client";
import axios, { AxiosInstance } from "axios";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";
export const API = `${BACKEND_URL}/api`;

export const DISTRICT_KEY = "seri_active_district";

const api: AxiosInstance = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  if (typeof window !== "undefined") {
    const t = localStorage.getItem("seri_token");
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
    // Which district a multi-district District Admin is currently acting as. The server
    // validates this against their actual assignments on every request, so it is a
    // request, not a grant -- an unassigned id comes back 403.
    const d = localStorage.getItem(DISTRICT_KEY);
    if (d) cfg.headers["X-District-Id"] = d;
  }
  return cfg;
});

let isRefreshing = false;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (typeof window === "undefined") return Promise.reject(err);
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      const refresh = localStorage.getItem("seri_refresh");
      if (refresh && !isRefreshing) {
        isRefreshing = true;
        try {
          const { data } = await axios.post(`${API}/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem("seri_token", data.access_token);
          localStorage.setItem("seri_refresh", data.refresh_token);
          original._retry = true;
          original.headers.Authorization = `Bearer ${data.access_token}`;
          isRefreshing = false;
          return api(original);
        } catch {
          isRefreshing = false;
          localStorage.removeItem("seri_token");
          localStorage.removeItem("seri_refresh");
          localStorage.removeItem("seri_user");
        localStorage.removeItem(DISTRICT_KEY);
          if (window.location.pathname !== "/login") window.location.href = "/login";
        }
      } else {
        localStorage.removeItem("seri_token");
        localStorage.removeItem("seri_refresh");
        localStorage.removeItem("seri_user");
        localStorage.removeItem(DISTRICT_KEY);
        if (window.location.pathname !== "/login") window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export function fmtErr(detail: unknown): string {
  if (!detail) return "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e: { msg?: string }) => e?.msg || JSON.stringify(e)).join("; ");
  return String(detail);
}

export default api;
