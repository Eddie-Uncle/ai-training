# Code Analyzer Agent - Deployment Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## 1. Installation

### Step 1: Create Virtual Environment

```bash
cd python
python -m venv venv
```

### Step 2: Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Requirements installed:**
- `fastapi==0.109.0` - Web framework
- `uvicorn==0.27.0` - ASGI server
- `pydantic==2.5.3` - Data validation
- `anthropic==0.18.0` - Anthropic Claude client
- `openai==1.12.0` - OpenAI client
- `google-generativeai==0.8.0` - Google Gemini client
- `python-dotenv==1.0.0` - Environment variable management

## 2. Configuration

### Current LLM Provider: **Google Gemini 2.5 Flash**

The application is configured to use Google's Gemini model (free tier).

**Model Details:**
- Provider: Google AI Studio
- Model: `models/gemini-2.5-flash`
- API Key: Set in `.env` file
- Rate Limits: Generous free tier

### Environment Variables

The `.env` file is already configured with:
```bash
GOOGLE_API_KEY=your-key-here
LLM_PROVIDER=google
```

**To switch providers**, edit `.env`:
- For OpenAI: Set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY`
- For Anthropic: Set `LLM_PROVIDER=anthropic` and provide `ANTHROPIC_API_KEY`

## 3. Start the Server

### Option 1: Standard Start
```bash
cd python
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### Option 2: Background Process
```bash
cd python
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
```

### Expected Output
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## 4. Testing the API

### Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "provider": "google"
}
```

### Analyze Code (General)

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def add(a,b):\n    return a+b\n\ndef process(data):\n    result=[]\n    for i in range(len(data)):\n        if data[i]>0:\n            result.append(data[i]*2)\n    return result",
    "language": "python"
  }' | python -m json.tool
```

### Security-Focused Analysis

```bash
curl -X POST http://localhost:8000/analyze/security \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import sqlite3\n\ndef login(username, password):\n    conn = sqlite3.connect(\"users.db\")\n    cursor = conn.cursor()\n    query = f\"SELECT * FROM users WHERE username='\''{username}'\'' AND password='\''{password}'\''\"\n    cursor.execute(query)\n    return cursor.fetchone()",
    "language": "python"
  }' | python -m json.tool
```

### Performance-Focused Analysis

```bash
curl -X POST http://localhost:8000/analyze/performance \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def inefficient_search(data, target):\n    for i in range(len(data)):\n        for j in range(len(data)):\n            if data[i] == target:\n                return i\n    return -1",
    "language": "python"
  }' | python -m json.tool
```

## 5. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and provider info |
| `/analyze` | POST | General code analysis |
| `/analyze/security` | POST | Security-focused analysis |
| `/analyze/performance` | POST | Performance-focused analysis |

### Request Schema

```json
{
  "code": "string (required)",
  "language": "string (default: python)"
}
```

### Response Schema

```json
{
  "summary": "string",
  "issues": [
    {
      "severity": "critical|high|medium|low",
      "line": "number|null",
      "category": "bug|security|performance|style|maintainability",
      "description": "string",
      "suggestion": "string"
    }
  ],
  "suggestions": ["string"],
  "metrics": {
    "complexity": "low|medium|high",
    "readability": "poor|fair|good|excellent",
    "test_coverage_estimate": "none|partial|good"
  }
}
```

## 6. Stopping the Server

### Kill by Port
```bash
lsof -ti:8000 | xargs kill -9
```

### Or use Ctrl+C
If running in foreground, press `Ctrl+C` to stop.

## 7. Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9
```

### Module Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key Issues
- Verify `GOOGLE_API_KEY` is set in `.env`
- Check API key is valid at https://aistudio.google.com/
- Ensure `.env` file is in the `python/` directory

### Model Not Found Error
- Current model: `models/gemini-2.5-flash`
- Check available models with:
```python
import google.generativeai as genai
genai.configure(api_key="your-key")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
```

## 8. Production Deployment

For production deployment, consider:
- Using environment variables instead of `.env` file
- Setting up proper logging
- Implementing rate limiting
- Adding authentication
- Using a production ASGI server configuration
- Monitoring and error tracking

See [README.md](../README.md) for deployment to Railway or Vercel.
