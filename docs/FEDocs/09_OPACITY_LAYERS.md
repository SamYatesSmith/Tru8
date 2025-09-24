# 09. Opacity Layers - Visual Depth System

## 🎯 Objective
Implement a sophisticated layered opacity system inspired by Reflect.app to create visual depth, enhance information hierarchy, and provide a premium, spacially-aware design that guides user attention effectively.

## 📊 Current State Analysis

### Existing Layer System (web/app/globals.css)
```css
/* Current z-index management */
.navbar-pill-system { z-index: 50; }
.navbar-primary-pill { z-index: 53; }
.navbar-secondary-pill { z-index: 49; }

/* Current background systems */
.hero-section {
  background: var(--gradient-hero);
}

.py-24.bg-white { background: var(--white); }
.py-16.bg-gray-100 { background: var(--gray-100); }
```

### Current Opacity Usage
- **Subtle shadows** - `rgba(0, 0, 0, 0.1)` on cards
- **Hero subtitle** - `opacity: 0.9` on text
- **Fixed positioning** - Basic z-index for navigation

## 🎨 Reflect.app Inspiration

### Layered Depth Characteristics Observed
1. **Multiple background layers** - Varying opacity levels create depth
2. **Content layering** - Foreground, midground, background separation
3. **Interactive depth** - Hover states change layer perception
4. **Contextual opacity** - Content importance affects opacity
5. **Seamless transitions** - Smooth opacity changes between states
6. **Spatial awareness** - Clear visual hierarchy through depth

## 🏗️ Implementation Strategy

### Opacity Layer System
**Create a systematic approach to visual depth:**

1. **Background layers** - Multiple semi-transparent backgrounds
2. **Content layers** - Foreground, midground, background content
3. **Interactive layers** - Hover and focus state depth changes
4. **Contextual layers** - Different opacity for different content types

## 🛠️ Technical Implementation

### 1. Enhanced CSS Variables (web/app/globals.css)

#### Opacity Layer System - AUTHORITATIVE SOURCE
```css
/* SINGLE SOURCE OF TRUTH: All opacity and z-index definitions originate here */
:root {
  /* Opacity levels for systematic layering */
  --opacity-background: 0.02;
  --opacity-subtle: 0.05;
  --opacity-light: 0.1;
  --opacity-medium: 0.2;
  --opacity-strong: 0.4;
  --opacity-prominent: 0.6;
  --opacity-dominant: 0.8;
  --opacity-opaque: 0.95;

  /* Layer z-index system */
  --layer-background: -1;
  --layer-content: 1;
  --layer-elevated: 10;
  --layer-floating: 20;
  --layer-overlay: 30;
  --layer-modal: 40;
  --layer-navigation: 50;
  --layer-tooltip: 60;

  /* Background layer colors */
  --bg-layer-primary: rgba(30, 64, 175, var(--opacity-background));
  --bg-layer-secondary: rgba(124, 58, 237, var(--opacity-subtle));
  --bg-layer-accent: rgba(236, 72, 153, var(--opacity-light));
  --bg-layer-neutral: rgba(17, 24, 39, var(--opacity-subtle));

  /* Content layer backgrounds */
  --content-layer-elevated: rgba(255, 255, 255, var(--opacity-opaque));
  --content-layer-floating: rgba(255, 255, 255, var(--opacity-prominent));
  --content-layer-subtle: rgba(255, 255, 255, var(--opacity-medium));
}
```

#### Interactive Layer States
```css
:root {
  /* Hover state opacity adjustments */
  --hover-opacity-increase: 0.1;
  --hover-opacity-decrease: -0.1;

  /* Focus state opacity */
  --focus-opacity-ring: 0.2;

  /* Animation durations for opacity changes */
  --opacity-transition-fast: 0.15s ease-out;
  --opacity-transition-medium: 0.3s ease-out;
  --opacity-transition-slow: 0.5s ease-out;
}
```

### 2. Layer Component Classes

