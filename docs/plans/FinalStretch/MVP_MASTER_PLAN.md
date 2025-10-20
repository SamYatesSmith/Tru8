# TRU8 MVP LAUNCH - MASTER PLAN

**Project:** Tru8 - Transparent Fact-Checking Platform
**Target Launch Date:** October 28, 2025
**Duration:** 2 weeks (October 17-28, 2025)
**Current Status:** 95% Feature Complete - Ready for Testing & Deployment
**Goal:** Launch production-ready MVP to acquire first 300 paying users

---

## 🎯 EXECUTIVE SUMMARY

Tru8 is a fact-checking platform that provides instant verification with transparent, dated evidence. The MVP is **95% complete** with all core features implemented. The remaining 2 weeks focus on **quality assurance, production deployment, and public launch**.

### What's Already Built (95%)
- ✅ **Marketing Page**: Full single-page site with animated background, carousel, pricing
- ✅ **Authentication**: Clerk integration with full route protection
- ✅ **Dashboard**: 5 complete pages (Home, History, New Check, Check Detail, Settings)
- ✅ **Backend API**: 18 endpoints covering all user/check/payment operations
- ✅ **ML Pipeline**: 5-stage fact-checking pipeline with <10s performance
- ✅ **Payment System**: Full Stripe integration (checkout, webhooks, portal)
- ✅ **Real-time Updates**: SSE progress streaming
- ✅ **Account Management**: Profile, subscriptions, notifications, deletion

### What's Left (5%)
- 🔧 **Testing**: Comprehensive QA of all features (Week 1)
- 🔧 **Deployment**: Production infrastructure setup (Week 2)
- 🔧 **Configuration**: Stripe production setup, DNS, SSL (Week 2)
- 🔧 **Launch**: Public announcement and initial user acquisition (Week 2)

---

## 📅 TWO-WEEK TIMELINE

### **WEEK 1: TESTING & POLISH** (Oct 17-21)
**Focus:** Validate everything works, fix bugs, polish UX

| Day | Focus | Key Tasks |
|-----|-------|-----------|
| **Day 1** | Auth & User Management | Sign-up/sign-in flows, middleware, account deletion |
| **Day 2** | Check Creation & Pipeline | URL/TEXT checks, SSE progress, pipeline performance |
| **Day 3** | Dashboard & History | All dashboard pages, search/filters, empty states |
| **Day 4** | Check Detail & Stripe | Detailed check views, Stripe checkout end-to-end |
| **Day 5** | Mobile & Performance | Responsive testing, Lighthouse audits, accessibility |

**Deliverables:**
- Zero critical bugs
- All user flows tested
- Mobile responsive verified
- Performance targets met (>90 Lighthouse)
- Bug tracker with prioritized issues

---

### **WEEK 2: PRODUCTION DEPLOYMENT** (Oct 22-28)
**Focus:** Deploy to production, configure services, launch publicly

| Day | Focus | Key Tasks |
|-----|-------|-----------|
| **Day 1** | Infrastructure Setup | PostgreSQL, Redis, backend deployment platform |
| **Day 2** | Backend Deployment | Deploy API + workers, configure env vars, health checks |
| **Day 3** | Frontend Deployment | Deploy to Vercel, custom domain, SSL, Clerk config |
| **Day 4** | Stripe Production | Create Professional plan, webhooks, test payments |
| **Day 5** | Production Testing | End-to-end user journeys, load testing, security |
| **Day 6** | Pre-Launch Prep | Legal pages, SEO, analytics, support setup |
| **Day 7** | **🚀 LAUNCH DAY** | Go live, announce publicly, monitor, collect feedback |

**Deliverables:**
- Production infrastructure running
- All services configured and tested
- Legal pages published (Privacy, Terms)
- Public launch completed
- First users acquired

---

## 🏗️ CURRENT ARCHITECTURE

### **Frontend (Next.js 14 + Tailwind)**
```
web/
├── app/
│   ├── page.tsx                    # Marketing page ✅
│   ├── dashboard/
│   │   ├── layout.tsx              # Authenticated layout ✅
│   │   ├── page.tsx                # Dashboard home ✅
│   │   ├── history/page.tsx        # Check history ✅
│   │   ├── new-check/page.tsx      # Create check ✅
│   │   ├── check/[id]/page.tsx     # Check detail ✅
│   │   └── settings/page.tsx       # Settings ✅
│   ├── privacy/page.tsx            # Privacy policy 🔧
│   ├── terms/page.tsx              # Terms of service 🔧
│   └── layout.tsx                  # Root layout ✅
├── components/
│   ├── marketing/                  # Marketing components ✅
│   ├── layout/                     # Navigation, footer ✅
│   └── dashboard/                  # Dashboard components ✅
└── middleware.ts                   # Clerk auth ✅
```

