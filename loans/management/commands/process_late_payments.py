# loans/management/commands/process_late_payments.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from loans.models import Loan, RepaymentSchedule
from notifications.models import Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Process late payments and apply automatic penalties'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Processing Late Payments - {today}")
        self.stdout.write(f"{'='*60}\n")
        
        # Get all overdue repayment schedules
        overdue_schedules = RepaymentSchedule.objects.filter(
            status='pending',
            due_date__lt=today,
            loan__status='active'
        ).select_related('loan__client')
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))
        
        total_loans_affected = set()
        total_fees_collected = Decimal('0')
        
        for schedule in overdue_schedules:
            loan = schedule.loan
            days_overdue = (today - schedule.due_date).days
            
            self.stdout.write(f"\nProcessing: Loan {loan.loan_id} - Client: {loan.client.full_name}")
            self.stdout.write(f"  Due Date: {schedule.due_date}")
            self.stdout.write(f"  Days Overdue: {days_overdue}")
            self.stdout.write(f"  Amount Due: ZMW {schedule.expected_amount:,.2f}")
            
            # Check if late fee should be applied
            if days_overdue >= 3:  # Apply after 3 days
                late_fee = schedule.expected_amount * Decimal('0.05')  # 5% late fee
                self.stdout.write(f"  Late Fee: ZMW {late_fee:,.2f}")
                
                if not dry_run:
                    # Apply late fee to schedule
                    schedule.late_fee = late_fee
                    schedule.total_due = schedule.expected_amount + late_fee
                    schedule.status = 'overdue'
                    schedule.save()
                    
                    # Update loan totals
                    loan.late_fee_total += late_fee
                    loan.total_payback += late_fee
                    loan.remaining_balance += late_fee
                    loan.late_payment_count += 1
                    loan.penalty_interest_rate += Decimal('1.0')
                    loan.save()
                    
                    # Create notification for client
                    Notification.objects.create(
                        user=loan.client.registered_by,
                        title='Late Payment Penalty Applied',
                        message=f'A late fee of ZMW {late_fee:,.2f} has been applied to loan {loan.loan_id} for overdue payment.',
                        notification_type='alert',
                        priority='high',
                        link=f'/loans/{loan.id}/'
                    )
                    
                    total_fees_collected += late_fee
                
                total_loans_affected.add(loan.id)
            else:
                self.stdout.write(f"  Not yet eligible for late fee (needs 3+ days)")
        
        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("SUMMARY")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Total Overdue Schedules: {overdue_schedules.count()}")
        self.stdout.write(f"Loans Affected: {len(total_loans_affected)}")
        self.stdout.write(f"Total Late Fees: ZMW {total_fees_collected:,.2f}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\n✓ Successfully processed {overdue_schedules.count()} overdue payments"))
        else:
            self.stdout.write(self.style.WARNING("\n✓ Dry run completed - No changes made"))