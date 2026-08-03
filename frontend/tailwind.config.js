/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#081018',
        panel: '#0f172a',
        accent: '#22c55e',
        warm: '#f59e0b',
        danger: '#ef4444',
      },
      boxShadow: {
        glow: '0 20px 70px rgba(34, 197, 94, 0.15)',
      },
    },
  },
  plugins: [],
}
