"""
Security Vulnerabilities Fixed
This file demonstrates the security issues found and their fixes.
"""

print("=" * 80)
print("SECURITY VULNERABILITIES - BEFORE AND AFTER")
print("=" * 80)

# =============================================================================
# Issue 1: HARDCODED PASSWORD
# =============================================================================
print("\n1. HARDCODED PASSWORD")
print("-" * 80)

print("\n❌ VULNERABLE CODE:")
print('''
import os
password = "admin123"  # Hardcoded secret!
''')

print("\n✅ FIXED CODE:")
print('''
import os
from dotenv import load_dotenv

load_dotenv()
password = os.getenv("PASSWORD")  # Load from environment variable

# Or for production, use a secrets manager:
# import boto3
# client = boto3.client('secretsmanager')
# response = client.get_secret_value(SecretId='my-secret')
# password = response['SecretString']
''')

# =============================================================================
# Issue 2: SQL INJECTION
# =============================================================================
print("\n2. SQL INJECTION VULNERABILITY")
print("-" * 80)

print("\n❌ VULNERABLE CODE:")
print('''
import sqlite3

def get_user(user_input):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Dangerous: Direct string concatenation
    query = "SELECT * FROM users WHERE id = " + user_input
    cursor.execute(query)
    return cursor.fetchone()
''')

print("\n✅ FIXED CODE:")
print('''
import sqlite3

def get_user(user_input):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Safe: Parameterized query
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_input,))
    return cursor.fetchone()

# Or with a different database library:
# cursor.execute("SELECT * FROM users WHERE id = %s", (user_input,))
''')

# =============================================================================
# Issue 3: ARBITRARY CODE EXECUTION
# =============================================================================
print("\n3. ARBITRARY CODE EXECUTION (eval)")
print("-" * 80)

print("\n❌ VULNERABLE CODE:")
print('''
def calculate(user_code):
    # Extremely dangerous: Execute arbitrary code
    result = eval(user_code)
    return result

# An attacker could pass: "__import__('os').system('rm -rf /')"
''')

print("\n✅ FIXED CODE:")
print('''
import ast

def calculate(user_expression):
    try:
        # Safe: Only evaluate literal expressions
        result = ast.literal_eval(user_expression)
        return result
    except (ValueError, SyntaxError):
        return "Invalid expression"

# For mathematical expressions, use a safe parser:
import operator
import ast

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

def safe_eval_math(expr_str):
    """Safely evaluate mathematical expressions"""
    try:
        node = ast.parse(expr_str, mode='eval')
        
        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            elif isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type not in ALLOWED_OPERATORS:
                    raise ValueError(f"Operator not allowed: {op_type}")
                left = _eval(node.left)
                right = _eval(node.right)
                return ALLOWED_OPERATORS[op_type](left, right)
            else:
                raise ValueError(f"Unsupported node type: {type(node)}")
        
        return _eval(node)
    except Exception as e:
        return f"Error: {e}"

# Usage:
# result = safe_eval_math("2 + 3 * 4")  # Returns 14
# result = safe_eval_math("__import__('os')")  # Returns error
''')

print("\n" + "=" * 80)
print("All security vulnerabilities have been addressed!")
print("=" * 80)
