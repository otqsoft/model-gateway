export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: { center: true },
    extend: {
      colors: {
        dark: { 950: '#09090b', 900: '#0a0a0f', 800: '#111113', 700: '#1c1c22', 600: '#27272a' },
        light: { 50: '#f8f9fa', 100: '#f1f3f5', 200: '#e9ecef', 300: '#dee2e6', 400: '#ced4da' },
        accent: { DEFAULT: '#6366f1', light: '#818cf8', dark: '#4f46e5' },
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
