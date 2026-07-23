"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { fmtErr } from "@/lib/api";
import { Leaf } from "@phosphor-icons/react";
import { toast } from "sonner";

const HERO =
  "https://images.unsplash.com/photo-1640292343595-889db1c8262e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwxfHxoYW5kbG9vbSUyMHdlYXZpbmclMjBpbmRpYXxlbnwwfHx8fDE3ODExNTQ5ODV8MA&ixlib=rb-4.1.0&q=85";

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
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={HERO}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(33,61,38,0.55), rgba(33,61,38,0.85))",
          }}
        />
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

          <div
            className="mt-10 card p-4 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            <div className="label-tag mb-2">Demo accounts</div>
            <div>State Admin · 1111111111 / sa@123</div>
          </div>
        </div>
      </div>
    </div>
  );
}
