/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
          cyan: '#38c9cf',
          amber: '#e9ac55',
          rose: '#eb6c7a',
          emerald: '#10b981',
          indigo: '#6366f1',
        },
        store: {
          bg: '#faf8f5',
          surface: '#ffffff',
          dark: '#1e293b',
          terracotta: '#c85a32',
          olive: '#475569',
          border: '#e2e8f0',
        },
        northstar: {
          bg: '#f8fafc',
          sidebar: '#0f172a',
          card: '#ffffff',
          border: '#e2e8f0',
          teal: '#258e89',
        }
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'monospace'],
        display: ['Manrope', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
