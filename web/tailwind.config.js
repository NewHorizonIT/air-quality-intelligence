/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        good:             "#2d9e5f",
        moderate:         "#8dc63f",
        unhealthy:        "#f5a623",
        "very-unhealthy": "#d0021b",
        hazardous:        "#7b0000",
        brand:            "#1f3c88",
      },
    },
  },
  plugins: [],
}
