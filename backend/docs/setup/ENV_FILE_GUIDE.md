# Environment File Patterns - Tru8

**Purpose:** Document environment file naming conventions and patterns across the project
**Status:** Active documentation
**Last Updated:** October 16, 2025

---

## 📁 ENVIRONMENT FILE STRUCTURE

### **Backend (FastAPI)**

**Location:** `backend/.env`

**Pattern:** Single `.env` file in backend directory

**Contains:**
- Database credentials (`DATABASE_URL`)
- Redis configuration (`REDIS_URL`)
- Clerk authentication (`CLERK_SECRET_KEY`, `CLERK_JWT_ISSUER`)
- Stripe keys (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`)
- OpenAI API key (`OPENAI_API_KEY`)
- Environment flag (`DEBUG=true/false`)

**Example file:** `backend/.env.example`

---

### **Frontend (Next.js)**

**Location:** `web/.env` or `web/.env.local`

**Pattern:** Next.js convention
- `web/.env` - Shared/default values (can be committed with dummy values)
- `web/.env.local` - Local overrides (gitignored, developer-specific)
- `web/.env.production` - Production values (deployment only)

**Contains:**
- Public keys (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
- API URL (`NEXT_PUBLIC_API_URL`)
- Environment identifiers (`NEXT_PUBLIC_ENV`)

**Note:** Next.js only exposes variables prefixed with `NEXT_PUBLIC_` to the browser

---

## 🔐 GITIGNORE CONFIGURATION

**Current patterns in `.gitignore`:**

```gitignore
.env
.env.local
.env.production
.env*.local
*.env
```

**What's protected:**
- ✅ All `.env` files
- ✅ All `.env.local` files
- ✅ All `.env.production` files
- ✅ All `.env*.local` patterns (e.g., `.env.development.local`)
- ✅ Any file ending with `.env`

**What's safe to commit:**
- ✅ `.env.example` files (template with dummy values)
- ✅ Documentation referencing environment variables

---

## 📝 STANDARD PATTERNS

### **Backend Environment Variables**

**File:** `backend/.env`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tru8

# Redis
REDIS_URL=redis://localhost:6379/0

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_JWT_ISSUER=your-tenant.clerk.accounts.dev

# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PROFESSIONAL_PRICE_ID=price_xxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxx

# Environment
DEBUG=true
ENVIRONMENT=development
```

**Note:** Backend uses synchronous `.env` file loading via `python-dotenv`

---

### **Frontend Environment Variables**

**File:** `web/.env` or `web/.env.local`

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk (Public keys safe to expose)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# Environment Identifier
NEXT_PUBLIC_ENV=development
```

**Note:** Frontend uses Next.js built-in environment variable support

---

## 🚀 DEPLOYMENT PATTERNS

### **Development (Local)**

**Backend:**
- Uses `backend/.env`
- Loaded via `python-dotenv` in `backend/app/core/config.py`

**Frontend:**
- Uses `web/.env.local` (overrides `web/.env`)
- Loaded automatically by Next.js

---

### **Staging/Production (Fly.io/Vercel)**

**Backend (Fly.io):**
- Environment variables set via `fly secrets set`
- Does not use `.env` files in production
- Secrets stored in Fly.io dashboard

**Frontend (Vercel):**
- Environment variables set in Vercel dashboard
- Separate values for Preview vs Production
- Does not use `.env` files in deployment

---

## ✅ EXAMPLE FILES

### **Backend Example File**

**File:** `backend/.env.example`

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tru8

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Clerk Authentication (Get from https://dashboard.clerk.com)
CLERK_SECRET_KEY=sk_test_YOUR_KEY_HERE
CLERK_JWT_ISSUER=your-tenant.clerk.accounts.dev

# Stripe (Get from https://dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
STRIPE_PROFESSIONAL_PRICE_ID=price_YOUR_PRICE_ID_HERE

# OpenAI (Get from https://platform.openai.com)
OPENAI_API_KEY=sk-YOUR_KEY_HERE

# Environment
DEBUG=true
ENVIRONMENT=development
```

---

### **Frontend Example File**

**File:** `web/.env.example` (to be created)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk Configuration (Get from https://dashboard.clerk.com)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE

# Environment
NEXT_PUBLIC_ENV=development
```

---

## 🔍 TROUBLESHOOTING

### **Backend can't find environment variables**

**Check:**
1. Does `backend/.env` exist?
2. Is it in the correct location? (root of `backend/` directory)
3. Are variables correctly formatted? (`KEY=value` with no spaces around `=`)
4. Restart backend after changes

---

### **Frontend can't find environment variables**

**Check:**
1. Do variables start with `NEXT_PUBLIC_`?
2. Is `web/.env.local` in the correct location? (root of `web/` directory)
3. Did you restart Next.js dev server after adding variables?
4. Variables added after build require rebuild (`npm run build`)

---

### **Variables work locally but not in production**

**Check:**
1. Backend: Are secrets set via `fly secrets list`?
2. Frontend: Are variables set in Vercel dashboard?
3. Are production values different from development?
4. Did you redeploy after setting variables?

---

## 🔐 SECURITY BEST PRACTICES

### **✅ DO:**

- Use `.env.example` files with dummy values as templates
- Commit `.env.example` files to git
- Document all required environment variables
- Use different values for development vs production
- Rotate secrets regularly (especially after public leaks)
- Use strong, randomly generated secrets

### **❌ DON'T:**

- Commit actual `.env` files with real secrets
- Share `.env` files via email, Slack, or Discord
- Use production secrets in development
- Hardcode secrets in source code
- Use weak or predictable secrets (e.g., "password123")
- Commit files containing API keys or tokens

---

## 📋 CHECKLIST FOR NEW DEVELOPERS

**Setting up local development:**

- [ ] Copy `backend/.env.example` to `backend/.env`
- [ ] Fill in Clerk keys (get from Clerk dashboard)
- [ ] Fill in Stripe keys (get from Stripe dashboard)
- [ ] Fill in OpenAI API key (get from OpenAI)
- [ ] Set `DATABASE_URL` to local PostgreSQL instance
- [ ] Set `REDIS_URL` to local Redis instance
- [ ] Copy `web/.env.example` to `web/.env.local` (if exists)
- [ ] Fill in `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [ ] Set `NEXT_PUBLIC_API_URL` to `http://localhost:8000`
- [ ] Verify backend starts: `cd backend && uvicorn app.main:app --reload`
- [ ] Verify frontend starts: `cd web && npm run dev`

---

## 🔄 ENVIRONMENT VARIABLE SYNC

**When to update `.env.example` files:**

- ✅ When adding new required environment variables
- ✅ When removing environment variables
- ✅ When changing variable names
- ✅ When adding comments/documentation

**Keep in sync:**
- `backend/.env.example` should match keys in `backend/.env`
- Documentation should list all required variables
- Deployment configs should include all required variables

---

## 📊 CURRENT STATUS

| File | Exists | Purpose | Gitignored |
|------|--------|---------|------------|
| `backend/.env` | ✅ Yes | Development secrets | ✅ Yes |
| `backend/.env.example` | ✅ Yes | Template with dummy values | ❌ No (committed) |
| `web/.env` | ✅ Yes | Frontend configuration | ✅ Yes |
| `web/.env.local` | ❌ Missing | Local overrides | ✅ Yes (if created) |
| `web/.env.example` | ❌ TODO | Template with dummy values | ❌ No (to be committed) |

---

## 🎯 RECOMMENDATIONS

### **Immediate (Before MVP Launch):**

1. ✅ Verify all secrets in production environments
2. ✅ Test deployment with production environment variables
3. ⚠️ Create `web/.env.example` file (currently missing)
4. ⚠️ Document all required variables in setup guide

### **Post-Launch:**

1. Rotate all secrets after public launch
2. Set up secret rotation schedule (every 90 days)
3. Implement environment variable validation on startup
4. Add health check that verifies critical secrets are set

---

## 📞 WHERE TO GET SECRETS

### **Clerk (Authentication)**
- Dashboard: https://dashboard.clerk.com
- Get `CLERK_SECRET_KEY` and `CLERK_JWT_ISSUER` from API Keys section
- Get `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from API Keys section

### **Stripe (Payments)**
- Dashboard: https://dashboard.stripe.com
- Get `STRIPE_SECRET_KEY` from Developers → API Keys
- Get `STRIPE_WEBHOOK_SECRET` from Developers → Webhooks
- Get `STRIPE_PROFESSIONAL_PRICE_ID` from Products → Professional Plan → Pricing

### **OpenAI (LLM)**
- Dashboard: https://platform.openai.com
- Get `OPENAI_API_KEY` from API Keys section
- Use organization key if part of team

---

**Maintained By:** Tru8 Development Team
**Review Frequency:** After adding/removing environment variables
**Questions:** Check with team lead before committing any `.env` files
