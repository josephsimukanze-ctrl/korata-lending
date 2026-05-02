from django.db import models
from django.utils import timezone
from decimal import Decimal
from clients.models import Client
from collateral.models import Collateral
from users.models import CustomUser

class Loan(models.Model):
    """Main Loan Model"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('rejected', 'Rejected'),
        ('restructured', 'Restructured'),
    )
    
    INTEREST_PERIOD_CHOICES = (
        ('week', 'Weekly'),
        ('month', 'Monthly'),
    )
    
    # Loan Information
    loan_id = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='loans')
    collateral = models.ForeignKey(Collateral, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans')
    
    # Loan Details
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Interest rate percentage")
    interest_period = models.CharField(max_length=10, choices=INTEREST_PERIOD_CHOICES, default='week')
    duration_weeks = models.IntegerField(help_text="Loan duration in weeks")
    
    # Calculated Fields
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_payback = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    weekly_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Dates
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval Tracking
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_loans')
    approval_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Additional Info
    purpose = models.TextField(blank=True, null=True, help_text="Purpose of the loan")
    notes = models.TextField(blank=True, null=True)
    
    # Tracking
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_loans')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['loan_id']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.loan_id:
            # Generate loan ID: L-YYYY-XXXX
            year = timezone.now().year
            last_loan = Loan.objects.filter(loan_id__startswith=f'L-{year}').order_by('-loan_id').first()
            if last_loan:
                last_num = int(last_loan.loan_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.loan_id = f'L-{year}-{new_num:04d}'
        
        # Calculate financials if not set
        if not self.total_payback:
            self.calculate_loan()
        
        super().save(*args, **kwargs)
    # loans/models.py


    
    # Late payment tracking
    late_payment_count = models.IntegerField(default=0, help_text="Number of late payments")
    late_fee_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total late fees accumulated")
    last_late_fee_applied = models.DateTimeField(null=True, blank=True, help_text="When the last late fee was applied")
    penalty_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Additional penalty interest")
    
    # Late fee configuration (can be moved to settings)
    LATE_FEE_PERCENTAGE = Decimal('0.05')  # 5% of payment
    LATE_FEE_DAYS_THRESHOLD = 3  # Days after due date to apply fee
    PENALTY_INTEREST_INCREMENT = Decimal('1.0')  # 1% increase per late occurrence
    
    def apply_late_fee(self, payment_amount):
        """Apply late fee for overdue payment"""
        fee = payment_amount * self.LATE_FEE_PERCENTAGE
        self.late_fee_total += fee
        self.late_payment_count += 1
        self.last_late_fee_applied = timezone.now()
        
        # Increase penalty interest rate
        self.penalty_interest_rate += self.PENALTY_INTEREST_INCREMENT
        
        # Update total payback with penalty
        self.total_payback += fee
        self.remaining_balance += fee
        
        self.save()
        return fee
    
    def calculate_days_overdue(self, due_date):
        """Calculate days a payment is overdue"""
        if due_date and due_date < timezone.now().date():
            return (timezone.now().date() - due_date).days
        return 0
    
    def is_overdue(self, due_date):
        """Check if payment is overdue"""
        days = self.calculate_days_overdue(due_date)
        return days > self.LATE_FEE_DAYS_THRESHOLD
    def calculate_loan(self):
        """Calculate loan financials"""
        if self.interest_period == 'week':
            self.total_interest = self.principal * (self.interest_rate / 100) * self.duration_weeks
            self.total_payback = self.principal + self.total_interest
            self.weekly_payment = self.total_payback / self.duration_weeks
        else:  # monthly
            months = self.duration_weeks / 4
            self.total_interest = self.principal * (self.interest_rate / 100) * months
            self.total_payback = self.principal + self.total_interest
            self.weekly_payment = self.total_payback / months / 4
        
        self.remaining_balance = self.total_payback
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Current outstanding balance"
    )
    amount_paid = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Total amount paid so far"
    )
    def approve(self, user, notes=None):
        """Approve the loan"""
        self.status = 'approved'
        self.approved_by = user
        self.approval_date = timezone.now()
        self.approval_notes = notes
        self.save()
        
        # Create repayment schedule
        self.create_repayment_schedule()
    
    def activate(self):
        """Activate the loan"""
        self.status = 'active'
        self.start_date = timezone.now().date()
        self.expected_end_date = self.start_date + timezone.timedelta(weeks=self.duration_weeks)
        self.save()
    
    def complete(self):
        """Mark loan as completed"""
        self.status = 'completed'
        self.actual_end_date = timezone.now().date()
        self.save()
    
    def default(self):
        """Mark loan as defaulted"""
        self.status = 'defaulted'
        self.save()
    
    def reject(self, reason):
        """Reject the loan"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save()
    
    def create_repayment_schedule(self):
        """Create repayment schedule for the loan"""
        from .models import RepaymentSchedule
        
        schedule_date = self.start_date or timezone.now().date()
        
        for week in range(1, self.duration_weeks + 1):
            due_date = schedule_date + timezone.timedelta(weeks=week)
            RepaymentSchedule.objects.create(
                loan=self,
                week_number=week,
                due_date=due_date,
                expected_amount=self.weekly_payment
            )
    
    def update_balance(self):
        """Update remaining balance based on payments"""
        from .models import Payment
        
        total_paid = Payment.objects.filter(loan=self).aggregate(total=models.Sum('amount'))['total'] or 0
        self.remaining_balance = self.total_payback - total_paid
        self.save()
    
    @property
    def amount_paid(self):
        """Total amount paid so far"""
        from .models import Payment
        return Payment.objects.filter(loan=self).aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def amount_due(self):
        """Amount due (including penalties)"""
        from .models import RepaymentSchedule
        today = timezone.now().date()
        overdue_schedules = RepaymentSchedule.objects.filter(
            loan=self,
            due_date__lt=today,
            status__in=['pending', 'partial']
        )
        due_amount = overdue_schedules.aggregate(total=models.Sum('expected_amount'))['total'] or 0
        return due_amount
    
    @property
    def is_overdue(self):
        """Check if loan is overdue"""
        from .models import RepaymentSchedule
        today = timezone.now().date()
        return RepaymentSchedule.objects.filter(
            loan=self,
            due_date__lt=today,
            status__in=['pending', 'partial']
        ).exists()
    
    def __str__(self):
        return f"{self.loan_id} - {self.client.full_name} - {self.get_status_display()}"


