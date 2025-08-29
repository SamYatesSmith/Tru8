# Tru8 - Fact-Checking Platform Configuration

## 🎯 Project Context
**Project:** Tru8 - Instant fact-checking with dated evidence  
**Goal:** MVP launch in 6-8 weeks → 300 users → £1,500/month  
**Architecture:** Mobile (React Native) + Web (Next.js) + API (FastAPI) + ML Pipeline

## 🚀 Quick Commands

### Backend (FastAPI)
```bash
cd backend
uvicorn main:app --reload          # Start API server
celery -A tasks worker --loglevel=info  # Start worker
pytest tests/ -v                    # Run tests
alembic upgrade head                # Run migrations
```

### Web (Next.js)
```bash
cd web
npm run dev                         # Start dev server
npm run build && npm run start      # Production build
npm run lint && npm run typecheck   # Validate code
```

### Mobile (React Native/Expo)
```bash
cd mobile
npx expo start                      # Start Expo
npx expo run:ios                    # iOS simulator
npx expo run:android                # Android emulator
eas build --platform all            # Build for stores
```

## 📁 Project Structure
```
/
├── backend/                # FastAPI + ML Pipeline
│   ├── api/               # Endpoints
│   ├── pipeline/          # Verification pipeline
│   │   ├── ingest/       # URL/OCR/transcript
│   │   ├── extract/      # Claim extraction
│   │   ├── retrieve/     # Evidence search
│   │   ├── verify/       # NLI verification
│   │   └── judge/        # LLM judgment
│   ├── models/           # SQLModel schemas
│   ├── workers/          # Celery tasks
│   └── ml/              # ONNX models
├── web/                  # Next.js frontend
│   ├── app/             # App Router pages
│   ├── components/      # React components
│   └── lib/            # Utils & hooks
├── mobile/              # React Native app
│   ├── app/            # Expo Router
│   ├── components/     # Native components
│   └── services/       # API client
└── shared/             # Shared types/utils
```

## 🎨 Design System Implementation

**CRITICAL: ALL frontend development MUST follow the comprehensive design system in DESIGN_SYSTEM.md**

### Key Design Principles
- **4pt Grid System**: All spacing uses multiples of 4px (`var(--space-*)`)
- **Centralized Content**: All content uses container classes, max-width 1024px
- **Bold Professional**: High contrast, strong typography, authoritative colors
- **Consistent Components**: Standardized buttons, cards, pills, bars

### Colors (CSS Variables Only)
```css
/* Brand Colors - Professional Authority */
--tru8-primary: #1E40AF;        /* Deep Blue */
--gradient-primary: linear-gradient(135deg, #1E40AF 0%, #7C3AED 100%);
--gradient-hero: linear-gradient(135deg, #1E40AF 0%, #7C3AED 50%, #EC4899 100%);

/* Verdict System - High Contrast */
--verdict-supported: #059669;     /* Emerald */  
--verdict-contradicted: #DC2626;  /* Red */
--verdict-uncertain: #D97706;     /* Amber */
```

### Typography Scale (Responsive)
```css
--text-5xl: clamp(2.5rem, 5vw, 3rem);    /* Hero headlines */
--text-4xl: clamp(2rem, 4vw, 2.25rem);   /* Page titles */
--font-weight-black: 900;                 /* Stand-out headings */
```

### MANDATORY Component Usage
1. **Verdict Pills** - Semantic color system with borders
2. **Confidence Bars** - Animated with gradient fills  
3. **Citation Chips** - `Publisher · Date · Credibility`
4. **Card System** - Standard shadows and spacing
5. **Button Hierarchy** - Primary gradients, secondary borders

### Layout Requirements
- All pages use `.container` (max-width: 1024px, centered)
- All spacing uses 4pt grid (`--space-4`, `--space-6`, etc.)
- All borders use consistent radius (`--radius-md`, `--radius-lg`)
- Mobile-first responsive with defined breakpoints

## 🔧 Development Guidelines

### API Development (FastAPI)
- Use Pydantic models for validation
- Implement dependency injection
- Add OpenAPI documentation
- Use async/await for I/O operations
- Handle errors with HTTPException

### Pipeline Development
- Each stage must be idempotent
- Log with structured logging
- Implement circuit breakers
- Cache expensive operations
- Monitor token usage

### Frontend Development
- Mobile-first responsive design
- Implement skeleton loading
- Use React Query for caching
- Optimize bundle size
- Ensure WCAG AA compliance

### Testing Strategy
```bash
# Backend
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/pipeline/      # Pipeline tests

# Frontend
npm run test:unit          # Component tests
npm run test:e2e           # Playwright tests
```

## 🚨 Critical Paths to Validate

### 1. Verification Pipeline
- Claim extraction accuracy
- Evidence retrieval relevance
- NLI model performance
- Judge prompt effectiveness
- End-to-end latency (<10s)

### 2. Payment Integration
- RevenueCat entitlements sync
- Stripe webhook handling
- Credit reservation/finalisation
- Usage tracking accuracy

### 3. Cross-Platform Auth
- Clerk token validation
- Session management
- Rate limiting enforcement

## 📊 Performance Targets
- **Pipeline latency:** <10s for Quick mode
- **API response:** <200ms p95
- **Web Core Vitals:** LCP <2.5s, FID <100ms
- **Mobile app size:** <50MB
- **Token cost:** <$0.02 per check

## 🔐 Security Checklist
- [ ] Sanitize all HTML inputs (bleach)
- [ ] Validate claim extraction JSON
- [ ] Rate limit by user & IP
- [ ] Implement prompt injection guards
- [ ] Respect robots.txt
- [ ] GDPR compliance endpoints
- [ ] Secure blob storage (signed URLs)

## 🚀 Week-by-Week Focus

### Current Week Tasks
- [ ] Set up FastAPI skeleton
- [ ] Configure Postgres + migrations
- [ ] Implement Clerk auth
- [ ] Set up Redis/Celery
- [ ] Create basic UI shells

### Pipeline Priorities
1. **Ingest** - URL fetch, OCR, transcripts
2. **Extract** - LLM claim extraction
3. **Retrieve** - Search + embedding
4. **Verify** - NLI + aggregation
5. **Judge** - Final verdict generation

## 💡 Development Tips

### For ML Components
- Use ONNX for production inference
- Batch operations where possible
- Monitor GPU/CPU usage
- Implement fallback models
- Log confidence distributions

### For Real-time Updates
- Use SSE for progress updates
- Implement exponential backoff
- Handle connection drops
- Cache partial results

### For Mobile Development
- Use Expo EAS for builds
- Test on real devices early
- Optimize image loading
- Handle offline scenarios

## 🎯 MVP Feature Flags
```typescript
const features = {
  deepMode: false,         // Hidden initially
  reverseImageSearch: false,
  longVideoSupport: false,
  lightTheme: false,
  localPrivacyMode: false
}
```

## 📈 Monitoring & Analytics
- **User events:** PostHog
- **Errors:** Sentry
- **API metrics:** Prometheus
- **Costs:** Token usage dashboard
- **Revenue:** RevenueCat/Stripe dashboards

## 🔄 CI/CD Commands
```bash
# Pre-commit checks
black backend/ --check
isort backend/ --check
mypy backend/
npm run lint
npm run typecheck

# Deployment
fly deploy                 # Backend
vercel --prod             # Web
eas build --auto-submit   # Mobile
```

---
*Optimized for Tru8 MVP development - 6-8 week sprint to launch*