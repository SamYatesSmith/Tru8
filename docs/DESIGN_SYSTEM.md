# Tru8 Design System
*Professional, Bold, Trustworthy - Authoritative fact-checking aesthetics*

## 🎯 **Design Philosophy**

### **Core Principles**
1. **Truth-Focused**: Clean, high-contrast design that prioritizes information clarity
2. **Professional Authority**: Bold typography and strong colors convey expertise
3. **Modern Confidence**: Sharp edges, strategic gradients, pop sophistication
4. **Consistent Experience**: 4pt grid system, centralized content, unified components
5. **Mobile-First**: Responsive design with touch-friendly interactions

### **Visual Identity**
- **Primary Emotion**: Trust and Authority
- **Secondary Emotion**: Modern Confidence  
- **Aesthetic**: Pop sophistication - vibrant but authoritative
- **Hierarchy**: Bold headings, clear content sections, obvious CTAs

---

## 🎨 **Color System**

### **Brand Colors**
```css
/* Primary Palette - Bold, Energetic, Authoritative */
:root {
  --tru8-primary: #f57a07;        /* Tru8 Orange - main brand */
  --tru8-primary-hover: #e06a00;  /* Orange hover state */
  --tru8-cyan: #22d3ee;           /* Accent cyan - icons, highlights */
  --tru8-dark: #0f1419;           /* Dark background */
  --tru8-card: #1e293b;           /* Card/container background */

  /* Gradient System */
  --gradient-primary: linear-gradient(135deg, #f57a07 0%, #fb923c 100%);
  --gradient-hero: radial-gradient(ellipse, #f57a07, #fb923c, #fca55f, #ffffff);
  --gradient-card: linear-gradient(145deg, #1e293b 0%, #0f1419 100%);
}
```

### **Verdict System (Semantic Colors)**
```css
/* High-contrast semantic states */
:root {
  --verdict-supported: #059669;      /* Emerald Green */
  --verdict-contradicted: #DC2626;   /* Strong Red */
  --verdict-uncertain: #D97706;      /* Warning Amber */
  
  /* Verdict backgrounds */
  --verdict-supported-bg: #ECFDF5;
  --verdict-supported-border: #A7F3D0;
  --verdict-contradicted-bg: #FEF2F2;
  --verdict-contradicted-border: #FECACA;
  --verdict-uncertain-bg: #FFFBEB;
  --verdict-uncertain-border: #FDE68A;
}
```

### **Neutral Palette (Information Hierarchy)**
```css
/* Gray scale - High contrast */
:root {
  --gray-900: #111827;  /* Primary headings */
  --gray-800: #1F2937;  /* Body text */
  --gray-700: #374151;  /* Secondary text */
  --gray-600: #4B5563;  /* Muted text */
  --gray-500: #6B7280;  /* Placeholder */
  --gray-400: #9CA3AF;  /* Disabled */
  --gray-300: #D1D5DB;  /* Borders */
  --gray-200: #E5E7EB;  /* Light borders */
  --gray-100: #F3F4F6;  /* Section backgrounds */
  --gray-50: #F9FAFB;   /* Page background */
  --white: #FFFFFF;     /* Card backgrounds */
}
```

---

## ✏️ **Typography System**

### **Font Stack**
```css
:root {
  --font-heading: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', monospace;
}

/* Font weights */
:root {
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --font-weight-black: 900;
}
```

### **Type Scale (Responsive)**
```css
/* Heading scales - Bold impact */
:root {
  --text-5xl: clamp(2.5rem, 5vw, 3rem);      /* Hero titles */
  --text-4xl: clamp(2rem, 4vw, 2.25rem);     /* Page titles */
  --text-3xl: clamp(1.5rem, 3vw, 1.875rem);  /* Section headers */
  --text-2xl: clamp(1.25rem, 2.5vw, 1.5rem); /* Card titles */
  --text-xl: 1.25rem;                        /* Large text */
  
  /* Body text scales */
  --text-lg: 1.125rem;   /* Prominent body */
  --text-base: 1rem;     /* Standard body */
  --text-sm: 0.875rem;   /* Secondary text */
  --text-xs: 0.75rem;    /* Captions, labels */
}
```

### **Typography Usage Rules**
```css
/* Headings - Always bold, high contrast */
h1, h2, h3, h4 {
  font-family: var(--font-heading);
  font-weight: var(--font-weight-bold);
  color: var(--gray-900);
  line-height: 1.2;
}

/* Body text - Readable, consistent */
body, p {
  font-family: var(--font-body);
  font-weight: var(--font-weight-normal);
  color: var(--gray-800);
  line-height: 1.6;
}
```

---

## 📐 **Spacing System (4pt Grid)**

### **Base Spacing Units**
```css
/* All spacing must be multiples of 4px */
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  --space-24: 6rem;     /* 96px */
  --space-32: 8rem;     /* 128px */
}
```

### **Layout Spacing Rules**
- **Section Padding**: `var(--space-8)` minimum
- **Card Padding**: `var(--space-6)` standard
- **Element Margins**: `var(--space-4)` between elements
- **Component Gaps**: `var(--space-3)` internal spacing

---

## 📱 **Layout System**

### **Container System (Centralized Content)**
```css
/* Content containers - Always centered */
:root {
  --container-sm: 640px;    /* Mobile forms */
  --container-md: 768px;    /* Tablet content */
  --container-lg: 1024px;   /* Desktop standard */
  --container-xl: 1280px;   /* Wide content */
  --container-2xl: 1536px;  /* Hero sections */
}

.container {
  max-width: var(--container-lg);
  margin: 0 auto;
  padding-left: var(--space-4);
  padding-right: var(--space-4);
}

.container-wide {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding-left: var(--space-6);
  padding-right: var(--space-6);
}
```

