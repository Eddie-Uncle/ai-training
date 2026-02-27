#!/bin/bash

set -euo pipefail

# Railway Deployment Script for Code Analyzer Agent
# Using Google Gemini (Free Tier)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -z "${GOOGLE_API_KEY:-}" ]] && [[ -f "$ENV_FILE" ]]; then
	echo "ℹ️ Loading GOOGLE_API_KEY from $ENV_FILE"
	set -a
	source "$ENV_FILE"
	set +a
fi

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
	echo "ℹ️ GOOGLE_API_KEY is not set in environment."
	read -r -s -p "Enter GOOGLE_API_KEY: " GOOGLE_API_KEY
	echo
fi

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
	echo "❌ GOOGLE_API_KEY cannot be empty."
	exit 1
fi

# Create Procfile for Railway
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Initialize Railway project
railway init --name "Code Analyzer Agent"

# Set environment variables
railway variables set GOOGLE_API_KEY="$GOOGLE_API_KEY"
railway variables set LLM_PROVIDER=google

# Deploy to Railway
railway up

echo "✅ Deployment complete!"
echo "🔗 Your API will be available at the Railway URL"
echo "📝 Test with: curl https://your-app.railway.app/health"
