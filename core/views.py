# core/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from clients.models import Client
from loans.models import Loan
from payments.models import Payment
from collateral.models import Collateral
from notifications.models import Notification


def home(request):
    """Home page view"""
    context = {
        'total_clients': Client.objects.count(),
        'total_loans': Loan.objects.count(),
        'total_disbursed': Loan.objects.aggregate(total=Sum('principal'))['total'] or 0,
    }
    return render(request, 'core/home.html', context)

# core/views.py - Update your dashboard view

@login_required
def dashboard(request):
    """Main dashboard view with paginated records and analytics"""
    
    # Get all loans with related client data
    all_loans = Loan.objects.all().select_related('client').order_by('-created_at')
    
    # Get all notifications for the current user
    all_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Get all pending tasks
    pending_approvals_list = Loan.objects.filter(status='pending').select_related('client')
    pending_payments_list = Payment.objects.filter(status='pending').select_related('loan__client')
    
    # Get all active loans for monitoring - using expected_end_date
    active_loans_list = Loan.objects.filter(status='active').select_related('client').order_by('expected_end_date')
    
    # Get all upcoming payments (next 7 days)
    today = timezone.now().date()
    upcoming_payments_list = Payment.objects.filter(
        payment_date__date__gte=today,
        payment_date__date__lte=today + timedelta(days=7),
        status='pending'
    ).select_related('loan__client').order_by('payment_date')
    
    # Get recent clients
    recent_clients = Client.objects.all().order_by('-registration_date')[:10]
    
    # Get recent payments
    recent_payments = Payment.objects.filter(status='completed').select_related('loan__client').order_by('-payment_date')[:10]
    
    # Pagination for active loans (10 per page for dashboard)
    active_loans_paginator = Paginator(active_loans_list, 10)
    active_loans_page = request.GET.get('active_page', 1)
    active_loans_obj = active_loans_paginator.get_page(active_loans_page)
    
    # Count statistics
    pending_approvals_count = pending_approvals_list.count()
    pending_payments_count = pending_payments_list.count()
    active_loans_count = active_loans_list.count()
    upcoming_payments_count = upcoming_payments_list.count()
    
    # Calculate summary statistics
    total_disbursed = Loan.objects.aggregate(total=Sum('principal'))['total'] or 0
    total_collections = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    active_clients_count = Client.objects.filter(status='active').count()
    total_clients_count = Client.objects.count()
    total_loans_count = all_loans.count()
    
    # Calculate loan status distribution
    loan_status = {
        'active': Loan.objects.filter(status='active').count(),
        'pending': Loan.objects.filter(status='pending').count(),
        'approved': Loan.objects.filter(status='approved').count(),
        'completed': Loan.objects.filter(status='completed').count(),
        'defaulted': Loan.objects.filter(status='defaulted').count(),
    }
    
    # Calculate financial metrics
    total_principal = Loan.objects.filter(status='active').aggregate(total=Sum('principal'))['total'] or 0
    total_interest = Loan.objects.filter(status='active').aggregate(total=Sum('total_interest'))['total'] or 0
    total_repaid = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    outstanding = total_disbursed - total_repaid
    
    # Calculate repayment rate
    repayment_rate = round((total_repaid / total_disbursed * 100) if total_disbursed > 0 else 0, 1)
    
    # Calculate payment completion rate
    total_expected_payments = Loan.objects.aggregate(total=Sum('weekly_payment'))['total'] or 0
    payment_completion_rate = round((total_repaid / total_expected_payments * 100) if total_expected_payments > 0 else 0, 1)
    
    # Calculate monthly payments count
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_payments_count = Payment.objects.filter(
        payment_date__year=current_year,
        payment_date__month=current_month,
        status='completed'
    ).count()
    
    total_payments_count = Payment.objects.filter(status='completed').count()
    
    # Calculate growth metrics
    today = timezone.now().date()
    last_month = today - timedelta(days=30)
    previous_month = last_month - timedelta(days=30)
    
    clients_last_month = Client.objects.filter(registration_date__gte=last_month).count()
    clients_previous_month = Client.objects.filter(registration_date__range=[previous_month, last_month]).count()
    client_growth = round(((clients_last_month - clients_previous_month) / clients_previous_month * 100) if clients_previous_month > 0 else 0, 1)
    
    # Chart data - Last 6 months loan disbursement
    chart_labels = []
    chart_data = []
    
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        if i > 0:
            month_end = (month_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            month_end = today
        
        month_label = month_date.strftime('%B %Y')
        chart_labels.append(month_label)
        
        monthly_disbursed = Loan.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
            status__in=['active', 'completed', 'approved']
        ).aggregate(total=Sum('principal'))['total'] or 0
        
        chart_data.append(float(monthly_disbursed))
    
    # Pending KYC count (if you have this field)
    pending_kyc = Client.objects.filter(kyc_verified=False).count() if hasattr(Client, 'kyc_verified') else 0
    
    context = {
        # Paginated objects
        'active_loans': active_loans_obj,
        'notifications': all_notifications[:10],
        'pending_approvals': pending_approvals_list[:5],
        'pending_payments': pending_payments_list[:5],
        'recent_clients': recent_clients,
        'recent_payments': recent_payments,
        
        # Counts
        'pending_approvals_count': pending_approvals_count,
        'pending_payments_count': pending_payments_count,
        'active_loans_count': active_loans_count,
        'upcoming_payments_count': upcoming_payments_count,
        'total_loans_count': total_loans_count,
        'total_notifications_count': all_notifications.count(),
        'total_clients_count': total_clients_count,
        'total_payments_count': total_payments_count,
        'monthly_payments_count': monthly_payments_count,
        
        # Summary statistics for dashboard cards
        'total_clients': total_clients_count,
        'active_clients': active_clients_count,
        'total_loans': total_loans_count,
        'total_disbursed': total_disbursed,
        'total_collections': total_collections,
        'total_principal': total_principal,
        'total_interest': total_interest,
        'total_repaid': total_repaid,
        'outstanding': outstanding,
        'repayment_rate': repayment_rate,
        'payment_completion_rate': payment_completion_rate,
        
        # Loan status distribution
        'loan_status': loan_status,
        
        # Growth metrics
        'client_growth': client_growth,
        'pending_kyc': pending_kyc,
        
        # Chart data
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'dashboard.html', context)

