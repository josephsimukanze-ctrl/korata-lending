from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Payment, PaymentMethod, PaymentCategory, PaymentRefund, ScheduledPayment, PaymentNotification
from .forms import PaymentForm, PaymentApprovalForm, PaymentRefundForm, ScheduledPaymentForm, PaymentFilterForm
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
# payments/views.py - Complete imports section

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User  # If using User model
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import Payment
from loans.models import Loan
from clients.models import Client  # Required import
from notifications.models import Notification
import uuid
import json
def is_admin_or_ceo(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin'])

def is_accountant(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'accountant'])

def is_loan_officer(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer'])

# ==================== MAIN PAYMENT VIEWS ====================

@login_required
def payment_list(request):
    """List all payments with filtering"""
    if not is_accountant(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    payments = Payment.objects.all()
    
    # Apply filters
    form = PaymentFilterForm(request.GET)
    if form.is_valid():
        payment_id = form.cleaned_data.get('payment_id')
        if payment_id:
            payments = payments.filter(payment_id__icontains=payment_id)
        
        client_name = form.cleaned_data.get('client_name')
        if client_name:
            payments = payments.filter(
                Q(client__first_name__icontains=client_name) |
                Q(client__last_name__icontains=client_name)
            )
        
        status = form.cleaned_data.get('status')
        if status:
            payments = payments.filter(status=status)
        
        date_from = form.cleaned_data.get('date_from')
        if date_from:
            payments = payments.filter(payment_date__date__gte=date_from)
        
        date_to = form.cleaned_data.get('date_to')
        if date_to:
            payments = payments.filter(payment_date__date__lte=date_to)
        
        min_amount = form.cleaned_data.get('min_amount')
        if min_amount:
            payments = payments.filter(amount__gte=min_amount)
        
        max_amount = form.cleaned_data.get('max_amount')
        if max_amount:
            payments = payments.filter(amount__lte=max_amount)
    
    # Pagination
    paginator = Paginator(payments, 20)
    page = request.GET.get('page', 1)
    payments_page = paginator.get_page(page)
    
    # Statistics
    stats = {
        'total_payments': payments.count(),
        'total_amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'completed_count': payments.filter(status='completed').count(),
        'completed_amount': payments.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_count': payments.filter(status='pending').count(),
        'pending_amount': payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
        'refunded_count': payments.filter(status='refunded').count(),
    }
    
    context = {
        'payments': payments_page,
        'form': form,
        'stats': stats,
    }
    return render(request, 'payments/payment_list.html', context)


@login_required
def payment_detail(request, payment_id):
    """View payment details"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if not is_accountant(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    context = {
        'payment': payment,
        'refunds': payment.refunds.all(),
    }
    return render(request, 'payments/payment_detail.html', context)

@login_required
@user_passes_test(is_accountant)
def payment_create(request):
    """Create new payment with notifications"""
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            
            # ============ CREATE NOTIFICATIONS ============
            
            # 1. Notification for the payment creator
            Notification.objects.create(
                user=request.user,
                title='Payment Recorded',
                message=f'✅ Payment of ZMW {payment.amount:,.2f} from {payment.client.full_name} has been recorded successfully.\nReference: {payment.payment_id}',
                notification_type='payment_received',
                priority='medium',
                link=f'/payments/{payment.id}/',
                related_payment_id=payment.id,
                related_client_id=payment.client.id,
            )
            
            # 2. Notification for the client's registered officer (if exists)
            if payment.client.registered_by:
                Notification.objects.create(
                    user=payment.client.registered_by,
                    title='New Payment Received',
                    message=f'💰 New payment of ZMW {payment.amount:,.2f} received from {payment.client.full_name}.\nReference: {payment.payment_id}\nStatus: Pending Approval',
                    notification_type='payment_received',
                    priority='high',
                    link=f'/payments/{payment.id}/approve/',
                    related_payment_id=payment.id,
                    related_client_id=payment.client.id,
                )
            
            # 3. Notification for the loan officer if payment is linked to a loan
            if payment.loan and payment.loan.created_by:
                Notification.objects.create(
                    user=payment.loan.created_by,
                    title='Payment on Loan',
                    message=f'💰 Payment of ZMW {payment.amount:,.2f} received for loan {payment.loan.loan_id} from {payment.client.full_name}.',
                    notification_type='payment_received',
                    priority='medium',
                    link=f'/payments/{payment.id}/',
                    related_payment_id=payment.id,
                    related_loan_id=payment.loan.id,
                    related_client_id=payment.client.id,
                )
            
            # 4. Notification for all system admins (for high-value payments)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if payment.amount > 5000:  # High-value threshold
                admins = User.objects.filter(is_superuser=True).exclude(id=request.user.id)
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        title='High-Value Payment Alert',
                        message=f'⚠️ High-value payment of ZMW {payment.amount:,.2f} from {payment.client.full_name} requires attention.\nReference: {payment.payment_id}',
                        notification_type='alert',
                        priority='urgent',
                        link=f'/payments/{payment.id}/approve/',
                        related_payment_id=payment.id,
                        related_client_id=payment.client.id,
                    )
            
            # 5. SMS Notification for client (if phone number exists and SMS is enabled)
            if payment.client.phone_number:
                try:
                    from notifications.sms_utils import send_sms
                    send_sms(
                        phone_number=payment.client.phone_number,
                        message=f"Korata: Payment of ZMW {payment.amount:,.2f} received. Reference: {payment.payment_id}. Awaiting approval.",
                    )
                except ImportError:
                    pass  # SMS module not installed
            
            # 6. Push notification for web (if using web push)
            try:
                from notifications.push_utils import send_push_notification
                if payment.client.registered_by:
                    send_push_notification(
                        user=payment.client.registered_by,
                        title='New Payment',
                        body=f'Payment received from {payment.client.full_name}: ZMW {payment.amount:,.2f}',
                        url=f'/payments/{payment.id}/',
                    )
            except ImportError:
                pass  # Push module not installed
            
            # 7. Keep the existing PaymentNotification for backward compatibility
            PaymentNotification.objects.create(
                client=payment.client,
                payment=payment,
                notification_type='payment_received',
                sent_via='system',
                subject=f'Payment Received - {payment.payment_id}',
                message=f'Your payment of ZMW {payment.amount:,.2f} has been received and is pending approval.\nReference: {payment.payment_id}'
            )
            
            messages.success(
                request, 
                f'✅ Payment {payment.payment_id} created successfully!\n'
                f'Amount: ZMW {payment.amount:,.2f}\n'
                f'Client: {payment.client.full_name}'
            )
            return redirect('payments:payment_detail', payment_id=payment.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm()
    
    # Get relevant data for form
    clients = Client.objects.filter(status='active')
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    categories = PaymentCategory.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'title': 'Create New Payment',
        'clients': clients,
        'payment_methods': payment_methods,
        'categories': categories,
    }
    return render(request, 'payments/payment_form.html', context)
# payments/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Payment, PaymentNotification
from notifications.models import Notification  # Add this import

@login_required
@user_passes_test(is_accountant)
def payment_approve(request, payment_id):
    """Approve a pending payment"""
    from .models import Payment
    from notifications.models import Notification
    
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        messages.error(request, f'Payment with ID {payment_id} does not exist.')
        return redirect('payments:payment_list')
    
    # Check if payment is already approved
    if payment.status == 'completed':
        messages.warning(request, f'Payment {payment.payment_id} is already completed.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    if payment.status != 'pending':
        messages.warning(request, f'Payment {payment.payment_id} is {payment.get_status_display()} and cannot be approved.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        
        try:
            # Approve the payment
            payment.approve(request.user, notes)
            
            # ============ NOTIFICATION CODE - PLACE THIS HERE ============
            
            # Create notification for the client's registered officer
            if payment.client.registered_by:
                Notification.objects.create(
                    user=payment.client.registered_by,
                    title='Payment Approved',
                    message=f'✅ Payment of ZMW {payment.amount:,.2f} from {payment.client.full_name} has been approved.\nReference: {payment.payment_id}',
                    notification_type='payment_approved',
                    priority='high',
                    link=f'/payments/{payment.id}/',
                    related_payment_id=payment.id,
                    related_client_id=payment.client.id,
                )
            
            # Create notification for the client (if they have a user account)
            if hasattr(payment.client, 'user') and payment.client.user:
                Notification.objects.create(
                    user=payment.client.user,
                    title='Your Payment Has Been Approved',
                    message=f'✅ Your payment of ZMW {payment.amount:,.2f} has been approved and processed successfully.\nReference: {payment.payment_id}\nDate: {timezone.now().strftime("%Y-%m-%d %H:%M")}',
                    notification_type='payment_approved',
                    priority='medium',
                    link=f'/payments/{payment.id}/',
                    related_payment_id=payment.id,
                )
            
            # Create notification for the system admin (optional)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(is_superuser=True).exclude(id=request.user.id)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title='Payment Approved',
                    message=f'Payment of ZMW {payment.amount:,.2f} was approved by {request.user.get_full_name() or request.user.username}',
                    notification_type='payment_approved',
                    priority='low',
                    link=f'/payments/{payment.id}/',
                    related_payment_id=payment.id,
                    related_client_id=payment.client.id,
                )
            
            # Also keep your existing PaymentNotification if you have it
            from .models import PaymentNotification
            PaymentNotification.objects.create(
                client=payment.client,
                payment=payment,
                notification_type='payment_confirmation',
                sent_via='system',
                subject=f'Payment Approved - {payment.payment_id}',
                message=f'Your payment of ZMW {payment.amount:,.2f} has been approved and processed.'
            )
            
            messages.success(request, f'✅ Payment {payment.payment_id} approved successfully!')
            return redirect('payments:payment_detail', payment_id=payment.id)
            
        except Exception as e:
            messages.error(request, f'Error approving payment: {str(e)}')
            return redirect('payments:payment_approve', payment_id=payment.id)
    
    context = {
        'payment': payment,
    }
    return render(request, 'payments/payment_approve.html', context)

@login_required
@user_passes_test(is_accountant)
def payment_refund(request, payment_id):
    """Process refund for a payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.status in ['refunded', 'cancelled']:
        messages.error(request, 'This payment has already been refunded or cancelled.')
        return redirect('payments:payment_detail', payment_id=payment.id)
    
    if request.method == 'POST':
        form = PaymentRefundForm(request.POST, payment=payment)
        if form.is_valid():
            refund = form.save(commit=False)
            refund.original_payment = payment
            refund.requested_by = request.user
            refund.save()
            
            messages.success(request, f'Refund request for {refund.amount} has been created.')
            return redirect('payments:payment_detail', payment_id=payment.id)
    else:
        form = PaymentRefundForm(payment=payment)
    
    context = {
        'payment': payment,
        'form': form,
    }
    return render(request, 'payments/payment_refund.html', context)


@login_required
@user_passes_test(is_accountant)
def payment_cancel(request, payment_id):
    """Cancel a pending payment"""
    payment = get_object_or_404(Payment, id=payment_id, status='pending')
    
    if request.method == 'POST':
        payment.status = 'cancelled'
        payment.save()
        messages.success(request, f'Payment {payment.payment_id} has been cancelled.')
        return redirect('payments:payment_list')
    
    context = {'payment': payment}
    return render(request, 'payments/payment_confirm_cancel.html', context)


# ==================== LOAN PAYMENT VIEWS ====================

@login_required
@user_passes_test(is_loan_officer)
def make_loan_payment(request, loan_id):
    """Make a payment towards a loan"""
    from loans.models import Loan, RepaymentSchedule
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get next due amount from repayment schedule
    next_schedule = RepaymentSchedule.objects.filter(
        loan=loan, 
        status='pending'
    ).order_by('week_number').first()
    
    suggested_amount = float(next_schedule.expected_amount) if next_schedule else float(loan.installment_amount or 0)
    min_amount = suggested_amount
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            payment_method_id = request.POST.get('payment_method')
            reference_number = request.POST.get('reference_number', '')
            notes = request.POST.get('notes', '')
            
            # Validate amount
            if amount < Decimal(str(min_amount)):
                messages.error(request, f'Payment amount cannot be less than ZMW {min_amount:,.2f}')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            if amount > loan.remaining_balance:
                messages.error(request, f'Payment amount cannot exceed the remaining balance of ZMW {loan.remaining_balance:,.2f}')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            # Get payment method
            try:
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
            except PaymentMethod.DoesNotExist:
                messages.error(request, 'Selected payment method does not exist.')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            # Get or create payment category for loan repayment
            category, _ = PaymentCategory.objects.get_or_create(
                code='loan_repayment',
                defaults={'name': 'Loan Repayment', 'is_active': True}
            )
            
            # Create payment record
            payment = Payment.objects.create(
                client=loan.client,
                loan=loan,
                payment_method=payment_method,
                category=category,
                payment_type='loan_repayment',
                amount=amount,
                transaction_reference=reference_number,
                notes=notes,
                payment_date=timezone.now(),
                created_by=request.user,
                status='completed'  # Auto-approve for now
            )
            
            # Update loan payment schedule
            remaining_amount = float(amount)
            schedules = RepaymentSchedule.objects.filter(
                loan=loan, 
                status='pending'
            ).order_by('week_number')
            
            for schedule in schedules:
                if remaining_amount <= 0:
                    break
                
                due_amount = float(schedule.expected_amount) - float(schedule.paid_amount or 0)
                if remaining_amount >= due_amount:
                    schedule.paid_amount = schedule.expected_amount
                    schedule.status = 'paid'
                    schedule.payment_date = timezone.now()
                    remaining_amount -= due_amount
                else:
                    schedule.paid_amount = (schedule.paid_amount or 0) + Decimal(str(remaining_amount))
                    schedule.status = 'partial'
                    remaining_amount = 0
                schedule.save()
            
            # Update loan totals
            loan.amount_paid = (loan.amount_paid or 0) + amount
            loan.remaining_balance = loan.total_payback - loan.amount_paid
            
            # Update loan status
            if loan.remaining_balance <= 0:
                loan.status = 'completed'
            else:
                overdue_exists = RepaymentSchedule.objects.filter(
                    loan=loan, 
                    due_date__lt=timezone.now().date(),
                    status='pending'
                ).exists()
                loan.status = 'defaulted' if overdue_exists else 'active'
            
            loan.save()
            
            # Create notification
            PaymentNotification.objects.create(
                client=loan.client,
                payment=payment,
                notification_type='payment_received',
                sent_via='system',
                subject=f'Payment Received - {payment.payment_id}',
                message=f'Your payment of ZMW {amount:,.2f} has been recorded for loan {loan.loan_id}.'
            )
            
            messages.success(
                request, 
                f'✅ Payment of ZMW {amount:,.2f} recorded successfully! Remaining balance: ZMW {loan.remaining_balance:,.2f}'
            )
            
            return redirect('loans:loan_detail', loan_id=loan.id)
            
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('payments:make_loan_payment', loan_id=loan.id)
    
    # GET request - show form
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    # Calculate payment progress
    total_payback = float(loan.total_payback)
    amount_paid = float(loan.amount_paid or 0)
    progress = (amount_paid / total_payback * 100) if total_payback > 0 else 0
    
    context = {
        'loan': loan,
        'payment_methods': payment_methods,
        'suggested_amount': suggested_amount,
        'min_amount': min_amount,
        'next_schedule': next_schedule,
        'progress': progress,
        'amount_paid': amount_paid,
        'remaining_balance': float(loan.remaining_balance),
        'title': 'Make Payment'
    }
    
    return render(request, 'payments/make_loan_payment.html', context)


# ==================== PAYMENT METHOD VIEWS ====================

@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_list(request):
    """List payment methods"""
    methods = PaymentMethod.objects.all()
    return render(request, 'payments/payment_method_list.html', {'methods': methods})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_create(request):
    """Create payment method"""
    if request.method == 'POST':
        name = request.POST.get('name')
        method_type = request.POST.get('method_type')
        
        method = PaymentMethod.objects.create(
            name=name,
            method_type=method_type,
            account_name=request.POST.get('account_name', ''),
            account_number=request.POST.get('account_number', ''),
            bank_name=request.POST.get('bank_name', ''),
            mobile_provider=request.POST.get('mobile_provider', ''),
            is_active=request.POST.get('is_active') == 'on',
            is_default=request.POST.get('is_default') == 'on',
            processing_fee_percent=request.POST.get('processing_fee_percent', 0),
            processing_fee_fixed=request.POST.get('processing_fee_fixed', 0),
        )
        
        messages.success(request, f'Payment method {method.name} created successfully!')
        return redirect('payments:payment_method_list')
    
    return render(request, 'payments/payment_method_form.html', {'title': 'Create Payment Method'})


# ==================== SCHEDULED PAYMENTS ====================

@login_required
@user_passes_test(is_accountant)
def scheduled_payment_list(request):
    """List scheduled payments"""
    scheduled = ScheduledPayment.objects.filter(is_active=True)
    
    # Get upcoming payments
    upcoming = scheduled.filter(next_payment_date__gte=timezone.now().date()).order_by('next_payment_date')[:10]
    
    # Get overdue scheduled payments
    overdue = scheduled.filter(next_payment_date__lt=timezone.now().date(), is_active=True)
    
    context = {
        'scheduled': scheduled,
        'upcoming': upcoming,
        'overdue': overdue,
    }
    return render(request, 'payments/scheduled_payment_list.html', context)


@login_required
@user_passes_test(is_accountant)
def scheduled_payment_create(request):
    """Create scheduled payment"""
    if request.method == 'POST':
        form = ScheduledPaymentForm(request.POST)
        if form.is_valid():
            scheduled = form.save(commit=False)
            scheduled.next_payment_date = scheduled.start_date
            scheduled.save()
            messages.success(request, 'Scheduled payment created successfully!')
            return redirect('payments:scheduled_payment_list')
    else:
        form = ScheduledPaymentForm()
    
    return render(request, 'payments/scheduled_payment_form.html', {'form': form, 'title': 'Create Scheduled Payment'})


@login_required
@user_passes_test(is_accountant)
def process_scheduled_payments(request):
    """Process due scheduled payments"""
    if request.method == 'POST':
        today = timezone.now().date()
        due_payments = ScheduledPayment.objects.filter(
            next_payment_date__lte=today,
            is_active=True
        )
        
        processed = 0
        for scheduled in due_payments:
            # Create payment record
            payment = Payment.objects.create(
                client=scheduled.client,
                loan=scheduled.loan,
                payment_method=scheduled.payment_method,
                amount=scheduled.amount,
                status='pending',
                payment_date=timezone.now(),
                created_by=request.user,
                notes=f"Auto-generated from scheduled payment"
            )
            
            # Update next payment date
            scheduled.update_next_payment_date()
            
            # Check if end date is reached
            if scheduled.end_date and scheduled.next_payment_date > scheduled.end_date:
                scheduled.is_active = False
                scheduled.save()
            
            processed += 1
        
        messages.success(request, f'Processed {processed} scheduled payments.')
        return redirect('payments:scheduled_payment_list')
    
    return redirect('payments:scheduled_payment_list')


# ==================== REPORTS ====================

@login_required
@user_passes_test(is_accountant)
def payment_report(request):
    """Generate payment reports"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    start_of_week = today - timedelta(days=today.weekday())
    
    # Get data for different periods
    today_payments = Payment.objects.filter(payment_date__date=today, status='completed')
    week_payments = Payment.objects.filter(payment_date__date__gte=start_of_week, status='completed')
    month_payments = Payment.objects.filter(payment_date__date__gte=start_of_month, status='completed')
    
    # Payment method breakdown
    method_breakdown = Payment.objects.filter(status='completed').values(
        'payment_method__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Daily payments for chart
    last_30_days = []
    for i in range(30):
        date = today - timedelta(days=i)
        daily_total = Payment.objects.filter(
            payment_date__date=date,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        last_30_days.append({
            'date': date.strftime('%Y-%m-%d'),
            'amount': float(daily_total)
        })
    
    context = {
        'today_total': today_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'today_count': today_payments.count(),
        'week_total': week_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'week_count': week_payments.count(),
        'month_total': month_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'month_count': month_payments.count(),
        'method_breakdown': method_breakdown,
        'daily_data': json.dumps(last_30_days[::-1]),
    }
    
    return render(request, 'payments/payment_report.html', context)


@login_required
@user_passes_test(is_accountant)
def export_payments(request):
    """Export payments to CSV"""
    format_type = request.GET.get('format', 'csv')
    
    payments = Payment.objects.all()
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    date_from = request.GET.get('date_from')
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    # Create CSV response
    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Payment ID', 'Client Name', 'Client NRC', 'Amount', 'Processing Fee',
        'Total Amount', 'Status', 'Payment Method', 'Payment Date', 
        'Transaction Reference', 'Notes'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.payment_id,
            payment.client.full_name,
            payment.client.nrc,
            payment.amount,
            payment.processing_fee,
            payment.total_amount,
            payment.get_status_display(),
            payment.payment_method.name if payment.payment_method else '-',
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.transaction_reference or '-',
            payment.notes or '-'
        ])
    
    return response


# ==================== API ENDPOINTS ====================

@login_required
def api_payment_stats(request):
    """API endpoint for payment statistics"""
    stats = {
        'total_payments': Payment.objects.count(),
        'total_amount': float(Payment.objects.aggregate(total=Sum('amount'))['total'] or 0),
        'completed_count': Payment.objects.filter(status='completed').count(),
        'completed_amount': float(Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0),
        'pending_count': Payment.objects.filter(status='pending').count(),
        'pending_amount': float(Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0),
        'today_amount': float(Payment.objects.filter(payment_date__date=timezone.now().date()).aggregate(total=Sum('amount'))['total'] or 0),
    }
    return JsonResponse(stats)


@login_required
def api_client_payments(request, client_id):
    """API endpoint for client payment history"""
    payments = Payment.objects.filter(client_id=client_id).order_by('-payment_date')
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'payment_id': payment.payment_id,
            'amount': float(payment.amount),
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'payment_date': payment.payment_date.isoformat(),
            'method': payment.payment_method.name if payment.payment_method else None,
        })
    
    return JsonResponse({'payments': payment_data})

# payments/views.py - Add this function
@login_required
@user_passes_test(is_loan_officer)
def make_loan_payment(request, loan_id):
    """Make a payment towards a loan"""
    from loans.models import Loan, RepaymentSchedule
    from decimal import Decimal
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get next due amount from repayment schedule
    next_schedule = RepaymentSchedule.objects.filter(
        loan=loan, 
        status='pending'
    ).order_by('week_number').first()
    
    suggested_amount = float(next_schedule.expected_amount) if next_schedule else float(getattr(loan, 'weekly_payment', 0) or 0)
    min_amount = suggested_amount
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            payment_method_id = request.POST.get('payment_method')
            reference_number = request.POST.get('reference_number', '')
            notes = request.POST.get('notes', '')
            
            # Validate amount
            if amount < Decimal(str(min_amount)):
                messages.error(request, f'Payment amount cannot be less than ZMW {min_amount:,.2f}')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            # Calculate remaining balance from the model's property
            current_remaining = loan.remaining_balance if hasattr(loan, 'remaining_balance') else loan.total_payback
            
            if amount > current_remaining:
                messages.error(request, f'Payment amount cannot exceed the remaining balance of ZMW {current_remaining:,.2f}')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            # Get payment method
            try:
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
            except PaymentMethod.DoesNotExist:
                messages.error(request, 'Selected payment method does not exist.')
                return redirect('payments:make_loan_payment', loan_id=loan.id)
            
            # Get or create payment category for loan repayment
            category, _ = PaymentCategory.objects.get_or_create(
                code='loan_repayment',
                defaults={'name': 'Loan Repayment', 'is_active': True}
            )
            
            # Create payment record
            payment = Payment.objects.create(
                client=loan.client,
                loan=loan,
                payment_method=payment_method,
                category=category,
                payment_type='loan_repayment',
                amount=amount,
                transaction_reference=reference_number,
                notes=notes,
                payment_date=timezone.now(),
                created_by=request.user,
                status='completed'
            )
            
            # Update loan payment schedule
            remaining_amount = float(amount)
            schedules = RepaymentSchedule.objects.filter(
                loan=loan, 
                status='pending'
            ).order_by('week_number')
            
            total_paid_amount = 0
            for schedule in schedules:
                if remaining_amount <= 0:
                    break
                
                due_amount = float(schedule.expected_amount) - float(schedule.paid_amount or 0)
                if remaining_amount >= due_amount:
                    schedule.paid_amount = schedule.expected_amount
                    schedule.status = 'paid'
                    schedule.payment_date = timezone.now()
                    remaining_amount -= due_amount
                    total_paid_amount += due_amount
                else:
                    schedule.paid_amount = (schedule.paid_amount or 0) + Decimal(str(remaining_amount))
                    schedule.status = 'partial'
                    total_paid_amount += remaining_amount
                    remaining_amount = 0
                schedule.save()
            
            # Update loan totals - use update on the model directly
            # Since amount_paid might be a property, we need to update a database field or track paid amount elsewhere
            
            # Option 1: If you have a 'paid_amount' field on Loan model
            if hasattr(loan, 'paid_amount'):
                loan.paid_amount = (loan.paid_amount or 0) + amount
                loan.save()
            
            # Option 2: Update the remaining balance in the schedule (already done)
            # Option 3: Create a separate model to track loan payments
            
            # Update loan status based on schedule
            all_paid = RepaymentSchedule.objects.filter(loan=loan, status__in=['pending', 'partial']).count() == 0
            if all_paid:
                loan.status = 'completed'
                loan.save()
            else:
                # Check if any schedules are overdue
                overdue_exists = RepaymentSchedule.objects.filter(
                    loan=loan, 
                    due_date__lt=timezone.now().date(),
                    status__in=['pending', 'partial']
                ).exists()
                if overdue_exists and loan.status != 'defaulted':
                    loan.status = 'defaulted'
                    loan.save()
                elif loan.status == 'pending':
                    loan.status = 'active'
                    loan.save()
            
            messages.success(
                request, 
                f'✅ Payment of ZMW {amount:,.2f} recorded successfully!'
            )
            
            return redirect('loans:loan_detail', loan_id=loan.id)
            
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('payments:make_loan_payment', loan_id=loan.id)
    
    # GET request - show form
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    # Calculate payment progress from schedules
    schedules = RepaymentSchedule.objects.filter(loan=loan)
    total_expected = sum(float(s.expected_amount) for s in schedules)
    total_paid = sum(float(s.paid_amount or 0) for s in schedules)
    progress = (total_paid / total_expected * 100) if total_expected > 0 else 0
    
    context = {
        'loan': loan,
        'payment_methods': payment_methods,
        'suggested_amount': suggested_amount,
        'min_amount': min_amount,
        'next_schedule': next_schedule,
        'amount_paid': total_paid,
        'remaining_balance': total_expected - total_paid,
        'title': 'Make Payment'
    }
    
    return render(request, 'payments/make_loan_payment.html', context)

@login_required
def api_loan_upcoming_payments(request, loan_id):
    """API endpoint to get upcoming payments for a loan"""
    from loans.models import RepaymentSchedule
    
    schedules = RepaymentSchedule.objects.filter(
        loan_id=loan_id,
        status='pending'
    ).order_by('week_number')[:10]
    
    payments = []
    for schedule in schedules:
        payments.append({
            'week': schedule.week_number,
            'due_date': schedule.due_date.strftime('%Y-%m-%d'),
            'amount': float(schedule.expected_amount)
        })
    
    return JsonResponse({'payments': payments})


@login_required
def api_payment_list(request):
    """API endpoint to get payments as JSON"""
    payments = Payment.objects.all().order_by('-payment_date')
    
    # Apply filters
    search = request.GET.get('search', '')
    if search:
        payments = payments.filter(
            Q(payment_id__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        payments = payments.filter(status=status)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'payment_id': payment.payment_id,
            'client_name': payment.client.full_name,
            'client_id': payment.client.client_id,
            'loan_id': payment.loan.loan_id if payment.loan else None,
            'amount': float(payment.amount),
            'method': payment.payment_method.name if payment.payment_method else 'Cash',
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'reference': payment.transaction_reference or '',
            'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
        })
    
    return JsonResponse({'payments': payment_data})


@login_required
def api_payment_stats(request):
    """API endpoint for payment statistics"""
    today = timezone.now().date()
    
    stats = {
        'total_count': Payment.objects.count(),
        'total_amount': float(Payment.objects.aggregate(total=Sum('amount'))['total'] or 0),
        'completed_count': Payment.objects.filter(status='completed').count(),
        'completed_amount': float(Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0),
        'pending_count': Payment.objects.filter(status='pending').count(),
        'pending_amount': float(Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0),
        'today_amount': float(Payment.objects.filter(payment_date__date=today).aggregate(total=Sum('amount'))['total'] or 0),
        'today_count': Payment.objects.filter(payment_date__date=today).count(),
    }
    return JsonResponse(stats)

@login_required
def api_payment_stats(request):
    """API endpoint for payment statistics"""
    from django.db.models import Sum
    from django.utils import timezone
    from .models import Payment
    
    today = timezone.now().date()
    
    stats = {
        'total_payments': Payment.objects.count(),
        'total_amount': float(Payment.objects.aggregate(total=Sum('amount'))['total'] or 0),
        'completed_count': Payment.objects.filter(status='completed').count(),
        'completed_amount': float(Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0),
        'pending_count': Payment.objects.filter(status='pending').count(),
        'pending_amount': float(Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0),
        'failed_count': Payment.objects.filter(status='failed').count(),
        'refunded_count': Payment.objects.filter(status='refunded').count(),
        'today_amount': float(Payment.objects.filter(payment_date__date=today).aggregate(total=Sum('amount'))['total'] or 0),
        'today_count': Payment.objects.filter(payment_date__date=today).count(),
        'this_week_amount': float(Payment.objects.filter(payment_date__week=today.isocalendar()[1]).aggregate(total=Sum('amount'))['total'] or 0),
        'this_month_amount': float(Payment.objects.filter(payment_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0),
    }
    return JsonResponse(stats)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import PaymentMethod
from .forms import PaymentMethodForm

# ==================== PAYMENT METHOD VIEWS ====================

@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_list(request):
    """List payment methods"""
    methods = PaymentMethod.objects.all()
    return render(request, 'payments/payment_method_list.html', {'methods': methods})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_create(request):
    """Create payment method"""
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            method = form.save()
            messages.success(request, f'Payment method {method.name} created successfully!')
            return redirect('payments:payment_method_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'payments/payment_method_form.html', {'form': form, 'title': 'Create Payment Method'})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_edit(request, method_id):
    """Edit payment method"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, f'Payment method {method.name} updated successfully!')
            return redirect('payments:payment_method_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentMethodForm(instance=method)
    
    return render(request, 'payments/payment_method_form.html', {'form': form, 'title': 'Edit Payment Method', 'method': method})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_delete(request, method_id):
    """Delete payment method"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        method_name = method.name
        method.delete()
        messages.success(request, f'Payment method {method_name} deleted successfully!')
        return redirect('payments:payment_method_list')
    
    return render(request, 'payments/payment_method_confirm_delete.html', {'method': method})


@login_required
@user_passes_test(is_admin_or_ceo)
@require_http_methods(["POST"])
def payment_method_toggle(request, method_id):
    """Toggle payment method active status"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    method.is_active = not method.is_active
    method.save()
    
    status = 'activated' if method.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'Method {status}', 'is_active': method.is_active})


@login_required
def api_method_fees(request, method_id):
    """API endpoint to get method fees"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    return JsonResponse({
        'fee_percent': float(method.processing_fee_percent),
        'fee_fixed': float(method.processing_fee_fixed)
    })


# Add these functions to your payments/views.py

@login_required
@user_passes_test(is_accountant)
@require_http_methods(["POST"])
def toggle_scheduled_payment(request, schedule_id):
    """Toggle scheduled payment active status"""
    from .models import ScheduledPayment
    
    schedule = get_object_or_404(ScheduledPayment, id=schedule_id)
    schedule.is_active = not schedule.is_active
    schedule.save()
    
    status = 'activated' if schedule.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'Schedule {status}', 'is_active': schedule.is_active})


@login_required
@user_passes_test(is_accountant)
@require_http_methods(["POST"])
def delete_scheduled_payment(request, schedule_id):
    """Delete scheduled payment"""
    from .models import ScheduledPayment
    
    schedule = get_object_or_404(ScheduledPayment, id=schedule_id)
    schedule.delete()
    return JsonResponse({'success': True, 'message': 'Schedule deleted successfully'})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_edit(request, method_id):
    """Edit payment method"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, f'Payment method {method.name} updated successfully!')
            return redirect('payments:payment_method_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentMethodForm(instance=method)
    
    return render(request, 'payments/payment_method_form.html', {'form': form, 'title': 'Edit Payment Method', 'method': method})


@login_required
@user_passes_test(is_admin_or_ceo)
def payment_method_delete(request, method_id):
    """Delete payment method"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        method_name = method.name
        method.delete()
        messages.success(request, f'Payment method {method_name} deleted successfully!')
        return redirect('payments:payment_method_list')
    
    return render(request, 'payments/payment_method_confirm_delete.html', {'method': method})


@login_required
@user_passes_test(is_admin_or_ceo)
@require_http_methods(["POST"])
def payment_method_toggle(request, method_id):
    """Toggle payment method active status"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    method.is_active = not method.is_active
    method.save()
    
    status = 'activated' if method.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'Method {status}', 'is_active': method.is_active})


