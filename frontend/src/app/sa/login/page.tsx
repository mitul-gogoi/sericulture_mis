"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
export default function SaLogin() { const r = useRouter(); useEffect(() => r.replace("/login"), [r]); return null; }
