#!/bin/bash

# Frontend Redeploy Script with Environment Variable Setup

echo "🚀 Vercel Frontend Redeploy Helper"
echo "=================================="
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ] || [ ! -f "next.config.js" ]; then
    echo "❌ ERROR: You're not in the frontend directory!"
    echo ""
    echo "Current directory: $(pwd)"
    echo ""
    echo "Please navigate to the frontend directory first:"
    echo "cd /Users/eagle/code/ai_training/labs/lab01-vibe-coding-intro/frontend"
    echo ""
    exit 1
fi

echo "✅ Correct directory detected!"
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "⚠️  Vercel CLI not found. Installing..."
    npm i -g vercel
fi

echo "📝 Backend URL Setup"
echo "-------------------"
echo ""
echo "You need to set the NEXT_PUBLIC_API_URL environment variable"
echo "to your Railway backend URL."
echo ""

read -p "Do you have your Railway backend URL? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo "To get your Railway backend URL:"
    echo "1. Open a new terminal"
    echo "2. cd /Users/eagle/code/ai_training/labs/lab01-vibe-coding-intro/backend"
    echo "3. railway status"
    echo "4. Copy the URL and come back here"
    echo ""
    exit 0
fi

echo ""
read -p "Enter your Railway backend URL (e.g., https://your-app.up.railway.app): " BACKEND_URL

if [ -z "$BACKEND_URL" ]; then
    echo "❌ No URL provided. Exiting."
    exit 1
fi

echo ""
echo "Setting environment variable on Vercel..."
echo "$BACKEND_URL" | vercel env add NEXT_PUBLIC_API_URL production

echo ""
echo "🚀 Deploying to Vercel..."
vercel --prod

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "✅ API routes created:"
echo "   - /app/api/shorten/route.ts"
echo "   - /app/api/urls/route.ts"
echo ""
echo "✅ Environment variable set:"
echo "   NEXT_PUBLIC_API_URL = $BACKEND_URL"
echo ""
echo "🌐 Test your frontend now!"
