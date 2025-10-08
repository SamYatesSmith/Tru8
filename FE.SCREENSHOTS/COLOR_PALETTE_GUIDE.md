# Tru8 Color Palette Guide

This document lists all colors actively used in the Tru8 application, organized by section and purpose.

---

## Brand Colors

### Primary Orange
- **`#f57a07`** / **`rgba(245, 122, 7, 1)`**
  - Primary brand color
  - CTA buttons, active states, accents
  - Used in: Hero CTA, navigation active states, form buttons, links, badges

- **`#e06a00`** / **`rgba(245, 122, 7, 0.9)`**
  - Orange hover state
  - Button hover effects

- **`rgba(245, 122, 7, 0.2)`**
  - Orange with 20% opacity
  - Glows, backgrounds, borders

- **`rgba(245, 122, 7, 0.1)`**
  - Orange with 10% opacity
  - Subtle backgrounds, gradients

---

## Background Colors

### Main Backgrounds
- **`#151823`**
  - Primary app background (signed-in pages)
  - Body background color
  - Footer background

- **`#1a1f2e`**
  - Card backgrounds (signed-in)
  - Mobile bottom nav
  - Form inputs, settings cards

- **`#1a1f2e/50`**
  - Semi-transparent card backgrounds
  - Overlay effects

### Gradient Backgrounds
- **Gradient 1**: `linear-gradient(135deg, #0f1419 0%, #1e293b 20%, #f57a07 35%, #334155 50%, #475569 70%, #64748b 100%)`
  - Animated gradient for special effects
  - Used in: Gradient creeping backgrounds

- **Gradient 2**: `linear-gradient(270deg, #cbd5e1, #94a3b8, #f57a07, #64748b)`
  - Backlight effect gradient
  - Used in: Hero card backlight, animated text

- **Gradient 3**: `linear-gradient(270deg, #cbd5e1, #f57a07, #94a3b8, #64748b)`
  - Alternative backlight gradient

---

## Slate/Gray Scale (Neutrals)

### Dark Slate Tones
- **`#0f1419`** - Darkest slate (gradient start)
- **`#1e293b`** - Slate 800 (pixel grid, cards)
- **`#334155`** - Slate 700 (pixel grid, borders)
- **`#475569`** - Slate 600 (pixel grid)
- **`#64748b`** - Slate 500 (pixel grid, text)

### Mid Slate Tones
- **`#94a3b8`** - Slate 400 (pixel grid, text, icons)
- **`#cbd5e1`** - Slate 300 (text, pixel grid)

### Light Slate Tones
- **`#e2e8f0`** - Slate 200 (pixel grid)
- **`#f1f5f9`** - Slate 100 (pixel grid)
- **`#f8fafc`** - Slate 50 (pixel grid, lightest)

### Stone Tones (Alternative Neutrals)
- **`#a8a29e`** - Stone 400 (pixel grid)
- **`#d6d3d1`** - Stone 300 (pixel grid)
- **`#e7e5e4`** - Stone 200 (pixel grid)
- **`#fafaf9`** - Stone 50 (pixel grid)

### Gray Scale (Signed-In UI)
- **`gray-400`** - Text, icons, labels
- **`gray-500`** - Placeholder text, secondary text
- **`gray-600`** - Borders, dividers
- **`gray-700`** - Borders, hover states
- **`gray-800`** - Borders, card backgrounds, inputs
- **`gray-900`** - Backgrounds

---

## Accent Colors

### Cyan/Teal (Secondary Accent)
- **`cyan-400`** / **`#22d3ee`**
  - Secondary accent color
  - Icons, progress indicators, checkmarks
  - Used in: Feature icons, pricing highlights, hover states

- **`cyan-500`** / **`#06b6d4`**
  - Cyan hover state
  - Badges, buttons

### Blue (Information/Progress)
- **`blue-300`** - Current step text
- **`blue-400`** - Icons, links
- **`blue-500`** - Progress indicators, icons
- **`blue-600`** - Links, hover states
- **`blue-700`** - Borders (current state)
- **`blue-900/20`** - Background (current state)

---

## Status Colors

### Success/Supported (Green)
- **`green-300`** - Complete step text
- **`green-400`** - Complete step text (alternative)
- **`green-500`** - Success icons, badges
- **`green-600`** - Success text, icons
- **`green-700`** - Borders (complete state)
- **`green-900/20`** - Background (complete state)

