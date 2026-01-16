#!/bin/bash
# Single script to run the entire CoTrial RAG application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 CoTrial RAG v2 - Startup Script${NC}"
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
fi

# Activate venv
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check dependencies
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
if ! python3 -c "import chromadb, mysql.connector, openai, fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies ready${NC}"
fi

# Load environment
echo -e "${BLUE}⚙️  Loading environment...${NC}"
if [ -f "setup_local_env.sh" ]; then
    source setup_local_env.sh
fi

# Set defaults for environment variables (after sourcing setup script)
export USE_LOCAL_MODE=1
export MYSQL_HOST=${MYSQL_HOST:-localhost}
export MYSQL_PORT=${MYSQL_PORT:-3306}
export MYSQL_DB=${MYSQL_DB:-cotrial_rag}
export MYSQL_USER=${MYSQL_USER:-root}

# Only set default password if not already set or if it's a placeholder
if [ -z "$MYSQL_PASSWORD" ] || [ "$MYSQL_PASSWORD" = "your_mysql_password" ]; then
    export MYSQL_PASSWORD=Pinnacle232
    echo -e "${YELLOW}⚠️  Using default MySQL password: Pinnacle232${NC}"
    echo -e "${YELLOW}   (Set MYSQL_PASSWORD to use a different password)${NC}"
fi

export RAG_API_URL=${RAG_API_URL:-http://localhost:8000}

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY is not set!${NC}"
    echo -e "${YELLOW}Please set it with:${NC}"
    echo -e "  ${BLUE}export OPENAI_API_KEY=sk-your-key-here${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment configured${NC}"
echo -e "${BLUE}   MySQL: ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}${NC}"
echo ""

# Check MySQL connection
echo -e "${BLUE}🔌 Checking MySQL connection...${NC}"
# Use MYSQL_PWD environment variable to avoid password in command line
export MYSQL_PWD="$MYSQL_PASSWORD"
if mysql -u "$MYSQL_USER" -h "$MYSQL_HOST" -e "USE $MYSQL_DB; SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ MySQL connected${NC}"
    unset MYSQL_PWD
else
    unset MYSQL_PWD
    echo -e "${RED}❌ MySQL connection failed!${NC}"
    echo -e "${YELLOW}Please check:${NC}"
    echo "  - MySQL is running: mysqladmin ping"
    echo "  - Password is correct (current: ${MYSQL_PASSWORD})"
    echo "  - Database exists: mysql -u root -p -e 'CREATE DATABASE IF NOT EXISTS $MYSQL_DB;'"
    echo ""
    echo -e "${YELLOW}You can set a different password with:${NC}"
    echo -e "  ${BLUE}export MYSQL_PASSWORD=your_password${NC}"
    exit 1
fi

# Check if dummy SQL tables exist (optional, non-blocking)
echo -e "${BLUE}📊 Checking dummy SQL tables...${NC}"
CREATE_TABLES=false

# Quick check: just try to connect and see if patients table exists
# This is much faster than running the full Python script
if mysql -u "$MYSQL_USER" -h "$MYSQL_HOST" -p"$MYSQL_PASSWORD" -e "USE $MYSQL_DB; SELECT COUNT(*) FROM patients LIMIT 1;" >/dev/null 2>&1; then
    PATIENT_COUNT=$(mysql -u "$MYSQL_USER" -h "$MYSQL_HOST" -p"$MYSQL_PASSWORD" -e "USE $MYSQL_DB; SELECT COUNT(*) FROM patients;" 2>/dev/null | tail -1)
    if [ -n "$PATIENT_COUNT" ] && [ "$PATIENT_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e "${GREEN}✅ Dummy SQL tables found with data (${PATIENT_COUNT} patients)${NC}"
    else
        echo -e "${YELLOW}⚠️  Dummy SQL tables exist but are empty${NC}"
        read -p "Create dummy SQL tables and data now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            CREATE_TABLES=true
        else
            echo -e "${YELLOW}⚠️  Skipping table creation. You can create later with: make create-dummy-data${NC}"
        fi
    fi
elif mysql -u "$MYSQL_USER" -h "$MYSQL_HOST" -p"$MYSQL_PASSWORD" -e "USE $MYSQL_DB; SHOW TABLES LIKE 'patients';" >/dev/null 2>&1; then
    # Table exists but query failed - probably empty
    echo -e "${YELLOW}⚠️  Dummy SQL tables exist but may be empty${NC}"
    read -p "Create dummy SQL tables and data now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CREATE_TABLES=true
    else
        echo -e "${YELLOW}⚠️  Skipping table creation. You can create later with: make create-dummy-data${NC}"
    fi
else
    # Tables don't exist
    echo -e "${YELLOW}⚠️  Dummy SQL tables not found${NC}"
    read -p "Create dummy SQL tables and data now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CREATE_TABLES=true
    else
        echo -e "${YELLOW}⚠️  Skipping table creation. You can create later with: make create-dummy-data${NC}"
    fi
fi

# Create tables if needed
if [ "$CREATE_TABLES" = true ]; then
    echo -e "${BLUE}🏗️  Creating dummy SQL tables and data (this may take a few minutes)...${NC}"
    PYTHONPATH=. python3 scripts/create_dummy_clinical_trial_data.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dummy SQL tables and data created${NC}"
    else
        echo -e "${RED}❌ Failed to create dummy tables. Check errors above.${NC}"
        exit 1
    fi
fi

# Check if PDF indices exist
echo -e "${BLUE}📚 Checking PDF indices...${NC}"
if [ -d "data/vector_db" ] && [ -f "data/vector_db/chroma.sqlite3" ]; then
    echo -e "${GREEN}✅ PDF indices found${NC}"
    BUILD_INDICES=false
else
    echo -e "${YELLOW}⚠️  PDF indices not found${NC}"
    read -p "Build PDF indices now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BUILD_INDICES=true
    else
        BUILD_INDICES=false
        echo -e "${YELLOW}⚠️  Skipping index build. You can build later with: make build-pdf-indices-local${NC}"
    fi
fi

# Build indices if needed
if [ "$BUILD_INDICES" = true ]; then
    echo -e "${BLUE}🏗️  Building PDF indices (this may take a few minutes)...${NC}"
    PYTHONPATH=. python3 scripts/build_pdf_index_vector_db.py \
        --input-dir data/AllProvidedFiles_438 \
        --model text-embedding-3-small
    echo -e "${GREEN}✅ PDF indices built${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down...${NC}"
    kill $API_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API in background
echo -e "${BLUE}🚀 Starting API server on http://localhost:8000...${NC}"
uvicorn src.api.server:app --reload --port 8000 > /tmp/rag_api.log 2>&1 &
API_PID=$!

# Wait for API to be ready
echo -e "${YELLOW}⏳ Waiting for API to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready!${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API failed to start. Check logs: tail -f /tmp/rag_api.log${NC}"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Application is running!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📍 Access points:${NC}"
echo -e "   Frontend: ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "   API Health: ${GREEN}http://localhost:8000/health${NC}"
echo ""
echo -e "${BLUE}📊 Process ID:${NC}"
echo -e "   API: $API_PID"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo -e "   API: ${YELLOW}tail -f /tmp/rag_api.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
wait

