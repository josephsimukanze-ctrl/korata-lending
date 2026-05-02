# loans/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def process_late_payments_daily():
    """Daily task to process late payments"""
    call_command('process_late_payments')
    
@shared_task
def send_overdue_reminders():
    """Send reminders for overdue payments"""
    from django.core.management import call_command
    call_command('send_overdue_reminders')