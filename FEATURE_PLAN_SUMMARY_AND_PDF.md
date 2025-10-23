# Feature Implementation Plan: Overall Summary & PDF Export

**Date Created:** 2025-10-21
**Status:** Ready for Implementation
**Estimated Total Time:** 8-10 hours

---

## 🎯 Overview

This plan covers two interconnected features:
1. **Overall Summary/TL;DR** - LLM-generated executive summary of fact-check results
2. **PDF Export** - Professional downloadable report with branding

Both features enhance user experience by providing:
- Quick understanding of overall credibility (summary)
- Shareable, professional documentation (PDF)
- Email-friendly format for sharing with colleagues/authorities

---

## 📋 Phase 1: Overall Summary Implementation

### 1.1 Database Changes

**File:** `backend/app/models/check.py`

**Add to Check model:**
```python
class Check(SQLModel, table=True):
    # ... existing fields ...

    # NEW FIELDS - Phase 1
    overall_summary: Optional[str] = Field(default=None, description="LLM-generated executive summary")
    credibility_score: Optional[int] = Field(default=None, ge=0, le=100, description="Overall credibility score 0-100")
    claims_supported: Optional[int] = Field(default=0, description="Count of supported claims")
    claims_contradicted: Optional[int] = Field(default=0, description="Count of contradicted claims")
    claims_uncertain: Optional[int] = Field(default=0, description="Count of uncertain claims")
```

**Migration needed:** Yes
```bash
cd backend
alembic revision --autogenerate -m "add_overall_summary_fields"
alembic upgrade head
```

---

### 1.2 Backend Logic

**File:** `backend/app/workers/pipeline.py`

**Add new function after judge stage (~line 300):**
```python
async def generate_overall_assessment(
    claims: List[Dict[str, Any]],
    check_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate overall credibility assessment after all claims judged.
    Returns: {
        "summary": str,           # 2-3 sentence executive summary
        "credibility_score": int, # 0-100 overall score
        "key_findings": str       # Bullet points of main issues
    }
    """
    from app.services.llm import get_llm_service

    # Calculate statistics
    total = len(claims)
    supported = sum(1 for c in claims if c.get('verdict') == 'supported')
    contradicted = sum(1 for c in claims if c.get('verdict') == 'contradicted')
    uncertain = sum(1 for c in claims if c.get('verdict') == 'uncertain')
    avg_confidence = sum(c.get('confidence', 0) for c in claims) / total if total > 0 else 0

    # Calculate overall credibility score (weighted)
    credibility_score = int(
        (supported * 100 + uncertain * 50 + contradicted * 0) / total if total > 0 else 50
    )

    # Prepare claims summary for LLM
    claims_summary = []
    for i, claim in enumerate(claims, 1):
        claims_summary.append({
            "number": i,
            "text": claim.get('text', '')[:200],  # Truncate long claims
            "verdict": claim.get('verdict'),
            "confidence": claim.get('confidence')
        })

    # LLM prompt
    prompt = f"""You are a fact-checking expert providing an overall assessment.

SOURCE: {check_url or 'User-submitted content'}

CLAIMS ANALYZED: {total}
- Supported: {supported} ({supported/total*100:.1f}%)
- Contradicted: {contradicted} ({contradicted/total*100:.1f}%)
- Uncertain: {uncertain} ({uncertain/total*100:.1f}%)
- Average Confidence: {avg_confidence:.1f}%

CLAIM DETAILS:
{json.dumps(claims_summary, indent=2)}

Generate a concise overall assessment in 2-3 sentences that answers:
1. What is the overall credibility of this content?
2. What can readers trust vs. what needs skepticism?
3. Are there any red flags or patterns?

Be direct and actionable. Focus on practical guidance for the reader.
"""

    llm_service = get_llm_service()
    summary = await llm_service.generate_completion(
        prompt=prompt,
        max_tokens=200,
        temperature=0.3
    )

    return {
        "summary": summary.strip(),
        "credibility_score": credibility_score,
        "claims_supported": supported,
        "claims_contradicted": contradicted,
        "claims_uncertain": uncertain
    }
```

