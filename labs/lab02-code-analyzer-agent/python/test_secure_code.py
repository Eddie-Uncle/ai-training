#!/usr/bin/env python3
"""Test the security-fixed code through the security analyzer API."""
import json
import requests

# Secure code with all vulnerabilities fixed
secure_code = """
import os
from dotenv import load_dotenv
import sqlite3
import ast

# FIX 1: Use environment variables instead of hardcoded passwords
load_dotenv()
password = os.getenv("PASSWORD")

# FIX 2: Use parameterized queries to prevent SQL injection
def get_user(user_input):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_input,))
    return cursor.fetchone()

# FIX 3: Use ast.literal_eval instead of eval for safe evaluation
def safe_calculate(user_expression):
    try:
        result = ast.literal_eval(user_expression)
        return result
    except (ValueError, SyntaxError):
        return "Invalid expression"
"""

print('\n' + '='*80)
print('🔒 SECURITY ANALYSIS - TESTING FIXED CODE')
print('='*80)

try:
    response = requests.post(
        "http://localhost:8000/analyze/security",
        json={"code": secure_code, "language": "python"}
    )
    response.raise_for_status()
    data = response.json()
    
    print('\n📝 SUMMARY:')
    print('-' * 80)
    print(data['summary'])
    
    critical_or_high = [i for i in data['issues'] if i['severity'] in ['critical', 'high']]
    
    print(f'\n\n⚠️  ISSUES FOUND: {len(data["issues"])}')
    print(f'🔴 CRITICAL/HIGH SEVERITY: {len(critical_or_high)}')
    print('-' * 80)
    
    if data['issues']:
        for i, issue in enumerate(data['issues'], 1):
            severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
            emoji = severity_emoji.get(issue['severity'], '⚪')
            print(f'\n{i}. {emoji} {issue["severity"].upper()} - {issue["category"].upper()}')
            if issue.get('line'):
                print(f'   Line: {issue["line"]}')
            print(f'   Issue: {issue["description"]}')
            print(f'   Fix: {issue["suggestion"]}')
    else:
        print('\n✅ No security issues found!')
    
    if data['suggestions']:
        print('\n\n💡 SUGGESTIONS:')
        print('-' * 80)
        for i, suggestion in enumerate(data['suggestions'], 1):
            print(f'{i}. {suggestion}')
    
    print('\n\n📊 VERDICT:')
    print('-' * 80)
    if critical_or_high:
        print('❌ FAILED - Critical or high severity issues still present')
    else:
        print('✅ PASSED - No critical or high severity security vulnerabilities!')
    
    print('\n' + '='*80 + '\n')
    
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to API: {e}")
    print("Make sure the server is running on http://localhost:8000")
except Exception as e:
    print(f"❌ Error: {e}")
