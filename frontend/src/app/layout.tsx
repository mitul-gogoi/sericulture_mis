import "./globals.css";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Sericulture MIS · Directorate of Sericulture, Assam",
  description: "Unified information platform for Eri, Muga, Mulberry and Tasar silk in Assam.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
