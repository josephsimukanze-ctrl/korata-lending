from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_welcome_email(user, password):
    """Send welcome email with login credentials"""
    try:
        subject = f'Welcome to Korata Lending System - Your Account Credentials'
        
        context = {
            'user': user,
            'password': password,
            'login_url': f"{settings.SITE_URL}/admin/login/",
            'site_name': 'Korata Lending System',
            'support_email': settings.DEFAULT_FROM_EMAIL
        }
        
        html_message = render_to_string('users/welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Welcome email sent to {user.email}')
        return True
    except Exception as e:
        logger.error(f'Failed to send welcome email to {user.email}: {str(e)}')
        return False


def send_password_reset_email(user, reset_link):
    """Send password reset email"""
    try:
        subject = 'Password Reset Request - Korata Lending System'
        
        context = {
            'user': user,
            'reset_link': reset_link,
            'site_name': 'Korata Lending System',
            'support_email': settings.DEFAULT_FROM_EMAIL
        }
        
        html_message = render_to_string('users/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Password reset email sent to {user.email}')
        return True
    except Exception as e:
        logger.error(f'Failed to send password reset email to {user.email}: {str(e)}')
        return False


def send_account_activation_email(user, activation_link):
    """Send account activation email"""
    try:
        subject = 'Activate Your Account - Korata Lending System'
        
        context = {
            'user': user,
            'activation_link': activation_link,
            'site_name': 'Korata Lending System'
        }
        
        html_message = render_to_string('users/activation_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send activation email to {user.email}: {str(e)}')
        return False