# CoTrial RAG v2 - Complete Setup Guide

This guide will help you set up and run the CoTrial RAG v2 application on your local machine from scratch.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.9+**
   ```bash
   python3 --version  # Should be 3.9 or higher
   ```

2. **MySQL 8.0+**
   - macOS: `brew install mysql`
   - Linux: `sudo apt-get install mysql-server` (Ubuntu/Debian)
   - Windows: Download from [MySQL website](https://dev.mysql.com/downloads/mysql/)

3. **Git**
   ```bash
   git --version
   ```

4. **OpenAI API Key**
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Get your API key from the dashboard

## 🚀 Quick Setup (Automated)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd cotrial-ragv2
```

### Step 2: Set Environment Variables

Create a `.env` file or export these variables:

```bash
# Required
export OPENAI_API_KEY=sk-your-key-here
export MYSQL_PASSWORD=your_mysql_password

# Optional (defaults shown)
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_DB=cotrial_rag
export USE_LOCAL_MODE=1
```

### Step 3: Run the Setup Script

```bash
chmod +x run_app.sh
./run_app.sh
```

This script will:
- ✅ Create a Python virtual environment
- ✅ Install all dependencies
- ✅ Check MySQL connection
- ✅ Build PDF indices (if needed)
- ✅ Start both API and frontend servers

**Access the application:** http://localhost:8501

---

## 📝 Manual Setup (Step-by-Step)

If you prefer to set up manually or the automated script doesn't work:

### Step 1: Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-frontend.txt
```

### Step 3: Set Up MySQL

1. **Start MySQL service:**
   ```bash
   # macOS
   brew services start mysql
   
   # Linux
   sudo systemctl start mysql
   ```

2. **Create the database:**
   ```bash
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS cotrial_rag;"
   ```

3. **Verify connection:**
   ```bash
   mysql -u root -p${MYSQL_PASSWORD} -e "USE cotrial_rag; SELECT 1;"
   ```

### Step 4: Set Environment Variables

```bash
export OPENAI_API_KEY=sk-your-key-here
export MYSQL_PASSWORD=your_mysql_password
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_DB=cotrial_rag
export USE_LOCAL_MODE=1
export RAG_API_URL=http://localhost:8000
```

**Tip:** Add these to your `~/.bashrc` or `~/.zshrc` to persist:

```bash
echo 'export OPENAI_API_KEY=sk-your-key-here' >> ~/.zshrc
echo 'export MYSQL_PASSWORD=your_mysql_password' >> ~/.zshrc
source ~/.zshrc
```

### Step 5: Build PDF Indices

```bash
# Make sure you're in the project root and venv is activated
PYTHONPATH=. python scripts/build_pdf_index_vector_db.py \
    --input-dir data/AllProvidedFiles_438 \
    --model text-embedding-3-small
```

This will:
- Process all PDFs in the specified directory
- Generate embeddings using OpenAI
- Store them in ChromaDB at `data/vector_db/`

**Note:** This may take several minutes depending on the number of PDFs.

### Step 6: Migrate SAS Data to MySQL (Optional)

If you have SAS files to migrate:

```bash
PYTHONPATH=. python scripts/migrate_sas_to_mysql.py \
    --input-dir path/to/sas/files \
    --db-name cotrial_rag
```

### Step 7: Start the Application

**Terminal 1 - API Server:**
```bash
source .venv/bin/activate
export OPENAI_API_KEY=sk-your-key-here
export MYSQL_PASSWORD=your_mysql_password
export USE_LOCAL_MODE=1

uvicorn src.api.server:app --reload --port 8000
```

**Note:** The frontend is now served automatically by the FastAPI server. No separate frontend process is needed.

### Step 8: Access the Application

- **Frontend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health

---

## 🗂️ Project Structure

```
cotrial-ragv2/
├── src/
│   ├── api/              # FastAPI backend
│   ├── retrieval/        # Hybrid retrieval system
│   ├── utils/            # Utilities (vector DB, SQL, LLM)
│   └── indexers/         # PDF indexing
├── static/               # Static HTML/CSS/JS frontend
│   ├── index.html        # Login page
│   ├── trials.html       # Trial selection page
│   ├── chat.html         # Chat interface
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript modules
├── scripts/              # Setup and migration scripts
├── data/
│   ├── AllProvidedFiles_438/  # PDF files
│   ├── prompt_engineering/    # Q&A examples for prompt engineering
│   └── vector_db/        # ChromaDB storage
├── docs/                 # Documentation
├── requirements.txt       # Backend dependencies
├── requirements-frontend.txt  # Frontend dependencies
├── run_app.sh           # Automated startup script
└── SETUP.md             # This file
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | - | Your OpenAI API key |
| `MYSQL_PASSWORD` | ✅ Yes | - | MySQL root password |
| `MYSQL_HOST` | No | `localhost` | MySQL host |
| `MYSQL_USER` | No | `root` | MySQL username |
| `MYSQL_DB` | No | `cotrial_rag` | Database name |
| `USE_LOCAL_MODE` | No | `1` | Use local ChromaDB |
| `RAG_API_URL` | No | `http://localhost:8000` | API URL for frontend |
| `VECTOR_DB_PATH` | No | `data/vector_db` | ChromaDB storage path |
| `ANSWER_MODEL` | No | `gpt-4o` | Model for answer generation |
| `ROUTER_MODEL` | No | `gpt-4o` | Model for query routing |
| `SQL_MODEL` | No | `gpt-4o` | Model for SQL generation |

### Model Configuration

You can change the LLM models used by setting:

```bash
export ANSWER_MODEL=gpt-4o-mini  # For faster/cheaper answers
export ROUTER_MODEL=gpt-4o-mini  # For faster routing
export SQL_MODEL=gpt-4o-mini     # For faster SQL generation
```

---

## 🧪 Testing the Setup

### 1. Test API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 2. Test API Status

```bash
curl http://localhost:8000/v1/status
```

### 3. Test a Query

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the inclusion criteria?", "top_k": 5}'
```

### 4. Test in Browser

1. Open http://localhost:8501
2. Login (any credentials work in dev mode)
3. Select a trial
4. Ask a question in the chat

---

## 🐛 Troubleshooting

### MySQL Connection Issues

**Problem:** `Access denied for user 'root'@'localhost'`

**Solutions:**
```bash
# 1. Check MySQL is running
brew services list  # macOS
sudo systemctl status mysql  # Linux

# 2. Reset MySQL password
mysql -u root -p
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';

# 3. Verify connection
mysql -u root -pnew_password -e "SELECT 1;"
```

### Port Already in Use

**Problem:** `Address already in use`

**Solutions:**
```bash
# Find process using port 8000
lsof -i :8000

# Find process using port 8501
lsof -i :8501

# Kill the process
kill -9 <PID>
```

### Missing Dependencies

**Problem:** `ModuleNotFoundError`

**Solutions:**
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-frontend.txt
```

### Vector DB Not Found

**Problem:** `ChromaDB collection not found`

**Solutions:**
```bash
# Rebuild PDF indices
PYTHONPATH=. python scripts/build_pdf_index_vector_db.py \
    --input-dir data/AllProvidedFiles_438 \
    --model text-embedding-3-small
```

### OpenAI API Errors

**Problem:** `Invalid API key` or `Rate limit exceeded`

**Solutions:**
1. Verify your API key: `echo $OPENAI_API_KEY`
2. Check API key is valid at [OpenAI Dashboard](https://platform.openai.com/api-keys)
3. Check your usage/billing at [OpenAI Usage](https://platform.openai.com/usage)

### Frontend Not Loading

**Problem:** Frontend shows errors or blank page

**Solutions:**
1. Check API is running: `curl http://localhost:8000/health`
2. Check frontend logs: `tail -f /tmp/rag_frontend.log`
3. Check browser console for errors (F12)
4. Verify `RAG_API_URL` is set correctly

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs (when API is running)
- **Quick Start Guide:** See `QUICK_START.md`
- **SQL Schema:** See `docs/SQL_SCHEMA.md`
- **LLM SQL Guide:** See `docs/LLM_SQL_GENERATION_GUIDE.md`

---

## 🆘 Getting Help

If you encounter issues not covered here:

1. Check the logs:
   - API: `tail -f /tmp/rag_api.log`
   - Frontend: `tail -f /tmp/rag_frontend.log`

2. Verify all prerequisites are installed

3. Check environment variables are set correctly

4. Review the troubleshooting section above

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] MySQL is running and accessible
- [ ] Virtual environment is activated
- [ ] All dependencies are installed
- [ ] Environment variables are set
- [ ] PDF indices are built (if using PDF search)
- [ ] API starts without errors
- [ ] Frontend starts without errors
- [ ] Can access http://localhost:8501
- [ ] Can login and see trials page
- [ ] Can ask questions in chat and get responses

---

**Happy querying! 🎉**

