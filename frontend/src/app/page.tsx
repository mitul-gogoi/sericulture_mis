"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user } = useAuth();
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.location.replace(user ? "/dashboard" : "/login");
    }
  }, [user]);
  return <div className="p-8 text-sm text-[#5C635B]">Loading…</div>;
}