### **Backend (FastAPI + Celery)**
```
backend/
├── app/
│   ├── api/v1/
│   │   ├── checks.py               # Check endpoints ✅
│   │   ├── users.py                # User endpoints ✅
│   │   ├── payments.py             # Stripe endpoints ✅
│   │   └── health.py               # Health checks ✅
│   ├── pipeline/
│   │   ├── ingest.py               # Content ingestion ✅
│   │   ├── extract.py              # Claim extraction ✅
│   │   ├── retrieve.py             # Evidence retrieval ✅
│   │   ├── verify.py               # NLI verification ✅
│   │   └── judge.py                # LLM judgment ✅
│   ├── workers/
│   │   └── pipeline.py             # Celery tasks ✅
│   ├── models/                     # Database models ✅
│   ├── core/                       # Auth, config, DB ✅
│   └── main.py                     # FastAPI app ✅
└── requirements.txt                ✅
```

---

## 📊 FEATURE COMPLETENESS MATRIX

| Feature | Status | Tested | Production Ready |
|---------|--------|--------|------------------|
| **Marketing Page** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Animated background | ✅ | 🔧 | 🔧 |
| - Navigation (desktop) | ✅ | 🔧 | 🔧 |
| - Mobile bottom nav | ✅ | 🔧 | 🔧 |
| - Hero section | ✅ | 🔧 | 🔧 |
| - Feature carousel | ✅ | 🔧 | 🔧 |
| - Pricing cards | ✅ | 🔧 | 🔧 |
| - Footer | ✅ | 🔧 | 🔧 |
| **Authentication** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Sign-up flow | ✅ | 🔧 | 🔧 |
| - Sign-in flow | ✅ | 🔧 | 🔧 |
| - Route protection | ✅ | 🔧 | 🔧 |
| - Session management | ✅ | 🔧 | 🔧 |
| **Dashboard Pages** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Home page | ✅ | 🔧 | 🔧 |
| - History page | ✅ | 🔧 | 🔧 |
| - New check page | ✅ | 🔧 | 🔧 |
| - Check detail page | ✅ | 🔧 | 🔧 |
| - Settings page | ✅ | 🔧 | 🔧 |
| **Check Creation** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - URL input | ✅ | 🔧 | 🔧 |
| - TEXT input | ✅ | 🔧 | 🔧 |
| - Validation | ✅ | 🔧 | 🔧 |
| - Credit deduction | ✅ | 🔧 | 🔧 |
| **Pipeline** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Content ingestion | ✅ | 🔧 | 🔧 |
| - Claim extraction | ✅ | 🔧 | 🔧 |
| - Evidence retrieval | ✅ | 🔧 | 🔧 |
| - NLI verification | ✅ | 🔧 | 🔧 |
| - LLM judgment | ✅ | 🔧 | 🔧 |
| - SSE progress | ✅ | 🔧 | 🔧 |
| **Payment System** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Stripe checkout | ✅ | 🔧 | 🔧 |
| - Webhook handling | ✅ | 🔧 | 🔧 |
| - Subscription mgmt | ✅ | 🔧 | 🔧 |
| - Cancellation | ✅ | 🔧 | 🔧 |
| - Reactivation | ✅ | 🔧 | 🔧 |
| - Billing portal | ✅ | 🔧 | 🔧 |
| **Account Management** | ✅ Complete | 🔧 Week 1 | 🔧 Week 2 |
| - Profile viewing | ✅ | 🔧 | 🔧 |
| - Account deletion | ✅ | 🔧 | 🔧 |
| - Notification prefs | ✅ | 🔧 | 🔧 |

**Legend:**
- ✅ Complete: Feature implemented
- 🔧 Week 1: Testing scheduled
- 🔧 Week 2: Production deployment scheduled

---

## 🎯 SUCCESS METRICS

