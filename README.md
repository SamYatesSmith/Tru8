# Tru8 - AI-Powered Fact Verification Platform

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- Git

### 1. Start Services
```bash
docker-compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
alembic upgrade head
uvicorn main:app --reload
```

### 3. Web Frontend
```bash
cd web
npm install
npm run dev
```

### 4. Mobile App
```bash
cd mobile
npm install
npx expo start
```

## 📁 Project Structure
```
tru8/
├── backend/          # FastAPI + ML Pipeline
├── web/             # Next.js Web App
├── mobile/          # React Native (Expo)
├── shared/          # Shared TypeScript types
├── .claude/         # Claude Code configuration
└── docker-compose.yml
```

## 🔑 Environment Variables

Create `.env` files in each directory:
- `backend/.env` - API keys, database URLs
- `web/.env.local` - Clerk public key, API URL
- `mobile/.env` - Clerk, RevenueCat keys

## 🧪 Testing

```bash
# Backend
cd backend && pytest

# Web
cd web && npm test

# Mobile
cd mobile && npm test
```

## 📊 Monitoring

- **API Docs**: http://localhost:8000/api/docs
- **Metrics**: http://localhost:8000/metrics
- **Flower** (Celery): http://localhost:5555

## 🎯 Development Plan

Following the phased approach in `DEVELOPMENT_PLAN.md`:
- **Phase 0**: Foundation ✅
- **Track A**: Backend Pipeline (Week 1-4) ✅ **COMPLETE**
- **Track B**: Web Frontend (Week 1-4) - In Progress
- **Track C**: Mobile App (Week 1-4) - In Progress
- **Phase 2**: Integration (Week 5-6)
- **Phase 3**: Launch Prep (Week 7-8)

### 🏆 Track A Achievements
- ✅ Full ML pipeline: Extract → Retrieve → Verify → Judge
- ✅ Real-time progress via SSE streaming
- ✅ Sub-10s end-to-end performance
- ✅ Production-ready NLI verification & LLM judgment
- ✅ Complete caching & optimization layers

## 📝 License

Private - All rights reserved