### **Grid System**
```css
/* Standard content grid */
.grid-main {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
}

@media (min-width: 768px) {
  .grid-main {
    grid-template-columns: 2fr 1fr; /* Content + sidebar */
  }
}

@media (min-width: 1024px) {
  .grid-main {
    gap: var(--space-8);
  }
}
```

---

## 🔘 **Border Radius System (4pt Based)**

```css
:root {
  --radius-sm: 0.25rem;   /* 4px - small elements */
  --radius-md: 0.5rem;    /* 8px - buttons, inputs */
  --radius-lg: 0.75rem;   /* 12px - cards */
  --radius-xl: 1rem;      /* 16px - modals */
  --radius-2xl: 1.5rem;   /* 24px - hero cards */
  --radius-full: 9999px;  /* Pills, avatars */
}
```

---

## 🧩 **Component Library**

### **Buttons (Bold Actions)**
```css
/* Primary CTA - Gradient background */
.btn-primary {
  background: var(--gradient-primary);
  color: white;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  font-size: var(--text-base);
  border: none;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(30, 64, 175, 0.4);
}

/* Secondary buttons */
.btn-secondary {
  background: var(--white);
  color: var(--gray-700);
  border: 1px solid var(--gray-300);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
}

/* Danger actions */
.btn-danger {
  background: var(--verdict-contradicted);
  color: white;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
}
```

### **Cards (Information Hierarchy)**
```css
/* Standard content card */
.card {
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease-in-out;
}

.card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Prominent/featured cards */
.card-featured {
  border: 1px solid var(--tru8-primary);
  box-shadow: 0 4px 6px -1px rgba(30, 64, 175, 0.1);
}

/* Result cards with verdict */
.card-result {
  padding: var(--space-6);
  border-left: 4px solid var(--gray-200);
}

.card-result.supported {
  border-left-color: var(--verdict-supported);
}

.card-result.contradicted {
  border-left-color: var(--verdict-contradicted);
}

.card-result.uncertain {
  border-left-color: var(--verdict-uncertain);
}
```

### **Verdict Pills (High Impact)**
```css
.verdict-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-semibold);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.verdict-supported {
  background: var(--verdict-supported-bg);
  color: var(--verdict-supported);
  border: 1px solid var(--verdict-supported-border);
}

.verdict-contradicted {
  background: var(--verdict-contradicted-bg);
  color: var(--verdict-contradicted);
  border: 1px solid var(--verdict-contradicted-border);
}

.verdict-uncertain {
  background: var(--verdict-uncertain-bg);
  color: var(--verdict-uncertain);
  border: 1px solid var(--verdict-uncertain-border);
}
```

### **Confidence Bars (Visual Progress)**
```css
.confidence-bar {
  width: 100%;
  height: var(--space-2);
  background: var(--gray-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: var(--gradient-primary);
  transition: width 1s ease-in-out;
  border-radius: var(--radius-full);
}

.confidence-text {
  font-weight: var(--font-weight-semibold);
  color: var(--gray-700);
  font-size: var(--text-sm);
  margin-top: var(--space-1);
}
```

---

## 📄 **Page-Specific Styling**

### **Landing Page**
```css
/* Hero section with gradient */
.hero-section {
  background: var(--gradient-hero);
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: white;
  position: relative;
}

.hero-title {
  font-size: var(--text-5xl);
  font-weight: var(--font-weight-black);
  line-height: 1.1;
  margin-bottom: var(--space-6);
}

.hero-subtitle {
  font-size: var(--text-xl);
  opacity: 0.9;
  margin-bottom: var(--space-8);
  max-width: 600px;
}
```

### **Dashboard Layout**
```css
.dashboard-container {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: var(--space-8) var(--space-4);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
}

@media (min-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 2fr 1fr;
    gap: var(--space-8);
  }
}
```

### **Results Page**
```css
.results-header {
  text-align: center;
  padding: var(--space-12) 0;
  background: var(--gradient-card);
  border-radius: var(--radius-xl);
  margin-bottom: var(--space-8);
}

.claims-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
}

@media (min-width: 768px) {
  .claims-grid {
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  }
}
```

---

## 🚫 **Design System Rules**

### **MUST Follow**
1. **All spacing MUST use 4pt grid** (`var(--space-*)`)
2. **All colors MUST use CSS variables** (no hex values in components)
3. **All content MUST be centered** using container classes
4. **All border-radius MUST be 4pt-based** (`var(--radius-*)`)
5. **All typography MUST use scale** (`var(--text-*)`)

### **NEVER Do**
- ❌ Use arbitrary spacing values (e.g., `margin: 15px`)
- ❌ Use inline colors (e.g., `color: #FF0000`)
- ❌ Create full-width content without containers
- ❌ Use inconsistent border-radius values
- ❌ Mix font families within components

### **Component Consistency**
- All buttons must have consistent padding and typography
- All cards must use standard shadows and borders
- All verdict indicators must use semantic color system
- All animations must use consistent timing (0.2s ease-in-out)

---

## 🎯 **Implementation Guidelines**

### **CSS Architecture**
1. Use CSS custom properties (variables) exclusively
2. Create utility classes for common patterns
3. Component-specific styles in component files
4. Global design tokens in `:root`
5. Mobile-first responsive design

### **Framework Integration**
- **Tailwind CSS**: Configure with design token variables
- **Next.js**: Global CSS imports for design system
- **Component Libraries**: Override with design system tokens

### **Quality Assurance**
- Design system variables must be used in all components
- Regular design reviews against this specification
- Automated testing for design token usage
- Documentation updates with any system changes

---

*This design system ensures consistent, professional, and accessible user experiences across all Tru8 interfaces. All frontend implementations must adhere to these specifications.*