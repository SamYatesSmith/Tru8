# Tru8 Integration Testing Guide

**Date:** October 14, 2025
**Goal:** Test all components working together
**Estimated Time:** 30-45 minutes

---

## 🚀 Part 1: Start the Stack (5 minutes)

### **Step 1: Start Infrastructure Services**

Open a terminal and run:

```bash
docker-compose up -d postgres redis qdrant
```

**Wait for services to start** (~30 seconds)

Verify they're running:
```bash
docker ps
```

You should see 3 containers:
- `tru8-postgres-1` (port 5433)
- `tru8-redis-1` (port 6379)
- `tru8-qdrant-1` (port 6333)

---

### **Step 2: Start Backend (FastAPI + Celery)**

Open a **NEW terminal window**:

```bash
cd backend
.\start-backend.bat
```

**Expected Output:**
```
✓ Redis is running
✓ Starting Celery worker...
✓ Starting FastAPI server...
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Verify Backend is Running:**
- Open browser: http://localhost:8000/api/docs
- You should see Swagger API documentation

**Leave this terminal open!**

---

### **Step 3: Start Frontend (Next.js)**

Open a **NEW terminal window** (3rd terminal):

```bash
cd web
npm run dev
```

**Expected Output:**
```
- Local:        http://localhost:3000
- Network:      http://192.168.x.x:3000
✓ Ready in 2.3s
```

**Verify Frontend is Running:**
- Open browser: http://localhost:3000
- You should see the Tru8 homepage

**Leave this terminal open!**

---

## ✅ Checkpoint 1: All Services Running

You should now have:
- ✅ 3 Docker containers (postgres, redis, qdrant)
- ✅ Backend running (http://localhost:8000)
- ✅ Frontend running (http://localhost:3000)
- ✅ 3 terminal windows open

**If any service fails to start, STOP HERE and troubleshoot before continuing.**

---

## 🧪 Part 2: Test Authentication Flow (5 minutes)

### **Test 1: Sign Up / Sign In**

1. Go to http://localhost:3000
2. Click **"Get Started"** or **"Sign In"** button
3. Clerk modal should appear
4. Sign in with existing account OR create new account
5. After signing in, you should be redirected to **/dashboard**

**Expected Result:**
- ✅ Dashboard loads successfully
- ✅ Shows your name/email in navbar
- ✅ Shows "3 checks remaining" (for free tier)
- ✅ Shows welcome message and stats

**Troubleshooting:**
- If modal doesn't open: Check browser console for errors
- If redirect fails: Check that `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard` in web/.env
- If dashboard is blank: Check that temporary mock data is still active (see TEMPORARY_CHANGES_AND_TODO.md)

---

## 💳 Part 3: Test Stripe Integration (10 minutes)

### **Test 2: Subscription Upgrade Flow**

1. From dashboard, click **"Settings"** in navbar
2. Click **"SUBSCRIPTION"** tab
3. You should see:
   - Current Plan: **Free**
   - Usage: **0 / 3 checks**
   - Two pricing cards (Free £0, Professional £7)

4. Click **"Upgrade to Professional"** button

**Expected Result:**
- ✅ Redirects to Stripe Checkout page
- ✅ Shows "Tru8 Professional" product
- ✅ Shows £7.00/month price
- ✅ Shows payment form

**🎉 SUCCESS:** If you see the Stripe checkout page, Stripe integration is working!

**Important:**
- **DO NOT complete the payment** unless you want to test the full flow
- Click **"Back to Tru8"** or close the tab to return
- We're just testing that the redirect works

**Troubleshooting:**
- **Error: "Failed to start upgrade process"**
  - Check `STRIPE_SECRET_KEY` is set in backend/.env
  - Check backend logs for Stripe errors
  - Verify `NEXT_PUBLIC_STRIPE_PRICE_ID_PRO` is set in web/.env

- **Error: 404 or 500**
  - Check backend is running
  - Check API_URL is correct (http://127.0.0.1:8000)
  - Check backend logs for errors

---

### **Test 3: Manage Subscription (If You Have Active Subscription)**

1. If you have an active subscription, you'll see **"Manage Subscription"** button
2. Click it
3. Should redirect to Stripe billing portal
4. Portal allows you to:
   - View invoices
   - Update payment method
   - Cancel subscription

**Expected Result:**
- ✅ Redirects to Stripe portal
- ✅ Shows subscription details
- ✅ Can navigate back to app

---

## 🗑️ Part 4: Test Account Deletion (10 minutes)

### **Test 4: Account Deletion Flow**

**⚠️ WARNING:** This will permanently delete your test account!

1. Go to **Settings → ACCOUNT** tab
2. Scroll to **"Danger Zone"** (red section at bottom)
3. Click **"Delete Account"** button

**Triple Confirmation Flow:**

**First Prompt:**
```
Are you absolutely sure? This action cannot be undone.
All your checks, data, and subscription will be permanently deleted.
```
- Click **OK** to continue (or Cancel to abort)

**Second Prompt:**
```
This is your last chance. Type DELETE in the next prompt to confirm.
```
- Click **OK**

**Third Prompt:**
```
Type DELETE to confirm account deletion:
```
- Type: **DELETE** (must be uppercase)
- Click **OK**

**Expected Result:**
- ✅ Button shows "Deleting..." briefly
- ✅ Backend deletes all data
- ✅ Clerk user deleted
- ✅ Signed out automatically
- ✅ Redirected to homepage (http://localhost:3000)

**Verify Deletion:**
1. Try signing in again with the same email
2. Should create a **NEW** user with 3 credits
3. All previous checks/data should be gone

**Troubleshooting:**
- **Error: "Failed to delete account"**
  - Check backend logs
  - Check database connection
  - Verify DELETE /api/v1/users/me endpoint exists

- **Still signed in after deletion:**
  - May need to manually sign out
  - Clear browser cache and try again

---

## 🧪 Part 5: Test Check Creation (Optional - 10 minutes)

### **Test 5: Create a Fact-Check**

1. From dashboard, click **"New Check"**
2. Choose input type:
   - **Text:** Paste a claim to fact-check
   - **URL:** Paste a URL to analyze
   - **Image/Video:** Upload a file

**Example Text:**
```
The Earth is flat and has been proven by scientists.
```

3. Click **"Check This"**

**Expected Result:**
- ✅ Check is created
- ✅ Redirected to check detail page
- ✅ Shows "Processing..." status
- ✅ Real-time progress updates (if SSE working)
- ✅ Eventually shows results with verdict

**Note:** Full pipeline testing requires:
- OpenAI API key configured
- Brave/SERP API keys configured
- Qdrant vector DB configured
- All pipeline stages working

**If pipeline fails:**
- Check backend logs for errors
- Verify all API keys are set
- Check Celery worker is running
- This is expected if pipeline isn't fully configured yet

---

## 📊 Part 6: Test Dashboard Features (5 minutes)

### **Test 6: Navigation and UI**

**Test Dashboard:**
1. Click **"Dashboard"** in navbar
2. Should show:
   - Welcome message with your name
   - Quick stats (checks, recent activity)
   - Recent checks list (if any exist)

**Test History:**
1. Click **"History"** in navbar
2. Should show:
   - List of all your checks
   - Search/filter options
   - Pagination (if >20 checks)

**Test Settings Tabs:**
1. Click **"Settings"** in navbar
2. Click each tab:
   - **ACCOUNT:** Profile info, security, danger zone
   - **SUBSCRIPTION:** Current plan, usage, upgrade button
   - **NOTIFICATIONS:** Email preferences (saved to localStorage)

**Verify All Pages Load:**
- ✅ Dashboard loads without errors
- ✅ History loads without errors
- ✅ Settings loads without errors
- ✅ All tabs switch correctly
- ✅ No 404 errors
- ✅ No white screens

---

## ✅ Checkpoint 2: Integration Testing Complete

### **What Should Be Working:**

✅ **Infrastructure:**
- Docker services running
- Backend API responding
- Frontend serving pages

✅ **Authentication:**
- Sign in/sign up works
- Dashboard accessible
- User data loads

✅ **Stripe Integration:**
- Checkout session creates
- Redirects to Stripe
- Subscription management works

✅ **Account Management:**
- Profile displays correctly
- Account deletion works
- Data is properly removed

✅ **UI/Navigation:**
- All pages load
- Tabs switch correctly
- Responsive design works

---

## 🐛 Common Issues & Solutions

### **Issue 1: Backend won't start**
```
Error: Redis not running
```
**Solution:**
```bash
docker-compose up -d redis
```

### **Issue 2: Frontend 500 errors**
```
API Error: Network request failed
```
**Solution:**
- Check backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in web/.env
- Check CORS is configured in backend

### **Issue 3: Stripe errors**
```
Error: No such price: 'price_...'
```
**Solution:**
- Verify price ID exists in Stripe dashboard
- Copy correct price ID to web/.env
- Restart frontend

### **Issue 4: Database connection errors**
```
Error: Connection refused to port 5433
```
**Solution:**
- Check PostgreSQL is running: `docker ps`
- Check port matches in backend/.env (5433)
- Restart Docker: `docker-compose restart postgres`

### **Issue 5: Authentication loops**
```
Keeps redirecting to sign-in page
```
**Solution:**
- Check Clerk keys in web/.env
- Clear browser cookies
- Check middleware isn't blocking routes

---

## 🎯 Testing Summary

After completing all tests, you should have verified:

1. ✅ **GAP-001:** Stripe keys configured and working
2. ✅ **GAP-002:** Account deletion endpoint works
3. ✅ **Stack Integration:** All services communicate correctly
4. ✅ **User Flows:** Sign-in, upgrade, delete work end-to-end

---

## 📝 Next Steps After Testing

### **If All Tests Pass:**
1. Mark testing tasks as complete
2. Move to GAP-003 (SSE Token Security)
3. Continue with additional features

### **If Tests Fail:**
1. Document which tests failed
2. Check logs for error details
3. Troubleshoot issues before continuing
4. Re-run failed tests after fixes

---

## 📞 Need Help?

**Check These Resources:**
- Backend logs (terminal where backend is running)
- Frontend logs (browser DevTools → Console)
- Docker logs: `docker-compose logs -f`
- API docs: http://localhost:8000/api/docs
- Error docs: ERROR.md
- Integration docs: FRONTEND_BACKEND_INTEGRATION.md

---

**Last Updated:** October 14, 2025
**Testing Mode:** Active
**Ready to Test!** 🚀
