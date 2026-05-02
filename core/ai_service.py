# core/ai_service.py - Optimized for concise responses

import logging
import ollama

logger = logging.getLogger(__name__)

class AILendingAssistant:
    """AI Assistant using Ollama with TinyLlama"""
    
    def __init__(self):
        self.model = 'tinyllama'
        self.is_available = False
        
        # Test connection
        try:
            test_response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                options={'num_predict': 5}
            )
            self.is_available = True
            print(f"✅ AI Assistant ready! Using model: {self.model}")
        except Exception as e:
            print(f"❌ AI Assistant error: {e}")
    
    def get_response(self, user_message, conversation_history=None):
        """Get AI response using Ollama"""
        
        if not self.is_available:
            return {
                'success': False,
                'response': "AI service is initializing. Please try again in a moment.",
                'provider': 'unavailable'
            }
        
        try:
            # Improved system prompt for concise responses
            system_prompt = """You are Korata AI, a helpful assistant for Korata Lending System in Zambia.

CRITICAL RULES:
1. Keep responses VERY SHORT (1-2 sentences maximum)
2. Be direct and specific - no fluff or examples
3. Answer ONLY the question asked
4. Use emojis sparingly (only 📊 ⚠️ 🏠 💳 ✅)

Key Information:
- Interest rates: 5% to 15% per annum
- Late payment penalty: 5% fee
- Collateral types: Vehicles (70-80% LTV), Property (60-70% LTV), Equipment (50-60% LTV), Jewelry (40-50% LTV)
- Payment methods: Mobile Money, Bank Transfer, Cash, Card
- KYC documents: NRC/Passport, proof of residence, proof of income
- Processing time: 24-48 hours after KYC verification

EXAMPLE GOOD RESPONSES:
Q: "What is the interest rate?" 
A: "📊 Interest rates range from 5% to 15% per annum."

Q: "What happens if I miss a payment?"
A: "⚠️ Late payments incur a 5% penalty fee."

Q: "How does collateral work?"
A: "🏠 We accept vehicles, property, equipment, and jewelry as collateral."

Q: "How long does processing take?"
A: "✅ Processing takes 24-48 hours after KYC verification."

Now answer the user's question in the SAME style - very short and direct."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Get response from Ollama with shorter output
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': 0.5,  # Lower temperature for more consistent responses
                    'num_predict': 100  # Limit response length
                }
            )
            
            ai_response = response['message']['content'].strip()
            
            # Clean up response - remove any "User:" or "Response:" prefixes
            ai_response = ai_response.replace('User:', '').replace('Response:', '').strip()
            
            # If response is too long, truncate
            if len(ai_response) > 300:
                ai_response = ai_response[:297] + "..."
            
            return {
                'success': True,
                'response': ai_response,
                'provider': 'ollama',
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return {
                'success': False,
                'response': self.get_fallback_response(user_message),
                'provider': 'error'
            }
    
    def get_fallback_response(self, user_message):
        """Short fallback responses"""
        msg = user_message.lower()
        
        if 'interest' in msg:
            return "📊 Interest rates: 5% to 15% per annum"
        
        if 'late' in msg or 'miss' in msg:
            return "⚠️ Late payment penalty: 5% fee"
        
        if 'collateral' in msg:
            return "🏠 We accept vehicles, property, equipment, and jewelry as collateral"
        
        if 'payment' in msg:
            return "💳 Payment methods: Mobile Money, Bank Transfer, Cash, Card"
        
        if 'kyc' in msg or 'document' in msg:
            return "✅ Required: NRC/Passport, proof of residence, proof of income"
        
        if 'processing' in msg or 'time' in msg:
            return "⏱️ Processing takes 24-48 hours after KYC verification"
        
        if 'requirement' in msg:
            return "📋 Requirements: Valid ID, proof of income, collateral, KYC verification"
        
        return "I can help with interest rates, payments, collateral, and loan requirements. What would you like to know?"

# Initialize global AI assistant
ai_assistant = AILendingAssistant()