#### Background Layer System
```css
/* Background layer classes */
.layer-background {
  position: relative;
  z-index: var(--layer-background);
}

.layer-background::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-layer-primary);
  z-index: -1;
}

.layer-background-secondary::before {
  background: var(--bg-layer-secondary);
}

.layer-background-accent::before {
  background: var(--bg-layer-accent);
}

/* Multi-layer background system */
.layer-background-multi {
  position: relative;
}

.layer-background-multi::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 20% 50%, var(--bg-layer-primary) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, var(--bg-layer-secondary) 0%, transparent 50%),
    radial-gradient(circle at 40% 20%, var(--bg-layer-accent) 0%, transparent 50%);
  z-index: -1;
}
```

#### Content Layer System
```css
/* Content layer elevation */
.layer-content {
  position: relative;
  z-index: var(--layer-content);
}

.layer-elevated {
  position: relative;
  z-index: var(--layer-elevated);
  background: var(--content-layer-elevated);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, var(--opacity-light));
  transition: all var(--opacity-transition-medium);
}

.layer-floating {
  position: relative;
  z-index: var(--layer-floating);
  background: var(--content-layer-floating);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, var(--opacity-medium));
  transition: all var(--opacity-transition-medium);
}

.layer-overlay {
  position: relative;
  z-index: var(--layer-overlay);
  background: var(--content-layer-subtle);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
```

#### Interactive Layer Effects
```css
/* Hover depth changes */
.layer-interactive {
  transition: all var(--opacity-transition-medium);
}

.layer-interactive:hover {
  z-index: calc(var(--layer-elevated) + 1);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, var(--opacity-strong));
  transform: translateY(-2px);
}

.layer-interactive:hover::before {
  opacity: calc(var(--opacity-subtle) + var(--hover-opacity-increase));
}

/* Focus layer enhancement */
.layer-focusable:focus {
  outline: none;
  box-shadow:
    0 0 0 3px rgba(30, 64, 175, var(--focus-opacity-ring)),
    0 20px 25px -5px rgba(0, 0, 0, var(--opacity-medium));
}
```

### 3. Section-Based Layering

#### Homepage Section Layers
```css
/* Hero section - Maximum depth */
.hero-section-layered {
  position: relative;
  background: var(--gradient-hero);
  overflow: hidden;
}

.hero-section-layered::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 30%),
    radial-gradient(circle at 70% 80%, rgba(255, 255, 255, 0.05) 0%, transparent 40%);
  z-index: 1;
}

.hero-content-layer {
  position: relative;
  z-index: 2;
}

/* Features section - Subtle layering */
.features-section-layered {
  position: relative;
  background: var(--white);
}

.features-section-layered::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    linear-gradient(135deg, var(--bg-layer-primary) 0%, transparent 50%),
    linear-gradient(45deg, var(--bg-layer-secondary) 0%, transparent 50%);
  z-index: -1;
}

/* CTA section - Strong layering */
.cta-section-layered {
  position: relative;
  background: var(--gradient-primary);
}

.cta-section-layered::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(17, 24, 39, var(--opacity-light));
  z-index: 1;
}

.cta-content-layer {
  position: relative;
  z-index: 2;
}
```

### 4. Component Layer Enhancement

#### Enhanced Card Layers
```css
/* Layered card system */
.card-layered {
  position: relative;
  background: var(--content-layer-elevated);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, var(--opacity-light));
  transition: all var(--opacity-transition-medium);
  overflow: hidden;
}

.card-layered::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-layer-primary);
  opacity: 0;
  transition: opacity var(--opacity-transition-medium);
  z-index: -1;
}

.card-layered:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, var(--opacity-medium));
  z-index: var(--layer-floating);
}

.card-layered:hover::before {
  opacity: 1;
}

/* Card content layers */
.card-content-primary {
  position: relative;
  z-index: 2;
}

.card-content-secondary {
  position: relative;
  z-index: 1;
  opacity: var(--opacity-dominant);
}
```

#### Navigation Layer Enhancement
```css
/* Enhanced navbar layering */
.navbar-layered-system {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--layer-navigation);
  background: rgba(255, 255, 255, var(--opacity-medium));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, var(--opacity-strong));
}

.navbar-layered-system::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-layer-neutral);
  z-index: -1;
}
```

### 5. Advanced Layer Effects

