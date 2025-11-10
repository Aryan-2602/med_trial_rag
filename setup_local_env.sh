#!/bin/bash
# Quick setup script for local development

echo "🔧 Setting up local environment variables..."

export USE_LOCAL_MODE=1

# MySQL (local machine)
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=cotrial_rag
export MYSQL_USER=root
export MYSQL_PASSWORD=your_mysql_password

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY is not set"
    echo "   Please set it with: export OPENAI_API_KEY=sk-your-key-here"
    echo "   Or add it to your .env file"
else
    echo "✅ OPENAI_API_KEY is set"
fi

echo ""
echo "✅ Environment variables set:"
echo "   USE_LOCAL_MODE=1"
echo "   MYSQL_HOST=localhost"
echo "   MYSQL_DB=cotrial_rag"
echo ""
echo "⚠️  Don't forget to set MYSQL_PASSWORD to your MySQL root password!"
echo ""
echo "To use these in your current shell, run:"
echo "   source setup_local_env.sh"