### **Launch Day Targets (Day 7)**
- **Traffic**: 500+ visitors
- **Sign-ups**: 50+ new users
- **Checks Created**: 20+ checks processed
- **Paid Conversions**: 2+ paying users
- **Uptime**: 99.9%
- **Errors**: <10 critical errors
- **Performance**: >90 Lighthouse score

### **Week 1 Post-Launch Targets**
- **Users**: 100+ total users
- **Checks**: 100+ checks processed
- **Revenue**: £14+ (2+ Professional subscriptions)
- **Retention**: >50% of users create second check
- **NPS**: >40 (if collected)

### **Month 1 Targets**
- **Users**: 300+ total users
- **Paying Users**: 20+ Professional subscriptions
- **Revenue**: £140+/month
- **Checks**: 500+ total checks
- **Uptime**: 99.5%+

---

## 💰 BUSINESS MODEL

### **Pricing**
- **Free Plan**: 3 checks/month, £0
- **Professional Plan**: 40 checks/month, £7/month

### **Revenue Projections**
| Scenario | Users | Paid Users | MRR | ARR |
|----------|-------|------------|-----|-----|
| **Conservative** | 300 | 15 (5%) | £105 | £1,260 |
| **Target** | 300 | 20 (6.67%) | £140 | £1,680 |
| **Optimistic** | 300 | 30 (10%) | £210 | £2,520 |

### **Cost Structure (Monthly)**
- **Infrastructure**: £30-50 (Railway/Fly.io)
- **APIs**: £20-40 (OpenAI, search APIs)
- **Services**: £20 (Clerk, Stripe)
- **Total**: £70-110/month

**Break-even**: 11-16 paying users

---

## 🔧 PRODUCTION TECH STACK

### **Hosting**
- **Backend**: Fly.io or Railway
- **Frontend**: Vercel
- **Database**: Railway PostgreSQL or Supabase
- **Redis**: Upstash or Railway Redis
- **CDN**: Vercel Edge Network

### **Services**
- **Authentication**: Clerk (Production instance)
- **Payments**: Stripe (Live mode)
- **Error Tracking**: Sentry
- **Analytics**: Vercel Analytics + PostHog
- **Uptime Monitoring**: UptimeRobot

### **APIs**
- **LLM**: OpenAI (gpt-4o-mini) + Anthropic (Claude fallback)
- **Search**: Brave Search API
- **NLI Model**: DeBERTa v3 (self-hosted)
- **OCR**: Tesseract (self-hosted)

---

## 🚨 KNOWN GAPS & DECISIONS

### **Minor Gaps (Non-Blocking)**

1. **SSE Token Endpoint** (`POST /api/v1/checks/{id}/sse-token`)
   - **Status**: Not implemented
   - **Impact**: SSE works but uses direct auth token (less secure)
   - **Priority**: Medium (security hardening)
   - **Decision**: Ship without, add in Week 3

2. **Invoice History** (`GET /api/v1/payments/invoices`)
   - **Status**: Not implemented
   - **Impact**: Settings page doesn't show billing history
   - **Priority**: Low (nice-to-have)
   - **Decision**: Ship without, add post-launch

3. **S3 Storage**
   - **Status**: Using local file storage
   - **Impact**: Image uploads work but files stored locally
   - **Priority**: Low (can migrate post-launch)
   - **Decision**: Ship with local storage, migrate to S3 in Month 2

### **MVP Scope Decisions**
- **✅ Include**: URL checks, TEXT checks, SSE progress, Stripe payments
- **❌ Exclude**: IMAGE checks, VIDEO checks, Deep Mode, Light theme
- **📅 Post-Launch**: Mobile app, API access, team plans, browser extension

---

## 📋 CRITICAL PATH CHECKLIST

### **Pre-Launch (Week 1-2)**
- [ ] All Week 1 testing completed
- [ ] All P0 bugs fixed
- [ ] All P1 bugs fixed
- [ ] Backend deployed to production
- [ ] Frontend deployed to production
- [ ] Database configured with backups
- [ ] Stripe production configured
- [ ] Webhooks configured and tested
- [ ] Legal pages published
- [ ] Monitoring configured
- [ ] Support email configured
- [ ] Analytics configured

### **Launch Day (Day 7)**
- [ ] Final smoke test passed
- [ ] Beta testers given access
- [ ] Launch announcement prepared
- [ ] Monitoring dashboards open
- [ ] Support email monitored
- [ ] Social media posts scheduled

