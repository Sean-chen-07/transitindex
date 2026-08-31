import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

// Tokens are defined as CSS variables in src/app/globals.css (the single source of
// truth, mirrored from DESIGN.md). Tailwind references them so utilities like
// `bg-bg`, `text-ink-2`, `border-line` resolve to the warm, low-chroma palette.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        card: "var(--card)",
        "card-2": "var(--card-2)",
        ink: "var(--ink)",
        "ink-2": "var(--ink-2)",
        "ink-3": "var(--ink-3)",
        line: "var(--line)",
        "line-2": "var(--line-2)",
        grid: "var(--grid)",
        coral: "var(--coral)",
        "coral-ink": "var(--coral-ink)", // small coral text (AA on paper/cream)
        "coral-soft": "var(--coral-soft)",
        teal: "var(--teal)",
        "teal-soft": "var(--teal-soft)",
        // mode-group accents (always paired with an icon + label, never color alone)
        "mode-blue": "var(--blue)",
        "mode-sage": "var(--sage)",
        "mode-yellow": "var(--yellow)",
        // agency-card ticket stock
        paper: "var(--paper)",
        "paper-line": "var(--paper-line)",
      },
      fontFamily: {
        sans: ["var(--font-outfit)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "18px",
        ticket: "5px", // the agency card is a paper ticket, not a soft card
        cell: "6px",
      },
      boxShadow: {
        soft: "0 6px 20px rgba(60,50,30,.06)",
        "soft-hover": "0 10px 28px rgba(60,50,30,.10)",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
