# Phase 4: Content Sections (How It Works + Carousel + Video)

**Status:** Not Started
**Estimated Time:** 3 hours
**Dependencies:** Phase 3 (Hero section complete)
**Backend Integration:** None (all static marketing content)

---

## 🎯 Objectives

1. Create "How Tru8 Works" 3-step process section
2. Create "Professional Fact-Checking Tools" rollerdeck carousel (6 features)
3. Create "See Tru8 in Action" video demo placeholder
4. Implement carousel auto-play (5 seconds) + manual controls
5. Test carousel 3D rollerdeck effect and animations

---

## 📋 Task Checklist

- [ ] **Task 4.1:** Create "How Tru8 Works" component (3 cards)
- [ ] **Task 4.2:** Create rollerdeck carousel component with 3D perspective
- [ ] **Task 4.3:** Implement carousel auto-play and manual controls
- [ ] **Task 4.4:** Add 6 feature cards to carousel
- [ ] **Task 4.5:** Create video demo placeholder component
- [ ] **Task 4.6:** Add all sections to page
- [ ] **Task 4.7:** Test carousel interactions and animations

---

## 🔧 Implementation (Key Components)

### **Task 4.1: How Tru8 Works Component**

File: `web/components/marketing/how-it-works.tsx`

**3 Steps:**
1. **Submit Content** (Upload icon) - "Upload articles, images, videos, or paste text directly into our platform"
2. **AI Verification** (Zap icon) - "Our AI analyzes content against thousands of verified sources in real-time"
3. **Get Results** (FileText icon) - "Receive detailed reports with evidence, sources, and confidence scores"

**Styling:**
- Orange heading: "How Tru8 Works"
- Gray subheading: "Three simple steps to professional fact-checking"
- 3 cards in grid (stacks on mobile)
- Cards: dark background (#1a1f2e/80), cyan icons, numbered badges

---

### **Task 4.2-4.4: Rollerdeck Carousel**

File: `web/components/marketing/feature-carousel.tsx`

**6 Features (with provided copy):**
1. Multi-Source Verification
2. Article Analysis
3. Dated Evidence
4. Source Credibility
5. Confidence Scoring
6. Global Coverage

**Rollerdeck Specifications:**
- **Center card:** Scale 1.0, opacity 100%, z-index highest
- **Adjacent cards:** Scale 0.85, opacity 70%, slightly behind
- **Far cards:** Scale 0.7, opacity 40%, furthest back
- **Auto-play:** 5-second interval
- **Manual:** Left/Right arrow buttons
- **Animation:** Smooth slide transition (300ms ease-in-out)
- **Mobile:** Show 1 card only, swipeable

**CSS Implementation:**
```css
.carousel-container {
  perspective: 1200px; /* 3D perspective */
}

.carousel-card {
  transition: all 300ms ease-in-out;
  transform-style: preserve-3d;
}

.carousel-card-center {
  transform: scale(1) translateZ(0) rotateY(0);
  opacity: 1;
  z-index: 3;
}

.carousel-card-adjacent {
  transform: scale(0.85) translateZ(-100px) rotateY(5deg);
  opacity: 0.7;
  z-index: 2;
}

.carousel-card-far {
  transform: scale(0.7) translateZ(-200px) rotateY(10deg);
  opacity: 0.4;
  z-index: 1;
}
```

---

### **Task 4.5: Video Demo Placeholder**

File: `web/components/marketing/video-demo.tsx`

**Content:**
- Orange heading: "See Tru8 in Action"
- Gray subheading: "Watch how Tru8 verifies content in real-time"
- Large placeholder box with play button icon (cyan)
- Text: "Demo video coming soon"
- Text: "This section is ready for your demo video"

**Styling:**
- Dark card background (#1a1f2e)
- Play button: Cyan circle with play icon
- Ready for video embed (YouTube/Vimeo iframe)

---

## ✅ Testing Checklist

### How It Works Tests
- [ ] 3 cards display in grid (desktop) / stack (mobile)
- [ ] Icons display correctly (Upload, Zap, FileText)
- [ ] Numbered badges show 1, 2, 3
- [ ] Text readable and properly formatted

### Carousel Tests
- [ ] 6 feature cards created with correct copy
- [ ] Rollerdeck effect displays (3D perspective)
- [ ] Center card largest and fully opaque
- [ ] Adjacent cards scaled down and semi-transparent
- [ ] Auto-play advances every 5 seconds
- [ ] Left/Right arrows work correctly
- [ ] Clicking arrow stops auto-play temporarily
- [ ] Animation smooth (no jank)
- [ ] Mobile shows 1 card, swipeable

### Video Demo Tests
- [ ] Placeholder displays correctly
- [ ] Play button icon centered
- [ ] Text displays: "Demo video coming soon"
- [ ] Ready for video URL to be added later

---

## 📝 Commit Message Template

```
[Phase 4] Add content sections: How It Works, Feature Carousel, Video Demo

How Tru8 Works Section:
- 3-step process cards (Submit → AI Verification → Get Results)
- Icons: Upload, Zap, FileText (cyan-400)
- Numbered badges (1, 2, 3)
- Grid layout (desktop), stack (mobile)

Professional Fact-Checking Tools Carousel:
- 6 feature cards (Multi-Source, Article Analysis, Dated Evidence, etc.)
- Rollerdeck 3D effect with perspective: 1200px
- Center card: scale 1.0, opacity 100%
- Adjacent: scale 0.85, opacity 70%
- Far: scale 0.7, opacity 40%
- Auto-play: 5 seconds interval
- Manual controls: Left/Right arrows
- Smooth transitions: 300ms ease-in-out
- Mobile: 1 card visible, swipeable

See Tru8 in Action:
- Video demo placeholder with play button
- Cyan play icon
- "Demo video coming soon" text
- Ready for video embed

Files created:
- components/marketing/how-it-works.tsx
- components/marketing/feature-carousel.tsx
- components/marketing/video-demo.tsx

Files modified:
- app/page.tsx (added sections)
- app/globals.css (carousel 3D styles)

Testing performed:
- ✅ All 3 sections render correctly
- ✅ Carousel auto-play works (5s interval)
- ✅ Manual controls work
- ✅ Rollerdeck 3D effect displays correctly
- ✅ Mobile responsive (1 card visible)
```

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Next Phase:** Phase 5 (Pricing)
