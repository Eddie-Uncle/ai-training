#!/bin/bash

# URL Shortener API Test Script

echo "=== Testing URL Shortener API ==="
echo ""

# Test 1: Health Check
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq .
echo ""

# Test 2: Shorten a URL
echo "2. Shortening a URL..."
RESPONSE=$(curl -s -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com/very/long/url/path"}')
echo $RESPONSE | jq .
SHORT_CODE=$(echo $RESPONSE | jq -r '.short_code')
echo ""

# Test 3: Test duplicate URL (should return same short code)
echo "3. Testing duplicate URL handling..."
curl -s -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com/very/long/url/path"}' | jq .
echo ""

# Test 4: Test redirect (show headers)
echo "4. Testing redirect (showing headers)..."
curl -I http://localhost:8000/$SHORT_CODE
echo ""

# Test 5: Test invalid short code
echo "5. Testing invalid short code..."
curl -s http://localhost:8000/invalid | jq .
echo ""

# Test 6: Test nonexistent short code
echo "6. Testing nonexistent short code..."
curl -s http://localhost:8000/AAAAAA | jq .
echo ""

echo "=== Tests Complete ==="
