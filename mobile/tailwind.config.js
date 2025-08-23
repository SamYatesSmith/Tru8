/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        // Tru8 Brand Colors
        darkIndigo: "#2C2C54",
        deepPurpleGrey: "#474787", 
        coolGrey: "#AAABB8",
        lightGrey: "#ECECEC",
        
        // Semantic Colors
        supported: "#1E6F3D",
        contradicted: "#B3261E",
        uncertain: "#A15C00",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};