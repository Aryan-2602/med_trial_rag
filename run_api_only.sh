#!/bin/bash
# Script to run only the API server

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting CoTrial RAG API...${NC}"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Virtual environment not found. Run: python3 -m venv .venv${NC}"
    exit 1
fi

# Load environment
if [ -f "setup_local_env.sh" ]; then
    source setup_local_env.sh
fi

# Set defaults
export USE_LOCAL_MODE=1
export MYSQL_PASSWORD=${MYSQL_PASSWORD:-Pinnacle232}
export MYSQL_HOST=${MYSQL_HOST:-localhost}
export MYSQL_PORT=${MYSQL_PORT:-3306}
export MYSQL_DB=${MYSQL_DB:-cotrial_rag}
export MYSQL_USER=${MYSQL_USER:-root}

# Check OpenAI key
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set. Some features may not work.${NC}"
fi

echo -e "${GREEN}✅ Starting API on http://localhost:8000${NC}"
echo -e "${BLUE}📚 API Docs: http://localhost:8000/docs${NC}"
echo ""

# Run API
uvicorn src.api.server:app --reload --port 8000

