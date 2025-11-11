# Quick Start Guide

## 🚀 Easiest Way: Run Everything at Once

```bash
# 1. Set your MySQL password and OpenAI API key
export MYSQL_PASSWORD=Pinnacle232
export OPENAI_API_KEY=sk-your-key-here

# 2. Run the application (starts both API and frontend)
./run_app.sh
```

This will:
- ✅ Check/install dependencies
- ✅ Set up environment
- ✅ Check MySQL connection
- ✅ Build PDF indices (if needed)
- ✅ Start API on http://localhost:8000
- ✅ Start Frontend on http://localhost:8501

**Access the app:** Open http://localhost:8501 in your browser

---

## 📋 Alternative: Run Separately (2 Terminals)

### Terminal 1: API Server

```bash
# Activate venv
source .venv/bin/activate

# Set environment
export USE_LOCAL_MODE=1
export MYSQL_PASSWORD=Pinnacle232
export OPENAI_API_KEY=sk-your-key-here

# Run API
make run
# OR
uvicorn src.api.server:app --reload --port 8000
```

**API will be at:** http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Terminal 2: Frontend

```bash
# Activate venv
source .venv/bin/activate

# Set environment
export USE_LOCAL_MODE=1
export RAG_API_URL=http://localhost:8000

# Run API (frontend is served automatically)
make run
# OR
uvicorn src.api.server:app --reload --port 8000
```

**Frontend will be at:** http://localhost:8000

---

## 🔧 Prerequisites

### 1. Environment Variables

Required:
- `OPENAI_API_KEY` - Your OpenAI API key
- `MYSQL_PASSWORD` - Your MySQL root password (default: Pinnacle232)

Optional (defaults provided):
- `MYSQL_HOST` - Default: localhost
- `MYSQL_USER` - Default: root
- `MYSQL_DB` - Default: cotrial_rag
- `USE_LOCAL_MODE` - Default: 1

### 2. MySQL Database

Make sure MySQL is running and the database exists:

```bash
# Check MySQL is running
mysql -u root -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"

# Create database if needed
mysql -u root -p${MYSQL_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS cotrial_rag;"
```

### 3. Data Setup (One-time)

**Build PDF indices:**
```bash
make build-pdf-indices-local
```

**Migrate SAS data to MySQL:**
```bash
make migrate-sas
```

---

## 🧪 Test the System

### Test API directly:

```bash
# Health check
curl http://localhost:8000/health

# Status
curl http://localhost:8000/v1/status

# Test query
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the inclusion criteria?", "top_k": 5}'
```

### Test in browser:

1. Open http://localhost:8501
2. Type a question in the chat interface
3. See results with citations

---

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8000
lsof -i :8000

# Check what's using port 8501
lsof -i :8501

# Kill process if needed
kill -9 <PID>
```

**MySQL connection failed:**
- Check MySQL is running: `brew services list` (macOS) or `systemctl status mysql` (Linux)
- Verify password: `mysql -u root -p${MYSQL_PASSWORD} -e "SELECT 1;"`
- Check database exists: `mysql -u root -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"`

**Dependencies missing:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-frontend.txt
```

**Vector DB not found:**
```bash
# Build PDF indices
make build-pdf-indices-local
```

**No prompt examples loaded:**
- Check `data/prompt_engineering/` folder has JSON files
- Files are automatically cleaned when loaded
- See `data/prompt_engineering/README.md` for details

---

## 📚 More Information

- **API Documentation**: http://localhost:8000/docs (when API is running)
- **Makefile commands**: `make help` or see `Makefile`
- **Environment setup**: See `setup_local_env.sh`

