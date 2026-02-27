"""URL Shortener Backend"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional
import aiosqlite
import string
import random
import hashlib
from contextlib import asynccontextmanager

# Database path
DB_PATH = "urls.db"

# Lifespan context manager for database setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed
    pass

app = FastAPI(title="URL Shortener", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class URLRequest(BaseModel):
    url: HttpUrl

    @validator('url')
    def validate_url(cls, v):
        """Ensure URL is valid and has a scheme"""
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str

# Database Functions
async def init_db() -> None:
    """Initialize SQLite database with urls table"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                url_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_url_hash ON urls(url_hash)
        """)
        await db.commit()

def generate_short_code(length: int = 6) -> str:
    """Generate a random alphanumeric short code"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def hash_url(url: str) -> str:
    """Create a hash of the URL for duplicate detection"""
    return hashlib.sha256(url.encode()).hexdigest()

async def get_existing_short_code(url_hash: str) -> Optional[str]:
    """Check if URL already exists and return its short code"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT short_code FROM urls WHERE url_hash = ?", 
            (url_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_url(short_code: str, original_url: str, url_hash: str) -> None:
    """Save URL mapping to database"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO urls (short_code, original_url, url_hash) VALUES (?, ?, ?)",
            (short_code, original_url, url_hash)
        )
        await db.commit()

async def get_original_url(short_code: str) -> Optional[str]:
    """Retrieve original URL from short code"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT original_url FROM urls WHERE short_code = ?",
            (short_code,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def short_code_exists(short_code: str) -> bool:
    """Check if a short code already exists"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM urls WHERE short_code = ?",
            (short_code,)
        ) as cursor:
            return await cursor.fetchone() is not None

async def get_all_urls(limit: int = 50) -> list:
    """Get all shortened URLs, most recent first"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT short_code, original_url, created_at FROM urls ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "short_code": row[0],
                    "original_url": row[1],
                    "created_at": row[2]
                }
                for row in rows
            ]

async def delete_all_urls() -> None:
    """Delete all shortened URLs from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM urls")
        await db.commit()

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "URL Shortener API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "shorten": "POST /shorten",
            "list_urls": "GET /urls",
            "redirect": "GET /{short_code}"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/urls")
async def get_urls(req: Request, limit: int = 50):
    """
    Get all shortened URLs
    
    - **limit**: Maximum number of URLs to return (default: 50)
    """
    urls = await get_all_urls(limit)
    base_url = f"{req.url.scheme}://{req.url.netloc}"
    
    return [
        {
            "short_code": url["short_code"],
            "short_url": f"{base_url}/{url['short_code']}",
            "original_url": url["original_url"],
            "created_at": url["created_at"]
        }
        for url in urls
    ]

@app.delete("/urls")
async def clear_urls():
    """
    Clear all shortened URLs from the database
    """
    await delete_all_urls()
    return {"message": "All URLs cleared successfully"}

@app.post("/shorten", response_model=URLResponse)
async def shorten_url(request: URLRequest, req: Request) -> URLResponse:
    """
    Shorten a URL
    
    - **url**: The long URL to shorten
    
    Returns the short code and complete short URL
    """
    original_url = str(request.url)
    url_hash = hash_url(original_url)
    
    # Check if URL already exists
    existing_code = await get_existing_short_code(url_hash)
    if existing_code:
        # Return existing short code for duplicate URL
        base_url = f"{req.url.scheme}://{req.url.netloc}"
        return URLResponse(
            short_code=existing_code,
            short_url=f"{base_url}/{existing_code}",
            original_url=original_url
        )
    
    # Generate unique short code
    max_attempts = 10
    for _ in range(max_attempts):
        short_code = generate_short_code()
        if not await short_code_exists(short_code):
            break
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate unique short code. Please try again."
        )
    
    # Save to database
    try:
        await save_url(short_code, original_url, url_hash)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save URL: {str(e)}"
        )
    
    # Build and return response
    base_url = f"{req.url.scheme}://{req.url.netloc}"
    return URLResponse(
        short_code=short_code,
        short_url=f"{base_url}/{short_code}",
        original_url=original_url
    )

@app.get("/{short_code}")
async def redirect_to_url(short_code: str) -> RedirectResponse:
    """
    Redirect to original URL using short code
    
    - **short_code**: The short code to look up
    """
    # Validate short code format (alphanumeric, 6 chars)
    if not short_code.isalnum() or len(short_code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Invalid short code format"
        )
    
    # Get original URL
    original_url = await get_original_url(short_code)
    
    if not original_url:
        raise HTTPException(
            status_code=404,
            detail="Short code not found"
        )
    
    # Redirect to original URL
    return RedirectResponse(url=original_url, status_code=307)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
