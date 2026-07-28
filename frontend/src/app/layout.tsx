import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Sericulture MIS · Directorate of Sericulture, Assam",
  description: "Unified information platform for Eri, Muga, Mulberry and Tasar silk in Assam.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Sericulture MIS",
  },
};

export const viewport: Viewport = {
  themeColor: "#2D5134",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
