/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 50: "#f8fafc", 100: "#f1f5f9", 600: "#475569", 900: "#0f172a" },
        accent: {
          50: "#eef2ff", 100: "#e0e7ff", 500: "#6366f1",
          600: "#4f46e5", 700: "#4338ca", 900: "#312e81",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
