import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'tru8-orange': '#f57a07',
        'tru8-orange-hover': '#e06a00',
        'tru8-cyan': '#22d3ee',
      },
    },
  },
  plugins: [],
};
export default config;
