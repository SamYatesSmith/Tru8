import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Tru8 Design System - Use CSS Variables
        'tru8-primary': 'var(--tru8-primary)',
        'tru8-primary-light': 'var(--tru8-primary-light)',
        'tru8-primary-dark': 'var(--tru8-primary-dark)',
        
        // Semantic Verdict Colors - Match Design System
        'verdict-supported': 'var(--verdict-supported)',
        'verdict-contradicted': 'var(--verdict-contradicted)',
        'verdict-uncertain': 'var(--verdict-uncertain)',
        
        // Gray Scale
        'gray-900': 'var(--gray-900)',
        'gray-800': 'var(--gray-800)',
        'gray-700': 'var(--gray-700)',
        'gray-600': 'var(--gray-600)',
        'gray-500': 'var(--gray-500)',
        'gray-400': 'var(--gray-400)',
        'gray-300': 'var(--gray-300)',
        'gray-200': 'var(--gray-200)',
        'gray-100': 'var(--gray-100)',
        'gray-50': 'var(--gray-50)',
        'white': 'var(--white)',
        
        // Shadcn/UI Integration
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        primary: {
          DEFAULT: "var(--tru8-primary)", // Use our design system primary
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        // Design System Typography Scale
        '5xl': 'var(--text-5xl)', // Hero titles  
        '4xl': 'var(--text-4xl)', // Page titles
        '3xl': 'var(--text-3xl)', // Section headers
        '2xl': 'var(--text-2xl)', // Card titles
        'xl': 'var(--text-xl)',   // Large text
        'lg': 'var(--text-lg)',   // Prominent body
        'base': 'var(--text-base)', // Standard body
        'sm': 'var(--text-sm)',   // Secondary text  
        'xs': 'var(--text-xs)',   // Captions, labels
      },
      spacing: {
        // 4pt Grid System  
        '1': 'var(--space-1)',   // 4px
        '2': 'var(--space-2)',   // 8px
        '3': 'var(--space-3)',   // 12px
        '4': 'var(--space-4)',   // 16px
        '6': 'var(--space-6)',   // 24px
        '8': 'var(--space-8)',   // 32px
        '12': 'var(--space-12)', // 48px
        '16': 'var(--space-16)', // 64px
        '20': 'var(--space-20)', // 80px
        '24': 'var(--space-24)', // 96px
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',   // 4px
        'md': 'var(--radius-md)',   // 8px  
        'lg': 'var(--radius-lg)',   // 12px
        'xl': 'var(--radius-xl)',   // 16px
        'full': 'var(--radius-full)', // Pills
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;