@login_required
def api_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get client stats
    total_clients = Client.objects.count()
    active_clients = Client.objects.filter(status='active').count()
    
    # Get loan stats
    total_loans = Loan.objects.count()
    active_loans = Loan.objects.filter(status='active').count()
    pending_loans = Loan.objects.filter(status='pending').count()
    completed_loans = Loan.objects.filter(status='completed').count()
    defaulted_loans = Loan.objects.filter(status='defaulted').count()
    
    # Get payment stats
    total_collections = float(Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0)
    today_collections = float(Payment.objects.filter(payment_date__date=today, status='completed').aggregate(total=Sum('amount'))['total'] or 0)
    week_collections = float(Payment.objects.filter(payment_date__date__gte=week_start, status='completed').aggregate(total=Sum('amount'))['total'] or 0)
    month_collections = float(Payment.objects.filter(payment_date__date__gte=month_start, status='completed').aggregate(total=Sum('amount'))['total'] or 0)
    
    # Get pending counts
    pending_payments = Payment.objects.filter(status='pending').count()
    
    # Get collateral stats
    total_collateral = Collateral.objects.count()
    pledged_collateral = Collateral.objects.filter(status='pledged').count()
    
    # Calculate growth percentages
    last_month = today - timedelta(days=30)
    previous_month = last_month - timedelta(days=30)
    
    clients_last_month = Client.objects.filter(registration_date__gte=last_month).count()
    clients_previous_month = Client.objects.filter(registration_date__range=[previous_month, last_month]).count()
    client_growth = round(((clients_last_month - clients_previous_month) / clients_previous_month * 100) if clients_previous_month > 0 else 0, 1)
    
    loans_last_month = Loan.objects.filter(created_at__date__gte=last_month).count()
    loans_previous_month = Loan.objects.filter(created_at__date__range=[previous_month, last_month]).count()
    loan_growth = round(((loans_last_month - loans_previous_month) / loans_previous_month * 100) if loans_previous_month > 0 else 0, 1)
    
    stats = {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'pending_loans': pending_loans,
        'completed_loans': completed_loans,
        'defaulted_loans': defaulted_loans,
        'total_collections': total_collections,
        'today_collections': today_collections,
        'week_collections': week_collections,
        'month_collections': month_collections,
        'pending_payments': pending_payments,
        'total_collateral': total_collateral,
        'pledged_collateral': pledged_collateral,
        'client_growth': client_growth,
        'loan_growth': loan_growth,
    }
    return JsonResponse(stats)


