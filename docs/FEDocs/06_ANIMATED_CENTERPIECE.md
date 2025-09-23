# 06. Animated Centerpiece - Marketing Hero (Track A Only)

## 🎯 Objective
Create an engaging, animated centerpiece for the **marketing hero section (signed-out users only)** inspired by Reflect.app's captivating central animations that demonstrate Tru8's fact-checking capabilities and drive conversion without overwhelming the marketing message.

## 🔀 Track A Marketing Context
**This document applies exclusively to Track A (Marketing - Signed-Out Users)**
- **Signed-out users**: See animated centerpiece demonstrating product capabilities
- **Signed-in users**: Skip this entirely - go straight to dashboard/app functionality
- **Purpose**: Convert visitors by showing product value visually

## 📊 Current State Analysis

### Existing Hero Section (web/app/page.tsx)
```tsx
<section className="hero-section">
  <div className="container">
    <div className="hero-title">
      Instant Fact-Checking with Dated Evidence
    </div>
    <p className="hero-subtitle">
      Get explainable verdicts on claims from articles, images, videos, and text.
      Professional-grade verification in seconds.
    </p>

    <SignedOut>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
        <SignInButton mode="modal">
          <Button size="lg" className="btn-primary px-8 py-4 text-lg">
            Start Fact-Checking Now
          </Button>
        </SignInButton>
        <Button variant="outline" size="lg">
          View Demo
        </Button>
      </div>
    </SignedOut>
  </div>
</section>
```

### Current Hero Styling (web/app/globals.css)
```css
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
  font-weight: 900;
  line-height: 1.1;
  margin-bottom: var(--space-6);
}
```

## 🎨 Reflect.app Inspiration

### Animated Centerpiece Characteristics Observed
1. **Central focus point** - Eye-catching element that draws attention
2. **Subtle motion** - Smooth, non-distracting animations
3. **Product representation** - Visually represents the service/product
4. **Interactive hints** - Suggests interactivity and engagement
5. **Brand integration** - Incorporates brand colors and style
6. **Performance optimized** - Smooth 60fps animations

## 🏗️ Implementation Strategy

### Animated Centerpiece Concept
**Create a fact-checking visualization that demonstrates Tru8's capabilities:**

1. **Central animation hub** - Floating fact-check interface mockup
2. **Data flow visualization** - Animated information processing
3. **Verdict display** - Dynamic verdict pills and confidence bars
4. **Interactive elements** - Hover and scroll-triggered animations
5. **Brand consistency** - Use established design system colors

## 🛠️ Technical Implementation

### 1. Enhanced Hero Structure

#### New Hero Layout with Centerpiece
```tsx
// Enhanced hero section with animated centerpiece
<section className="hero-section hero-section-animated">
  <div className="hero-background-layers">
    <div className="hero-background-primary"></div>
    <div className="hero-background-secondary"></div>
    <div className="hero-background-accent"></div>
  </div>

  <div className="container hero-content-container">
    <div className="hero-content-grid">
      {/* Left: Text Content */}
      <div className="hero-text-content">
        <h1 className="heading-hero gradient-text-hero">
          Instant Fact-Checking with Dated Evidence
        </h1>
        <p className="hero-subtitle">
          Get explainable verdicts on claims from articles, images, videos, and text.
          Professional-grade verification in seconds.
        </p>
        <div className="hero-cta-buttons">
          {/* CTA buttons */}
        </div>
      </div>

      {/* Right: Animated Centerpiece */}
      <div className="hero-centerpiece-container">
        <div className="animated-centerpiece">
          <FactCheckingAnimation />
        </div>
      </div>
    </div>
  </div>
</section>
```

### 2. CSS Animation System (web/app/globals.css)

#### Hero Layout Enhancement
```css
/* Enhanced hero section with animation support */
.hero-section-animated {
  background: var(--gradient-hero);
  min-height: 90vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-background-layers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
}

.hero-background-primary {
  position: absolute;
  top: 20%;
  left: 10%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  border-radius: 50%;
  animation: floatSlow 8s ease-in-out infinite;
}

.hero-background-secondary {
  position: absolute;
  top: 60%;
  right: 15%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%);
  border-radius: 50%;
  animation: floatMedium 6s ease-in-out infinite reverse;
}

.hero-background-accent {
  position: absolute;
  top: 10%;
  right: 30%;
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, transparent 70%);
  border-radius: 50%;
  animation: floatFast 4s ease-in-out infinite;
}

.hero-content-container {
  position: relative;
  z-index: 10;
  width: 100%;
}

.hero-content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-16);
  align-items: center;
  min-height: 70vh;
}

@media (max-width: 1024px) {
  .hero-content-grid {
    grid-template-columns: 1fr;
    gap: var(--space-12);
    text-align: center;
  }
}
```

