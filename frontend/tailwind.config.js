/** @type {import('tailwindcss').Config} */
// Previously `theme: { extend: {} }` — none of the design tokens were available as
// utilities, which is why the codebase applies the palette by hand via
// style={{ color: "var(--text-muted)" }}. Exposing them here lets components use
// `text-muted` / `bg-surface` / `shadow-elev-2` and keeps one source of truth.
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        primary: { DEFAULT: "var(--primary)", hover: "var(--primary-hover)" },
        secondary: "var(--secondary)",
        accent: "var(--accent)",
        ink: { DEFAULT: "var(--text)", muted: "var(--text-muted)" },
        line: "var(--border)",
        success: "var(--success)",
        warning: "var(--warning)",
        error: "var(--error)",
        info: "var(--info)",
        sidebar: "var(--sidebar)",
        silk: {
          mulberry: "var(--silk-mulberry)",
          muga: "var(--silk-muga)",
          eri: "var(--silk-eri)",
          tasar: "var(--silk-tasar)",
        },
      },
      fontFamily: {
        heading: ["var(--font-heading)", "Manrope", "sans-serif"],
        body: ["var(--font-body)", "IBM Plex Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
        xl: "var(--r-xl)",
      },
      boxShadow: {
        "elev-1": "var(--elev-1)",
        "elev-2": "var(--elev-2)",
        "elev-3": "var(--elev-3)",
      },
    },
  },
  plugins: [],
};
