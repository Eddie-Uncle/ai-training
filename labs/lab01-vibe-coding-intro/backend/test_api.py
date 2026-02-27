"""Test the URL Shortener API"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"✓ Health check: {response.json()}")

def test_shorten():
    """Test URL shortening"""
    # Test creating a new short URL
    test_url = "https://www.example.com/very/long/path"
    response = requests.post(
        f"{BASE_URL}/shorten",
        json={"url": test_url}
    )
    data = response.json()
    print(f"\n✓ Shortened URL:")
    print(f"  Original: {data['original_url']}")
    print(f"  Short code: {data['short_code']}")
    print(f"  Short URL: {data['short_url']}")
    
    # Test duplicate URL (should return same code)
    response2 = requests.post(
        f"{BASE_URL}/shorten",
        json={"url": test_url}
    )
    data2 = response2.json()
    print(f"\n✓ Duplicate URL handling:")
    print(f"  Same short code returned: {data['short_code'] == data2['short_code']}")
    
    return data['short_code']

def test_redirect(short_code):
    """Test URL redirection"""
    response = requests.get(
        f"{BASE_URL}/{short_code}",
        allow_redirects=False
    )
    print(f"\n✓ Redirect test:")
    print(f"  Status: {response.status_code}")
    print(f"  Location: {response.headers.get('location')}")

def test_invalid_url():
    """Test invalid URL validation"""
    try:
        response = requests.post(
            f"{BASE_URL}/shorten",
            json={"url": "not-a-valid-url"}
        )
        if response.status_code == 422:
            print(f"\n✓ Invalid URL rejected (422)")
        else:
            print(f"\n✗ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"\n✗ Error: {e}")

def test_not_found():
    """Test non-existent short code"""
    response = requests.get(f"{BASE_URL}/XXXXXX")
    if response.status_code == 404:
        print(f"\n✓ Non-existent code returns 404")
    else:
        print(f"\n✗ Unexpected response: {response.status_code}")

if __name__ == "__main__":
    print("Testing URL Shortener API")
    print("=" * 50)
    
    try:
        test_health()
        short_code = test_shorten()
        test_redirect(short_code)
        test_invalid_url()
        test_not_found()
        print("\n" + "=" * 50)
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to server.")
        print("Please start the server with: python main.py")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
