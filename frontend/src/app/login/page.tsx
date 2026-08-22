"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { fmtErr } from "@/lib/api";
import { Leaf } from "@phosphor-icons/react";
import { toast } from "sonner";
import { Attribution } from "@/components/Attribution";


export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const router = useRouter();
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      const u = await login(mobile.trim(), password);
      toast.success(`Welcome, ${u.name || u.mobile_no}`);
      window.location.href = "/dashboard";
    } catch (e: any) {
      // slowapi's own 429 (too many login attempts from this IP) responds with
      // {"error": "..."} rather than FastAPI's usual {"detail": "..."} shape.
      const detail = e.response?.data?.detail ?? e.response?.data?.error;
      setErr(fmtErr(detail) || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
      <div
        className="hidden lg:flex w-1/2 relative"
        style={{ background: "var(--primary)" }}
      >
        {/* Self-contained: no external image, so the panel renders identically on an
            air-gapped government network. The motif is a woven silk-thread lattice. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(circle at 25% 15%, rgba(217,160,54,0.22), transparent 55%), linear-gradient(160deg, #2D5134 0%, #213D26 55%, #16281B 100%)",
          }}
        />
        <svg className="absolute inset-0 w-full h-full" aria-hidden="true" preserveAspectRatio="none">
          <defs>
            <pattern id="weave" width="26" height="26" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="26" stroke="#D9A036" strokeWidth="1" strokeOpacity="0.16" />
              <line x1="0" y1="0" x2="26" y2="0" stroke="#FFFFFF" strokeWidth="1" strokeOpacity="0.07" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#weave)" />
        </svg>
        <div className="relative z-10 p-12 flex flex-col justify-between text-white w-full">
          <div className="flex items-center gap-3">
            <Leaf size={32} weight="duotone" color="#D9A036" />
            <div className="font-heading font-extrabold text-lg">
              Directorate of Sericulture · Assam
            </div>
          </div>
          <div>
            <h1 className="font-heading text-4xl lg:text-5xl font-extrabold mt-3 leading-tight">
              SERICULTURE MIS
            </h1>
            <h1 className="font-heading font-extrabold text-lg">
              From leaf to thread.
            </h1>
            <p className="mt-4 text-white/80 max-w-md text-base">
              The unified information platform for Eri, Muga, Mulberry and Tasar
              —{" "}
              <b>
                connecting farmers, FIGs, district offices and the state
                administration{" "}
              </b>{" "}
              in one dignified workspace.
            </p>
          </div>
          <div className="text-xs text-white/60">
            © Directorate of Sericulture, Government of Assam
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <Leaf size={28} weight="duotone" color="#2D5134" />
            <span className="font-heading font-bold text-lg">
              Sericulture MIS
            </span>
          </div>
          <h2 className="font-heading text-3xl font-extrabold">Sign in</h2>
          <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
            Enter your registered mobile number and password
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="label-tag block mb-1.5">Mobile number</label>
              <input
                data-testid="login-mobile"
                className="input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={10}
                value={mobile}
                onChange={(e) => setMobile(e.target.value.replace(/\D/g, "").slice(0, 10))}
                placeholder="10-digit mobile"
                required
              />
            </div>
            <div>
              <label className="label-tag block mb-1.5">Password</label>
              <input
                data-testid="login-password"
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {err && (
              <div className="text-sm" style={{ color: "var(--error)" }}>
                {err}
              </div>
            )}
            <button
              data-testid="login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          {/* Under the form rather than in the hero panel: the hero is hidden below lg,
              so this is the one spot visible on every screen size. */}
          <Attribution className="mt-8 text-center"
                       style={{ color: "var(--text-muted)" }} />
        </div>
      </div>
    </div>
  );
}