### Error/Contradicted (Red)
- **`red-300`** - Error text (destructive toast)
- **`red-400`** - Error text, sign out button
- **`red-600`** - Error icons, text
- **`red-800`** - Error borders
- **`red-900/20`** - Error backgrounds

### Warning/Uncertain (Amber/Yellow)
- **`amber-500`** - Warning icons, uncertain status
- **`amber-600`** - Warning text, icons
- **`amber-800`** - Warning text (dark)
- **`amber-100`** - Warning background (light)

---

## Text Colors

### Primary Text
- **`white`** - Primary text (signed-in pages)
- **`text-white`** - Headings, labels, primary content

### Secondary Text
- **`slate-200`** - Hero subtitle
- **`slate-300`** - Body text, descriptions (marketing)
- **`slate-400`** - Secondary text, icons, inactive states
- **`slate-500`** - Tertiary text

### Signed-In Text
- **`gray-400`** - Secondary text, descriptions
- **`gray-500`** - Placeholder text
- **`gray-600`** - Tertiary text

---

## Border Colors

### Primary Borders
- **`border-gray-800`** - Primary border color (signed-in)
- **`border-gray-700`** - Hover borders
- **`border-slate-700`** - Marketing page borders
- **`border-slate-600`** - Navigation dividers

### Status Borders
- **`border-blue-700`** - Current/active state
- **`border-green-700`** - Complete state
- **`border-red-800`** - Error state

---

## Special Effects

### Shadows
- **`shadow-[rgba(245,122,7,0.2)]`** - Orange glow shadow
- **`shadow-lg`**, **`shadow-xl`**, **`shadow-2xl`** - Standard elevation shadows

### Rings (Focus/Active States)
- **`ring-2 ring-[rgba(245,122,7,1)]`** - Orange focus ring (current plan)
- **`ring-2 ring-cyan-400`** - Cyan focus ring (popular plan)

---

## Usage by Section

### Marketing Pages (Signed-Out)
- **Primary**: Orange (`#f57a07`), Cyan (`cyan-400`)
- **Backgrounds**: Slate gradients, pixel grid (slate/stone tones)
- **Text**: White, slate-200, slate-300, slate-400
- **Borders**: slate-700, slate-600

### Dashboard (Signed-In)
- **Primary**: Orange (`rgba(245,122,7,1)`)
- **Backgrounds**: `#151823`, `#1a1f2e`
- **Text**: White, gray-400, gray-500
- **Borders**: gray-800, gray-700
- **Status**: Green (supported), Red (contradicted), Amber (uncertain)

### Forms & Inputs
- **Background**: `#1a1f2e/50`, gray-800/50
- **Border**: gray-800, gray-700
- **Text**: White
- **Placeholder**: gray-500
- **Active**: Orange (`rgba(245,122,7,1)`)

### Navigation
- **Background**: `#1a1f2e` (mobile), slate-800 (marketing)
- **Text**: slate-300, white
- **Active**: Orange (`rgba(245,122,7,1)`)
- **Hover**: slate-700, white

### Footer
- **Background**: `#151823`
- **Text**: gray-400
- **Hover**: Orange (`rgba(245,122,7,1)`)
- **Border**: gray-800

---

## Color Consistency Rules

1. **Orange is the primary brand color** - Use `#f57a07` / `rgba(245,122,7,1)` consistently
2. **Cyan is the secondary accent** - Use for highlights, not primary actions
3. **Status colors are semantic**:
   - Green = Success/Supported
   - Red = Error/Contradicted
   - Amber = Warning/Uncertain
   - Blue = Information/Progress
4. **Backgrounds follow hierarchy**:
   - `#151823` = Page background
   - `#1a1f2e` = Card/component background
   - `#1a1f2e/50` = Overlay/subtle background
5. **Text follows contrast rules**:
   - White for primary content
   - Gray-400/Slate-300 for secondary
   - Gray-500/Slate-400 for tertiary

---

## Notes

- All colors listed are actively used in the codebase
- Tailwind color classes (e.g., `gray-800`) resolve to their standard Tailwind values
- Custom colors use hex or rgba notation
- Opacity variants are noted where used (e.g., `/50` = 50% opacity)
