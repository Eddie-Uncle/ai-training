import os
from dotenv import load_dotenv
import google.generativeai as genai

def test_setup():
    print("🔍 Testing setup...")
    
    # Load environment variables from .env file
    load_dotenv()

    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")
        return False

    # Test API call
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = model.generate_content("Hi")
        print("✅ Setup successful! API is working.")
        print(f"📝 Response: {response.text[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_setup()
