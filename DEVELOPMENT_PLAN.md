# Tru8 MVP Development Plan - Parallel Track Approach

## 🎯 Strategy: 3 Parallel Tracks + Integration Phase

**Timeline:** 6 weeks active development + 2 weeks buffer  
**Approach:** Backend-first with parallel UI development, early integration points

---

## Phase 0: Foundation (Day 1-2) ✅ START HERE

### All Tracks Together
```bash
# Project setup
mkdir -p backend web mobile shared
git init
```

1. **Backend Foundation**
   - [ ] FastAPI project structure
   - [ ] Docker Compose (Postgres, Redis, Qdrant)
   - [ ] SQLModel schemas
   - [ ] Alembic migrations setup
   - [ ] Environment config (.env)

2. **Web Foundation**
   - [ ] Next.js 14 App Router
   - [ ] Tailwind + Radix UI
   - [ ] Clerk auth setup
   - [ ] TypeScript config

3. **Mobile Foundation**
   - [ ] Expo project init
   - [ ] Tamagui/NativeWind setup
   - [ ] Expo Router config
   - [ ] Development builds

4. **Shared Foundation**
   - [ ] TypeScript types
   - [ ] API client interface
   - [ ] Constants (colors, limits)

---

## Track A: Backend Pipeline (Weeks 1-4) ✅ COMPLETED

### Week 1: Core Infrastructure ✅
**Goal:** Working API with auth and basic pipeline structure

- [x] FastAPI endpoints structure
- [x] Clerk JWT validation
- [x] User model + credits system
- [x] Celery + Redis setup
- [x] Basic `/checks` endpoint (mock)
- [x] Postgres migrations
- [x] **Integration Point:** API docs for frontend team

### Week 2: Ingest & Extract ✅
**Goal:** Can process URLs, images, videos → extract claims

- [x] URL fetcher (trafilatura)
- [x] OCR setup (Tesseract)
- [x] YouTube transcript API
- [x] Claim extraction (LLM integration)
- [x] Input sanitization (bleach)
- [x] **Integration Point:** `/checks/create` working

### Week 3: Retrieve & Verify ✅
**Goal:** Evidence retrieval and NLI verification working

- [x] Search API integration (Brave/Serp)
- [x] Evidence extraction
- [x] Embeddings (Sentence-Transformers)
- [x] Qdrant vector store
- [x] NLI model (DeBERTa ONNX)
- [x] Confidence calibration
- [x] **Integration Point:** Real verdicts returning

### Week 4: Judge & Optimize ✅
**Goal:** Complete pipeline under 10s

- [x] Judge LLM prompts
- [x] Result aggregation
- [x] Caching layer
- [x] Performance optimization
- [x] Error recovery
- [x] SSE progress updates
- [x] **Integration Point:** Full pipeline E2E

---

## Track B: Web Frontend (Weeks 1-4)

### Week 1: Auth & Layout
- [ ] Clerk integration
- [ ] Layout components
- [ ] Design system setup
- [ ] Home/Dashboard pages
- [ ] Mock data setup

### Week 2: Check Creation Flow
- [ ] URL input component
- [ ] File upload (image/video)
- [ ] Progress stepper UI
- [ ] Mock API integration
- [ ] Loading states

### Week 3: Results Display
- [ ] Claim cards component
- [ ] Verdict pills
- [ ] Confidence display
- [ ] Citation chips
- [ ] Evidence drawer
- [ ] Share functionality

### Week 4: Account & Payments
- [ ] Usage dashboard
- [ ] Credits display
- [ ] Stripe Checkout
- [ ] Subscription management
- [ ] Settings page

---

## Track C: Mobile App (Weeks 1-4)

### Week 1: Core Setup
- [ ] Expo Router navigation
- [ ] Clerk mobile auth
- [ ] Design system port
- [ ] Basic screens

