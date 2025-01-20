/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
       'primary': '#1f2937', // Dark primary color, could be blue or grey
       'primary-dark': '#111827', // Darker version for hover
       'secondary': '#f9fafb', // Off-white background
       'accent': '#0ea5e9',   // Bright accent color
       'accent-dark': '#0284c7',
       'text-dark': '#111827',    // Dark text color
       'text-light': '#6b7280',    // Light text color
      },
      fontFamily: {
        'sans': ['Inter', 'sans-serif'],
      },
    },
  },
    plugins: [
      require('@tailwindcss/forms'),
    ],
}