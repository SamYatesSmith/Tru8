# Pipeline Improvements UI Implementation Guide

**Created:** 2025-10-20
**Purpose:** Enable and test Phase 1-2 pipeline improvements with enhanced UI

---

## Overview

This guide walks through **enabling backend features** and **activating the new UI** to display pipeline improvements including:

- ✅ Evidence deduplication
- ✅ Source diversity tracking
- ✅ Fact-check detection & badges
- ✅ Temporal context analysis
- ✅ Claim classification (opinion/prediction/personal experience)
- ✅ Enhanced explainability (decision trails, confidence breakdowns)
- ✅ Transparency scores

---

## Step 1: Enable Backend Features

### Edit Backend Configuration

```bash
# File: backend/.env
# Add or update these feature flags:

# Phase 1: Core Improvements
ENABLE_EVIDENCE_DEDUPLICATION=true
ENABLE_SOURCE_DIVERSITY=true
ENABLE_FACTCHECK_INTEGRATION=true

# Phase 1.5: Temporal Context
ENABLE_TEMPORAL_CONTEXT=true

# Phase 2: Classification & Explainability
ENABLE_CLAIM_CLASSIFICATION=true
ENABLE_ENHANCED_EXPLAINABILITY=true
```

### Restart Backend

```bash
cd backend

# If running directly:
# Kill existing process (Ctrl+C)
python -m uvicorn main:app --reload

# If using Docker:
docker-compose restart backend

# If using start script:
./start-backend.bat  # Windows
# OR
./start-backend.sh   # Linux/Mac
```

---

## Step 2: Activate Enhanced UI Components

The enhanced UI components have been created. Now you need to **swap them into the main page**.

### Option A: Gradual Swap (Recommended for Testing)

Test the new UI on one page first, keep old UI as backup.

#### 2A.1: Update Check Detail Page

```tsx
// File: web/app/dashboard/check/[id]/page.tsx

import { CheckDetailClientEnhanced } from './check-detail-client-enhanced';

// Change line 52 from:
<CheckDetailClient initialData={checkData} checkId={params.id} />

// To:
<CheckDetailClientEnhanced initialData={checkData} checkId={params.id} />
```

That's it! The enhanced client uses all new components automatically.

### Option B: Full Replacement

Replace the old files entirely (cannot easily roll back).

```bash
cd web/app/dashboard/check/[id]

# Backup old files
mv check-detail-client.tsx check-detail-client.OLD.tsx
mv components/claims-section.tsx components/claims-section.OLD.tsx
mv components/check-metadata-card.tsx components/check-metadata-card.OLD.tsx

# Rename enhanced files
mv check-detail-client-enhanced.tsx check-detail-client.tsx
mv components/claims-section-enhanced.tsx components/claims-section.tsx
mv components/check-metadata-card-enhanced.tsx components/check-metadata-card.tsx
```

---

## Step 3: Install New UI Dependencies (if needed)

The new components use `lucide-react` icons. Check if already installed:

```bash
cd web
npm list lucide-react
```

If not installed:

```bash
npm install lucide-react
```

---

## Step 4: Test the Implementation

### 4.1: Start Web Application

```bash
cd web
npm run dev
```

### 4.2: Submit Test Claims

