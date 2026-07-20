import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        rail: {
          bg: "#0A0E1A",
          surface: "#111827",
          panel: "#151D2E",
          line: "#26314A",
          text: "#E8ECF4",
          muted: "#8992A9",
          amber: "#F2A93B",
          amberDim: "#7A5B22",
          signal: {
            green: "#3ECF8E",
            red: "#E5484D",
            yellow: "#F2A93B",
          },
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "monospace"],
        body: ["var(--font-body)", "sans-serif"],
      },
      boxShadow: {
        ticket: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.25" },
        },
        scan: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        rise: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        blink: "blink 1.4s ease-in-out infinite",
        scan: "scan 2.4s linear infinite",
        rise: "rise 0.22s ease-out",
      },
    },
  },
  plugins: [],
};
export default config;