@login_required
def api_scheduled_stats(request):
    """API endpoint for scheduled payment statistics"""
    from .models import ScheduledPayment
    from django.utils import timezone
    
    due_count = ScheduledPayment.objects.filter(
        next_payment_date__lte=timezone.now().date(),
        is_active=True
    ).count()
    
    total_active = ScheduledPayment.objects.filter(is_active=True).count()
    
    return JsonResponse({
        'due_count': due_count,
        'total_active': total_active
    })


@login_required
def api_method_fees(request, method_id):
    """API endpoint to get method fees"""
    method = get_object_or_404(PaymentMethod, id=method_id)
    return JsonResponse({
        'fee_percent': float(method.processing_fee_percent),
        'fee_fixed': float(method.processing_fee_fixed)
    })


@login_required
def api_payment_list(request):
    """API endpoint for payment list"""
    payments = Payment.objects.all().order_by('-payment_date')
    
    # Apply filters
    search = request.GET.get('search', '')
    if search:
        payments = payments.filter(
            Q(payment_id__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        payments = payments.filter(status=status)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'payment_id': payment.payment_id,
            'client_name': payment.client.full_name,
            'client_id': payment.client.client_id,
            'loan_id': payment.loan.loan_id if payment.loan else None,
            'amount': float(payment.amount),
            'method': payment.payment_method.name if payment.payment_method else 'Cash',
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'reference': payment.transaction_reference or '',
            'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
        })
    
    return JsonResponse({'payments': payment_data})