**Integrate into pipeline (line ~296):**
```python
# After judge stage
results = asyncio.run(judge_claims_parallel(claims, evidence, verifications))

# NEW: Generate overall assessment
logger.info(f"Generating overall assessment for check {check_id}")
assessment = asyncio.run(
    generate_overall_assessment(results, input_data.get('url'))
)

final_result = {
    "claims": results,
    "overall_summary": assessment["summary"],              # NEW
    "credibility_score": assessment["credibility_score"],  # NEW
    "claims_supported": assessment["claims_supported"],    # NEW
    "claims_contradicted": assessment["claims_contradicted"], # NEW
    "claims_uncertain": assessment["claims_uncertain"],    # NEW
    # ... rest of existing fields ...
}
```

**Update save_check_results_sync (line ~103):**
```python
def save_check_results_sync(check_id: str, results: Dict[str, Any]):
    # ... existing code ...

    check.status = "completed"
    check.completed_at = datetime.utcnow()
    check.processing_time_ms = results.get("processing_time_ms", 0)

    # NEW: Save overall summary fields
    check.overall_summary = results.get("overall_summary")
    check.credibility_score = results.get("credibility_score")
    check.claims_supported = results.get("claims_supported", 0)
    check.claims_contradicted = results.get("claims_contradicted", 0)
    check.claims_uncertain = results.get("claims_uncertain", 0)

    # ... rest of existing code ...
```

**Estimated Time:** 2 hours

---

### 1.3 Frontend UI - Summary Display

**Location:** `web/app/dashboard/check/[id]/check-detail-client.tsx`

**Add new component above ClaimsSection:**
```typescript
{check.status === 'completed' && check.overall_summary && (
  <OverallSummaryCard check={check} />
)}
```

**New File:** `web/app/dashboard/check/[id]/components/overall-summary-card.tsx`