#### Parallax Layer System
```css
/* Parallax layering for depth */
.parallax-container {
  position: relative;
  overflow: hidden;
}

.parallax-layer-back {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translateZ(-1px) scale(2);
  opacity: var(--opacity-subtle);
}

.parallax-layer-mid {
  position: relative;
  z-index: 1;
  opacity: var(--opacity-strong);
}

.parallax-layer-front {
  position: relative;
  z-index: 2;
  opacity: var(--opacity-opaque);
}
```

#### Contextual Layer Adjustments
```css
/* Content-based opacity */
.content-primary { opacity: var(--opacity-opaque); }
.content-secondary { opacity: var(--opacity-dominant); }
.content-tertiary { opacity: var(--opacity-prominent); }
.content-subtle { opacity: var(--opacity-strong); }
.content-hint { opacity: var(--opacity-medium); }

/* State-based layering */
.state-active {
  opacity: var(--opacity-opaque);
  z-index: var(--layer-elevated);
}

.state-inactive {
  opacity: var(--opacity-strong);
  z-index: var(--layer-content);
}

.state-disabled {
  opacity: var(--opacity-medium);
  z-index: var(--layer-background);
}
```

## 🎨 Component Integration Examples

### Enhanced Homepage Sections
```tsx
export default function HomePage() {
  return (
    <MainLayout>
      {/* Layered Hero Section */}
      <section className="hero-section hero-section-layered">
        <div className="hero-content-layer container">
          <h1 className="heading-hero gradient-text-hero">
            Instant Fact-Checking with Dated Evidence
          </h1>
        </div>
      </section>

      {/* Layered Features Section */}
      <section className="features-section-layered py-24">
        <div className="container">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map(feature => (
              <div key={feature.id} className="card-layered layer-interactive">
                <div className="card-content-primary">
                  <h3 className="text-xl font-semibold">{feature.title}</h3>
                </div>
                <div className="card-content-secondary">
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
```

### Layered Navigation Component
```tsx
export function LayeredNavigation() {
  return (
    <div className="navbar-layered-system">
      <nav className="navbar-pill-system layer-floating">
        {/* Existing pill system with enhanced layering */}
      </nav>
    </div>
  );
}
```

## ✅ Testing Checklist

### Visual Testing
- [ ] Layer depth appears correctly across all sections
- [ ] Opacity transitions work smoothly
- [ ] Z-index stacking order is maintained
- [ ] Background layers don't interfere with content

### Performance Testing
- [ ] Opacity changes don't cause layout thrashing
- [ ] Layer animations maintain 60fps
- [ ] Complex layering doesn't impact scroll performance
- [ ] Mobile devices handle layers efficiently

### Accessibility Testing
- [ ] Content remains readable at all opacity levels
- [ ] Focus states are visible through layers
- [ ] High contrast mode compatibility
- [ ] Screen reader navigation unaffected by layers

### Browser Compatibility
- [ ] CSS opacity works consistently
- [ ] Z-index behavior is predictable
- [ ] Backdrop-filter compatibility with layers
- [ ] Fallbacks work for older browsers

## 📈 Success Metrics

### Visual Impact
- Enhanced depth perception and visual hierarchy
- Improved content organization and flow
- Premium, sophisticated appearance

### User Experience
- Clearer information hierarchy
- Better visual guidance and attention direction
- Maintained content readability

## 🚀 Implementation Phases

### Phase 5A: Foundation (Day 1)
1. Add opacity layer variables and base classes
2. Implement z-index management system
3. Test basic layer stacking

### Phase 5B: Background Layers (Day 2)
1. Create multi-layer background system
2. Apply to homepage sections
3. Test visual depth effects

### Phase 5C: Content Layers (Day 3)
1. Implement content layer hierarchy
2. Add interactive layer effects
3. Test card and component layering

### Phase 5D: Advanced Integration (Day 4)
1. Add parallax layer effects
2. Implement contextual opacity
3. Optimize performance and accessibility

## 🔗 Related Documents
- **04_GLEAM_EFFECTS.md** - Glass morphism integration with layers
- **06_ANIMATED_CENTERPIECE.md** - Animation layer considerations
- **08_SPATIAL_DESIGN.md** - Layer-based spatial organization

---

**Phase**: 2B - Visual Effects
**Priority**: Medium
**Estimated Effort**: 4-5 days
**Dependencies**: 04_GLEAM_EFFECTS.md
**Impact**: High - Sophisticated visual depth system