class RepaymentSchedule(models.Model):
    """Repayment Schedule for each loan"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('partial', 'Partial Payment'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayment_schedules')
    week_number = models.IntegerField()
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_date = models.DateTimeField(null=True, blank=True)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Late fee applied")
    total_due = models.DecimalField(max_digits=12, decimal_places=2, help_text="Expected amount + late fee")
    
    def save(self, *args, **kwargs):
        self.total_due = self.expected_amount + self.late_fee
        super().save(*args, **kwargs)
    class Meta:
        db_table = 'repayment_schedules'
        ordering = ['due_date']
        unique_together = ['loan', 'week_number']
    
    def mark_as_paid(self, amount):
        """Mark payment for this schedule"""
        self.paid_amount += amount
        if self.paid_amount >= self.expected_amount:
            self.status = 'paid'
            self.paid_date = timezone.now()
        elif self.paid_amount > 0:
            self.status = 'partial'
        self.save()
    
    @property
    def remaining_amount(self):
        """Remaining amount for this schedule"""
        return self.expected_amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Check if this schedule is overdue"""
        return self.due_date < timezone.now().date() and self.status in ['pending', 'partial']
    
    def calculate_penalty(self):
        """Calculate penalty for overdue payment"""
        if self.is_overdue:
            days_overdue = (timezone.now().date() - self.due_date).days
            penalty_rate = Decimal('0.0005')  # 0.05% per day
            self.penalty_amount = self.expected_amount * penalty_rate * days_overdue
            self.save()
        return self.penalty_amount
    
    def __str__(self):
        return f"Week {self.week_number} - {self.loan.loan_id} - {self.status}"


class Payment(models.Model):
    """Payment records for loans"""
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card'),
        ('cheque', 'Cheque'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Receipt
    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Tracking
    collected_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='collected_payments')
    notes = models.TextField(blank=True, null=True)
    
    # Penalty
    penalty_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import uuid
            self.receipt_number = f"RCPT-{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)
        
        # Update loan balance
        self.loan.update_balance()
        
        # Update repayment schedule
        self.update_repayment_schedule()
    
    def update_repayment_schedule(self):
        """Update repayment schedule based on payment"""
        from .models import RepaymentSchedule
        
        # Get pending schedules
        pending_schedules = RepaymentSchedule.objects.filter(
            loan=self.loan,
            status__in=['pending', 'partial']
        ).order_by('due_date')
        
        remaining_amount = self.amount
        
        for schedule in pending_schedules:
            if remaining_amount <= 0:
                break
            
            if schedule.remaining_amount > 0:
                payment_to_schedule = min(remaining_amount, schedule.remaining_amount)
                schedule.mark_as_paid(payment_to_schedule)
                remaining_amount -= payment_to_schedule
    
    def __str__(self):
        return f"{self.receipt_number} - {self.loan.loan_id} - {self.amount}"
    
# loans/models.py
class LoanAgreement(models.Model):
    """Loan Agreement Document"""
    loan = models.OneToOneField('Loan', on_delete=models.CASCADE, related_name='agreement')
    agreement_number = models.CharField(max_length=50, unique=True, editable=False)
    agreement_date = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='loan_agreements/', blank=True, null=True)
    
    # Tracking
    signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    # Borrower Signature
    borrower_signed = models.BooleanField(default=False)
    borrower_signature_image = models.ImageField(upload_to='signatures/borrower/', blank=True, null=True)
    borrower_signed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='borrower_signatures')
    borrower_signed_at = models.DateTimeField(null=True, blank=True)
    borrower_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Lender/Collateral Officer Signature
    lender_signed = models.BooleanField(default=False)
    lender_signature_image = models.ImageField(upload_to='signatures/lender/', blank=True, null=True)
    lender_signed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='lender_signatures')
    lender_signed_at = models.DateTimeField(null=True, blank=True)
    lender_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Legacy fields (kept for compatibility)
    signed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_agreements')
    signature_image = models.ImageField(upload_to='signatures/', blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loan_agreements'
        ordering = ['-agreement_date']
    
    def save(self, *args, **kwargs):
        if not self.agreement_number:
            self.agreement_number = self.generate_agreement_number()
        super().save(*args, **kwargs)
    
    def generate_agreement_number(self):
        from django.utils.crypto import get_random_string
        year = timezone.now().year
        month = timezone.now().month
        random_str = get_random_string(6, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        return f"AGR-{year}{month:02d}-{random_str}"
    
    def __str__(self):
        return f"Agreement {self.agreement_number} for Loan {self.loan.loan_id}"
    
    @property
    def is_fully_signed(self):
        return self.borrower_signed and self.lender_signed
    
    @property
    def signed_by_client_name(self):
        if self.borrower_signed_by:
            return self.borrower_signed_by.get_full_name() or self.borrower_signed_by.username
        return self.loan.client.full_name
    
    @property
    def signed_by_officer_name(self):
        if self.lender_signed_by:
            return self.lender_signed_by.get_full_name() or self.lender_signed_by.username
        return "Collateral Officer"