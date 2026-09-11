/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        arya: {
          dark: "#080c14",
          card: "#0d1527",
          border: "#1e293b",
          cyan: "#00f2fe",
          blue: "#4facfe",
          purple: "#7f00ff",
          gold: "#f6d365",
          crimson: "#ff0844",
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 12s linear infinite',
      }
    },
  },
  plugins: [],
}
