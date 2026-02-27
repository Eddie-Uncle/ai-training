#!/usr/bin/env python3
"""Test the code analyzer and display results in a pretty format."""
import json
import requests

# Test code to analyze
test_code = """def add(a,b):
    return a+b

def process(data):
    if not isinstance(data, list):
        raise TypeError("data must be a list")
    result=[]
    for i in range(len(data)):
        if not isinstance(data[i], (int, float)):
            raise TypeError(f"Element at index {i} must be numeric")
        if data[i]>0:
            result.append(data[i]*2)
    return result"""

# Make the API request
try:
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"code": test_code, "language": "python"}
    )
    response.raise_for_status()
    data = response.json()
    
    # Pretty print the results
    print('\n' + '='*80)
    print('📊 CODE ANALYSIS REPORT')
    print('='*80)
    
    print('\n📝 SUMMARY:')
    print('-' * 80)
    print(data['summary'])
    
    print(f'\n\n⚠️  ISSUES FOUND: {len(data["issues"])}')
    print('-' * 80)
    for i, issue in enumerate(data['issues'], 1):
        severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        emoji = severity_emoji.get(issue['severity'], '⚪')
        print(f'\n{i}. {emoji} {issue["severity"].upper()} - {issue["category"].upper()}')
        if issue['line']:
            print(f'   Line: {issue["line"]}')
        print(f'   Issue: {issue["description"]}')
        print(f'   Fix: {issue["suggestion"]}')
    
    print('\n\n💡 SUGGESTIONS:')
    print('-' * 80)
    for i, suggestion in enumerate(data['suggestions'], 1):
        print(f'{i}. {suggestion}')
    
    print('\n\n📈 METRICS:')
    print('-' * 80)
    metrics = data['metrics']
    print(f'   Complexity: {metrics["complexity"].upper()}')
    print(f'   Readability: {metrics["readability"].upper()}')
    print(f'   Test Coverage: {metrics["test_coverage_estimate"].upper()}')
    
    print('\n' + '='*80 + '\n')
    
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to API: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