@login_required
def keep_alive(request):
    """Keep session alive"""
    if request.method == 'POST':
        request.session['last_activity'] = timezone.now().isoformat()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def ai_chat(request):
    """AI Chat Interface"""
    return render(request, 'core/ai_chat.html')


# core/views.py - Update AI chat endpoint
from .ai_service import ai_assistant

# core/views.py - Update the ai_chat_api function

# core/views.py
from .ai_service import ai_assistant  # Make sure this import is correct

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def ai_chat_api(request):
    """API endpoint for AI chat"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        # Log the incoming message
        print(f"📝 User message: {user_message}")
        
        # Get response from AI assistant
        result = ai_assistant.get_response(user_message)
        
        # Log the response
        print(f"🤖 AI response provider: {result.get('provider')}")
        print(f"🤖 AI response: {result['response'][:100]}...")
        
        return JsonResponse({
            'success': True,
            'response': result['response'],
            'provider': result.get('provider', 'unknown')
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'response': "I'm having trouble processing your request. Please try again."
        }, status=500)
@login_required
def ai_loan_assessment(request, loan_id):
    """AI-powered loan risk assessment"""
    from loans.models import Loan, RepaymentSchedule
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Calculate loan metrics
    total_paid = Payment.objects.filter(loan=loan, status='completed').aggregate(total=Sum('amount'))['total'] or 0
    progress = (float(total_paid) / float(loan.total_payback) * 100) if loan.total_payback > 0 else 0
    
    # Use expected_end_date instead of end_date
    days_remaining = max(0, (loan.expected_end_date - timezone.now().date()).days) if loan.expected_end_date else 0
    
    assessment = {
        'loan_id': loan.loan_id,
        'risk_level': 'Low' if progress > 50 else 'Medium' if progress > 25 else 'High',
        'risk_score': min(100, max(0, 100 - progress)),
        'recommendation': generate_risk_recommendation(progress),
        'factors': generate_risk_factors(loan, progress),
        'progress_percentage': round(progress, 1),
        'days_remaining': days_remaining,
        'on_time_payments': RepaymentSchedule.objects.filter(loan=loan, status='paid').count() if hasattr(RepaymentSchedule, 'objects') else 0,
    }
    
    if request.method == 'POST':
        return JsonResponse(assessment)
    
    return render(request, 'core/ai_assessment.html', {'loan': loan, 'assessment': assessment})


@login_required
def ai_eligibility_check(request, client_id):
    """AI-powered client eligibility check"""
    from clients.models import Client
    from decimal import Decimal
    
    client = get_object_or_404(Client, id=client_id)
    
    # Calculate eligibility metrics
    active_loans = client.loans.filter(status='active').count()
    total_borrowed = client.loans.filter(status__in=['active', 'completed']).aggregate(total=Sum('principal'))['total'] or 0
    completed_loans = client.loans.filter(status='completed').count()
    has_defaulted = client.loans.filter(status='defaulted').exists()
    
    eligibility = {
        'client_name': client.full_name,
        'eligible': active_loans < 3 and client.kyc_verified and not has_defaulted,
        'max_loan_amount': calculate_max_loan(client),
        'reason': generate_eligibility_reason(client, active_loans, has_defaulted),
        'suggestions': generate_eligibility_suggestions(client, active_loans, has_defaulted, client.kyc_verified),
        'active_loans': active_loans,
        'completed_loans': completed_loans,
        'total_borrowed': float(total_borrowed),
        'credit_score': getattr(client, 'credit_score', 650),
    }
    
    if request.method == 'POST':
        return JsonResponse(eligibility)
    
    return render(request, 'core/ai_eligibility.html', {'client': client, 'eligibility': eligibility})


# Helper functions
def generate_smart_response(message):
    """Generate intelligent response based on keywords"""
    msg = message.lower()
    
    if 'loan' in msg and 'requirement' in msg:
        return "To apply for a loan, you need:\n\n📋 Valid NRC/Passport\n💰 Proof of income (payslips or bank statements)\n🏠 Collateral documentation\n📝 Completed application form\n✅ KYC verification\n\nWould you like me to help you start an application?"
    
    if 'interest' in msg:
        return "Interest rates range from 5% to 15% per annum, depending on:\n• Loan type and purpose\n• Loan duration\n• Collateral value\n• Credit history\n• Payment history\n\nWould you like a personalized rate estimate?"
    
    if 'payment' in msg and 'method' in msg:
        return "We accept multiple payment methods:\n\n📱 Mobile Money (MTN, Airtel, Zamtel) - Instant\n🏦 Bank Transfer - 1-2 business days\n💵 Cash at our offices - Instant\n📝 Cheque - 3-5 business days\n💳 Card (Visa, Mastercard) - Instant\n\nMobile Money and Cash are the fastest options!"
    
    if 'late' in msg or 'overdue' in msg:
        return "⚠️ Late Payment Policy:\n\n• 1-3 days late: Reminder notification\n• 3-7 days late: 5% late fee applied\n• 7-30 days late: Additional penalty interest\n• 30+ days late: May lead to collateral seizure\n\n💡 I recommend contacting our collections department immediately to arrange a payment plan."
    
    if 'collateral' in msg:
        return "🏠 Acceptable Collateral:\n\n• Vehicles (Cars, trucks, motorcycles) - 70-80% LTV\n• Property (Land, houses, commercial) - 60-70% LTV\n• Equipment (Machinery, electronics) - 50-60% LTV\n• Jewelry (Gold, diamonds) - 40-50% LTV\n\nHigher value collateral = Better loan terms!\n\nWould you like to register collateral?"
    
    if 'kyc' in msg or 'verification' in msg:
        return "✅ KYC Verification Process:\n\n1. Submit valid NRC/Passport\n2. Provide proof of residence (utility bill)\n3. Proof of income (payslips/bank statements)\n4. In-person verification (if required)\n5. Biometric capture\n\nVerification typically takes 24-48 hours once all documents are submitted."
    
    if 'status' in msg or 'application' in msg:
        return "You can check your application status by:\n\n1. Logging into your dashboard\n2. Clicking on 'My Loans'\n3. Viewing the status column\n\nStatus indicators:\n🟡 Pending - Under review\n🟢 Approved - Ready for disbursement\n🔴 Rejected - Check reasons\n🔵 Active - Currently paying"
    
    return "I'm here to help with loans, payments, collateral, and general inquiries. Could you please rephrase your question? You can ask me about:\n\n• Loan requirements\n• Interest rates\n• Payment methods\n• Late payment policies\n• Collateral valuation\n• KYC verification\n• Application status"


def generate_risk_recommendation(progress):
    """Generate risk recommendation based on payment progress"""
    if progress >= 50:
        return "Low risk - Client is on track with payments. Continue regular monitoring."
    elif progress >= 25:
        return "Medium risk - Client has made some payments but may need follow-up. Send automated payment reminders."
    else:
        return "High risk - Client is significantly behind on payments. Immediate escalation to collections department required."


def generate_risk_factors(loan, progress):
    """Generate risk factors for loan"""
    factors = []
    
    if loan.status == 'defaulted':
        factors.append("Loan is in default status")
    if progress < 25:
        factors.append("Critical payment progress (below 25%)")
    elif progress < 50:
        factors.append("Below target payment progress (below 50%)")
    if hasattr(loan, 'late_payment_count') and loan.late_payment_count > 0:
        factors.append(f"Multiple late payments ({loan.late_payment_count} occurrences)")
    
    if not factors:
        factors.append("No major risk factors identified")
    
    return factors


def calculate_max_loan(client):
    """Calculate maximum loan amount for client"""
    from decimal import Decimal
    
    monthly_income = float(client.monthly_income) if client.monthly_income else 0
    max_loan = monthly_income * 5  # 5x monthly income
    
    # Check existing loans
    existing_total = client.loans.filter(status='active').aggregate(total=Sum('principal'))['total'] or 0
    available = max(0, max_loan - float(existing_total))
    
    # Consider collateral value if available
    if hasattr(client, 'collaterals'):
        collateral_value = client.collaterals.aggregate(total=Sum('estimated_value'))['total'] or 0
        available = max(available, float(collateral_value) * 0.7)
    
    return min(available, 100000)  # Cap at ZMW 100,000


def generate_eligibility_reason(client, active_loans, has_defaulted):
    """Generate eligibility reason"""
    if has_defaulted:
        return "Not eligible - Previous loan default on record"
    
    if active_loans >= 3:
        return "Not eligible - Too many active loans (maximum 3)"
    
    if not client.kyc_verified:
        return "Not eligible - KYC verification required. Please complete KYC process."
    
    if float(client.monthly_income or 0) < 1000:
        return "Not eligible - Monthly income below minimum requirement (ZMW 1,000)"
    
    return "Eligible - Meets all criteria! Ready to apply."


def generate_eligibility_suggestions(client, active_loans, has_defaulted, kyc_verified):
    """Generate suggestions to improve eligibility"""
    suggestions = []
    
    if has_defaulted:
        suggestions.append("Settle outstanding defaulted loans")
        suggestions.append("Contact collections to arrange payment plan")
    
    if active_loans >= 3:
        suggestions.append("Complete payments on existing loans before applying for new ones")
        suggestions.append("Consider early repayment to free up eligibility")
    
    if not kyc_verified:
        suggestions.append("Complete KYC verification process (submit NRC, proof of residence, income proof)")
        suggestions.append("Visit our office for biometric capture")
    
    if float(client.monthly_income or 0) < 1000:
        suggestions.append("Increase monthly income through additional employment or business")
        suggestions.append("Provide additional income proof (e.g., business statements, rental income)")
        suggestions.append("Consider applying with a co-signer or additional collateral")
    
    if not suggestions:
        suggestions.append("✓ Your profile looks excellent! You are eligible for a loan.")
        suggestions.append("Apply now to get your loan approved quickly")
    
    return suggestions


# core/views.py - Add a status endpoint
@login_required
def ai_status(request):
    """Check AI service status"""
    status = {
        'ollama_available': ai_assistant.use_ollama,
        'openai_available': ai_assistant.openai_client is not None,
        'current_provider': ai_assistant.current_provider,
        'model': ai_assistant.model
    }
    return JsonResponse(status)

@login_required
def ai_status(request):
    """Check AI service status"""
    from .ai_service import ai_assistant
    
    # Test AI response
    test_response = ai_assistant.get_response("Hello, are you working?")
    
    status = {
        'ollama_available': ai_assistant.use_ollama,
        'openai_available': ai_assistant.openai_client is not None,
        'current_provider': ai_assistant.current_provider,
        'model': ai_assistant.model,
        'test_response': test_response.get('response', 'No response'),
        'test_success': test_response.get('success', False)
    }
    return JsonResponse(status)