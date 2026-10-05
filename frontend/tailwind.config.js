/** Design tokens: neutral slate surfaces, one restrained accent, semantic risk colors. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      colors: {
        accent: { DEFAULT: '#1d4ed8', hover: '#1e40af', soft: '#eff6ff', border: '#bfdbfe' },
        risk: {
          low: { fg: '#166534', bg: '#f0fdf4', border: '#bbf7d0', dot: '#16a34a' },
          medium: { fg: '#92400e', bg: '#fffbeb', border: '#fde68a', dot: '#d97706' },
          high: { fg: '#991b1b', bg: '#fef2f2', border: '#fecaca', dot: '#dc2626' },
          unknown: { fg: '#475569', bg: '#f1f5f9', border: '#cbd5e1', dot: '#94a3b8' },
        },
      },
    },
  },
  plugins: [],
}
