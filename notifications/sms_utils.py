# notifications/sms_utils.py
import os
import logging
import re
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SMSProvider:
    """Base SMS Provider Class"""
    
    def __init__(self):
        self.name = "Base Provider"
    
    def send(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        raise NotImplementedError
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number to international format"""
        # Remove any whitespace
        phone_number = re.sub(r'\s+', '', phone_number)
        
        # Remove any non-digit characters except '+'
        phone_number = re.sub(r'[^\d+]', '', phone_number)
        
        # Format for Zambia (+260)
        if phone_number.startswith('0'):
            phone_number = '+260' + phone_number[1:]
        elif not phone_number.startswith('+'):
            phone_number = '+260' + phone_number
        
        return phone_number
    
    def truncate_message(self, message: str, max_length: int = 160) -> str:
        """Truncate message to SMS length limit"""
        if len(message) > max_length:
            # Add ellipsis and truncate
            return message[:max_length - 3] + "..."
        return message


class AfricaTalkingSMSProvider(SMSProvider):
    """Africa's Talking SMS Provider"""
    
    def __init__(self):
        super().__init__()
        self.name = "Africa's Talking"
        self.username = getattr(settings, 'AFRICASTALKING_USERNAME', '')
        self.api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
        self.shortcode = getattr(settings, 'SMS_SHORTCODE', '')
        
        if not self.username or not self.api_key:
            logger.warning("Africa's Talking credentials not configured")
    
    def send(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """Send SMS using Africa's Talking API"""
        try:
            import africastalking
            
            # Initialize Africa's Talking
            africastalking.initialize(self.username, self.api_key)
            sms = africastalking.SMS
            
            # Format phone number
            phone = self.format_phone_number(phone_number)
            formatted_message = self.truncate_message(message)
            
            # Send SMS
            sender = sender_id or self.shortcode or None
            response = sms.send(formatted_message, [phone], sender)
            
            logger.info(f"Africa's Talking SMS sent to {phone}: {response}")
            
            return {
                'success': True,
                'provider': self.name,
                'phone_number': phone,
                'message_id': response.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId'),
                'status': response.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('status')
            }
            
        except Exception as e:
            logger.error(f"Africa's Talking SMS failed: {str(e)}")
            return {
                'success': False,
                'provider': self.name,
                'error': str(e)
            }


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS Provider (Backup)"""
    
    def __init__(self):
        super().__init__()
        self.name = "Twilio"
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured")
    
    def send(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """Send SMS using Twilio API"""
        try:
            from twilio.rest import Client
            
            # Initialize Twilio client
            client = Client(self.account_sid, self.auth_token)
            
            # Format phone number
            phone = self.format_phone_number(phone_number)
            formatted_message = self.truncate_message(message)
            
            # Send SMS
            from_number = sender_id or self.phone_number
            message_obj = client.messages.create(
                body=formatted_message,
                from_=from_number,
                to=phone
            )
            
            logger.info(f"Twilio SMS sent to {phone}: {message_obj.sid}")
            
            return {
                'success': True,
                'provider': self.name,
                'phone_number': phone,
                'message_id': message_obj.sid,
                'status': message_obj.status
            }
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return {
                'success': False,
                'provider': self.name,
                'error': str(e)
            }


class MessageBirdSMSProvider(SMSProvider):
    """MessageBird SMS Provider"""
    
    def __init__(self):
        super().__init__()
        self.name = "MessageBird"
        self.api_key = getattr(settings, 'MESSAGEBIRD_API_KEY', '')
        
        if not self.api_key:
            logger.warning("MessageBird credentials not configured")
    
    def send(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """Send SMS using MessageBird API"""
        try:
            import requests
            
            # Format phone number
            phone = self.format_phone_number(phone_number)
            formatted_message = self.truncate_message(message)
            
            # API endpoint
            url = "https://rest.messagebird.com/messages"
            
            # Headers
            headers = {
                'Authorization': f'AccessKey {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Payload
            payload = {
                'recipients': [phone],
                'body': formatted_message,
                'originator': sender_id or 'Korata',
                'type': 'sms'
            }
            
            # Send request
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"MessageBird SMS sent to {phone}: {data.get('id')}")
                return {
                    'success': True,
                    'provider': self.name,
                    'phone_number': phone,
                    'message_id': data.get('id'),
                    'status': data.get('status')
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"MessageBird SMS failed: {str(e)}")
            return {
                'success': False,
                'provider': self.name,
                'error': str(e)
            }


class MockSMSProvider(SMSProvider):
    """Mock SMS Provider for Development/Testing"""
    
    def __init__(self):
        super().__init__()
        self.name = "Mock Provider"
    
    def send(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """Mock SMS sending for development"""
        phone = self.format_phone_number(phone_number)
        formatted_message = self.truncate_message(message)
        
        # Log to console
        logger.info(f"[MOCK SMS] To: {phone} | From: {sender_id or 'Korata'} | Message: {formatted_message}")
        
        # Store in cache for testing
        cache_key = f"sms_mock_{phone}_{hash(formatted_message)}"
        cache.set(cache_key, {
            'phone': phone,
            'message': formatted_message,
            'timestamp': timezone.now().isoformat()
        }, 300)
        
        return {
            'success': True,
            'provider': self.name,
            'phone_number': phone,
            'message_id': f"mock_{hash(formatted_message)}",
            'status': 'sent'
        }


class SMSManager:
    """SMS Manager with multiple provider support and fallback"""
    
    def __init__(self):
        self.providers = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize SMS providers in priority order"""
        # Primary: Africa's Talking (best for Africa)
        if getattr(settings, 'AFRICASTALKING_USERNAME', '') and getattr(settings, 'AFRICASTALKING_API_KEY', ''):
            self.providers.append(AfricaTalkingSMSProvider())
        
        # Secondary: MessageBird
        if getattr(settings, 'MESSAGEBIRD_API_KEY', ''):
            self.providers.append(MessageBirdSMSProvider())
        
        # Tertiary: Twilio
        if getattr(settings, 'TWILIO_ACCOUNT_SID', '') and getattr(settings, 'TWILIO_AUTH_TOKEN', ''):
            self.providers.append(TwilioSMSProvider())
        
        # Fallback: Mock provider for development
        if not self.providers or getattr(settings, 'DEBUG', False):
            self.providers.append(MockSMSProvider())
    
    def send_sms(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """
        Send SMS using available providers with fallback
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
            sender_id: Optional sender ID (e.g., 'Korata')
        
        Returns:
            Dict with send status and details
        """
        if not phone_number:
            return {
                'success': False,
                'error': 'No phone number provided'
            }
        
        # Try each provider in order
        for provider in self.providers:
            result = provider.send(phone_number, message, sender_id)
            
            if result['success']:
                # Log successful send
                logger.info(f"SMS sent via {provider.name} to {phone_number}")
                return result
            else:
                # Log failed attempt
                logger.warning(f"SMS failed via {provider.name}: {result.get('error')}")
                continue
        
        # All providers failed
        logger.error(f"All SMS providers failed for {phone_number}")
        return {
            'success': False,
            'error': 'All SMS providers failed',
            'providers_tried': [p.name for p in self.providers]
        }
    
    def send_bulk_sms(self, phone_numbers: list, message: str, sender_id: str = None) -> Dict[str, Any]:
        """
        Send bulk SMS to multiple recipients
        
        Args:
            phone_numbers: List of recipient phone numbers
            message: SMS message content
            sender_id: Optional sender ID
        
        Returns:
            Dict with summary of sends
        """
        results = {
            'total': len(phone_numbers),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for phone in phone_numbers:
            result = self.send_sms(phone, message, sender_id)
            results['details'].append(result)
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def send_scheduled_sms(self, phone_number: str, message: str, send_time, sender_id: str = None):
        """
        Schedule SMS for future delivery
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
            send_time: datetime object for scheduled send
            sender_id: Optional sender ID
        """
        from django_q.tasks import schedule
        
        # Schedule task using Django Q
        schedule(
            'notifications.sms_utils.send_sms_task',
            phone_number,
            message,
            sender_id,
            schedule_type='O',
            next_run=send_time
        )
        
        logger.info(f"SMS scheduled for {phone_number} at {send_time}")

# Global SMS manager instance
sms_manager = SMSManager()


def send_sms(phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
    """
    Send SMS notification (main entry point)
    
    Args:
        phone_number: Recipient phone number
        message: SMS message content
        sender_id: Optional sender ID (e.g., 'Korata')
    
    Returns:
        Dict with send status
    """
    return sms_manager.send_sms(phone_number, message, sender_id)


def send_bulk_sms(phone_numbers: list, message: str, sender_id: str = None) -> Dict[str, Any]:
    """Send bulk SMS notifications"""
    return sms_manager.send_bulk_sms(phone_numbers, message, sender_id)


def send_scheduled_sms(phone_number: str, message: str, send_time, sender_id: str = None):
    """Schedule SMS for future delivery"""
    return sms_manager.send_scheduled_sms(phone_number, message, send_time, sender_id)


# SMS Templates
class SMSTemplates:
    """Pre-defined SMS templates"""
    
    @staticmethod
    def welcome(user, password):
        return f"""Welcome to Korata Lending! Your account has been created.
Username: {user.username}
Password: {password}
Login: {settings.SITE_URL}/users/login/
Please change your password immediately."""
    
    @staticmethod
    def loan_approved(loan):
        return f"""✅ Loan Approved! Your loan #{loan.loan_id} of ZMW {loan.principal:,.2f} has been approved. Funds will be disbursed within 24 hours."""
    
    @staticmethod
    def payment_reminder(payment):
        return f"""⏰ Payment Reminder: Your payment of ZMW {payment.amount:,.2f} for loan #{payment.loan.loan_id} is due on {payment.payment_date}. Late payments may incur penalties."""
    
    @staticmethod
    def payment_received(payment):
        return f"""💰 Payment Received: We've received your payment of ZMW {payment.amount:,.2f} for loan #{payment.loan.loan_id}. Thank you!"""
    
    @staticmethod
    def otp_code(code):
        return f"""Your Korata verification code is: {code}. This code expires in 10 minutes. Do not share this code with anyone."""
    
    @staticmethod
    def password_changed():
        return f"""🔑 Your Korata account password was changed. If you didn't make this change, contact support immediately."""
    
    @staticmethod
    def login_alert(device, time):
        return f"""🔐 Security Alert: New login to your Korata account from {device} at {time}. If this wasn't you, contact support."""
    
    @staticmethod
    def loan_disbursed(loan):
        return f"""💵 Loan Disbursed: ZMW {loan.principal:,.2f} has been disbursed for loan #{loan.loan_id}. First payment due on {loan.first_payment_date}."""
    
    @staticmethod
    def collateral_verified(collateral):
        return f"""✓ Collateral Verified: Your {collateral.title} has been verified and is now active for loan applications."""
    
    @staticmethod
    def kyc_verified(user):
        return f"""✓ KYC Complete: Your KYC verification has been approved. You can now apply for loans up to ZMW {user.credit_limit:,.2f}."""


# Async task for scheduled SMS
def send_sms_task(phone_number: str, message: str, sender_id: str = None):
    """Async task for sending SMS"""
    return send_sms(phone_number, message, sender_id)