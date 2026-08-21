import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Manrope, IBM_Plex_Sans } from "next/font/google";
import { Providers } from "./providers";

// Self-hosted at build time rather than pulled from fonts.googleapis.com at runtime.
// The old CSS @import was render-blocking and produced a visible font swap on every
// page load; next/font inlines the face declarations and serves the files from our
// own origin, which also means the app still renders correctly with no internet.
const manrope = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-heading",
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

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
    <html lang="en" className={`${manrope.variable} ${plexSans.variable}`}>
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
