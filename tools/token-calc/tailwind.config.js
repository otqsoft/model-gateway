/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        // 数据天文台配色
        obs: {
          bg: "#0A0E14",
          panel: "#0F1722",
          card: "#141C2A",
          cardHi: "#1E2A3A",
          border: "#243244",
          borderHi: "#324256",
        },
        cyan: {
          DEFAULT: "#22D3EE",
          glow: "#67E8F9",
          dim: "#0E7490",
        },
        amber: {
          DEFAULT: "#FBBF24",
          glow: "#FCD34D",
          dim: "#92400E",
        },
        ink: {
          DEFAULT: "#E2E8F0",
          muted: "#94A3B8",
          dim: "#64748B",
        },
        ok: "#34D399",
        warn: "#F87171",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px -4px rgba(34, 211, 238, 0.35)",
        "glow-amber": "0 0 24px -4px rgba(251, 191, 36, 0.35)",
        card: "0 8px 32px -8px rgba(0, 0, 0, 0.6), inset 0 1px 0 0 rgba(255, 255, 255, 0.03)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(36, 50, 68, 0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(36, 50, 68, 0.4) 1px, transparent 1px)",
        "radial-cyan":
          "radial-gradient(circle at 30% 20%, rgba(34, 211, 238, 0.08), transparent 50%)",
        "radial-amber":
          "radial-gradient(circle at 80% 80%, rgba(251, 191, 36, 0.06), transparent 50%)",
      },
      animation: {
        "pulse-glow": "pulse-glow 2.4s ease-in-out infinite",
        "fade-up": "fade-up 0.5s ease-out both",
        "count-roll": "count-roll 0.4s ease-out",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "count-roll": {
          "0%": { transform: "translateY(-4px)", opacity: "0.5" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
