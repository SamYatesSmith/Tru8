# Phase 6: Footer

**Status:** Not Started
**Estimated Time:** 30 minutes
**Dependencies:** None
**Backend Integration:** None (all static links)

---

## 🎯 Objectives

1. Create footer component with logo and tagline
2. Add Product and Company navigation links
3. Add legal links (Privacy, Terms, Cookie Policy)
4. Add copyright notice
5. Ensure all links route correctly

---

## 📋 Task Checklist

- [ ] **Task 6.1:** Create footer component with layout
- [ ] **Task 6.2:** Add logo and tagline
- [ ] **Task 6.3:** Add Product and Company link columns
- [ ] **Task 6.4:** Add legal links and copyright
- [ ] **Task 6.5:** Test footer responsiveness

---

## 🔧 Implementation

### **Task 6.1-6.4: Footer Component**

File: `web/components/layout/footer.tsx`

**Structure:**
```
┌─────────────────────────────────────────────────┐
│  Logo + Tagline                                 │
│                                                 │
│  Product          Company                       │
│  - Features       - About                       │
│  - How It Works   - Blog                        │
│  - Pricing        - Contact                     │
│                                                 │
│  © 2025 Tru8   Privacy | Terms | Cookie Policy  │
└─────────────────────────────────────────────────┘
```

**Content:**

**Logo:** Tru8 "8" icon + "Professional fact-checking platform providing instant verification with dated evidence for those that prefer truth to...bilge."

**Product Links:**
- Features → Scroll to #features
- How It Works → Scroll to #how-it-works
- Pricing → Scroll to #pricing

**Company Links:**
- About → `/about` (placeholder page)
- Blog → `/blog` (placeholder page)
- Contact → `/contact` (placeholder page)

**Legal Links:**
- Privacy Policy → `/privacy` (placeholder)
- Terms of Service → `/terms` (placeholder)
- Cookie Policy → `/cookies` (placeholder)

**Copyright:** "© 2025 Tru8. All rights reserved."

**Styling:**
- Background: `#151823`
- Text: `gray-400`
- Links: `gray-400` → `#f57a07` on hover
- Border top: `gray-800`
- Responsive: 2 columns (desktop) → stack (mobile)

---

### **Implementation Code:**

```typescript
'use client';

export function Footer() {
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="bg-[#151823] border-t border-gray-800 py-12">
      <div className="container mx-auto px-4">
        {/* Logo and Tagline */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <div className="text-3xl font-bold text-white">8</div>
            <span className="text-xl font-semibold text-white">Tru8</span>
          </div>
          <p className="text-gray-400 max-w-md text-sm">
            Professional fact-checking platform providing instant verification
            with dated evidence for those that prefer truth to...bilge.
          </p>
        </div>

        {/* Links Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          {/* Product */}
          <div>
            <h3 className="text-white font-semibold mb-3">Product</h3>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={() => scrollToSection('features')}
                  className="text-gray-400 hover:text-[#f57a07] text-sm"
                >
                  Features
                </button>
              </li>
              <li>
                <button
                  onClick={() => scrollToSection('how-it-works')}
                  className="text-gray-400 hover:text-[#f57a07] text-sm"
                >
                  How It Works
                </button>
              </li>
              <li>
                <button
                  onClick={() => scrollToSection('pricing')}
                  className="text-gray-400 hover:text-[#f57a07] text-sm"
                >
                  Pricing
                </button>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-white font-semibold mb-3">Company</h3>
            <ul className="space-y-2">
              <li>
                <a href="/about" className="text-gray-400 hover:text-[#f57a07] text-sm">
                  About
                </a>
              </li>
              <li>
                <a href="/blog" className="text-gray-400 hover:text-[#f57a07] text-sm">
                  Blog
                </a>
              </li>
              <li>
                <a href="/contact" className="text-gray-400 hover:text-[#f57a07] text-sm">
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Legal and Copyright */}
        <div className="border-t border-gray-800 pt-6 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-400">
          <p>© 2025 Tru8. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="/privacy" className="hover:text-[#f57a07]">
              Privacy Policy
            </a>
            <a href="/terms" className="hover:text-[#f57a07]">
              Terms of Service
            </a>
            <a href="/cookies" className="hover:text-[#f57a07]">
              Cookie Policy
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
```

---

## ✅ Testing Checklist

- [ ] Footer displays at bottom of page
- [ ] Logo and tagline display correctly
- [ ] Product links scroll to correct sections
- [ ] Company links route correctly (even if placeholder pages)
- [ ] Legal links route correctly
- [ ] Hover states show orange color
- [ ] Responsive: 2 columns (desktop) → stack (mobile)
- [ ] Copyright text displays correctly

---

## 📝 Commit Message Template

```
[Phase 6] Add footer with navigation and legal links

Footer Component:
- Logo + tagline at top
- 2-column grid: Product + Company links
- Product links: Features, How It Works, Pricing (smooth scroll)
- Company links: About, Blog, Contact (routes to pages)
- Legal links: Privacy Policy, Terms of Service, Cookie Policy
- Copyright: © 2025 Tru8

Styling:
- Background: #151823
- Text: gray-400
- Hover: #f57a07 (orange)
- Border top: gray-800
- Responsive: Stacks on mobile

Files created:
- components/layout/footer.tsx

Files modified:
- app/page.tsx (added Footer component)

Testing performed:
- ✅ Footer displays correctly
- ✅ Smooth scroll links work
- ✅ Hover states show orange
- ✅ Responsive design works
```

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Next Phase:** Phase 7 (Responsive & Polish)
