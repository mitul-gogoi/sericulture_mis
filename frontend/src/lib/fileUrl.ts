"use client";

/**
 * Link to an uploaded file, for a plain <a href> the browser navigates to.
 *
 * The token goes in the query string rather than an Authorization header because these
 * are ordinary navigations (target="_blank"), which cannot carry axios's headers — the
 * backend's GET /api/files/{path} accepts `?auth=` for exactly this reason.
 *
 * Every stored path contains spaces ("File Uploads/FIG Details/..."), so each segment is
 * encoded; the slashes are preserved because the route is declared as {path:path}.
 */
export function fileViewerUrl(path: string): string {
  const token = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  const encoded = path.split("/").map(encodeURIComponent).join("/");
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${encoded}?auth=${token ?? ""}`;
}