### **Post-Launch (Week 3+)**
- [ ] All launch day issues resolved
- [ ] User feedback collected
- [ ] Metrics tracked and analyzed
- [ ] Roadmap prioritized based on feedback
- [ ] Growth experiments planned

---

## 🎓 DOCUMENTATION INDEX

### **Planning Documents**
1. **[MVP_MASTER_PLAN.md](./MVP_MASTER_PLAN.md)** (This Document)
   - Executive summary
   - Timeline overview
   - Success metrics
   - Architecture overview

2. **[MVP_WEEK1_TESTING_POLISH.md](./MVP_WEEK1_TESTING_POLISH.md)**
   - Day-by-day testing plan
   - Test scenarios and checklists
   - Bug tracking templates
   - Quality assurance procedures

3. **[MVP_WEEK2_PRODUCTION_DEPLOYMENT.md](./MVP_WEEK2_PRODUCTION_DEPLOYMENT.md)**
   - Infrastructure setup
   - Deployment procedures
   - Stripe configuration
   - Launch day plan

### **Implementation Documents**
4. **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)**
   - Complete dashboard implementation summary
   - All 6 implementation plans
   - Component specifications

5. **[BACKEND_ENDPOINTS_REQUIRED.md](./BACKEND_ENDPOINTS_REQUIRED.md)**
   - Complete API endpoint documentation
   - Request/response schemas
   - Implementation status

### **Technical Documentation**
6. **[DESIGN_SYSTEM.md](../DESIGN_SYSTEM.md)**
   - Color palette
   - Typography scale
   - Component specifications
   - 4pt grid system

7. **[frontend-backend-integration.md](../integration/frontend-backend-integration.md)**
   - API client implementation
   - Authentication patterns
   - Error handling

8. **[backend-integration-guide.md](../integration/backend-integration-guide.md)**
   - Backend setup instructions
   - Environment variables
   - Database configuration

---

## 🚀 QUICK START GUIDE

### **For Development**
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure environment variables
alembic upgrade head
uvicorn app.main:app --reload

# In separate terminal - Celery worker
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# Frontend
cd web
npm install
cp .env.example .env.local  # Configure environment variables
npm run dev
```

### **For Testing (Week 1)**
```bash
# Follow MVP_WEEK1_TESTING_POLISH.md
# Day 1: Authentication testing
# Day 2: Check creation testing
# Day 3: Dashboard testing
# Day 4: Stripe testing
# Day 5: Mobile & performance testing
```

### **For Deployment (Week 2)**
```bash
# Follow MVP_WEEK2_PRODUCTION_DEPLOYMENT.md
# Day 1: Infrastructure setup
# Day 2: Backend deployment
# Day 3: Frontend deployment
# Day 4: Stripe production setup
# Day 5: Production testing
# Day 6: Pre-launch prep
# Day 7: Launch!
```

---

## 📞 SUPPORT & CONTACT

### **During Launch**
- **Primary Contact**: [Your Email]
- **Support Email**: support@tru8.com (set up on Day 6)
- **Emergency Contact**: [Your Phone] (for P0 issues only)

### **Monitoring Links** (set up during Week 2)
- **Uptime**: https://uptimerobot.com/dashboard
- **Errors**: https://sentry.io/organizations/[org]/issues/
- **Analytics**: https://vercel.com/[username]/tru8/analytics
- **Stripe**: https://dashboard.stripe.com/dashboard

---

## 🎉 LAUNCH ANNOUNCEMENT TEMPLATES

### **Twitter/X**
```
🚀 Introducing Tru8 - Transparent Fact-Checking with Dated Evidence

Get instant verification of claims with sourced, dated evidence.
Built for journalists, researchers, and anyone who demands accuracy.

✅ Multi-source verification
✅ Dated evidence
✅ AI-powered analysis
✅ Free to start

Try it: https://tru8.com
```

### **LinkedIn**
```
Excited to launch Tru8 - a new fact-checking platform built for transparency.

The Problem: Misinformation spreads faster than verification.

The Solution: Instant fact verification with transparent, dated evidence.

Built with: FastAPI, Next.js, OpenAI, DeBERTa NLI
Pricing: Free (3 checks) | £7/month (40 checks)

Try it: https://tru8.com
```

### **Hacker News (Show HN)**
```
Show HN: Tru8 - Transparent fact-checking with AI and dated evidence

