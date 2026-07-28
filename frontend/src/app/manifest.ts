import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Sericulture MIS · Directorate of Sericulture, Assam",
    short_name: "Sericulture MIS",
    description: "Unified information platform for Eri, Muga, Mulberry and Tasar silk in Assam.",
    start_url: "/",
    display: "standalone",
    background_color: "#F8F7F4",
    theme_color: "#2D5134",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
