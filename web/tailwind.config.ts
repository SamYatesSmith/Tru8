import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        surface: 'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        'border-default': 'var(--border)',
        'border-strong': 'var(--border-strong)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        accent: 'var(--accent)',
        'accent-muted': 'var(--accent-muted)',
        'state-supported': 'var(--state-supported)',
        'state-supported-bg': 'var(--state-supported-bg)',
        'state-disputed': 'var(--state-disputed)',
        'state-disputed-bg': 'var(--state-disputed-bg)',
        'state-unresolved': 'var(--state-unresolved)',
        'state-unresolved-bg': 'var(--state-unresolved-bg)',
        'state-contextual': 'var(--state-contextual)',
        'state-contextual-bg': 'var(--state-contextual-bg)',
        success: 'var(--success)',
        danger: 'var(--danger)',
        warning: 'var(--warning)',
        info: 'var(--info)',
      },
    },
  },
  plugins: [],
};
export default config;
