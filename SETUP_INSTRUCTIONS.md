# Tru8 Project Setup Instructions

## Prerequisites Installed
✅ Node.js v22.19.0 & npm 11.5.2
✅ Python 3.13.7
❌ Docker Desktop (Required for databases)

## Installation Status

### 1. Frontend Dependencies ✅
```bash
# Web (Next.js)
cd web && npm install  # COMPLETED

# Mobile (React Native/Expo)
cd mobile && npm install --legacy-peer-deps  # COMPLETED

# Shared Types
cd shared && npm install  # COMPLETED
```

### 2. Backend Dependencies ⚙️
```bash
cd backend
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt  # IN PROGRESS
```

**Note:** Modified dependencies for Python 3.13 compatibility:
- `onnxruntime==1.16.3` → `onnxruntime==1.20.0`
- `numpy==1.24.3` → `numpy>=2.0.0`

## Required Actions

### 1. Install Docker Desktop
Download and install from: https://www.docker.com/products/docker-desktop/

After installation, run:
```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Qdrant Vector DB (port 6333)
- MinIO S3 Storage (port 9000)

### 2. Configure Environment Variables

#### Backend (`backend/.env`)
Create file with:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/tru8_dev
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
SECRET_KEY=your-secret-key-here
CLERK_SECRET_KEY=your-clerk-secret-key
```

#### Web (`web/.env.local`)
Create file with:
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Mobile (`mobile/.env`)
Copy from `.env.example` and update:
```env
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
EXPO_PUBLIC_API_URL=http://localhost:8000
```

### 3. Fix Security Vulnerability
```bash
cd web && npm audit fix
```

### 4. Database Setup (after Docker is running)
```bash
cd backend
./venv/Scripts/python.exe -m alembic upgrade head
```

## Running the Application

### Start all services:
```bash
# Terminal 1: Database services
docker-compose up

# Terminal 2: Backend API
cd backend
./venv/Scripts/python.exe main.py

# Terminal 3: Web frontend
cd web
npm run dev

# Terminal 4: Mobile app (optional)
cd mobile
npm start
```

## Verification Commands

```bash
# Check web app
curl http://localhost:3000

# Check API health
curl http://localhost:8000/health

# Check database connection
docker exec -it tru8_postgres_1 psql -U postgres -d tru8_dev -c "\dt"
```

## Troubleshooting

### Python Package Issues
If packages fail to install due to Python 3.13 compatibility:
1. Consider using Python 3.11 or 3.12 instead
2. Or update package versions in requirements.txt

### Docker Issues
- Ensure Docker Desktop is running
- Check Windows WSL2 is enabled
- Verify no other services using ports 5432, 6379, 6333

### Node.js Issues
- Clear npm cache: `npm cache clean --force`
- Delete node_modules and reinstall

## Project Structure
- `/backend` - FastAPI Python backend with ML pipeline
- `/web` - Next.js web application
- `/mobile` - React Native mobile app
- `/shared` - Shared TypeScript types