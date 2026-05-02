# loans/management/commands/send_overdue_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from loans.models import RepaymentSchedule
from notifications.models import Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send reminders for overdue payments'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get schedules that are 1, 3, 7 days overdue
        for days in [1, 3, 7]:
            target_date = today - timedelta(days=days)
            schedules = RepaymentSchedule.objects.filter(
                status='pending',
                due_date=target_date,
                loan__status='active'
            ).select_related('loan__client')
            
            for schedule in schedules:
                loan = schedule.loan
                message = self.get_message_by_days(days, schedule, loan)
                
                # Send notification
                Notification.objects.create(
                    user=loan.client.registered_by,
                    title=f'Payment Overdue - {days} Day{"s" if days > 1 else ""}',
                    message=message,
                    notification_type='alert',
                    priority='high',
                    link=f'/loans/{loan.id}/'
                )
                
                self.stdout.write(f"Sent reminder to {loan.client.full_name} - {days} days overdue")
    
    def get_message_by_days(self, days, schedule, loan):
        if days == 1:
            return f"⚠️ Your payment of ZMW {schedule.expected_amount:,.2f} for loan {loan.loan_id} is 1 day overdue. Please make payment to avoid late fees."
        elif days == 3:
            late_fee = schedule.expected_amount * Decimal('0.05')
            return f"🔴 Late fee of ZMW {late_fee:,.2f} has been applied to loan {loan.loan_id}. Total due: ZMW {schedule.expected_amount + late_fee:,.2f}"
        else:
            return f"🚨 URGENT: Your payment for loan {loan.loan_id} is {days} days overdue. Immediate action required to avoid escalation."