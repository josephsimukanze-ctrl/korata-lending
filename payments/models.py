from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()

class PaymentMethod(models.Model):
    """Payment methods like Cash, Bank Transfer, Mobile Money, etc."""
    METHOD_TYPES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    account_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    mobile_provider = models.CharField(max_length=50, blank=True, null=True)  # MTN, Airtel, etc.
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    processing_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    processing_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.get_method_type_display()} - {self.name}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentCategory(models.Model):
    """Categories for payments (Loan Repayment, Processing Fee, Late Fee, etc.)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Payment Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Payment(models.Model):
    """Main Payment Model for tracking all financial transactions"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_TYPES = [
        ('loan_repayment', 'Loan Repayment'),
        ('processing_fee', 'Processing Fee'),
        ('late_fee', 'Late Fee'),
        ('penalty', 'Penalty'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]
    
    # Relationships - Using unique related_name to avoid conflicts
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payment_transactions')
    loan = models.ForeignKey('loans.Loan', on_delete=models.CASCADE, related_name='payment_transactions', null=True, blank=True)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, related_name='payment_transactions')
    category = models.ForeignKey('PaymentCategory', on_delete=models.SET_NULL, null=True, related_name='payment_transactions')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payment_transactions')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payment_transactions')
    
    # Payment Details
    payment_id = models.CharField(max_length=50, unique=True, editable=False)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='loan_repayment')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount applied to this payment")
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tax amount for this payment")
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)  # amount + processing_fee + tax - discount
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Payment Reference Information
    transaction_reference = models.CharField(max_length=200, blank=True, null=True, help_text="Bank transaction ID or reference")
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    mobile_transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Mobile money transaction ID")
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, null=True, help_text="Related invoice number")
    
    # Dates
    payment_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(blank=True, null=True, help_text="Due date for this payment")
    approved_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional Info
    notes = models.TextField(blank=True, null=True)
    receipt_upload = models.FileField(upload_to='payments/receipts/%Y/%m/', blank=True, null=True)
    attachment = models.FileField(upload_to='payments/attachments/%Y/%m/', blank=True, null=True)
    
    # Tracking
    is_verified = models.BooleanField(default=False, help_text="Whether the payment has been verified")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verified_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['client', 'payment_date']),
            models.Index(fields=['payment_type']),
            models.Index(fields=['transaction_reference']),
        ]
    
    def __str__(self):
        return f"{self.payment_id} - {self.client.full_name} - {self.get_payment_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Override save to calculate total amount and generate payment ID"""
        if not self.payment_id:
            self.payment_id = self.generate_payment_id()
        
        # Calculate total amount: amount + processing_fee + tax - discount
        self.total_amount = self.amount + self.processing_fee + self.tax - self.discount
        
        # Ensure total amount is not negative
        if self.total_amount < 0:
            self.total_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    def generate_payment_id(self):
        """Generate unique payment ID: PAY-YYYYMMDD-XXXX"""
        from django.utils.crypto import get_random_string
        
        # Get the count of payments today for sequential numbering
        today = timezone.now().date()
        today_count = Payment.objects.filter(payment_date__date=today).count() + 1
        
        date_str = timezone.now().strftime('%Y%m%d')
        sequential = str(today_count).zfill(4)
        random_suffix = get_random_string(2, allowed_chars='0123456789ABCDEF')
        
        return f"PAY-{date_str}-{sequential}{random_suffix}"
    
    @property
    def is_approved(self):
        """Check if payment is approved"""
        return self.status == 'completed'
    
    @property
    def is_pending(self):
        """Check if payment is pending"""
        return self.status == 'pending'
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.due_date and self.status == 'pending':
            return timezone.now() > self.due_date
        return False
    
    @property
    def net_amount(self):
        """Calculate net amount after fees and discounts"""
        return self.total_amount
    
    @property
    def formatted_amount(self):
        """Return formatted amount with currency"""
        return f"ZMW {self.amount:,.2f}"
    
    @property
    def formatted_total(self):
        """Return formatted total amount with currency"""
        return f"ZMW {self.total_amount:,.2f}"
    
    def approve(self, user, notes=None):
        """Approve the payment"""
        if self.status != 'pending':
            raise ValueError(f"Cannot approve payment with status: {self.status}")
        
        self.status = 'completed'
        self.approved_by = user
        self.approved_date = timezone.now()
        
        if notes:
            self.notes = f"{self.notes}\n\nApproval notes: {notes}" if self.notes else f"Approval notes: {notes}"
        
        self.save()
        
        # Update loan balance if this is a loan repayment
        if self.loan and self.payment_type == 'loan_repayment':
            self.update_loan_balance()
        
        # Create notification
        self.create_notification('payment_confirmation')
        
        return True
    
    def reject(self, user, reason):
        """Reject the payment"""
        if self.status != 'pending':
            raise ValueError(f"Cannot reject payment with status: {self.status}")
        
        self.status = 'failed'
        self.notes = f"{self.notes}\n\nRejection reason: {reason}" if self.notes else f"Rejection reason: {reason}"
        self.save()
        
        # Create notification
        self.create_notification('payment_failed')
        
        return True
    
    def cancel(self, user, reason):
        """Cancel the payment"""
        if self.status not in ['pending', 'completed']:
            raise ValueError(f"Cannot cancel payment with status: {self.status}")
        
        original_status = self.status
        self.status = 'cancelled'
        self.notes = f"{self.notes}\n\nCancellation reason: {reason}" if self.notes else f"Cancellation reason: {reason}"
        self.save()
        
        # If payment was completed, reverse loan balance
        if original_status == 'completed' and self.loan and self.payment_type == 'loan_repayment':
            self.reverse_loan_balance()
        
        # Create notification
        self.create_notification('payment_cancelled')
        
        return True
    
    def refund(self, amount=None, reason=None, user=None):
        """Process refund for this payment"""
        from .models import PaymentRefund
        
        refund_amount = amount or self.amount
        
        # Validate refund amount
        if refund_amount > self.amount:
            raise ValueError(f"Refund amount ({refund_amount}) cannot exceed payment amount ({self.amount})")
        
        # Check if already fully refunded
        if self.status == 'refunded':
            raise ValueError("Payment has already been fully refunded")
        
        # Calculate total refunded amount
        total_refunded = self.refunds.filter(status__in=['approved', 'completed']).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if total_refunded + refund_amount > self.amount:
            raise ValueError(f"Total refund amount would exceed payment amount")
        
        # Create refund record
        refund = PaymentRefund.objects.create(
            original_payment=self,
            amount=refund_amount,
            reason=reason or "Customer requested refund",
            requested_by=user or self.created_by
        )
        
        # Update payment status
        if total_refunded + refund_amount >= self.amount:
            self.status = 'refunded'
        else:
            self.status = 'partially_refunded'
        
        self.save()
        
        # Update loan balance if needed
        if self.loan and self.payment_type == 'loan_repayment':
            self.reverse_loan_balance(refund_amount)
        
        # Create notification
        self.create_notification('payment_refunded')
        
        return refund
    
    def update_loan_balance(self):
        """Update the associated loan balance"""
        if self.loan:
            # Reduce loan balance by the payment amount
            self.loan.balance = max(Decimal('0.00'), self.loan.balance - self.amount)
            
            # Update loan status if balance is zero
            if self.loan.balance == 0:
                self.loan.status = 'completed'
            
            self.loan.save()
    
    def reverse_loan_balance(self, amount=None):
        """Reverse the loan balance update (for refunds/cancellations)"""
        if self.loan:
            reverse_amount = amount or self.amount
            self.loan.balance += reverse_amount
            
            # Update loan status if it was completed
            if self.loan.status == 'completed' and self.loan.balance > 0:
                self.loan.status = 'active'
            
            self.loan.save()
    
    def create_notification(self, notification_type):
        """Create a notification for this payment"""
        from .models import PaymentNotification
        
        notification_messages = {
            'payment_confirmation': f'Your payment of {self.formatted_amount} has been confirmed and processed.',
            'payment_failed': f'Your payment of {self.formatted_amount} could not be processed. Please contact support.',
            'payment_cancelled': f'Your payment of {self.formatted_amount} has been cancelled.',
            'payment_refunded': f'A refund of {self.formatted_amount} has been processed for your payment.',
        }
        
        subject = f"Payment {notification_type.replace('_', ' ').title()} - {self.payment_id}"
        message = notification_messages.get(notification_type, f"Payment update for {self.payment_id}")
        
        PaymentNotification.objects.create(
            client=self.client,
            payment=self,
            notification_type=notification_type,
            sent_via='system',
            subject=subject,
            message=message
        )
    
    @classmethod
    def get_payment_summary(cls, client=None, start_date=None, end_date=None):
        """Get payment summary for a client or date range"""
        queryset = cls.objects.filter(status='completed')
        
        if client:
            queryset = queryset.filter(client=client)
        
        if start_date:
            queryset = queryset.filter(payment_date__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(payment_date__date__lte=end_date)
        
        return {
            'total_count': queryset.count(),
            'total_amount': queryset.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00'),
            'total_fees': queryset.aggregate(total=models.Sum('processing_fee'))['total'] or Decimal('0.00'),
            'by_type': queryset.values('payment_type').annotate(
                count=models.Count('id'),
                total=models.Sum('amount')
            ),
            'by_method': queryset.values('payment_method__name').annotate(
                count=models.Count('id'),
                total=models.Sum('amount')
            ),
        }

class PaymentRefund(models.Model):
    """Track payment refunds"""
    REFUND_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    original_payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_refunds')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refunds')
    transaction_reference = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund for {self.original_payment.payment_id} - {self.amount}"
    
    def approve(self, user):
        self.status = 'approved'
        self.approved_by = user
        self.save()
    
    def complete(self, user, reference=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if reference:
            self.transaction_reference = reference
        self.save()


class ScheduledPayment(models.Model):
    """Recurring/Scheduled Payments"""
    FREQUENCY = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='scheduled_payments')
    loan = models.ForeignKey('loans.Loan', on_delete=models.CASCADE, related_name='scheduled_payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    next_payment_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['next_payment_date']
    
    def __str__(self):
        return f"Scheduled payment for {self.client.full_name} - {self.amount} {self.frequency}"
    
    def update_next_payment_date(self):
        """Update the next payment date based on frequency"""
        from datetime import timedelta
        
        if self.frequency == 'daily':
            self.next_payment_date += timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_payment_date += timedelta(days=7)
        elif self.frequency == 'biweekly':
            self.next_payment_date += timedelta(days=14)
        elif self.frequency == 'monthly':
            # Add month (handle different month lengths)
            month = self.next_payment_date.month
            year = self.next_payment_date.year
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            self.next_payment_date = self.next_payment_date.replace(year=next_year, month=next_month)
        elif self.frequency == 'quarterly':
            # Add 3 months
            month = self.next_payment_date.month
            year = self.next_payment_date.year
            next_month = month + 3
            next_year = year
            if next_month > 12:
                next_month -= 12
                next_year += 1
            self.next_payment_date = self.next_payment_date.replace(year=next_year, month=next_month)
        
        self.save()


class PaymentNotification(models.Model):
    """Track payment notifications sent to clients"""
    NOTIFICATION_TYPES = [
        ('payment_due', 'Payment Due'),
        ('payment_received', 'Payment Received'),
        ('payment_overdue', 'Payment Overdue'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('receipt', 'Receipt'),
    ]
    
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payment_notifications')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    sent_via = models.CharField(max_length=50)  # email, sms, push
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.client.full_name} - {self.sent_at}"