# core/management/commands/test_ai.py
from django.core.management.base import BaseCommand
from core.ai_service import ai_assistant

class Command(BaseCommand):
    help = 'Test AI assistant functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing AI Assistant...'))
        self.stdout.write(f"Provider: {ai_assistant.current_provider}")
        self.stdout.write(f"Model: {ai_assistant.model}")
        self.stdout.write(f"Ollama available: {ai_assistant.use_ollama}")
        self.stdout.write(f"OpenAI available: {ai_assistant.openai_client is not None}")
        
        # Test messages
        test_messages = [
            "What is the interest rate?",
            "What happens if I miss a payment?",
            "How does collateral work?"
        ]
        
        for msg in test_messages:
            self.stdout.write(f"\n📝 User: {msg}")
            result = ai_assistant.get_response(msg)
            self.stdout.write(f"🤖 AI: {result['response'][:200]}...")
            self.stdout.write(f"Provider: {result.get('provider')}")