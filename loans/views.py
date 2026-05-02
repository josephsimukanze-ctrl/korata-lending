from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Avg, Count  # Make sure 'models' is NOT needed here
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
import json
import csv
from decimal import Decimal
from django.http import JsonResponse
from .models import Loan, RepaymentSchedule, Payment
from clients.models import Client
from collateral.models import Collateral
from users.models import CustomUser
from .models import Loan, RepaymentSchedule, Payment
from clients.models import Client
from collateral.models import Collateral

def is_admin_or_ceo(user):
    return user.is_superuser or user.role in ['ceo', 'admin']

def is_officer_or_higher(user):
    return user.is_superuser or user.role in ['ceo', 'admin', 'collateral_officer']

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Loan, RepaymentSchedule
from payments.models import Payment

def is_officer_or_higher(user):
    """Check if user is loan officer or higher"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer'])

@login_required
def loan_list(request):
    """List all loans with enhanced filtering and JSON data for frontend"""
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    loans_list = Loan.objects.all().select_related('client').order_by('-created_at')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        loans_list = loans_list.filter(
            Q(loan_id__icontains=search_query) |
            Q(client__first_name__icontains=search_query) |
            Q(client__last_name__icontains=search_query) |
            Q(client__phone_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        loans_list = loans_list.filter(status=status_filter)
    
    # Prepare loan data for JSON (for frontend initialization)
    loan_data = []
    for loan in loans_list:
        # Calculate remaining balance
        total_paid = loan.amount_paid if hasattr(loan, 'amount_paid') else 0
        total_payback = loan.total_payback if hasattr(loan, 'total_payback') else loan.principal
        remaining_balance = total_payback - total_paid
        
        # Check if overdue
        is_overdue = False
        if loan.status == 'active':
            next_schedule = RepaymentSchedule.objects.filter(
                loan=loan, 
                status='pending'
            ).order_by('due_date').first()
            if next_schedule and next_schedule.due_date < timezone.now().date():
                is_overdue = True
        
        loan_data.append({
            'id': loan.id,
            'loan_id': loan.loan_id,
            'client_name': loan.client.full_name,
            'principal': float(loan.principal),
            'total_payback': float(total_payback),
            'remaining_balance': float(remaining_balance),
            'status': loan.status,
            'is_overdue': is_overdue,
            'created_at': loan.created_at.isoformat() if loan.created_at else None,
        })
    
    # Pagination
    paginator = Paginator(loans_list, 20)
    page = request.GET.get('page', 1)
    loans = paginator.get_page(page)
    
    # Stats
    stats = {
        'total': Loan.objects.count(),
        'active': Loan.objects.filter(status='active').count(),
        'pending': Loan.objects.filter(status='pending').count(),
        'completed': Loan.objects.filter(status='completed').count(),
        'defaulted': Loan.objects.filter(status='defaulted').count(),
        'total_disbursed': float(Loan.objects.filter(status__in=['active', 'completed']).aggregate(total=Sum('principal'))['total'] or 0),
    }
    
    context = {
        'loans': loans,
        'loans_json': json.dumps(loan_data),
        'search_query': search_query,
        'status_filter': status_filter,
        'stats': stats,
    }
    
    return render(request, 'loans/loan_list.html', context)


@login_required
def loan_detail(request, loan_id):
    """View loan details with enhanced statistics and analytics"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    # Get repayment schedule
    schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')
    
    # Get payments from payments app
    from payments.models import Payment
    payments = Payment.objects.filter(loan=loan).order_by('-payment_date')
    
    # Calculate basic statistics
    total_paid = float(loan.amount_paid) if hasattr(loan, 'amount_paid') and loan.amount_paid else 0
    total_due = float(loan.total_payback) if hasattr(loan, 'total_payback') and loan.total_payback else float(loan.principal)
    remaining = float(loan.remaining_balance) if hasattr(loan, 'remaining_balance') and loan.remaining_balance else total_due - total_paid
    progress = (total_paid / total_due * 100) if total_due and total_due > 0 else 0
    
    # Calculate payment statistics from schedule
    schedule_count = schedule.count()
    on_time_payments = schedule.filter(status='paid').count()
    late_payments = schedule.filter(status='overdue').count()
    pending_payments = schedule.filter(status='pending').count()
    
    # Calculate payment performance
    payment_performance = (on_time_payments / schedule_count * 100) if schedule_count > 0 else 0
    
    # Calculate average payment amount
    total_payment_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    payment_count = payments.count()
    avg_payment = float(total_payment_amount) / payment_count if payment_count > 0 else 0
    
    # Get next due date
    next_due = RepaymentSchedule.objects.filter(loan=loan, status='pending').order_by('due_date').first()
    
    # Calculate days since last payment
    last_payment = payments.first()
    days_since_last_payment = (timezone.now().date() - last_payment.payment_date.date()).days if last_payment and last_payment.payment_date else None
    
    # Calculate estimated completion date
    estimated_completion = None
    if next_due and loan.status == 'active':
        remaining_weeks = schedule.filter(status__in=['pending', 'partial']).count()
        estimated_completion = timezone.now().date() + timedelta(weeks=remaining_weeks)
    
    # Get payment method breakdown
    payment_methods = {}
    for payment in payments:
        method = payment.payment_method.name if payment.payment_method else 'Cash'
        payment_methods[method] = payment_methods.get(method, 0) + 1
    
    # Prepare chart data
    chart_weeks = []
    chart_expected = []
    chart_actual = []
    cumulative_expected = 0
    cumulative_actual = 0
    chart_cumulative_expected = []
    chart_cumulative_actual = []
    
    for week_schedule in schedule:
        chart_weeks.append(week_schedule.week_number)
        expected_amount = float(week_schedule.expected_amount)
        paid_amount = float(week_schedule.paid_amount) if week_schedule.paid_amount else 0
        
        chart_expected.append(expected_amount)
        chart_actual.append(paid_amount)
        
        cumulative_expected += expected_amount
        cumulative_actual += paid_amount
        chart_cumulative_expected.append(cumulative_expected)
        chart_cumulative_actual.append(cumulative_actual)
    
    # Calculate overdue amounts
    total_overdue = 0
    for overdue in schedule.filter(status='overdue'):
        total_overdue += float(overdue.expected_amount)
    
    # Check if loan is nearing completion (80% or more paid)
    is_nearing_completion = progress >= 80
    
    # Get collateral details if exists
    collateral_info = None
    if hasattr(loan, 'collateral') and loan.collateral:
        collateral = loan.collateral
        
        # Safely get asset type display
        asset_type_display = None
        if hasattr(collateral, 'get_asset_type_display'):
            try:
                asset_type_display = collateral.get_asset_type_display()
            except (AttributeError, TypeError):
                asset_type_display = str(getattr(collateral, 'asset_type', 'Asset'))
        elif hasattr(collateral, 'asset_type'):
            if hasattr(collateral.asset_type, 'name'):
                asset_type_display = collateral.asset_type.name
            else:
                asset_type_display = str(collateral.asset_type)
        else:
            asset_type_display = 'Asset'
        
        # Safely get condition display - use property if available
        condition_display = None
        if hasattr(collateral, 'get_condition_display_name'):
            condition_display = collateral.get_condition_display_name
        elif hasattr(collateral, 'condition'):
            condition_display = collateral.condition.replace('_', ' ').title()
        else:
            condition_display = 'Good'
        
        collateral_info = {
            'id': collateral.id,
            'type': asset_type_display,
            'serial': getattr(collateral, 'serial_number', 'N/A'),
            'value': float(collateral.estimated_value) if hasattr(collateral, 'estimated_value') else 0,
            'condition': condition_display,
            'location': getattr(collateral, 'storage_location', 'N/A'),
            'insured': getattr(collateral, 'is_insured', False)
        }
    
    # Get payment history for timeline
    payment_history = []
    for payment in payments[:10]:  # Last 10 payments
        payment_history.append({
            'id': payment.id,
            'amount': float(payment.amount),
            'date': payment.payment_date.isoformat() if payment.payment_date else None,
            'method': payment.payment_method.name if payment.payment_method else 'Cash',
            'reference': payment.transaction_reference or '',
        })
    
    # Prepare schedule data for frontend - FIXED: Remove payment_date reference
    schedule_data = []
    for week_schedule in schedule:
        schedule_data.append({
            'week': week_schedule.week_number,
            'due_date': week_schedule.due_date.isoformat() if hasattr(week_schedule, 'due_date') and week_schedule.due_date else None,
            'expected_amount': float(week_schedule.expected_amount) if hasattr(week_schedule, 'expected_amount') else 0,
            'paid_amount': float(week_schedule.paid_amount) if hasattr(week_schedule, 'paid_amount') and week_schedule.paid_amount else 0,
            'status': week_schedule.status if hasattr(week_schedule, 'status') else 'pending',
            # Remove payment_date if it doesn't exist
        })
    
    context = {
        'loan': loan,
        'schedule': schedule,
        'payments': payments,
        'total_paid': total_paid,
        'total_due': total_due,
        'remaining': remaining,
        'progress': round(progress, 2),
        'next_due': next_due,
        'on_time_payments': on_time_payments,
        'late_payments': late_payments,
        'pending_payments': pending_payments,
        'total_schedule_count': schedule_count,
        'payment_performance': round(payment_performance, 2),
        'avg_payment': round(avg_payment, 2),
        'days_since_last_payment': days_since_last_payment,
        'estimated_completion': estimated_completion,
        'payment_methods': payment_methods,
        'total_overdue': round(total_overdue, 2),
        'is_nearing_completion': is_nearing_completion,
        'collateral_info': collateral_info,
        'payment_history': payment_history,
        # Chart data as JSON for frontend
        'chart_weeks_json': json.dumps(chart_weeks),
        'chart_expected_json': json.dumps(chart_expected),
        'chart_actual_json': json.dumps(chart_actual),
        'chart_cumulative_expected_json': json.dumps(chart_cumulative_expected),
        'chart_cumulative_actual_json': json.dumps(chart_cumulative_actual),
        'schedule_data_json': json.dumps(schedule_data),
    }
    
    return render(request, 'loans/loan_detail.html', context)

