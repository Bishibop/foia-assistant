#!/usr/bin/env python3
"""Debug script to test OpenAI API key."""

import os

from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

print(f"API Key loaded: {'Yes' if api_key else 'No'}")
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"API Key starts with: {api_key[:20]}..." if api_key else "No key found")
print(f"API Key ends with: ...{api_key[-20:]}" if api_key else "No key found")

# Try a simple API call
try:
    client = OpenAI(api_key=api_key)

    # Simple test
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'API key is working!'"}],
        max_tokens=10,
    )

    print(f"\nAPI Test Result: {response.choices[0].message.content}")
    print("✅ API key is valid!")

except Exception as e:
    print(f"\n❌ API Error: {e}")
    print("\nPossible issues:")
    print("1. The API key might be invalid or expired")
    print("2. You might not have access to the model")
    print("3. Your account might not have credits")
    print("\nPlease check: https://platform.openai.com/api-keys")
