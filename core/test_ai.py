#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append('/home/kali/website/korata_lending')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'korata_lending.settings')
django.setup()

from core.ai_service import ai_assistant

def test_ai():
    print("=" * 50)
    print("Testing AI Assistant")
    print("=" * 50)
    
    print(f"\n📊 Status:")
    print(f"  Provider: {ai_assistant.current_provider}")
    print(f"  Model: {ai_assistant.model}")
    print(f"  Ollama: {ai_assistant.use_ollama}")
    print(f"  OpenAI: {ai_assistant.openai_client is not None}")
    
    print("\n" + "=" * 50)
    print("Testing Questions:")
    print("=" * 50)
    
    questions = [
        ("Interest Rate", "What is the interest rate for a loan?"),
        ("Late Payment", "What happens if I miss a payment?"),
        ("Collateral", "How does collateral work?"),
        ("KYC", "What documents do I need for KYC?"),
        ("Loan Requirements", "What are the loan requirements?"),
        ("Payment Methods", "How can I make a payment?"),
    ]
    
    for name, question in questions:
        print(f"\n📝 [{name}]")
        print(f"   User: {question}")
        
        result = ai_assistant.get_response(question)
        
        print(f"   Provider: {result.get('provider', 'unknown')}")
        print(f"   Intent: {result.get('intent', 'unknown')}")
        print(f"   Response: {result['response'][:150]}...")
        
        if not result.get('success'):
            print(f"   ❌ Error: {result.get('error')}")
        else:
            print(f"   ✅ Success")
    
    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)

if __name__ == "__main__":
    test_ai()