#### Animation Keyframes
```css
/* Background float animations */
@keyframes floatSlow {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  25% { transform: translate(10px, -15px) rotate(1deg); }
  50% { transform: translate(-5px, -10px) rotate(-1deg); }
  75% { transform: translate(-10px, 5px) rotate(0.5deg); }
}

@keyframes floatMedium {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(15px, -10px) scale(1.05); }
  66% { transform: translate(-10px, 10px) scale(0.95); }
}

@keyframes floatFast {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(8px, -12px); }
}

/* Centerpiece animations */
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.9; }
}

@keyframes slideInUp {
  0% { transform: translateY(30px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

@keyframes fadeInScale {
  0% { transform: scale(0.8); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* Data flow animations */
@keyframes dataFlow {
  0% { transform: translateX(-100%) scaleX(0); }
  50% { transform: translateX(0) scaleX(1); }
  100% { transform: translateX(100%) scaleX(0); }
}

@keyframes verdictAppear {
  0% { transform: scale(0) rotate(-5deg); opacity: 0; }
  50% { transform: scale(1.1) rotate(2deg); opacity: 0.8; }
  100% { transform: scale(1) rotate(0deg); opacity: 1; }
}
```

### 3. React Animated Centerpiece Component

#### Fact-Checking Animation Component
```tsx
// FactCheckingAnimation.tsx
'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, Search, Clock } from 'lucide-react';

export function FactCheckingAnimation() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(true);

  const steps = [
    { icon: Search, label: 'Analyzing Claim', color: 'text-blue-500' },
    { icon: Clock, label: 'Gathering Evidence', color: 'text-amber-500' },
    { icon: CheckCircle, label: 'Verdict Ready', color: 'text-green-500' }
  ];

  useEffect(() => {
    if (!isAnimating) return;

    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % steps.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [isAnimating, steps.length]);

  return (
    <div className="animated-centerpiece-container">
      {/* Main Interface Mockup */}
      <motion.div
        className="fact-check-interface"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        {/* Input Area */}
        <div className="interface-input">
          <div className="input-mockup">
            <div className="input-placeholder">
              Enter URL, text, or upload image...
            </div>
            <div className="input-button">
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className="check-button"
              >
                Check
              </motion.div>
            </div>
          </div>
        </div>

        {/* Processing Animation */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            className="interface-processing"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5 }}
          >
            <div className="processing-step">
              {steps[currentStep] && (
                <>
                  <motion.div
                    className={`step-icon ${steps[currentStep].color}`}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <steps[currentStep].icon size={24} />
                  </motion.div>
                  <span className="step-label">{steps[currentStep].label}</span>
                </>
              )}
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Results Area */}
        <motion.div
          className="interface-results"
          initial={{ opacity: 0 }}
          animate={{ opacity: currentStep === 2 ? 1 : 0.3 }}
          transition={{ duration: 0.5 }}
        >
          <div className="verdict-pills-demo">
            <motion.div
              className="verdict-pill verdict-supported"
              initial={{ scale: 0 }}
              animate={{ scale: currentStep === 2 ? 1 : 0.8 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              Supported
            </motion.div>
            <div className="confidence-display">
              <div className="confidence-label">Confidence</div>
              <motion.div
                className="confidence-bar-demo"
                initial={{ width: '0%' }}
                animate={{ width: currentStep === 2 ? '87%' : '20%' }}
                transition={{ duration: 1, delay: 0.5 }}
              />
              <span className="confidence-value">87%</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Floating Data Points */}
      <div className="floating-data-points">
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="data-point"
            style={{
              left: `${20 + i * 12}%`,
              top: `${30 + Math.sin(i) * 20}%`,
            }}
            animate={{
              y: [0, -10, 0],
              opacity: [0.3, 0.8, 0.3],
            }}
            transition={{
              duration: 3 + i * 0.5,
              repeat: Infinity,
              delay: i * 0.2,
            }}
          />
        ))}
      </div>
    </div>
  );
}
```

### 4. Centerpiece Styling