from django.http import HttpResponse
import csv
from datetime import datetime

@login_required
def export_payment_report(request):
    """Export payment report to CSV or Excel"""
    format_type = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    payments = Payment.objects.all().order_by('-payment_date')
    
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    # Create CSV response
    filename = f"payment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Payment ID', 'Client Name', 'Client NRC', 'Amount', 'Processing Fee',
        'Total Amount', 'Status', 'Payment Method', 'Payment Date', 
        'Transaction Reference', 'Loan ID', 'Notes'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.payment_id,
            payment.client.full_name,
            payment.client.nrc,
            payment.amount,
            payment.processing_fee,
            payment.total_amount,
            payment.get_status_display(),
            payment.payment_method.name if payment.payment_method else '-',
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.transaction_reference or '-',
            payment.loan.loan_id if payment.loan else '-',
            payment.notes or '-'
        ])
    
    return response


@login_required
def export_payments(request):
    """Export payments to CSV"""
    format_type = request.GET.get('format', 'csv')
    
    payments = Payment.objects.all()
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    date_from = request.GET.get('date_from')
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    # Create CSV response
    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Payment ID', 'Client Name', 'Client NRC', 'Amount', 'Processing Fee',
        'Total Amount', 'Status', 'Payment Method', 'Payment Date', 
        'Transaction Reference', 'Notes'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.payment_id,
            payment.client.full_name,
            payment.client.nrc,
            payment.amount,
            payment.processing_fee,
            payment.total_amount,
            payment.get_status_display(),
            payment.payment_method.name if payment.payment_method else '-',
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.transaction_reference or '-',
            payment.notes or '-'
        ])
    
    return response