```typescript
'use client';

interface OverallSummaryCardProps {
  check: {
    overall_summary: string;
    credibility_score: number;
    claims_supported: number;
    claims_contradicted: number;
    claims_uncertain: number;
  };
}

export function OverallSummaryCard({ check }: OverallSummaryCardProps) {
  // Calculate credibility level
  const getCredibilityLevel = (score: number) => {
    if (score >= 80) return { label: 'High Credibility', color: 'text-emerald-400', bg: 'bg-emerald-500/20' };
    if (score >= 60) return { label: 'Moderate Credibility', color: 'text-amber-400', bg: 'bg-amber-500/20' };
    return { label: 'Low Credibility', color: 'text-red-400', bg: 'bg-red-500/20' };
  };

  const credibility = getCredibilityLevel(check.credibility_score);

  return (
    <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-8 mb-8">
      {/* Header with Score */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-black text-white mb-2">Overall Assessment</h2>
          <div className="flex items-center gap-3">
            <div className={`${credibility.bg} ${credibility.color} px-4 py-2 rounded-lg font-bold text-sm`}>
              {credibility.label}
            </div>
            <div className="text-white/60 text-sm">
              Credibility Score: <span className="text-white font-bold text-lg">{check.credibility_score}/100</span>
            </div>
          </div>
        </div>

        {/* Score Gauge */}
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-slate-700"
            />
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 40}`}
              strokeDashoffset={`${2 * Math.PI * 40 * (1 - check.credibility_score / 100)}`}
              className={credibility.color}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-black text-white">{check.credibility_score}</span>
          </div>
        </div>
      </div>

      {/* Summary Text */}
      <div className="bg-slate-900/50 rounded-lg p-6 mb-6">
        <p className="text-white/90 text-lg leading-relaxed">
          {check.overall_summary}
        </p>
      </div>

      {/* Claims Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-emerald-400">{check.claims_supported}</div>
          <div className="text-sm text-emerald-400/70 font-medium">Supported</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-amber-400">{check.claims_uncertain}</div>
          <div className="text-sm text-amber-400/70 font-medium">Uncertain</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
          <div className="text-3xl font-black text-red-400">{check.claims_contradicted}</div>
          <div className="text-sm text-red-400/70 font-medium">Contradicted</div>
        </div>
      </div>
    </div>
  );
}
```

**Estimated Time:** 1.5 hours

---

## 📄 Phase 2: PDF Export Implementation

### 2.1 Backend Dependencies

**File:** `backend/requirements.txt`

**Add:**
```
weasyprint==62.3
jinja2==3.1.4
```

**Install:**
```bash
cd backend
pip install weasyprint jinja2
```

**Note:** WeasyPrint requires system dependencies (Cairo, Pango). On Windows, install GTK3 runtime.

---

### 2.2 PDF Template

**New File:** `backend/app/templates/pdf/fact_check_report.html`

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Helvetica', 'Arial', sans-serif;
      color: #1e293b;
      line-height: 1.6;
      padding: 40px;
      background: #ffffff;
    }

    .header {
      border-bottom: 4px solid #1e40af;
      padding-bottom: 20px;
      margin-bottom: 30px;
    }

    .logo {
      font-size: 32px;
      font-weight: 900;
      color: #1e40af;
      margin-bottom: 10px;
    }

    .tagline {
      color: #64748b;
      font-size: 14px;
    }

    .metadata {
      background: #f1f5f9;
      border-left: 4px solid #1e40af;
      padding: 20px;
      margin-bottom: 30px;
    }

    .metadata-item {
      margin-bottom: 8px;
    }

    .metadata-label {
      font-weight: 700;
      color: #1e40af;
      display: inline-block;
      width: 140px;
    }

    .summary-box {
      background: linear-gradient(135deg, #1e40af15 0%, #7c3aed15 100%);
      border: 2px solid #1e40af;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 30px;
    }

    .summary-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .summary-title {
      font-size: 20px;
      font-weight: 900;
      color: #1e40af;
    }

    .credibility-score {
      font-size: 32px;
      font-weight: 900;
      color: #1e40af;
    }

    .credibility-label {
      font-size: 12px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .summary-text {
      font-size: 16px;
      line-height: 1.8;
      color: #334155;
    }

    .claims-breakdown {
      display: flex;
      justify-content: space-around;
      margin: 20px 0 30px 0;
      padding: 20px;
      background: #ffffff;
      border-radius: 8px;
    }

    .stat-item {
      text-align: center;
    }

    .stat-value {
      font-size: 36px;
      font-weight: 900;
      line-height: 1;
    }

    .stat-value.supported { color: #059669; }
    .stat-value.uncertain { color: #d97706; }
    .stat-value.contradicted { color: #dc2626; }

    .stat-label {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      margin-top: 4px;
      color: #64748b;
    }

    .section-title {
      font-size: 22px;
      font-weight: 900;
      color: #1e293b;
      margin-top: 40px;
      margin-bottom: 20px;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 8px;
    }

    .claim-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
      page-break-inside: avoid;
    }

    .claim-header {
      display: flex;
      justify-content: space-between;
      align-items: start;
      margin-bottom: 12px;
    }

    .claim-number {
      font-size: 14px;
      font-weight: 700;
      color: #64748b;
      margin-right: 8px;
    }

    .claim-text {
      flex: 1;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
      line-height: 1.6;
    }

    .verdict-badge {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .verdict-supported {
      background: #059669;
      color: #ffffff;
    }

    .verdict-contradicted {
      background: #dc2626;
      color: #ffffff;
    }

    .verdict-uncertain {
      background: #d97706;
      color: #ffffff;
    }

    .confidence {
      font-size: 12px;
      color: #64748b;
      margin-left: 8px;
    }

    .claim-rationale {
      margin-top: 12px;
      padding: 12px;
      background: #f8fafc;
      border-left: 3px solid #1e40af;
      font-size: 14px;
      color: #475569;
      font-style: italic;
    }

    .evidence-section {
      margin-top: 16px;
    }

    .evidence-title {
      font-size: 14px;
      font-weight: 700;
      color: #1e40af;
      margin-bottom: 8px;
    }

    .evidence-item {
      margin-bottom: 12px;
      padding-left: 20px;
      position: relative;
    }

    .evidence-item:before {
      content: "•";
      position: absolute;
      left: 8px;
      color: #1e40af;
      font-weight: 900;
    }

    .evidence-source {
      font-weight: 700;
      color: #1e40af;
      font-size: 13px;
    }

    .evidence-title-text {
      font-size: 13px;
      color: #334155;
      margin-bottom: 4px;
    }

    .evidence-snippet {
      font-size: 12px;
      color: #64748b;
      line-height: 1.5;
    }

    .footer {
      margin-top: 60px;
      padding-top: 20px;
      border-top: 2px solid #e2e8f0;
      text-align: center;
      color: #94a3b8;
      font-size: 12px;
    }

    .footer-logo {
      font-weight: 900;
      color: #1e40af;
      font-size: 14px;
      margin-bottom: 4px;
    }

    .page-break {
      page-break-after: always;
    }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="logo">TRU8</div>
    <div class="tagline">Independent Fact-Checking Report</div>
  </div>

  <!-- Metadata -->
  <div class="metadata">
    <div class="metadata-item">
      <span class="metadata-label">Source URL:</span>
      <span>{{ check.input_url or 'User-submitted text' }}</span>
    </div>
    <div class="metadata-item">
      <span class="metadata-label">Date Checked:</span>
      <span>{{ check.created_at.strftime('%B %d, %Y at %H:%M UTC') }}</span>
    </div>
    <div class="metadata-item">
      <span class="metadata-label">Report ID:</span>
      <span>{{ check.id[:8] }}</span>
    </div>
    <div class="metadata-item">
      <span class="metadata-label">Processing Time:</span>
      <span>{{ (check.processing_time_ms / 1000)|round(1) }} seconds</span>
    </div>
  </div>

  <!-- Overall Summary -->
  <div class="summary-box">
    <div class="summary-header">
      <div>
        <div class="summary-title">Overall Assessment</div>
      </div>
      <div style="text-align: right;">
        <div class="credibility-score">{{ check.credibility_score }}/100</div>
        <div class="credibility-label">Credibility Score</div>
      </div>
    </div>

    <p class="summary-text">{{ check.overall_summary }}</p>
  </div>

  <!-- Claims Breakdown -->
  <div class="claims-breakdown">
    <div class="stat-item">
      <div class="stat-value supported">{{ check.claims_supported }}</div>
      <div class="stat-label">Supported</div>
    </div>
    <div class="stat-item">
      <div class="stat-value uncertain">{{ check.claims_uncertain }}</div>
      <div class="stat-label">Uncertain</div>
    </div>
    <div class="stat-item">
      <div class="stat-value contradicted">{{ check.claims_contradicted }}</div>
      <div class="stat-label">Contradicted</div>
    </div>
  </div>

  <!-- Claims Detail -->
  <h2 class="section-title">Claims Analyzed ({{ claims|length }})</h2>

  {% for claim in claims %}
  <div class="claim-card">
    <div class="claim-header">
      <div style="flex: 1;">
        <span class="claim-number">Claim {{ loop.index }}</span>
        <div class="claim-text">{{ claim.text }}</div>
      </div>
      <div style="text-align: right; white-space: nowrap;">
        <span class="verdict-badge verdict-{{ claim.verdict }}">
          {{ claim.verdict }}
        </span>
        <div class="confidence">{{ claim.confidence }}% confidence</div>
      </div>
    </div>

    <div class="claim-rationale">
      {{ claim.rationale }}
    </div>

    {% if claim.evidence %}
    <div class="evidence-section">
      <div class="evidence-title">Supporting Evidence ({{ claim.evidence|length }} sources)</div>
      {% for evidence in claim.evidence[:3] %}
      <div class="evidence-item">
        <div class="evidence-source">{{ evidence.source }}</div>
        <div class="evidence-title-text">{{ evidence.title }}</div>
        <div class="evidence-snippet">{{ evidence.snippet[:150] }}...</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endfor %}

  <!-- Footer -->
  <div class="footer">
    <div class="footer-logo">TRU8</div>
    <div>This report was generated automatically using AI-powered fact-checking technology.</div>
    <div>For more information, visit https://tru8.com</div>
    <div style="margin-top: 8px;">Generated on {{ now.strftime('%B %d, %Y at %H:%M UTC') }}</div>
  </div>
</body>
</html>
```

**Estimated Time:** 2 hours

---

### 2.3 Backend PDF API Endpoint

**File:** `backend/app/api/v1/checks.py`

**Add new endpoint:**
```python
from fastapi.responses import Response
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime

# Setup Jinja2 environment
template_dir = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(template_dir))

@router.get("/{check_id}/export/pdf")
async def export_check_pdf(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Export fact-check as PDF report"""

    # Fetch check with all related data
    stmt = (
        select(Check)
        .where(Check.id == check_id)
        .where(Check.user_id == current_user["id"])
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if check.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="PDF export only available for completed checks"
        )

    # Fetch claims
    claims_stmt = (
        select(Claim)
        .where(Claim.check_id == check_id)
        .order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    # Fetch evidence for each claim
    claims_with_evidence = []
    for claim in claims:
        evidence_stmt = (
            select(Evidence)
            .where(Evidence.claim_id == claim.id)
            .order_by(desc(Evidence.relevance_score))
            .limit(3)  # Top 3 evidence per claim for PDF
        )
        evidence_result = await session.execute(evidence_stmt)
        evidence_list = evidence_result.scalars().all()

        claims_with_evidence.append({
            "text": claim.text,
            "verdict": claim.verdict,
            "confidence": claim.confidence,
            "rationale": claim.rationale,
            "evidence": evidence_list
        })

    # Render HTML template
    template = jinja_env.get_template("pdf/fact_check_report.html")
    html_content = template.render(
        check=check,
        claims=claims_with_evidence,
        now=datetime.utcnow()
    )

    # Generate PDF
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF. Please try again."
        )

    # Return PDF
    filename = f"tru8-factcheck-{check_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )
```

**Estimated Time:** 1.5 hours

---

### 2.4 Frontend PDF Download Button

**File:** `web/app/dashboard/check/[id]/components/share-section.tsx`

**Update to add PDF download:**
```typescript
import { Facebook, Twitter, Linkedin, Link as LinkIcon, Check, Download } from 'lucide-react';

// ... existing code ...

const handleDownloadPDF = async () => {
  try {
    const response = await fetch(`/api/v1/checks/${checkId}/export/pdf`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });

    if (!response.ok) throw new Error('PDF generation failed');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tru8-factcheck-${checkId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('PDF download failed:', error);
    alert('Failed to download PDF. Please try again.');
  }
};

// In the JSX, add before social share buttons:
return (
  <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
    <h3 className="text-xl font-bold text-white mb-4">Share & Export</h3>

    {/* PDF Download Button - Prominent placement */}
    <button
      onClick={handleDownloadPDF}
      className="w-full mb-6 flex items-center justify-center gap-3 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg font-bold transition-all shadow-lg hover:shadow-xl"
    >
      <Download size={20} />
      Download PDF Report
    </button>

    {/* Existing social share buttons */}
    <div className="flex items-center gap-3">
      {/* ... existing social buttons ... */}
    </div>
  </div>
);
```

**Estimated Time:** 0.5 hours

---

## 🎨 Phase 3: Social Media Preview Enhancement

### 3.1 Open Graph Meta Tags

**File:** `web/app/dashboard/check/[id]/page.tsx`

**Update metadata generation:**
```typescript
export async function generateMetadata({ params }: CheckDetailPageProps): Promise<Metadata> {
  const { id } = params;

  try {
    // Fetch check data (server-side)
    const check = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/checks/${id}`).then(r => r.json());

    const title = `Fact-Check Report: ${check.input_url ? new URL(check.input_url).hostname : 'Content Analysis'}`;
    const description = check.overall_summary ||
      `${check.claims_supported} claims supported, ${check.claims_contradicted} contradicted, ${check.claims_uncertain} uncertain. Credibility score: ${check.credibility_score}/100.`;

    const imageUrl = `${process.env.NEXT_PUBLIC_APP_URL}/api/og-image?checkId=${id}`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: 'article',
        url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/check/${id}`,
        images: [
          {
            url: imageUrl,
            width: 1200,
            height: 630,
            alt: 'Tru8 Fact-Check Report'
          }
        ],
        siteName: 'Tru8',
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
        images: [imageUrl],
        creator: '@tru8app'
      }
    };
  } catch (error) {
    return {
      title: 'Fact-Check Report | Tru8',
      description: 'View detailed fact-checking analysis with evidence and sources.'
    };
  }
}
```

---

### 3.2 Dynamic OG Image Generator (Optional - Advanced)

**New File:** `web/app/api/og-image/route.tsx` (Next.js ImageResponse API)

```typescript
import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const checkId = searchParams.get('checkId');

  // Fetch check data
  const check = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/checks/${checkId}`)
    .then(r => r.json());

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f172a',
          backgroundImage: 'linear-gradient(135deg, #1e40af 0%, #7c3aed 100%)',
        }}
      >
        <div style={{ display: 'flex', fontSize: 60, fontWeight: 900, color: 'white' }}>
          TRU8
        </div>
        <div style={{ fontSize: 32, color: 'white', marginTop: 20 }}>
          Fact-Check Report
        </div>
        <div style={{
          marginTop: 40,
          padding: '20px 40px',
          background: 'white',
          borderRadius: 16,
          display: 'flex',
          gap: 40
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: '#059669' }}>
              {check.claims_supported}
            </div>
            <div style={{ fontSize: 16, color: '#64748b' }}>Supported</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: '#d97706' }}>
              {check.claims_uncertain}
            </div>
            <div style={{ fontSize: 16, color: '#64748b' }}>Uncertain</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: '#dc2626' }}>
              {check.claims_contradicted}
            </div>
            <div style={{ fontSize: 16, color: '#64748b' }}>Contradicted</div>
          </div>
        </div>
        <div style={{
          marginTop: 40,
          fontSize: 24,
          color: 'white',
          fontWeight: 700
        }}>
          Credibility Score: {check.credibility_score}/100
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
```