#### Animated Interface Styles
```css
/* Animated centerpiece container */
.animated-centerpiece-container {
  position: relative;
  width: 100%;
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Fact-checking interface mockup */
.fact-check-interface {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  width: 400px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 10;
}

.interface-input {
  margin-bottom: var(--space-6);
}

.input-mockup {
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.input-placeholder {
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.check-button {
  background: var(--gradient-primary);
  color: white;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  cursor: pointer;
}

.interface-processing {
  margin-bottom: var(--space-6);
  text-align: center;
}

.processing-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.step-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
}

.step-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--text-sm);
  font-weight: 500;
}

.interface-results {
  text-align: center;
}

.verdict-pills-demo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.confidence-bar-demo {
  height: 4px;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  transition: width 1s ease-out;
}

.confidence-display {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  justify-content: space-between;
}

.confidence-label {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.8);
}

.confidence-value {
  font-size: var(--text-xs);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

/* Floating data points */
.floating-data-points {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 5;
}

.data-point {
  position: absolute;
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
}
```

## 🎨 Performance Optimizations

### Animation Performance
```css
/* Hardware acceleration for smooth animations */
.animated-centerpiece-container,
.fact-check-interface,
.floating-data-points {
  transform: translateZ(0);
  will-change: transform;
}

/* Optimize animations for mobile */
@media (max-width: 768px) {
  .hero-background-primary,
  .hero-background-secondary,
  .hero-background-accent {
    animation-duration: 12s; /* Slower on mobile */
  }

  .animated-centerpiece-container {
    height: 400px; /* Smaller on mobile */
  }

  .fact-check-interface {
    width: 320px;
    padding: var(--space-6);
  }
}

/* Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  .hero-background-primary,
  .hero-background-secondary,
  .hero-background-accent,
  .data-point {
    animation: none;
  }

  .fact-check-interface {
    transition: none;
  }
}
```

## ✅ Testing Checklist

### Animation Testing
- [ ] All animations run smoothly at 60fps
- [ ] No janky or stuttering motion
- [ ] Animations pause/resume correctly
- [ ] Mobile performance is acceptable

### Accessibility Testing
- [ ] Reduced motion preferences are respected
- [ ] Animations don't interfere with screen readers
- [ ] Focus states remain visible during animations
- [ ] No seizure-inducing effects

### Performance Testing
- [ ] No significant impact on page load time
- [ ] Memory usage remains stable during animations
- [ ] CPU usage is acceptable on mobile devices
- [ ] Battery drain is minimal

### Browser Compatibility
- [ ] CSS animations work across all target browsers
- [ ] Framer Motion animations render correctly
- [ ] Fallbacks work for unsupported features

## 📈 Success Metrics

### Marketing Conversion (Track A - Signed-Out Users Only)
- **Increased hero engagement time** (target: +60% dwell time)
- **Higher conversion rates** from hero CTAs (target: +30% click-through)
- **Improved product understanding** (reduced demo requests, higher direct sign-ups)
- **Enhanced perceived value** (user feedback on product sophistication)

### Visual Impact Measurement
- **Animation completion rates** (how many users watch full demo)
- **Scroll progression** (users continuing past hero after seeing animation)
- **Social sharing** of marketing page (demonstration value)
- **Brand recall** improvement from animated demo

### Technical Performance (Marketing Pages Only)
- Maintained 60fps animation performance on marketing pages
- No impact on marketing page load times
- Cross-browser consistency for prospect experience
- Mobile animation performance (conversion device parity)

## 🚀 Implementation Phases

### Phase 6A: Foundation (Day 1-2)
1. Create basic animated centerpiece structure
2. Implement CSS animations and keyframes
3. Test performance across devices

### Phase 6B: React Integration (Day 2-3)
1. Build React animation components
2. Add Framer Motion for advanced effects
3. Integrate with existing hero section

### Phase 6C: Polish & Optimize (Day 3-4)
1. Fine-tune animation timing and easing
2. Optimize for mobile performance
3. Add reduced motion support

### Phase 6D: Advanced Effects (Day 4-5)
1. Add scroll-triggered animations
2. Implement interactive hover states
3. Create multiple animation variants

## 🔗 Related Documents
- **03_GRADIENT_HEADINGS.md** - Hero text animation integration
- **05_OPACITY_LAYERS.md** - Animation layer management
- **09_FEATURE_ANIMATIONS.md** - Consistent animation system

---

**Phase**: 2C - Visual Effects
**Priority**: Medium
**Estimated Effort**: 5-6 days
**Dependencies**: 01-05 (Foundation & Effects)
**Impact**: High - Engaging user experience centerpiece