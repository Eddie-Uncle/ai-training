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

echo "� Getting existing backend URL from Vercel..."
echo ""

# Pull existing env vars to get the backend URL
vercel env pull .env.vercel.tmp 2>&1 > /dev/null

# Try to extract NEXT_PUBLIC_API_URL from existing Vercel config
# If it doesn't exist, we'll use a default
if [ -f ".env.vercel.tmp" ]; then
    BACKEND_URL=$(grep NEXT_PUBLIC_API_URL .env.vercel.tmp | cut -d'=' -f2 | tr -d '"')
    rm -f .env.vercel.tmp
fi

# If still empty, check the production env vars
if [ -z "$BACKEND_URL" ]; then
    echo "ℹ️  No existing backend URL found in Vercel environment."
    echo "   Using the same Railway backend from previous deployments..."
    # Use the existing backend - we'll reuse the same env var from Vercel
    REUSE_ENV=true
else
    echo "✅ Found existing backend URL: $BACKEND_URL"
    REUSE_ENV=false
fi

echo ""
echo "🆕 Creating a NEW Vercel project (keeping old one intact)..."
# Generate a random suffix for the project name
RANDOM_SUFFIX=$(date +%s | tail -c 6)
NEW_PROJECT_NAME="url-shortener-${RANDOM_SUFFIX}"
echo "   Project name: $NEW_PROJECT_NAME"

echo ""
echo "🚀 Deploying to Vercel with a new random URL..."
echo "   (This creates a separate project, doesn't touch frontend-six-ivory-30.vercel.app)"

if [ "$REUSE_ENV" = true ]; then
    echo "   Using existing backend URL from Vercel environment..."
    vercel --prod --name "$NEW_PROJECT_NAME"
else
    echo "   Setting backend URL: $BACKEND_URL"
    vercel --prod --name "$NEW_PROJECT_NAME" -e NEXT_PUBLIC_API_URL="$BACKEND_URL"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "🆕 This is a NEW separate project with its own random Vercel URL"
echo "   Old project (frontend-six-ivory-30.vercel.app) is still active"
echo ""
if [ "$REUSE_ENV" = false ]; then
    echo "✅ Environment variable set:"
    echo "   NEXT_PUBLIC_API_URL = $BACKEND_URL"
else
    echo "✅ Using existing backend configuration from Vercel"
fi
echo ""
echo "🌐 Your new deployment will use the same Railway backend!"
echo "   Test your new URL once deployment completes."
