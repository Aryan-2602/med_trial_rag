#!/bin/bash
# Script to clear cached Git credentials

echo "🔧 Clearing Git credentials..."

# Remove credential username from local config
git config --unset credential.username 2>/dev/null || true
git config --local --unset credential.username 2>/dev/null || true

# Remove credential username from global config
git config --global --unset credential.username 2>/dev/null || true

echo "✅ Git credential.username removed"
echo ""
echo "🔑 To clear macOS Keychain credentials:"
echo ""
echo "Option 1: Use Keychain Access app"
echo "   1. Open 'Keychain Access' app"
echo "   2. Search for 'github.com'"
echo "   3. Delete any entries found"
echo ""
echo "Option 2: Use command line (run this manually):"
echo "   security delete-internet-password -s github.com"
echo ""
echo "Option 3: Clear all GitHub credentials:"
echo "   git credential-osxkeychain erase"
echo "   host=github.com"
echo "   protocol=https"
echo "   (Press Enter twice)"
echo ""
echo "After clearing, Git will prompt for new credentials on next push."