### Week 2: Check Creation
- [ ] Camera integration
- [ ] File picker
- [ ] URL share extension
- [ ] Progress UI

### Week 3: Results & History
- [ ] Results screen
- [ ] History list
- [ ] Push notifications
- [ ] Share sheet

### Week 4: IAP & Polish
- [ ] RevenueCat setup
- [ ] Subscription UI
- [ ] Settings screen
- [ ] Offline handling

---

## Phase 2: Integration & Hardening (Weeks 5-6)

### Week 5: Full Integration
**All tracks converge**

- [ ] End-to-end testing
- [ ] Payment flow verification
- [ ] Credit system testing
- [ ] Cross-platform auth sync
- [ ] Performance optimization
- [ ] Error state handling
- [ ] GDPR compliance

### Week 6: Production Ready
**Polish and deployment prep**

- [ ] Security audit
- [ ] Rate limiting
- [ ] Monitoring setup (Sentry, PostHog)
- [ ] Load testing
- [ ] Documentation
- [ ] TestFlight/Play Console setup
- [ ] Production configs

---

## Phase 3: Buffer & Launch (Weeks 7-8)

### Week 7: Beta Testing
- [ ] Internal testing
- [ ] Fix critical bugs
- [ ] Performance tuning
- [ ] Token cost optimization
- [ ] Final UI polish

### Week 8: Launch Prep
- [ ] App store listings
- [ ] Marketing materials
- [ ] Terms & Privacy
- [ ] Support documentation
- [ ] Launch monitoring

---

## 📊 Success Metrics per Phase

### Phase 0-1 Success: ✅ ACHIEVED
- [x] API returns mock data
- [x] All 3 apps authenticate  
- [x] Docker services running

### Track A Success: ✅ ACHIEVED
- [x] Pipeline < 10s latency
- [x] Claims extracted accurately
- [x] Full E2E pipeline working
- [x] NLI verification implemented
- [x] Vector search operational
- [x] LLM judge integration complete

### Phase 2 Success: (Web/Mobile Integration)
- [ ] UI displays results
- [ ] Cross-platform auth working

### Phase 3 Success:
- Payments working E2E
- <2% error rate
- Passes security audit

---

## 🚀 Daily Standup Structure

```markdown
### Track A (Backend)
- Yesterday: [completed]
- Today: [focus]
- Blockers: [issues]

### Track B (Web)
- Yesterday: [completed]
- Today: [focus]
- Blockers: [issues]

### Track C (Mobile)
- Yesterday: [completed]
- Today: [focus]
- Blockers: [issues]

### Integration Points
- Ready: [what's ready to integrate]
- Needed: [what's blocking others]
```

---

## 🔥 Quick Start Commands

```bash
# Start everything
docker-compose up -d
cd backend && uvicorn main:app --reload &
cd web && npm run dev &
cd mobile && npx expo start

# Run tests
./scripts/test-all.sh

# Check pipeline
curl -X POST localhost:8000/checks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url": "https://example.com/article"}'
```

---

## ⚡ Efficiency Tips

1. **Parallel Development**: Backend team provides OpenAPI specs early
2. **Mock First**: Frontend uses MSW for API mocking
3. **Shared Types**: Single source of truth in `/shared`
4. **Daily Integration**: Merge to main daily, feature flags for WIP
5. **Automated Testing**: CI runs on every push

---

## 🎯 Week 1 Immediate Actions

**Today (Day 1):**
1. Set up project structure
2. Initialize all three codebases
3. Configure Docker Compose
4. Set up CI/CD pipeline

**Tomorrow (Day 2):**
1. Backend: FastAPI + first endpoint
2. Web: Next.js + Clerk auth
3. Mobile: Expo + navigation
4. Shared: Type definitions

**By End of Week 1:**
- Working auth across all platforms
- Mock API returning fake checks
- Basic UI showing mock data
- Pipeline structure defined

---

*This plan optimizes for parallel development while ensuring integration points don't block progress.*