/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1f2937',
          dark: '#111827',
        },
        secondary: '#f9fafb',
        accent: {
          DEFAULT: '#0ea5e9',
          dark: '#0284c7',
        },
        text: {
          dark: '#111827',
          light: '#6b7280',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
