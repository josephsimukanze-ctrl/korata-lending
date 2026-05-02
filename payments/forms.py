from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Payment, PaymentMethod, PaymentCategory, ScheduledPayment, PaymentRefund
from decimal import Decimal

# payments/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Payment, PaymentMethod, PaymentCategory, ScheduledPayment, PaymentRefund
from decimal import Decimal

class PaymentForm(forms.ModelForm):
    """Enhanced payment form with Tailwind CSS styling"""
    
    class Meta:
        model = Payment
        fields = [
            'client', 'loan', 'payment_method', 'payment_type', 'category', 'amount',
            'processing_fee', 'discount', 'tax', 'transaction_reference', 
            'cheque_number', 'mobile_transaction_id', 'receipt_number', 'invoice_number',
            'payment_date', 'due_date', 'notes', 'receipt_upload'
        ]
        widgets = {
            'payment_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200',
                'placeholder': 'Additional notes about this payment...'
            }),
            'client': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer'
            }),
            'loan': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer'
            }),
            'payment_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full pl-16 pr-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200',
                'step': '0.01',
                'placeholder': '0.00',
                'value': '0.00'
            }),
            'processing_fee': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'step': '0.01',
                'placeholder': '0.00',
                'value': '0'
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'step': '0.01',
                'placeholder': '0.00',
                'value': '0'
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'step': '0.01',
                'placeholder': '0.00',
                'value': '0'
            }),
            'transaction_reference': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'placeholder': 'Bank transaction ID or reference'
            }),
            'cheque_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'placeholder': 'Cheque number'
            }),
            'mobile_transaction_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'placeholder': 'Mobile money transaction ID'
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'placeholder': 'Receipt number'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all duration-200',
                'placeholder': 'Invoice number'
            }),
            'receipt_upload': forms.FileInput(attrs={
                'class': 'absolute inset-0 w-full h-full opacity-0 cursor-pointer',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['amount'].help_text = 'Enter the payment amount in ZMW'
        self.fields['processing_fee'].help_text = 'Processing fee charged for this payment'
        self.fields['discount'].help_text = 'Discount applied to this payment (if any)'
        self.fields['tax'].help_text = 'Tax amount for this payment'
        self.fields['payment_date'].help_text = 'Date and time when payment was made'
        self.fields['due_date'].help_text = 'Due date for this payment (if applicable)'
        self.fields['transaction_reference'].help_text = 'Bank transaction ID or reference'
        self.fields['mobile_transaction_id'].help_text = 'Mobile money transaction ID'
        self.fields['invoice_number'].help_text = 'Related invoice number'
        
        # Filter querysets
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)
        self.fields['category'].queryset = PaymentCategory.objects.filter(is_active=True)
        
        # Set initial values
        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now()
            self.fields['payment_type'].initial = 'loan_repayment'
            self.fields['processing_fee'].initial = 0
            self.fields['discount'].initial = 0
            self.fields['tax'].initial = 0
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        if amount and amount > 10000000:
            raise ValidationError('Amount exceeds maximum allowed limit (ZMW 10,000,000).')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount', 0)
        discount = cleaned_data.get('discount', 0)
        
        if discount > amount:
            raise ValidationError('Discount cannot exceed the payment amount.')
        
        return cleaned_data
# payments/forms.py - Simplified version

from django import forms

class PaymentApprovalForm(forms.Form):
    """Form for approving payments - Simplified version"""
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-green-500 dark:bg-gray-700 dark:text-white resize-none',
            'placeholder': 'Add approval notes (optional)...'
        }),
        label='Approval Notes'
    )
    
    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        label='Send notification to client',
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-green-600 rounded'})
    )
    
    verify_funds = forms.BooleanField(
        required=False,
        initial=True,
        label='Funds verified',
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-green-600 rounded'})
    )
    
    verify_documents = forms.BooleanField(
        required=False,
        initial=True,
        label='Documents verified',
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-green-600 rounded'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        # No validation errors - form will always be valid
        return cleaned_data

class PaymentRefundForm(forms.ModelForm):
    """Enhanced refund form with better validation"""
    
    class Meta:
        model = PaymentRefund
        fields = ['amount', 'reason', 'notes']
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-textarea',
                'placeholder': 'Detailed reason for the refund...'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2, 
                'class': 'form-textarea',
                'placeholder': 'Additional notes (optional)...'
            }),
        }
        labels = {
            'amount': 'Refund Amount (ZMW)',
            'reason': 'Refund Reason',
            'notes': 'Additional Notes',
        }
    
    def __init__(self, *args, **kwargs):
        self.payment = kwargs.pop('payment', None)
        super().__init__(*args, **kwargs)
        
        if self.payment:
            # Calculate maximum refundable amount
            total_refunded = self.payment.refunds.filter(
                status__in=['approved', 'completed']
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            
            max_refund = self.payment.amount - total_refunded
            
            self.fields['amount'].initial = min(self.payment.amount, max_refund)
            self.fields['amount'].widget.attrs.update({
                'max': float(max_refund),
                'min': '0.01',
                'step': '0.01',
                'class': 'form-input',
                'placeholder': f'Max: {max_refund:.2f}'
            })
            
            # Add help text
            self.fields['amount'].help_text = f'Maximum refundable amount: ZMW {max_refund:.2f}'
            
            # Show already refunded amount
            if total_refunded > 0:
                self.fields['amount'].help_text += f' (Already refunded: ZMW {total_refunded:.2f})'
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise ValidationError('Refund amount is required.')
        
        if amount <= 0:
            raise ValidationError('Refund amount must be greater than zero.')
        
        if self.payment:
            # Calculate already refunded amount
            total_refunded = self.payment.refunds.filter(
                status__in=['approved', 'completed']
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            
            max_refund = self.payment.amount - total_refunded
            
            if amount > max_refund:
                raise ValidationError(f'Refund amount cannot exceed the remaining payment amount (ZMW {max_refund:.2f}).')
        
        return amount


class ScheduledPaymentForm(forms.ModelForm):
    """Enhanced scheduled payment form"""
    
    class Meta:
        model = ScheduledPayment
        fields = ['client', 'loan', 'payment_method', 'amount', 'frequency', 
                  'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0.00'}),
        }
        labels = {
            'frequency': 'Payment Frequency',
            'is_active': 'Active Schedule',
        }
        help_texts = {
            'frequency': 'How often should this payment be processed?',
            'start_date': 'When should the first payment be processed?',
            'end_date': 'Optional: When should this schedule end?',
            'is_active': 'Uncheck to pause this schedule',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        select_fields = ['client', 'loan', 'payment_method', 'frequency']
        for field_name in select_fields:
            self.fields[field_name].widget.attrs['class'] = 'form-select select2'
        
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)
        
        # Set initial values
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['frequency'].initial = 'monthly'
            self.fields['is_active'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        amount = cleaned_data.get('amount')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError('Start date must be before end date.')
        
        if start_date and start_date < timezone.now().date():
            raise ValidationError('Start date cannot be in the past.')
        
        if amount and amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        
        return cleaned_data


class PaymentFilterForm(forms.Form):
    """Enhanced filter form for payment list"""
    
    STATUS_CHOICES = [('', 'All Status')] + list(Payment.PAYMENT_STATUS)
    PAYMENT_TYPE_CHOICES = [('', 'All Types')] + list(Payment.PAYMENT_TYPES)
    
    payment_id = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by payment ID...'
        })
    )
    client_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by client name...'
        })
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        empty_label="All Methods",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    date_to = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    min_amount = forms.DecimalField(
        required=False, 
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Min Amount',
            'step': '0.01'
        })
    )
    max_amount = forms.DecimalField(
        required=False, 
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Max Amount',
            'step': '0.01'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('From date must be before To date.')
        
        if min_amount and max_amount and min_amount > max_amount:
            raise ValidationError('Minimum amount cannot be greater than maximum amount.')
        
        return cleaned_data


class PaymentMethodForm(forms.ModelForm):
    """Form for creating/editing payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'method_type', 'account_name', 'account_number', 
            'bank_name', 'mobile_provider', 'is_active', 'is_default',
            'processing_fee_percent', 'processing_fee_fixed'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., MTN Mobile Money'}),
            'method_type': forms.Select(attrs={'class': 'form-select'}),
            'account_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Account holder name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Account number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bank name'}),
            'mobile_provider': forms.Select(attrs={'class': 'form-select'}),
            'processing_fee_percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0'}),
            'processing_fee_fixed': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0'}),
        }
        labels = {
            'processing_fee_percent': 'Processing Fee (%)',
            'processing_fee_fixed': 'Fixed Processing Fee (ZMW)',
            'is_active': 'Active',
            'is_default': 'Set as Default',
        }
        help_texts = {
            'processing_fee_percent': 'Percentage fee charged on each transaction',
            'processing_fee_fixed': 'Fixed fee charged on each transaction',
            'is_default': 'This will be the default payment method for new payments',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        
        if is_default:
            # Ensure only one default method
            PaymentMethod.objects.filter(is_default=True).exclude(
                id=self.instance.id if self.instance else None
            ).update(is_default=False)
        
        return cleaned_data
    
# payments/forms.py - Add this form

from django import forms
from .models import PaymentMethod

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'method_type', 'account_name', 'account_number', 'bank_name',
            'mobile_provider', 'is_active', 'is_default', 'processing_fee_percent',
            'processing_fee_fixed'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., MTN Mobile Money'}),
            'method_type': forms.Select(attrs={'class': 'form-select'}),
            'account_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Account holder name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Account number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bank name'}),
            'mobile_provider': forms.Select(attrs={'class': 'form-select'}),
            'processing_fee_percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0'}),
            'processing_fee_fixed': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        
        if is_default:
            # Remove default from other methods
            PaymentMethod.objects.filter(is_default=True).exclude(
                id=self.instance.id if self.instance else None
            ).update(is_default=False)
        
        return cleaned_data