@login_required
def api_payment_reports(request):
    """API endpoint for comprehensive payment reports"""
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    from .models import Payment
    
    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    period = request.GET.get('period', 'month')
    
    # Base queryset
    payments = Payment.objects.all()
    
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Today stats
    today_payments = payments.filter(payment_date__date=today)
    today_stats = {
        'amount': float(today_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': today_payments.count()
    }
    
    # Week stats
    week_payments = payments.filter(payment_date__date__gte=week_start)
    week_stats = {
        'amount': float(week_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': week_payments.count()
    }
    
    # Month stats
    month_payments = payments.filter(payment_date__date__gte=month_start)
    month_stats = {
        'amount': float(month_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': month_payments.count()
    }
    
    # Total stats
    total_stats = {
        'amount': float(payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': payments.count()
    }
    
    # Pending stats
    pending_payments = payments.filter(status='pending')
    pending_stats = {
        'amount': float(pending_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': pending_payments.count()
    }
    
    # Failed stats
    failed_payments = payments.filter(status='failed')
    failed_stats = {
        'amount': float(failed_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': failed_payments.count()
    }
    
    # Refunded stats
    refunded_payments = payments.filter(status='refunded')
    refunded_stats = {
        'amount': float(refunded_payments.aggregate(total=Sum('amount'))['total'] or 0),
        'count': refunded_payments.count()
    }
    
    # Average payment
    avg_result = payments.aggregate(avg=Sum('amount'))
    average_payment = float(avg_result['avg'] / payments.count()) if payments.count() > 0 else 0
    
    # Top clients
    top_clients = payments.values('client__id', 'client__full_name', 'client__client_id').annotate(
        total_amount=Sum('amount'),
        payment_count=Count('id')
    ).order_by('-total_amount')[:10]
    
    top_clients_data = []
    for client in top_clients:
        top_clients_data.append({
            'id': client['client__client_id'],
            'name': client['client__full_name'],
            'total_amount': float(client['total_amount'] or 0),
            'payment_count': client['payment_count']
        })
    
    # Method breakdown
    method_breakdown = payments.values('payment_method__name').annotate(
        amount=Sum('amount'),
        count=Count('id')
    ).order_by('-amount')
    
    method_data = []
    for method in method_breakdown:
        if method['payment_method__name']:
            method_data.append({
                'name': method['payment_method__name'],
                'amount': float(method['amount'] or 0),
                'count': method['count']
            })
    
    # Status distribution
    status_distribution = payments.values('status').annotate(
        amount=Sum('amount'),
        count=Count('id')
    )
    
    status_data = []
    for status in status_distribution:
        status_data.append({
            'name': dict(Payment.PAYMENT_STATUS).get(status['status'], status['status']),
            'amount': float(status['amount'] or 0),
            'count': status['count']
        })
    
    # Daily trends
    if period == 'week':
        days = 7
    elif period == 'quarter':
        days = 90
    else:
        days = 30
    
    daily_labels = []
    daily_amounts = []
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        day_payments = payments.filter(payment_date__date=date)
        daily_labels.append(date.strftime('%Y-%m-%d'))
        daily_amounts.append(float(day_payments.aggregate(total=Sum('amount'))['total'] or 0))
    
    return JsonResponse({
        'today': today_stats,
        'week': week_stats,
        'month': month_stats,
        'total': total_stats,
        'pending': pending_stats,
        'failed': failed_stats,
        'refunded': refunded_stats,
        'average_payment': average_payment,
        'top_clients': top_clients_data,
        'method_breakdown': method_data,
        'status_distribution': status_data,
        'daily_labels': daily_labels,
        'daily_amounts': daily_amounts,
    })

@login_required
def api_payment_stats(request):
    """API endpoint for payment statistics"""
    from django.db.models import Sum
    from django.utils import timezone
    
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    all_payments = Payment.objects.all()
    today_payments = Payment.objects.filter(payment_date__date=today)
    week_payments = Payment.objects.filter(payment_date__date__gte=week_start)
    month_payments = Payment.objects.filter(payment_date__date__gte=month_start)
    
    stats = {
        # Basic counts
        'total_count': Payment.objects.count(),
        'total_amount': float(all_payments.aggregate(total=Sum('amount'))['total'] or 0),
        
        # Completed payments
        'completed_count': Payment.objects.filter(status='completed').count(),
        'completed_amount': float(Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0),
        
        # Pending payments
        'pending_count': Payment.objects.filter(status='pending').count(),
        'pending_amount': float(Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0),
        
        # Failed payments
        'failed_count': Payment.objects.filter(status='failed').count(),
        'failed_amount': float(Payment.objects.filter(status='failed').aggregate(total=Sum('amount'))['total'] or 0),
        
        # Refunded payments
        'refunded_count': Payment.objects.filter(status='refunded').count(),
        'refunded_amount': float(Payment.objects.filter(status='refunded').aggregate(total=Sum('amount'))['total'] or 0),
        
        # Today's stats
        'today_count': today_payments.count(),
        'today_amount': float(today_payments.aggregate(total=Sum('amount'))['total'] or 0),
        
        # This week stats
        'week_count': week_payments.count(),
        'week_amount': float(week_payments.aggregate(total=Sum('amount'))['total'] or 0),
        
        # This month stats
        'month_count': month_payments.count(),
        'month_amount': float(month_payments.aggregate(total=Sum('amount'))['total'] or 0),
    }
    return JsonResponse(stats)

@login_required
def api_payment_reports(request):
    """API endpoint for comprehensive payment reports"""
    from django.db.models import Sum, Count, F
    from django.utils import timezone
    from datetime import timedelta
    from .models import Payment
    
    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    period = request.GET.get('period', 'month')
    
    # Base queryset
    payments = Payment.objects.all()
    
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Helper function to format amount
    def format_amount(amount):
        return float(amount) if amount else 0.0
    
    # Today stats
    today_payments = Payment.objects.filter(payment_date__date=today)
    today_stats = {
        'amount': format_amount(today_payments.aggregate(total=Sum('amount'))['total']),
        'count': today_payments.count()
    }
    
    # Week stats
    week_payments = Payment.objects.filter(payment_date__date__gte=week_start)
    week_stats = {
        'amount': format_amount(week_payments.aggregate(total=Sum('amount'))['total']),
        'count': week_payments.count()
    }
    
    # Month stats
    month_payments = Payment.objects.filter(payment_date__date__gte=month_start)
    month_stats = {
        'amount': format_amount(month_payments.aggregate(total=Sum('amount'))['total']),
        'count': month_payments.count()
    }
    
    # Total stats (all time, but respect date filters if applied)
    total_stats = {
        'amount': format_amount(payments.aggregate(total=Sum('amount'))['total']),
        'count': payments.count()
    }
    
    # Pending stats
    pending_payments = payments.filter(status='pending')
    pending_stats = {
        'amount': format_amount(pending_payments.aggregate(total=Sum('amount'))['total']),
        'count': pending_payments.count()
    }
    
    # Failed stats
    failed_payments = payments.filter(status='failed')
    failed_stats = {
        'amount': format_amount(failed_payments.aggregate(total=Sum('amount'))['total']),
        'count': failed_payments.count()
    }
    
    # Refunded stats
    refunded_payments = payments.filter(status='refunded')
    refunded_stats = {
        'amount': format_amount(refunded_payments.aggregate(total=Sum('amount'))['total']),
        'count': refunded_payments.count()
    }
    
    # Average payment
    total_amount = total_stats['amount']
    total_count = total_stats['count']
    average_payment = total_amount / total_count if total_count > 0 else 0
    
    # Top clients - Using first_name and last_name instead of full_name
    top_clients = payments.values('client__first_name', 'client__last_name', 'client__client_id').annotate(
        total_amount=Sum('amount'),
        payment_count=Count('id')
    ).order_by('-total_amount')[:10]
    
    top_clients_data = []
    for client in top_clients:
        # Combine first and last name for full name
        full_name = f"{client['client__first_name']} {client['client__last_name']}".strip()
        if not full_name:
            full_name = client['client__client_id'] or 'Unknown'
            
        top_clients_data.append({
            'id': client['client__client_id'] or '',
            'name': full_name,
            'total_amount': format_amount(client['total_amount']),
            'payment_count': client['payment_count']
        })
    
    # Method breakdown
    method_breakdown = payments.values('payment_method__name').annotate(
        amount=Sum('amount'),
        count=Count('id')
    ).order_by('-amount')
    
    method_data = []
    for method in method_breakdown:
        if method['payment_method__name']:
            method_data.append({
                'name': method['payment_method__name'],
                'amount': format_amount(method['amount']),
                'count': method['count']
            })
    
    # If no method breakdown data, add sample data or empty array
    if not method_data:
        method_data = []
    
    # Status distribution
    status_distribution = payments.values('status').annotate(
        amount=Sum('amount'),
        count=Count('id')
    )
    
    status_data = []
    status_names = {
        'pending': 'Pending',
        'completed': 'Completed',
        'failed': 'Failed',
        'cancelled': 'Cancelled',
        'refunded': 'Refunded'
    }
    
    for status in status_distribution:
        status_data.append({
            'name': status_names.get(status['status'], status['status']),
            'amount': format_amount(status['amount']),
            'count': status['count']
        })
    
    # Daily trends
    if period == 'week':
        days = 7
    elif period == 'quarter':
        days = 90
    else:
        days = 30
    
    daily_labels = []
    daily_amounts = []
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        day_payments = Payment.objects.filter(payment_date__date=date)
        daily_labels.append(date.strftime('%Y-%m-%d'))
        daily_amounts.append(format_amount(day_payments.aggregate(total=Sum('amount'))['total']))
    
    # Prepare response
    response_data = {
        'today': today_stats,
        'week': week_stats,
        'month': month_stats,
        'total': total_stats,
        'pending': pending_stats,
        'failed': failed_stats,
        'refunded': refunded_stats,
        'average_payment': average_payment,
        'top_clients': top_clients_data,
        'method_breakdown': method_data,
        'status_distribution': status_data,
        'daily_labels': daily_labels,
        'daily_amounts': daily_amounts,
    }
    
    return JsonResponse(response_data)