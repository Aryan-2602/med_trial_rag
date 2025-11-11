#!/bin/bash
# Script to fix git remote URL by removing embedded token

echo "🔧 Fixing git remote URL..."

# Remove token from remote URL
git remote set-url origin https://github.com/aryanmaheshwari-cotrial-ai/cotrial-ragv2.git

echo "✅ Remote URL updated (token removed)"
echo ""
echo "📝 To verify:"
echo "   git remote -v"
echo ""
echo "⚠️  IMPORTANT: If this token was exposed, revoke it at:"
echo "   https://github.com/settings/tokens"

