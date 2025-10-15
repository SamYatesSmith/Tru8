# Tru8 Quick Start Guide

**Get your entire stack running in under 5 minutes.**

---

## Prerequisites

- **Python 3.12+** installed
- **Node.js 18+** installed
- **Docker** installed and running

---

## 🚀 Step-by-Step Startup

### 1. Start Infrastructure (30 seconds)

Open a terminal in the project root and run:

```bash
docker-compose up -d postgres redis qdrant
```

This starts:
- PostgreSQL database on port **5433**
- Redis on port **6379**
- Qdrant vector DB on port **6333**

**Verify:** Run `docker ps` - you should see 3 containers running.

---

### 2. Set Up Backend (2 minutes)

#### First Time Only: Create Virtual Environment
```bash
cd backend
python -m venv venv
```

#### Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Run Database Migrations
```bash
alembic upgrade head
```

#### Start Backend Services
**Windows:**
```bash
.\start-backend.bat
```

**Linux/macOS:**
```bash
chmod +x start-backend.sh
./start-backend.sh
```

This starts:
- **FastAPI server** on http://localhost:8000
- **Celery worker** for background processing

**Verify:** Open http://localhost:8000/api/docs - you should see the Swagger UI.

---

### 3. Start Frontend (1 minute)

Open a **new terminal** window:

```bash
cd web
npm install          # First time only
npm run dev
```

This starts:
- **Next.js dev server** on http://localhost:3000

**Verify:** Open http://localhost:3000 - you should see the Tru8 homepage.

---

## 🧪 Test the Integration

### 1. Sign In
1. Go to http://localhost:3000
2. Click "Get Started" or "Sign In"
3. Create a test account via Clerk
4. You should be redirected to the dashboard

### 2. Create a Fact-Check
1. Click "New Check" in the dashboard
2. Paste a URL or enter text
3. Click "Check This"
4. You should see real-time progress updates

### 3. View Results
1. Check should appear in History
2. Click to view detailed results with claims and evidence

---

## 🛑 Stopping Everything

### Stop Frontend
Press `Ctrl+C` in the terminal running `npm run dev`

### Stop Backend
Press `Ctrl+C` in the terminal running the backend script

### Stop Infrastructure
```bash
docker-compose down
```

To also remove data volumes:
```bash
docker-compose down -v
```

---

## 🐛 Troubleshooting

### "Redis not running" Error
Make sure Docker containers are running:
```bash
docker ps
```

If not running, start them:
```bash
docker-compose up -d
```

### "Port 8000 already in use"
Another FastAPI server is running. Find and kill it:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

### "Connection refused" to Database
Check PostgreSQL is running on port 5433:
```bash
docker logs tru8-postgres-1
```

If you see port conflicts, the port might already be in use. Edit `docker-compose.yml` to change the port.

### Backend Import Errors
Make sure you've activated the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Frontend Build Errors
Delete node_modules and reinstall:
```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

---

## 📁 Project Structure Reminder

```
Tru8/
├── backend/          # FastAPI + ML Pipeline
│   ├── app/         # Application code
│   ├── alembic/     # Database migrations
│   ├── main.py      # FastAPI entry point
│   └── .env         # Backend config
├── web/             # Next.js frontend
│   ├── app/         # App Router pages
│   ├── components/  # React components
│   └── .env         # Frontend config
├── docker-compose.yml  # Infrastructure
└── QUICK_START.md      # This file
```

---

## 🔑 Important URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3000 | Main user interface |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/api/docs | Swagger UI |
| PostgreSQL | localhost:5433 | Database |
| Redis | localhost:6379 | Task queue |
| Qdrant | localhost:6333 | Vector search |

---

## 📊 System Requirements

### Minimum
- 4 GB RAM
- 2 CPU cores
- 5 GB disk space

### Recommended
- 8 GB RAM
- 4 CPU cores
- 10 GB disk space

---

## 🎯 Next Steps

Once everything is running:

1. **Read FRONTEND_BACKEND_INTEGRATION.md** for detailed integration info
2. **Check ERROR.md** for known issues and resolutions
3. **Review .claude/CLAUDE.md** for development guidelines
4. **Explore backend/README-STARTUP.md** for advanced backend configuration

---

## 💡 Pro Tips

### Keep Everything Running
Open 3 terminal tabs:
1. **Tab 1:** Docker logs (`docker-compose logs -f`)
2. **Tab 2:** Backend (`cd backend && .\start-backend.bat`)
3. **Tab 3:** Frontend (`cd web && npm run dev`)

### Check Service Health
```bash
# Backend
curl http://localhost:8000/api/v1/health

# Redis
docker exec -it tru8-redis-1 redis-cli ping

# PostgreSQL
docker exec -it tru8-postgres-1 psql -U postgres -c "SELECT 1"
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

**Last Updated:** October 14, 2025
**Questions?** Check ERROR.md or FRONTEND_BACKEND_INTEGRATION.md