Navigate to your web app (http://localhost:3000) and submit checks with different claim types:

#### Test Case 1: Opinion (Non-Verifiable)
**Input:** "I think chocolate ice cream is the best flavor in the world."

**Expected UI:**
- ✅ "Not Verifiable (Opinion)" notice
- ✅ Explanation: "This claim expresses a subjective opinion..."
- ❌ NO verdict pill or confidence bar

#### Test Case 2: Factual Claim
**Input:** "The Earth is round and orbits the Sun."

**Expected UI:**
- ✅ SUPPORTED verdict pill
- ✅ High confidence (85-95%)
- ✅ Confidence breakdown (if explainability enabled)
- ✅ Decision trail (collapsible "How was this determined?")
- ✅ Fact-check badges on evidence (if Snopes/Full Fact found)

#### Test Case 3: Time-Sensitive Claim
**Input:** "The stock market crashed yesterday, losing 5% in value."

**Expected UI:**
- ✅ "Time-Sensitive (Recent)" badge
- ✅ Evidence sorted by recency
- ✅ Temporal relevance scores shown

#### Test Case 4: Prediction
**Input:** "AI will replace all programmers by 2030."

**Expected UI:**
- ✅ "Not Verifiable (prediction)" notice
- ✅ Explanation about future predictions

#### Test Case 5: Uncertain Verdict
**Input:** "Wearing masks reduces COVID transmission by exactly 50%."

**Expected UI:**
- ✅ UNCERTAIN verdict pill
- ✅ Lower confidence (40-60%)
- ✅ **Uncertainty explanation** box explaining WHY uncertain
- ✅ Confidence breakdown showing conflicting factors

### 4.3: Verify Database Fields Populated

```sql
-- Connect to your database
psql your_database_name

-- Check transparency score on check
SELECT id, status, transparency_score
FROM "check"
ORDER BY created_at DESC
LIMIT 1;

-- Check claim fields
SELECT
  text,
  claim_type,
  is_verifiable,
  is_time_sensitive,
  verdict,
  uncertainty_explanation
FROM claim
WHERE check_id = 'YOUR_CHECK_ID_HERE'
ORDER BY position;

-- Check evidence fields
SELECT
  source,
  is_factcheck,
  factcheck_publisher,
  parent_company,
  is_syndicated,
  temporal_relevance_score
FROM evidence
WHERE claim_id = 'YOUR_CLAIM_ID_HERE'
ORDER BY relevance_score DESC
LIMIT 10;
```

---

## UI Components Reference

### New Components Created

All components follow the dark theme aesthetic (slate-800/900 backgrounds, orange accents).

#### 1. `transparency-score.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Shows overall check transparency (0-100%)
**Props:** `score: number` (0-1)

#### 2. `decision-trail.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Collapsible 3-stage decision process
**Props:** `decisionTrail: { stages: [], transparency_score: number }`

#### 3. `confidence-breakdown.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Shows factors affecting confidence (checkmarks/x-marks)
**Props:** `breakdown: { overall_confidence: number, factors: [] }`

#### 4. `uncertainty-explanation.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Amber warning box explaining uncertain verdicts
**Props:** `explanation: string`

#### 5. `non-verifiable-notice.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Replaces verdict for opinions/predictions/personal experiences
**Props:** `claimType: string, reason: string`

#### 6. `fact-check-badge.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Blue badge for fact-checked evidence
**Props:** `publisher: string, rating?: string`

#### 7. `time-sensitive-indicator.tsx`
**Location:** `web/app/dashboard/components/`
**Purpose:** Amber badge for time-sensitive claims
**Props:** `timeReference: string`

### Enhanced Main Components

#### `claims-section-enhanced.tsx`
**Integrates all new components:**
- Conditionally shows non-verifiable notice OR normal verdict
- Displays time-sensitive indicators
- Shows uncertainty explanations
- Renders confidence breakdowns
- Includes collapsible decision trails
- Adds fact-check badges to evidence
- Displays parent company info

#### `check-metadata-card-enhanced.tsx`
**Additions:**
- Displays transparency score below metadata (if completed)

#### `check-detail-client-enhanced.tsx`
**Wrapper that uses:**
- CheckMetadataCardEnhanced
- ClaimsSectionEnhanced

---

## Styling Notes

All components follow the existing dark theme:

### Colors
- **Background:** `bg-slate-800/50` with `border-slate-700`
- **Text:** `text-white` (headings), `text-slate-300/400` (body)
- **Accent:** `text-[#f57a07]` for CTAs and highlights
- **Verdict colors:** Emerald (supported), Red (contradicted), Amber (uncertain)

### Spacing
- **Card padding:** `p-6`
- **Section gaps:** `space-y-4` or `space-y-6`
- **Border radius:** `rounded-xl` (12px)

### Animations
- **Confidence/transparency bars:** 1000ms ease-out width transition
- **Hover states:** `hover:border-slate-600` with `transition-colors`

---

## Troubleshooting

### Issue: "Cannot find module 'lucide-react'"
**Solution:** Install icons package
```bash
cd web
npm install lucide-react
```

### Issue: Transparency score not showing
**Causes:**
1. Feature flag `ENABLE_ENHANCED_EXPLAINABILITY=false`
2. Check status not "completed"
3. Backend not returning `transparency_score` field

**Debug:**
```bash
# Check backend logs for feature activation
cd backend
# Look for: "Enhanced explainability enabled"

# Check API response
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/checks/YOUR_CHECK_ID
```

### Issue: Non-verifiable claims showing normal verdict
**Causes:**
1. Feature flag `ENABLE_CLAIM_CLASSIFICATION=false`
2. Using old ClaimsSection component

**Solution:**
- Verify `.env` has `ENABLE_CLAIM_CLASSIFICATION=true`
- Ensure using `ClaimsSectionEnhanced` not `ClaimsSection`

### Issue: Fact-check badges not appearing
**Causes:**
1. Feature flag `ENABLE_FACTCHECK_INTEGRATION=false`
2. No fact-checks found for this claim
3. Evidence missing `isFactcheck` field

**Debug:**
```sql
SELECT source, is_factcheck, factcheck_publisher
FROM evidence
WHERE claim_id = 'YOUR_CLAIM_ID'
AND is_factcheck = true;
```

### Issue: Decision trail empty or missing
**Causes:**
1. Feature flag `ENABLE_ENHANCED_EXPLAINABILITY=false`
2. Check was processed before features enabled (old data)

**Solution:**
- Submit NEW check after enabling features
- Old checks won't have new fields populated

---

## Rollback Procedure

If new UI causes issues, you can roll back quickly:

### Rollback UI Only (Keep Backend Features)

```tsx
// File: web/app/dashboard/check/[id]/page.tsx

// Change back to:
import { CheckDetailClient } from './check-detail-client';

<CheckDetailClient initialData={checkData} checkId={params.id} />
```

### Rollback Backend Features

```bash
# File: backend/.env
# Set all flags to false:

ENABLE_EVIDENCE_DEDUPLICATION=false
ENABLE_SOURCE_DIVERSITY=false
ENABLE_FACTCHECK_INTEGRATION=false
ENABLE_TEMPORAL_CONTEXT=false
ENABLE_CLAIM_CLASSIFICATION=false
ENABLE_ENHANCED_EXPLAINABILITY=false

# Restart backend
```

### Full Rollback (Restore Old Files)

```bash
cd web/app/dashboard/check/[id]

# If you made backups:
mv check-detail-client.OLD.tsx check-detail-client.tsx
mv components/claims-section.OLD.tsx components/claims-section.tsx
mv components/check-metadata-card.OLD.tsx components/check-metadata-card.tsx
```

---

## Performance Considerations

### Expected UI Performance Impact

**Minimal:** New components are React functional components with minimal state.

- **Decision Trail:** Collapsible, only renders when expanded
- **Confidence Breakdown:** Simple list iteration
- **Animations:** CSS transitions (GPU-accelerated)

### Backend Performance

Refer to `docs/pipeline/IMPLEMENTATION_STATUS.md` for backend performance metrics:
- Total overhead: ~1.3s added to pipeline
- Token cost increase: +$0.001 per check
- All within acceptable targets

---

## Next Steps After Testing

### Phase 1: Validate Individual Features
1. Test deduplication (submit claims with known duplicates)
2. Test fact-check detection (submit well-known fact-checked claims)
3. Test temporal context (submit "yesterday" vs "in 1945")
4. Test claim classification (opinions, predictions, facts)

### Phase 2: Gradual Production Rollout
Follow `docs/pipeline/FEATURE_ROLLOUT_PLAN.md`:
- Week 1: Backend features only (test via database)
- Week 2: UI features (internal testing)
- Week 3: Beta users
- Week 4: Full rollout

### Phase 3: User Feedback Collection
- Monitor user engagement with decision trails (click rates)
- Track confidence in verdicts (user surveys)
- Measure support ticket reduction (better explanations)

---

## Summary

**To enable everything:**

1. ✅ Set 6 feature flags to `true` in `backend/.env`
2. ✅ Restart backend
3. ✅ Update 1 import in `web/app/dashboard/check/[id]/page.tsx`
4. ✅ Submit test checks via UI
5. ✅ Verify new UI elements appear

**Components created:** 10 new files
**Backward compatible:** Yes (old UI still works)
**Rollback time:** < 5 minutes
**Testing time:** 15-30 minutes

All features default to disabled for safe gradual rollout.

---

**Questions? Issues?** Check the Troubleshooting section or refer to:
- `docs/pipeline/IMPLEMENTATION_STATUS.md` (backend details)
- `docs/pipeline/FEATURE_ROLLOUT_PLAN.md` (rollout strategy)
- `docs/DESIGN_SYSTEM.md` (styling guidelines)