# API endpoints for AJAX calls
@login_required
def api_loan_list(request):
    """API endpoint to get loans as JSON for frontend"""
    if not is_officer_or_higher(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    loans = Loan.objects.all().select_related('client').order_by('-created_at')
    
    # Apply filters
    search = request.GET.get('search', '')
    if search:
        loans = loans.filter(
            Q(loan_id__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        loans = loans.filter(status=status)
    
    loan_data = []
    for loan in loans:
        total_paid = loan.amount_paid if hasattr(loan, 'amount_paid') else 0
        total_payback = loan.total_payback if hasattr(loan, 'total_payback') else loan.principal
        remaining_balance = total_payback - total_paid
        
        # Check if overdue
        is_overdue = False
        if loan.status == 'active':
            next_schedule = RepaymentSchedule.objects.filter(
                loan=loan, status='pending'
            ).order_by('due_date').first()
            if next_schedule and next_schedule.due_date < timezone.now().date():
                is_overdue = True
        
        loan_data.append({
            'id': loan.id,
            'loan_id': loan.loan_id,
            'client_name': loan.client.full_name,
            'principal': float(loan.principal),
            'total_payback': float(total_payback),
            'remaining_balance': float(remaining_balance),
            'status': loan.status,
            'status_display': loan.get_status_display(),
            'is_overdue': is_overdue,
            'created_at': loan.created_at.isoformat() if loan.created_at else None,
        })
    
    return JsonResponse({'loans': loan_data})


@login_required
def api_loan_stats(request):
    """API endpoint to get loan statistics"""
    if not is_officer_or_higher(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    stats = {
        'total': Loan.objects.count(),
        'active': Loan.objects.filter(status='active').count(),
        'pending': Loan.objects.filter(status='pending').count(),
        'completed': Loan.objects.filter(status='completed').count(),
        'defaulted': Loan.objects.filter(status='defaulted').count(),
        'total_disbursed': float(Loan.objects.filter(status__in=['active', 'completed']).aggregate(total=Sum('principal'))['total'] or 0),
    }
    return JsonResponse(stats)


@login_required
def api_loan_schedule(request, loan_id):
    """API endpoint to get repayment schedule for a loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if not is_officer_or_higher(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')
    
    schedule_data = []
    for item in schedule:
        schedule_data.append({
            'week': item.week_number,
            'due_date': item.due_date.isoformat() if item.due_date else None,
            'expected_amount': float(item.expected_amount),
            'paid_amount': float(item.paid_amount) if item.paid_amount else 0,
            'status': item.status,
            'status_display': item.get_status_display(),
            'payment_date': item.payment_date.isoformat() if item.payment_date else None,
        })
    
    return JsonResponse({'schedule': schedule_data})

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from decimal import Decimal
from clients.models import Client
from collateral.models import Collateral
from .models import Loan

logger = logging.getLogger(__name__)

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from decimal import Decimal
from django.conf import settings
from clients.models import Client
from collateral.models import Collateral
from .models import Loan

logger = logging.getLogger(__name__)

def is_admin_or_ceo(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin'])

@login_required
@user_passes_test(is_admin_or_ceo)
def loan_create(request):
    """Create new loan application with enhanced collateral handling"""
    from clients.models import Client
    from collateral.models import Collateral
    
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        collateral_id = request.POST.get('collateral_id')
        
        # Validate client
        if not client_id:
            messages.error(request, 'Please select a client.')
            return redirect('loans:loan_create')
        
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            messages.error(request, 'Selected client does not exist.')
            return redirect('loans:loan_create')
        
        # Validate collateral if provided
        collateral = None
        if collateral_id:
            try:
                collateral = Collateral.objects.get(id=collateral_id)
                # Check if collateral is available
                if collateral.is_seized:
                    messages.warning(request, f'Selected collateral "{collateral}" is seized and cannot be used.')
                    collateral = None
                elif collateral.status != 'available':
                    messages.warning(request, f'Selected collateral "{collateral}" status is {collateral.status}. Only available collateral can be used.')
                    collateral = None
                elif hasattr(collateral, 'loan') and collateral.loan and collateral.loan.status in ['active', 'pending']:
                    messages.warning(request, f'Selected collateral is already assigned to another active loan.')
                    collateral = None
                else:
                    messages.info(request, f'Collateral "{collateral}" selected successfully.')
            except Collateral.DoesNotExist:
                messages.warning(request, 'Selected collateral does not exist. Loan can be processed without collateral.')
        
        # Get form data with validation
        try:
            principal = float(request.POST.get('principal', 0))
            interest_rate = float(request.POST.get('interest_rate', 0))
            interest_period = request.POST.get('interest_period', 'week')
            duration_value = int(request.POST.get('duration_weeks', 0))
        except ValueError as e:
            logger.error(f"Value error in loan creation: {e}")
            messages.error(request, 'Invalid numeric values provided.')
            return redirect('loans:loan_create')
        
        # Validate principal amount
        if principal <= 0:
            messages.error(request, 'Principal amount must be greater than zero.')
            return redirect('loans:loan_create')
        
        if principal < 100:
            messages.error(request, 'Minimum loan amount is ZMW 100.')
            return redirect('loans:loan_create')
        
        if principal > 1000000:
            messages.error(request, 'Maximum loan amount is ZMW 1,000,000.')
            return redirect('loans:loan_create')
        
        # Validate interest rate
        if interest_rate <= 0:
            messages.error(request, 'Interest rate must be greater than zero.')
            return redirect('loans:loan_create')
        
        if interest_rate > 50:
            messages.error(request, 'Interest rate cannot exceed 50%.')
            return redirect('loans:loan_create')
        
        # Validate duration
        if duration_value <= 0:
            messages.error(request, 'Duration must be greater than zero.')
            return redirect('loans:loan_create')
        
        # Convert months to weeks if needed
        if interest_period == 'month':
            duration_weeks = duration_value * 4
            if duration_value > 24:
                messages.error(request, 'Maximum loan duration is 24 months (2 years).')
                return redirect('loans:loan_create')
        else:
            duration_weeks = duration_value
            if duration_value > 52:
                messages.error(request, 'Maximum loan duration is 52 weeks (1 year).')
                return redirect('loans:loan_create')
        
        # Create the loan
        try:
            loan = Loan.objects.create(
                client=client,
                collateral=collateral,
                principal=principal,
                interest_rate=interest_rate,
                interest_period=interest_period,
                duration_weeks=duration_weeks,
                purpose=request.POST.get('purpose', '').strip(),
                notes=request.POST.get('notes', '').strip(),
                created_by=request.user,
                status='pending'
            )
            
            # Calculate loan financials
            loan.calculate_loan()
            loan.save()
            
            # If collateral was used, update its status
            if collateral:
                collateral.status = 'assigned'
                collateral.save()
                messages.info(request, f'Collateral "{collateral}" has been assigned to this loan.')
            
            messages.success(
                request, 
                f'✅ Loan application {loan.loan_id} created successfully!\n'
                f'📊 Principal: ZMW {principal:,.2f}\n'
                f'💰 Total Payback: ZMW {loan.total_payback:,.2f}\n'
                f'📅 {loan.get_payment_frequency_display()}: ZMW {loan.installment_amount:,.2f}'
            )
            
            return redirect('loans:loan_detail', loan_id=loan.id)
            
        except Exception as e:
            logger.error(f"Error creating loan: {str(e)}")
            messages.error(request, f'Error creating loan: {str(e)}')
            return redirect('loans:loan_create')
    
    # GET request - display form with all data
    logger.info("Loading loan creation form")
    
    # Get all active clients
    clients = Client.objects.filter(status='active')
    clients_count = clients.count()
    logger.info(f"Found {clients_count} active clients")
    
    # Get all available collateral
    collaterals = []
    try:
        # Get collateral that is available, not seized
        collaterals_queryset = Collateral.objects.filter(
            is_seized=False,
            status='available'
        )
        
        # Check loan relationship - handle both ForeignKey and ManyToMany
        if hasattr(Collateral, 'loan'):
            # ForeignKey relationship
            collaterals_queryset = collaterals_queryset.filter(
                Q(loan__isnull=True) | Q(loan__status__not_in=['active', 'pending'])
            )
        elif hasattr(Collateral, 'loans'):
            # ManyToMany relationship
            collaterals_queryset = collaterals_queryset.exclude(
                loans__status__in=['active', 'pending']
            ).distinct()
        
        # Convert to list
        collaterals = list(collaterals_queryset)
        
        logger.info(f"Found {len(collaterals)} available collateral items")
        
    except Exception as e:
        logger.error(f"Error fetching collateral: {str(e)}")
        collaterals = []
    
    # If no clients found, show all clients
    if clients_count == 0:
        messages.info(request, 'No active clients found. Please register a client first.')
        clients = Client.objects.all()
    
    context = {
        'clients': clients,
        'collaterals': collaterals,
        'collateral_count': len(collaterals),
        'title': 'Create New Loan Application',
        'has_collateral': len(collaterals) > 0,
    }
    
    # Add debug info in development
    if settings.DEBUG:
        context['debug_collateral_count'] = len(collaterals)
        context['debug_all_collateral_count'] = Collateral.objects.filter(is_seized=False).count()
    
    return render(request, 'loans/loan_form.html', context)
@login_required
@user_passes_test(is_admin_or_ceo)
def loan_edit(request, loan_id):
    """Edit loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        loan.principal = request.POST.get('principal', loan.principal)
        loan.interest_rate = request.POST.get('interest_rate', loan.interest_rate)
        loan.interest_period = request.POST.get('interest_period', loan.interest_period)
        loan.duration_weeks = request.POST.get('duration_weeks', loan.duration_weeks)
        loan.purpose = request.POST.get('purpose', loan.purpose)
        loan.notes = request.POST.get('notes', loan.notes)
        loan.save()
        
        # Recalculate loan
        loan.calculate_loan()
        loan.save()
        
        messages.success(request, f'Loan {loan.loan_id} updated successfully!')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    clients = Client.objects.filter(status='active')
    collaterals = Collateral.objects.filter(is_seized=False) if Collateral.objects.exists() else []
    
    context = {
        'loan': loan,
        'clients': clients,
        'collaterals': collaterals,
        'title': 'Edit Loan'
    }
    
    return render(request, 'loans/loan_form.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_delete(request, loan_id):
    """Delete loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        loan_id_display = loan.loan_id
        loan.delete()
        messages.success(request, f'Loan {loan_id_display} deleted successfully!')
        return redirect('loans:loan_list')
    
    return render(request, 'loans/loan_confirm_delete.html', {'loan': loan})


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_approve(request, loan_id):
    """Approve loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        loan.approve(request.user, notes)
        messages.success(request, f'Loan {loan.loan_id} approved successfully!')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    return render(request, 'loans/loan_approve.html', {'loan': loan})


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_activate(request, loan_id):
    """Activate loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        loan.activate()
        messages.success(request, f'Loan {loan.loan_id} activated successfully!')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    return render(request, 'loans/loan_activate.html', {'loan': loan})


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_complete(request, loan_id):
    """Mark loan as completed"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        loan.complete()
        messages.success(request, f'Loan {loan.loan_id} marked as completed!')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    return render(request, 'loans/loan_complete.html', {'loan': loan})


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_default(request, loan_id):
    """Mark loan as defaulted"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        loan.default()
        messages.success(request, f'Loan {loan.loan_id} marked as defaulted!')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    return render(request, 'loans/loan_default.html', {'loan': loan})


@login_required
@user_passes_test(is_admin_or_ceo)
def loan_reject(request, loan_id):
    """Reject loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        loan.reject(reason)
        messages.success(request, f'Loan {loan.loan_id} rejected!')
        return redirect('loans:loan_list')
    
    return render(request, 'loans/loan_reject.html', {'loan': loan})

@login_required
def loan_calculator(request):
    """Loan calculator page"""
    return render(request, 'loans/loan_calculator.html')


@login_required
def api_loan_list(request):
    """API endpoint for loan list"""
    loans = Loan.objects.all().values(
        'id', 'loan_id', 'principal', 'status', 'total_payback', 'remaining_balance',
        'client__first_name', 'client__last_name', 'created_at'
    )
    
    loan_list = []
    for loan in loans:
        loan_list.append({
            'id': loan['id'],
            'loan_id': loan['loan_id'],
            'client_name': f"{loan['client__first_name']} {loan['client__last_name']}",
            'principal': float(loan['principal']),
            'status': loan['status'],
            'total_payback': float(loan['total_payback']) if loan['total_payback'] else 0,
            'remaining_balance': float(loan['remaining_balance']) if loan['remaining_balance'] else 0,
            'created_at': loan['created_at'],
        })
    
    return JsonResponse({'loans': loan_list})


@login_required
def api_loan_stats(request):
    """API endpoint for loan statistics"""
    stats = {
        'total': Loan.objects.count(),
        'active': Loan.objects.filter(status='active').count(),
        'pending': Loan.objects.filter(status='pending').count(),
        'approved': Loan.objects.filter(status='approved').count(),
        'completed': Loan.objects.filter(status='completed').count(),
        'defaulted': Loan.objects.filter(status='defaulted').count(),
        'total_disbursed': float(Loan.objects.filter(status__in=['active', 'completed']).aggregate(total=Sum('principal'))['total'] or 0),
    }
    
    return JsonResponse(stats)


@login_required
def api_loan_calculate(request):
    """API endpoint for loan calculation"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            principal = Decimal(str(data.get('amount', 0)))
            rate = Decimal(str(data.get('interest_rate', 10)))
            period_type = data.get('period_type', 'week')
            duration_weeks = int(data.get('duration_weeks', 12))
            
            if period_type == 'week':
                total_interest = principal * (rate / 100) * duration_weeks
                total_payback = principal + total_interest
                installment = total_payback / duration_weeks
                
                due_dates = []
                start_date = timezone.now().date()
                for week in range(1, duration_weeks + 1):
                    due_date = start_date + timezone.timedelta(weeks=week)
                    due_dates.append({
                        'period': week,
                        'date': due_date.strftime('%Y-%m-%d'),
                        'amount': float(installment)
                    })
            else:
                months = duration_weeks / 4
                total_interest = principal * (rate / 100) * months
                total_payback = principal + total_interest
                installment = total_payback / months
                
                due_dates = []
                start_date = timezone.now().date()
                for month in range(1, int(months) + 1):
                    due_date = start_date + timezone.timedelta(weeks=month*4)
                    due_dates.append({
                        'period': month,
                        'date': due_date.strftime('%Y-%m-%d'),
                        'amount': float(installment)
                    })
            
            return JsonResponse({
                'principal': float(principal),
                'interest_rate': float(rate),
                'total_interest': float(total_interest),
                'total_payback': float(total_payback),
                'installment_amount': float(installment),
                'duration': duration_weeks,
                'period_type': period_type,
                'due_dates': due_dates
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'POST method required'}, status=405)


@login_required
def api_upcoming_payments(request, loan_id):
    """API endpoint for upcoming payments"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get pending schedules
    pending_schedules = RepaymentSchedule.objects.filter(
        loan=loan,
        status__in=['pending', 'partial']
    ).order_by('due_date')[:5]
    
    payments = []
    for schedule in pending_schedules:
        payments.append({
            'week': schedule.week_number,
            'due_date': schedule.due_date.strftime('%Y-%m-%d'),
            'amount': float(schedule.expected_amount)
        })
    
    return JsonResponse({'payments': payments})

@login_required
def api_client_list(request):
    """API endpoint to get clients for select2 dropdown"""
    from clients.models import Client
    
    search = request.GET.get('search', '')
    clients = Client.objects.filter(status='active')
    
    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(client_id__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    client_list = []
    for client in clients[:20]:  # Limit to 20 results
        client_list.append({
            'id': client.id,
            'text': f"{client.full_name} ({client.client_id}) - {client.phone_number}",
            'name': client.full_name,
            'client_id': client.client_id,
            'phone': client.phone_number,
            'email': client.email or ''
        })
    
    return JsonResponse({'results': client_list})

@login_required
def api_loan_stats(request):
    """API endpoint for loan statistics"""
    from django.db.models import Sum
    from .models import Loan
    
    stats = {
        'total': Loan.objects.count(),
        'active': Loan.objects.filter(status='active').count(),
        'pending': Loan.objects.filter(status='pending').count(),
        'approved': Loan.objects.filter(status='approved').count(),
        'completed': Loan.objects.filter(status='completed').count(),
        'defaulted': Loan.objects.filter(status='defaulted').count(),
        'rejected': Loan.objects.filter(status='rejected').count(),
        'total_disbursed': float(Loan.objects.filter(status__in=['active', 'completed']).aggregate(total=Sum('principal'))['total'] or 0),
        'total_interest': float(Loan.objects.filter(status__in=['active', 'completed']).aggregate(total=Sum('total_interest'))['total'] or 0),
    }
    return JsonResponse(stats)

from django.template.loader import get_template
from django.http import HttpResponse
# ADD THIS INSTEAD:
from xhtml2pdf import pisa
from io import BytesIO
from .models import LoanAgreement


# Replace the existing generate_loan_agreement function with:
# loans/views.py - Add this function
@login_required
def generate_loan_agreement(request, loan_id):
    """Generate and download loan agreement PDF using reportlab with signature"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from io import BytesIO
    from PIL import Image as PILImage
    import os
    from django.conf import settings
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to generate this agreement.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    agreement, created = LoanAgreement.objects.get_or_create(loan=loan)
    payment_schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')[:10]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           topMargin=1.5*inch, 
                           bottomMargin=1.5*inch,
                           leftMargin=1*inch,
                           rightMargin=1*inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title', 
        parent=styles['Heading1'], 
        fontSize=24, 
        alignment=TA_CENTER, 
        spaceAfter=20,
        textColor=colors.HexColor('#1e3a8a')
    )
    
    section_style = ParagraphStyle(
        'Section', 
        parent=styles['Heading2'], 
        fontSize=14, 
        spaceBefore=12, 
        spaceAfter=8,
        textColor=colors.HexColor('#2563eb'),
        leftIndent=0
    )
    
    normal_style = ParagraphStyle(
        'Normal', 
        parent=styles['Normal'], 
        fontSize=10, 
        leading=14,
        alignment=TA_LEFT
    )
    
    small_style = ParagraphStyle(
        'Small', 
        parent=styles['Normal'], 
        fontSize=8, 
        textColor=colors.gray,
        alignment=TA_CENTER
    )
    
    story = []
    
    # Header
    story.append(Paragraph("KORATA LENDING SYSTEM", title_style))
    story.append(Paragraph("LOAN AGREEMENT", styles['Heading2']))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Agreement No: {agreement.agreement_number}", normal_style))
    story.append(Paragraph(f"Date: {agreement.agreement_date.strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 20))
    
    # Loan Details Section
    story.append(Paragraph("1. LOAN DETAILS", section_style))
    loan_data = [
        ["Loan ID:", loan.loan_id],
        ["Client:", loan.client.full_name],
        ["NRC:", loan.client.nrc],
        ["Phone:", loan.client.phone_number],
        ["Principal:", f"ZMW {loan.principal:,.2f}"],
        ["Interest Rate:", f"{loan.interest_rate}% per {loan.interest_period}"],
        ["Duration:", f"{loan.duration_weeks} weeks"],
        ["Total Interest:", f"ZMW {loan.total_interest:,.2f}"],
        ["Total Payback:", f"<b>ZMW {loan.total_payback:,.2f}</b>"],
        ["Weekly Payment:", f"<b>ZMW {loan.weekly_payment:,.2f}</b>"],
    ]
    
    t = Table(loan_data, colWidths=[100, 300])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Collateral Section (if exists)
    if loan.collateral:
        story.append(Paragraph("2. COLLATERAL INFORMATION", section_style))
        collateral_data = [
            ["Asset Type:", loan.collateral.get_asset_type_display()],
            ["Asset Title:", loan.collateral.title],
            ["Serial Number:", loan.collateral.serial_number],
            ["Estimated Value:", f"ZMW {loan.collateral.estimated_value:,.2f}"],
            ["Condition:", loan.collateral.get_condition_display()],
            ["Storage Location:", loan.collateral.storage_location],
        ]
        
        ct = Table(collateral_data, colWidths=[100, 300])
        ct.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ct)
        story.append(Spacer(1, 15))
    
    # Terms and Conditions
    story.append(Paragraph("3. TERMS AND CONDITIONS", section_style))
    terms = [
        "3.1 The Borrower agrees to repay the loan amount in full according to the payment schedule.",
        "3.2 Late payments will incur a penalty fee of 5% of the payment amount.",
        "3.3 The Lender may seize the collateral in case of default for more than 30 days.",
        "3.4 Early repayment is allowed without penalty.",
        "3.5 The Borrower must notify the Lender of any change in contact information.",
        "3.6 This agreement is legally binding once signed by both parties.",
    ]
    for term in terms:
        story.append(Paragraph(term, normal_style))
    story.append(Spacer(1, 15))
    
    # Payment Schedule
    story.append(Paragraph("4. PAYMENT SCHEDULE (First 10 Weeks)", section_style))
    
    schedule_data = [['Week', 'Due Date', 'Amount (ZMW)']]
    for schedule in payment_schedule:
        schedule_data.append([
            str(schedule.week_number),
            schedule.due_date.strftime('%d %b %Y'),
            f"{schedule.expected_amount:,.2f}"
        ])
    
    if len(payment_schedule) > 10:
        schedule_data.append(['...', 'See full schedule in dashboard', '...'])
    
    schedule_table = Table(schedule_data, colWidths=[80, 120, 120])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -2), 1, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(schedule_table)
    story.append(Spacer(1, 15))
    
    # Acknowledgment
    story.append(Paragraph("5. ACKNOWLEDGMENT", section_style))
    story.append(Paragraph("The Borrower acknowledges that they have read, understood, and agree to be bound by all the terms and conditions stated in this agreement.", normal_style))
    story.append(Spacer(1, 10))
    
    # Signatures Section with actual signature image
    story.append(Paragraph("6. SIGNATURES", section_style))
    story.append(Spacer(1, 20))
    
    # Create signature table
    sign_data = []
    
    # Borrower Signature Column
    borrower_cell = []
    if agreement.signature_image and agreement.signature_image.path and os.path.exists(agreement.signature_image.path):
        try:
            # Add signature image
            img = PILImage.open(agreement.signature_image.path)
            # Resize image for PDF
            img_width = 150
            img_height = int(img.height * (img_width / img.width))
            img_path = agreement.signature_image.path
            signature_img = Image(img_path, width=img_width, height=img_height)
            borrower_cell.append(signature_img)
            borrower_cell.append(Spacer(1, 5))
            borrower_cell.append(Paragraph(f"<b>{agreement.signed_by.get_full_name|default:agreement.signed_by.username}</b>", normal_style))
            borrower_cell.append(Paragraph(f"Signed: {agreement.signed_at.strftime('%d %b %Y %H:%M')}", small_style))
            borrower_cell.append(Paragraph(f"IP: {agreement.ip_address}", small_style))
        except Exception as e:
            borrower_cell.append(Paragraph("_________________________", normal_style))
            borrower_cell.append(Paragraph("Borrower's Signature", normal_style))
    else:
        borrower_cell.append(Paragraph("_________________________", normal_style))
        borrower_cell.append(Paragraph("Borrower's Signature", normal_style))
    
    # Lender Signature Column
    lender_cell = [
        Paragraph("_________________________", normal_style),
        Paragraph("Lender's Signature", normal_style),
        Spacer(1, 10),
        Paragraph("Korata Lending System", normal_style),
        Paragraph(f"Date: {timezone.now().strftime('%d %b %Y')}", small_style),
    ]
    
    # Create two-column table for signatures
    sign_table = Table([[borrower_cell, lender_cell]], colWidths=[200, 200])
    sign_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(sign_table)
    
    # Signed badge
    if agreement.signed:
        story.append(Spacer(1, 20))
        signed_text = Paragraph(
            f'<font color="white" bgcolor="#10b981"> ✓ DIGITALLY SIGNED ON {agreement.signed_at.strftime("%d %b %Y %H:%M")} </font>',
            ParagraphStyle('Signed', parent=normal_style, alignment=TA_CENTER)
        )
        story.append(signed_text)
    
    # Footer note
    story.append(Spacer(1, 30))
    story.append(Paragraph("This agreement is legally binding once signed by both parties.", small_style))
    story.append(Paragraph(f"Korata Lending System | {agreement.agreement_number}", small_style))
    
    # Build PDF
    doc.build(story)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="loan_agreement_{loan.loan_id}.pdf"'
    return response
@login_required
def view_loan_agreement(request, loan_id):
    """View loan agreement in browser"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this agreement.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    agreement, created = LoanAgreement.objects.get_or_create(loan=loan)
    payment_schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')
    
    return render(request, 'loans/loan_agreement_pdf.html', {
        'loan': loan,
        'agreement': agreement,
        'payment_schedule': payment_schedule,
    })
@require_http_methods(["POST"])
def sign_loan_agreement(request, loan_id):
    """Sign the loan agreement with digital signatures"""
    import json
    import base64
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from PIL import Image
    from io import BytesIO
    
    loan = get_object_or_404(Loan, id=loan_id)
    agreement, created = LoanAgreement.objects.get_or_create(loan=loan)
    
    try:
        data = json.loads(request.body)
        
        # Check if already signed by this party
        is_lender = data.get('is_lender', False)
        
        if is_lender:
            if agreement.lender_signed:
                return JsonResponse({'success': False, 'error': 'Lender signature already provided'}, status=400)
        else:
            if agreement.borrower_signed:
                return JsonResponse({'success': False, 'error': 'Borrower signature already provided'}, status=400)
        
        # Process signature images
        borrower_signature = data.get('borrower_signature')
        lender_signature = data.get('lender_signature')
        
        # Handle Borrower Signature
        if borrower_signature:
            format, imgstr = borrower_signature.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            
            # Optimize image
            img = Image.open(BytesIO(image_data))
            if img.width > 300:
                ratio = 300 / img.width
                new_size = (300, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            
            filename = f"borrower_{agreement.agreement_number}_{int(timezone.now().timestamp())}.png"
            agreement.borrower_signature_image.save(filename, ContentFile(buffer.getvalue()), save=False)
            agreement.borrower_signed = True
            agreement.borrower_signed_by = loan.client.registered_by if hasattr(loan.client, 'registered_by') else None
            agreement.borrower_signed_at = timezone.now()
            agreement.borrower_ip = request.META.get('REMOTE_ADDR', '')
        
        # Handle Lender Signature
        if lender_signature:
            format, imgstr = lender_signature.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            
            # Optimize image
            img = Image.open(BytesIO(image_data))
            if img.width > 300:
                ratio = 300 / img.width
                new_size = (300, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            
            filename = f"lender_{agreement.agreement_number}_{int(timezone.now().timestamp())}.png"
            agreement.lender_signature_image.save(filename, ContentFile(buffer.getvalue()), save=False)
            agreement.lender_signed = True
            agreement.lender_signed_by = request.user
            agreement.lender_signed_at = timezone.now()
            agreement.lender_ip = request.META.get('REMOTE_ADDR', '')
        
        # Update overall signed status
        if agreement.borrower_signed and agreement.lender_signed:
            agreement.signed = True
            agreement.signed_at = timezone.now()
        
        agreement.save()
        
        # Generate updated PDF with both signatures
        if agreement.signed:
            generate_agreement_pdf_with_signatures(loan, agreement)
        
        return JsonResponse({'success': True, 'message': 'Signatures recorded successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def generate_agreement_pdf_with_signatures(loan, agreement):
    """Generate PDF with both signatures"""
    from xhtml2pdf import pisa
    from django.template.loader import get_template
    from django.core.files.base import ContentFile
    from io import BytesIO
    
    payment_schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')
    
    template = get_template('loans/loan_agreement_pdf.html')
    html = template.render({
        'loan': loan,
        'agreement': agreement,
        'payment_schedule': payment_schedule,
    })
    
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    
    if not pisa_status.err:
        pdf_buffer.seek(0)
        filename = f"agreement_{agreement.agreement_number}.pdf"
        agreement.pdf_file.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
@login_required
def view_loan_agreement(request, loan_id):
    """View loan agreement in browser - HTML version"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this agreement.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    agreement, created = LoanAgreement.objects.get_or_create(loan=loan)
    payment_schedule = RepaymentSchedule.objects.filter(loan=loan).order_by('week_number')
    
    return render(request, 'loans/loan_agreement_pdf.html', {
        'loan': loan,
        'agreement': agreement,
        'payment_schedule': payment_schedule,
    })