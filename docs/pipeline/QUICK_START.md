# Pipeline Improvements - Quick Start Guide

**Ready to test in 5 minutes!**

---

## ⚡ Quick Enable (All Features)

### 1. Backend Configuration (30 seconds)

```bash
# File: backend/.env
ENABLE_EVIDENCE_DEDUPLICATION=true
ENABLE_SOURCE_DIVERSITY=true
ENABLE_FACTCHECK_INTEGRATION=true
ENABLE_TEMPORAL_CONTEXT=true
ENABLE_CLAIM_CLASSIFICATION=true
ENABLE_ENHANCED_EXPLAINABILITY=true
```

### 2. Restart Backend (10 seconds)

```bash
cd backend
# Kill existing process (Ctrl+C if running)
python -m uvicorn main:app --reload
```

### 3. Activate Enhanced UI (20 seconds)

```tsx
// File: web/app/dashboard/check/[id]/page.tsx
// Line 6: Change import

// FROM:
import { CheckDetailClient } from './check-detail-client';

// TO:
import { CheckDetailClientEnhanced } from './check-detail-client-enhanced';

// Line 52: Change component

// FROM:
<CheckDetailClient initialData={checkData} checkId={params.id} />

// TO:
<CheckDetailClientEnhanced initialData={checkData} checkId={params.id} />
```

### 4. Start Web App (10 seconds)

```bash
cd web
npm run dev
```

---

## ✅ Test It

### Submit Test Claims

Go to http://localhost:3000 and submit:

1. **Opinion:** "I think chocolate is the best flavor"
   - Should show "Not Verifiable (Opinion)" notice

2. **Factual:** "The Earth is round"
   - Should show SUPPORTED verdict with confidence breakdown

3. **Time-sensitive:** "The market crashed yesterday"
   - Should show "Time-Sensitive (Recent)" badge

4. **Prediction:** "AI will replace programmers by 2030"
   - Should show "Not Verifiable (Prediction)" notice

---

## 🎨 What You'll See (New UI Elements)

### On Completed Checks:
- ✅ **Transparency Score** - Below check metadata
- ✅ **Time-Sensitive Badges** - On recent claims
- ✅ **Claim Type Tags** - Opinion/Prediction labels

### On Individual Claims:
- ✅ **Non-Verifiable Notices** - For opinions/predictions (replaces verdict)
- ✅ **Uncertainty Explanations** - Amber box explaining why uncertain
- ✅ **Confidence Breakdown** - Checkmarks showing factors
- ✅ **Decision Trail** - Collapsible "How was this determined?"

### On Evidence:
- ✅ **Fact-Check Badges** - Blue badges for Snopes/Full Fact/etc.
- ✅ **Parent Company Info** - Shows media ownership
- ✅ **Temporal Relevance** - Time scores for recent claims

---

## 🔄 Rollback (If Needed)

### Disable Features:

```bash
# backend/.env
ENABLE_EVIDENCE_DEDUPLICATION=false
ENABLE_SOURCE_DIVERSITY=false
ENABLE_FACTCHECK_INTEGRATION=false
ENABLE_TEMPORAL_CONTEXT=false
ENABLE_CLAIM_CLASSIFICATION=false
ENABLE_ENHANCED_EXPLAINABILITY=false

# Restart backend
```

### Revert UI:

```tsx
// web/app/dashboard/check/[id]/page.tsx
// Change back to:
import { CheckDetailClient } from './check-detail-client';
<CheckDetailClient initialData={checkData} checkId={params.id} />
```

---

## 📚 Full Documentation

- **UI Implementation Guide:** `docs/pipeline/UI_IMPLEMENTATION_GUIDE.md`
- **Implementation Status:** `docs/pipeline/IMPLEMENTATION_STATUS.md`
- **Rollout Plan:** `docs/pipeline/FEATURE_ROLLOUT_PLAN.md`

---

## 🐛 Common Issues

### "Cannot find module 'lucide-react'"
```bash
cd web && npm install lucide-react
```

### Transparency score not showing
- Check feature flag: `ENABLE_ENHANCED_EXPLAINABILITY=true`
- Submit NEW check (old checks won't have new fields)

### Fact-check badges missing
- Check feature flag: `ENABLE_FACTCHECK_INTEGRATION=true`
- Try known fact-checked claim like "vaccines cause autism"

---

**That's it!** Enable, restart, swap 2 lines of code, and test. 🚀
