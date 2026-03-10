/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nexo: {
          dark:     '#0A1128',
          panel:    '#101D35',
          surface:  '#152440',
          border:   '#1C3058',
          hover:    '#1A3A5C',
          green:    '#115243',
          'green-h':'#1A7A63',
          'green-l':'#2AA882',
          accent:   '#22D3A0',
          text:     '#E2E8F0',
          muted:    '#8B9AB5',
          dim:      '#5A6B85',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'nexo':    '0 2px 8px rgba(0,0,0,0.35)',
        'nexo-lg': '0 4px 16px rgba(0,0,0,0.45)',
      },
    },
  },
  plugins: [],
  darkMode: 'class'
}
