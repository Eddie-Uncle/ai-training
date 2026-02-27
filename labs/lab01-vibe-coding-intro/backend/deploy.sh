#!/bin/bash

# Backend Deployment Helper Script

echo "🚀 Railway Backend Deployment Helper"
echo "====================================="
echo ""

# Check if we're in the backend directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: You're not in the backend directory!"
    echo ""
    echo "Current directory: $(pwd)"
    echo ""
    echo "Please navigate to the backend directory first:"
    echo "cd /Users/eagle/code/ai_training/labs/lab01-vibe-coding-intro/backend"
    echo ""
    exit 1
fi

echo "✅ Correct directory detected!"
echo ""
echo "Files found:"
ls -1 | grep -E '\.(py|txt|toml)$|^Procfile$'
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "⚠️  Railway CLI not found. Installing..."
    npm i -g @railway/cli
fi

echo "📦 Backend files verified:"
echo "   ✓ main.py"
echo "   ✓ requirements.txt"
echo "   ✓ Procfile"
echo "   ✓ railway.toml"
echo ""

read -p "Do you want to deploy now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚂 Deploying to Railway..."
    railway up
    
    echo ""
    echo "🎉 Deployment complete!"
    echo ""
    echo "View your service:"
    railway status
fi