**Estimated Time:** 1.5 hours (if implementing OG image)

---

## 📋 Implementation Checklist

### Pre-Implementation
- [ ] Review plan with team
- [ ] Ensure all dependencies can be installed (WeasyPrint on Windows)
- [ ] Backup database before migration
- [ ] Test LLM API has sufficient quota for summary generation

### Phase 1: Overall Summary (3.5 hours)
- [ ] Create database migration for new fields
- [ ] Run migration on dev database
- [ ] Add `generate_overall_assessment()` function to pipeline.py
- [ ] Integrate assessment into pipeline results
- [ ] Update `save_check_results_sync()` to save new fields
- [ ] Create `OverallSummaryCard` component
- [ ] Add component to check detail page
- [ ] Test with sample check
- [ ] Verify summary appears correctly

### Phase 2: PDF Export (4.5 hours)
- [ ] Install WeasyPrint and Jinja2
- [ ] Create templates directory structure
- [ ] Create PDF HTML template
- [ ] Test PDF template renders correctly
- [ ] Add PDF export API endpoint
- [ ] Test PDF generation with real check data
- [ ] Add PDF download button to frontend
- [ ] Test PDF download flow
- [ ] Verify PDF formatting on print

### Phase 3: Social Media (1.5 hours)
- [ ] Update metadata generation in check detail page
- [ ] Test Open Graph preview on Facebook debugger
- [ ] Test Twitter card preview
- [ ] (Optional) Implement dynamic OG image generator
- [ ] Test social sharing on multiple platforms