Hi HN! I built Tru8 to verify claims quickly with transparent, dated evidence.

Tech stack: FastAPI, Next.js, OpenAI, DeBERTa NLI, PostgreSQL, Celery
Pricing: Free tier (3 checks) | £7/month (40 checks)

I'd love your feedback!

Try it: https://tru8.com
```

---

## ✅ FINAL PRE-LAUNCH CHECKLIST

### **Week 1 Complete**
- [ ] All 5 days of testing completed
- [ ] Bug tracker populated
- [ ] All P0 bugs fixed
- [ ] All P1 bugs fixed
- [ ] Performance targets met
- [ ] Accessibility audit passed
- [ ] Mobile testing completed

### **Week 2 Infrastructure**
- [ ] Database deployed and backed up
- [ ] Redis deployed
- [ ] Backend API deployed
- [ ] Celery workers deployed
- [ ] Frontend deployed
- [ ] Domain configured
- [ ] SSL certificates active

### **Week 2 Services**
- [ ] Clerk production configured
- [ ] Stripe production configured
- [ ] Stripe webhooks tested
- [ ] Monitoring active (Sentry, UptimeRobot)
- [ ] Analytics active

### **Week 2 Legal & Marketing**
- [ ] Privacy Policy published
- [ ] Terms of Service published
- [ ] Cookie Policy published
- [ ] Launch announcements prepared
- [ ] Support email active

### **Launch Day**
- [ ] Final smoke test passed
- [ ] Monitoring dashboards open
- [ ] Launch announcements posted
- [ ] First users acquired
- [ ] Metrics tracking started

---

## 🎯 POST-LAUNCH PRIORITIES

### **Week 3: Stabilize**
1. Fix all launch day issues
2. Respond to user feedback
3. Optimize performance based on real usage
4. Improve onboarding flow

### **Month 1: Optimize**
1. Implement most-requested features
2. Improve conversion rate (free → paid)
3. Add email notifications
4. Implement SSE token endpoint

### **Month 2-3: Grow**
1. Add IMAGE and VIDEO support
2. Implement Deep Mode
3. Launch referral program
4. Add team plans
5. Mobile app

### **Month 4-6: Scale**
1. Browser extension
2. API for developers
3. Enterprise features
4. Classroom packs
5. White-label solution

---

## 📊 METRICS DASHBOARD

Track these metrics weekly:

| Metric | Week 1 | Week 2 | Week 3 | Week 4 | Target |
|--------|--------|--------|--------|--------|--------|
| **Acquisition** |
| Total Users | ___ | ___ | ___ | ___ | 300 |
| New Sign-ups | ___ | ___ | ___ | ___ | 75/week |
| Traffic (visits) | ___ | ___ | ___ | ___ | 1000/week |
| **Activation** |
| Users who created check | ___ | ___ | ___ | ___ | 70% |
| Avg checks per user | ___ | ___ | ___ | ___ | 2.5 |
| **Revenue** |
| Paid Users | ___ | ___ | ___ | ___ | 20 |
| MRR | £___ | £___ | £___ | £___ | £140 |
| Conversion Rate (%) | ___% | ___% | ___% | ___% | 6.67% |
| **Engagement** |
| DAU | ___ | ___ | ___ | ___ | 50 |
| WAU | ___ | ___ | ___ | ___ | 150 |
| Checks per week | ___ | ___ | ___ | ___ | 200 |
| **Quality** |
| Uptime (%) | ___% | ___% | ___% | ___% | 99.5% |
| P0 Bugs | ___ | ___ | ___ | ___ | 0 |
| Avg check time (s) | ___ | ___ | ___ | ___ | <10s |
| Support tickets | ___ | ___ | ___ | ___ | <10/week |

---

## 🏁 CONCLUSION

Tru8 is **95% complete** and ready for final testing and deployment. With 2 weeks of focused effort on quality assurance and production setup, we'll have a polished, production-ready MVP.

**The path to launch:**
- Week 1: Test everything thoroughly, fix bugs, polish UX
- Week 2: Deploy to production, configure services, launch publicly

**We're ready. Let's ship! 🚀**

---

**Status:** READY TO BEGIN WEEK 1 TESTING
**Next Step:** Start Day 1 of [MVP_WEEK1_TESTING_POLISH.md](./MVP_WEEK1_TESTING_POLISH.md)
**Target Launch:** October 28, 2025
