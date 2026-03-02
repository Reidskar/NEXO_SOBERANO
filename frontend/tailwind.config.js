/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#1a1a1a',
        slate: '#2d3748',
      }
    },
  },
  plugins: [],
  darkMode: 'class'
}