### Post-Implementation
- [ ] Update documentation
- [ ] Add cost monitoring for additional LLM call
- [ ] Create user guide for PDF reports
- [ ] Monitor PDF generation performance
- [ ] Collect user feedback

---

## 💰 Cost Implications

**LLM Summary Generation:**
- 1 additional LLM call per check
- ~200 tokens per summary
- Estimated cost: $0.002 - $0.005 per check
- Monthly at 1000 checks: $2-5

**PDF Generation:**
- Server CPU: negligible (< 1 second per PDF)
- Storage: None (generated on-demand)

**Total:** Minimal cost impact

---

## 🎯 Success Metrics

**User Engagement:**
- % of users viewing summary section
- PDF download rate per completed check
- Social shares with updated OG tags

**Quality Metrics:**
- Summary relevance score (user feedback)
- PDF render success rate (target: >99%)
- Social preview click-through rate

---

## 🚨 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WeasyPrint installation fails on Windows | High | Document GTK3 installation steps, provide Docker alternative |
| PDF generation too slow (>3s) | Medium | Implement background job queue for PDF generation |
| LLM summary quality inconsistent | Medium | Add prompt engineering iteration, collect user feedback |
| Social previews don't update | Low | Clear CDN cache, use versioned OG image URLs |

---

## 📚 References

- WeasyPrint docs: https://doc.courtbouillon.org/weasyprint/
- Next.js OG Image: https://nextjs.org/docs/app/api-reference/functions/image-response
- Open Graph Protocol: https://ogp.me/

---

**Ready to implement tomorrow morning!** 🚀
