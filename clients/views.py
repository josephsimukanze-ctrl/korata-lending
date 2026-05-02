from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Client, Guarantor, ClientAsset, ClientNote
import csv
import json
from datetime import datetime, timedelta


# ==================== PERMISSION FUNCTIONS ====================
# clients/views.py - Update these permission functions

def is_admin_or_ceo(user):
    """Check if user is superuser, CEO, or Admin"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin'])

def can_view_clients(user):
    """Check if user can view clients - CEO, Admin, Loan Officer, Collateral Officer"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer', 'collateral_officer'])

def can_manage_clients(user):
    """Check if user can manage clients - CEO, Admin, Loan Officer, Collateral Officer"""
    # ADD 'collateral_officer' to this list
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer', 'collateral_officer'])

def can_create_clients(user):
    """Check if user can create clients - CEO, Admin, Loan Officer, Collateral Officer"""
    # Add this new function
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer', 'collateral_officer'])

def can_edit_clients(user):
    """Check if user can edit clients - CEO, Admin, Loan Officer only (Collateral Officers cannot edit)"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer'])

def is_loan_officer(user):
    """Check if user is loan officer or higher"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer'])

# ==================== MAIN VIEWS ====================

@login_required
def client_list(request):
    """List all clients with improved filtering and pagination"""
    if not can_view_clients(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    clients_list = Client.objects.all().order_by('-registration_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        clients_list = clients_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(client_id__icontains=search_query) |
            Q(nrc__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        clients_list = clients_list.filter(status=status_filter)
    
    # Filter by risk rating
    risk_filter = request.GET.get('risk', '')
    if risk_filter:
        clients_list = clients_list.filter(risk_rating=risk_filter)
    
    # Filter by city
    city_filter = request.GET.get('city', '')
    if city_filter:
        clients_list = clients_list.filter(city=city_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    if date_from:
        clients_list = clients_list.filter(registration_date__gte=date_from)
    date_to = request.GET.get('date_to', '')
    if date_to:
        clients_list = clients_list.filter(registration_date__lte=date_to)
    
    # Pagination
    items_per_page = int(request.GET.get('per_page', 20))
    paginator = Paginator(clients_list, items_per_page)
    page = request.GET.get('page', 1)
    clients = paginator.get_page(page)
    
    # Prepare client data for JSON (for the frontend)
    client_data = []
    for client in Client.objects.all():
        client_data.append({
            'id': client.id,
            'client_id': client.client_id,
            'full_name': client.full_name,
            'first_name': client.first_name,
            'last_name': client.last_name,
            'nrc': client.nrc,
            'phone_number': client.phone_number,
            'email': client.email,
            'city': client.city,
            'status': client.status,
            'risk_rating': client.risk_rating,
            'kyc_verified': client.kyc_verified,
            'monthly_income': float(client.monthly_income) if client.monthly_income else 0,
            'created_at': client.registration_date.isoformat() if client.registration_date else None,
        })
    
    # Get unique cities for filter dropdown
    cities_list = Client.objects.exclude(city__isnull=True).exclude(city='').values_list('city', flat=True).distinct()
    
    # Get total loans count
    total_loans = 0
    try:
        from loans.models import Loan
        total_loans = Loan.objects.count()
    except ImportError:
        pass
    
    # Calculate growth percentage
    now = timezone.now()
    last_month = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)
    
    this_month_count = Client.objects.filter(registration_date__gte=last_month).count()
    last_month_count = Client.objects.filter(registration_date__range=[two_months_ago, last_month]).count()
    
    growth_percentage = 0
    if last_month_count > 0:
        growth_percentage = round(((this_month_count - last_month_count) / last_month_count) * 100, 1)
    
    context = {
        'clients': clients,
        'clients_json': json.dumps(client_data),
        'cities_list': cities_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'risk_filter': risk_filter,
        'city_filter': city_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_clients': Client.objects.count(),
        'active_clients': Client.objects.filter(status='active').count(),
        'pending_clients': Client.objects.filter(status='pending').count(),
        'pending_kyc': Client.objects.filter(kyc_verified=False).count(),
        'blacklisted_clients': Client.objects.filter(status='blacklisted').count(),
        'total_loans': total_loans,
        'growth_percentage': growth_percentage,
    }
    
    return render(request, 'clients/client_list.html', context)


@login_required
def client_detail(request, client_id):
    """View client details"""
    client = get_object_or_404(Client, id=client_id)
    
    if not can_view_clients(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('clients:client_list')
    
    # Get guarantor
    try:
        guarantor = client.guarantor
    except Guarantor.DoesNotExist:
        guarantor = None
    
    # Get assets
    assets = ClientAsset.objects.filter(client=client)
    
    # Get notes
    notes = ClientNote.objects.filter(client=client).order_by('-created_at')
    
    # Get loans
    try:
        from loans.models import Loan
        loans = Loan.objects.filter(client=client).order_by('-start_date')
        total_loans = loans.count()
        total_borrowed = loans.filter(status='active').aggregate(Sum('principal'))['principal__sum'] or 0
    except ImportError:
        loans = []
        total_loans = 0
        total_borrowed = 0
    
    context = {
        'client': client,
        'guarantor': guarantor,
        'assets': assets,
        'notes': notes,
        'loans': loans,
        'total_loans': total_loans,
        'total_borrowed': total_borrowed,
    }
    
    return render(request, 'clients/client_detail.html', context)


@login_required
@user_passes_test(can_manage_clients)
def client_create(request):
    """Create new client with auto-generated client ID - Only Admin, CEO, Loan Officer"""
    if request.method == 'POST':
        try:
            # Generate client ID if not provided
            client_id = request.POST.get('client_id', '')
            if not client_id:
                from django.utils.crypto import get_random_string
                date_str = timezone.now().strftime('%Y%m%d')
                random_suffix = get_random_string(4, allowed_chars='0123456789')
                client_id = f"CUS-{date_str}-{random_suffix}"
            
            # Handle date_of_birth - convert empty string to None
            date_of_birth = request.POST.get('date_of_birth')
            if date_of_birth == '':
                date_of_birth = None
            
            # Handle gender - default to empty string if not provided
            gender = request.POST.get('gender', '')
            
            # Create client
            client = Client.objects.create(
                client_id=client_id,
                nrc=request.POST.get('nrc'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                middle_name=request.POST.get('middle_name', ''),
                phone_number=request.POST.get('phone_number'),
                alternate_phone=request.POST.get('alternate_phone', ''),
                email=request.POST.get('email', ''),
                physical_address=request.POST.get('physical_address'),
                city=request.POST.get('city'),
                district=request.POST.get('district', ''),
                province=request.POST.get('province', 'Lusaka'),
                postal_code=request.POST.get('postal_code', ''),
                employment_status=request.POST.get('employment_status', 'employed'),
                employer=request.POST.get('employer', ''),
                job_title=request.POST.get('job_title', ''),
                monthly_income=request.POST.get('monthly_income', 0),
                registered_by=request.user,
                status='pending',
                risk_rating='medium'
            )
            
            # Handle file uploads
            if request.FILES.get('client_photo'):
                client.client_photo = request.FILES['client_photo']
            if request.FILES.get('nrc_document'):
                client.nrc_document = request.FILES['nrc_document']
            if request.FILES.get('proof_of_residence'):
                client.proof_of_residence = request.FILES['proof_of_residence']
            if request.FILES.get('proof_of_income'):
                client.proof_of_income = request.FILES['proof_of_income']
            client.save()
            
            # Create guarantor if information provided
            guarantor_first_name = request.POST.get('guarantor_first_name')
            guarantor_last_name = request.POST.get('guarantor_last_name')
            if guarantor_first_name and guarantor_last_name:
                Guarantor.objects.create(
                    client=client,
                    first_name=guarantor_first_name,
                    last_name=guarantor_last_name,
                    nrc=request.POST.get('guarantor_nrc', ''),
                    phone_number=request.POST.get('guarantor_phone', ''),
                    employer=request.POST.get('guarantor_employer', ''),
                    relationship=request.POST.get('relationship', 'other'),
                    physical_address=client.physical_address,
                    city=client.city,
                    monthly_income=0,
                    relationship_years=0
                )
            
            # Add initial note if provided
            notes = request.POST.get('notes')
            if notes:
                ClientNote.objects.create(
                    client=client,
                    note=notes,
                    created_by=request.user,
                    note_type='general'
                )
            
            messages.success(request, f'Client {client.full_name} registered successfully! Client ID: {client.client_id}')
            return redirect('clients:client_detail', client_id=client.id)
            
        except Exception as e:
            messages.error(request, f'Error creating client: {str(e)}')
            return redirect('clients:client_create')
    
    # Generate a preview client ID for display
    from django.utils.crypto import get_random_string
    date_str = timezone.now().strftime('%Y%m%d')
    random_suffix = get_random_string(4, allowed_chars='0123456789')
    generated_client_id = f"CUS-{date_str}-{random_suffix}"
    
    return render(request, 'clients/client_form.html', {
        'title': 'Register New Client',
        'generated_client_id': generated_client_id
    })


@login_required
def client_edit(request, client_id):
    """Edit client - Only Admin, CEO, Loan Officer can edit"""
    client = get_object_or_404(Client, id=client_id)
    
    if not can_manage_clients(request.user):
        messages.error(request, 'You do not have permission to edit this client.')
        return redirect('clients:client_list')
    
    if request.method == 'POST':
        try:
            # Update client fields
            client.first_name = request.POST.get('first_name', client.first_name)
            client.last_name = request.POST.get('last_name', client.last_name)
            client.middle_name = request.POST.get('middle_name', client.middle_name)
            client.phone_number = request.POST.get('phone_number', client.phone_number)
            client.alternate_phone = request.POST.get('alternate_phone', client.alternate_phone)
            client.email = request.POST.get('email', client.email)
            client.physical_address = request.POST.get('physical_address', client.physical_address)
            client.city = request.POST.get('city', client.city)
            client.district = request.POST.get('district', client.district)
            client.province = request.POST.get('province', client.province)
            client.postal_code = request.POST.get('postal_code', client.postal_code)
            client.employment_status = request.POST.get('employment_status', client.employment_status)
            client.employer = request.POST.get('employer', client.employer)
            client.job_title = request.POST.get('job_title', client.job_title)
            client.monthly_income = request.POST.get('monthly_income', client.monthly_income)
            client.date_of_birth = request.POST.get('date_of_birth') or client.date_of_birth
            client.gender = request.POST.get('gender', client.gender)
            
            # Handle file uploads
            if request.FILES.get('client_photo'):
                client.client_photo = request.FILES['client_photo']
            if request.FILES.get('nrc_document'):
                client.nrc_document = request.FILES['nrc_document']
            if request.FILES.get('proof_of_residence'):
                client.proof_of_residence = request.FILES['proof_of_residence']
            if request.FILES.get('proof_of_income'):
                client.proof_of_income = request.FILES['proof_of_income']
            
            client.save()
            
            # Update or create guarantor
            guarantor_first_name = request.POST.get('guarantor_first_name')
            guarantor_last_name = request.POST.get('guarantor_last_name')
            if guarantor_first_name and guarantor_last_name:
                guarantor, created = Guarantor.objects.get_or_create(client=client)
                guarantor.first_name = guarantor_first_name
                guarantor.last_name = guarantor_last_name
                guarantor.nrc = request.POST.get('guarantor_nrc', '')
                guarantor.phone_number = request.POST.get('guarantor_phone', '')
                guarantor.employer = request.POST.get('guarantor_employer', '')
                guarantor.relationship = request.POST.get('relationship', 'other')
                guarantor.save()
            elif guarantor_first_name is None and guarantor_last_name is None:
                # If guarantor fields are empty, delete existing guarantor
                Guarantor.objects.filter(client=client).delete()
            
            messages.success(request, 'Client updated successfully!')
            return redirect('clients:client_detail', client_id=client.id)
            
        except Exception as e:
            messages.error(request, f'Error updating client: {str(e)}')
    
    # Get guarantor for the form
    try:
        guarantor = client.guarantor
    except Guarantor.DoesNotExist:
        guarantor = None
    
    return render(request, 'clients/client_form.html', {
        'client': client,
        'guarantor': guarantor,
        'title': 'Edit Client'
    })


@login_required
@user_passes_test(is_admin_or_ceo)
def client_delete(request, client_id):
    """Delete client - Admin/CEO only"""
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        client_name = client.full_name
        client.delete()
        messages.success(request, f'Client {client_name} deleted successfully!')
        return redirect('clients:client_list')
    
    return render(request, 'clients/client_confirm_delete.html', {'client': client})


# ==================== KYC AND NOTES ====================

@login_required
@user_passes_test(is_admin_or_ceo)
def verify_kyc(request, client_id):
    """Verify client KYC - Admin/CEO only"""
    client = get_object_or_404(Client, id=client_id)
    client.kyc_verified = True
    client.kyc_verified_by = request.user
    client.kyc_verified_date = timezone.now()
    if client.status == 'pending':
        client.status = 'active'
    client.save()
    
    messages.success(request, f'KYC verified for {client.full_name}')
    return redirect('clients:client_detail', client_id=client.id)


@login_required
def add_note(request, client_id):
    """Add note to client - Anyone who can view clients"""
    client = get_object_or_404(Client, id=client_id)
    
    if not can_view_clients(request.user):
        messages.error(request, 'You do not have permission to add notes.')
        return redirect('clients:client_list')
    
    if request.method == 'POST':
        note = request.POST.get('note')
        note_type = request.POST.get('note_type', 'general')
        if note:
            ClientNote.objects.create(
                client=client,
                note=note,
                created_by=request.user,
                note_type=note_type
            )
            messages.success(request, 'Note added successfully!')
    
    return redirect('clients:client_detail', client_id=client.id)


@login_required
@require_http_methods(["POST"])
def delete_note(request, note_id):
    """Delete a note (AJAX)"""
    note = get_object_or_404(ClientNote, id=note_id)
    
    # Check permission: only the note creator or admin/CEO can delete
    if request.user == note.created_by or is_admin_or_ceo(request.user):
        note.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Note deleted successfully'})
        messages.success(request, 'Note deleted successfully!')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, 'You do not have permission to delete this note.')
    
    # Redirect back to the client detail page
    return redirect('clients:client_detail', client_id=note.client.id)


# ==================== EXPORT ====================

@login_required
@user_passes_test(can_manage_clients)
def export_clients(request):
    """Export clients to CSV with filters"""
    format_type = request.GET.get('format', 'csv')
    
    # Apply filters to export
    clients = Client.objects.all().order_by('-registration_date')
    
    search = request.GET.get('search', '')
    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(client_id__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        clients = clients.filter(status=status)
    
    risk = request.GET.get('risk', '')
    if risk:
        clients = clients.filter(risk_rating=risk)
    
    city = request.GET.get('city', '')
    if city:
        clients = clients.filter(city=city)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        clients = clients.filter(registration_date__gte=date_from)
    date_to = request.GET.get('date_to', '')
    if date_to:
        clients = clients.filter(registration_date__lte=date_to)
    
    # Create CSV response
    filename = f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Client ID', 'Full Name', 'First Name', 'Last Name', 'NRC', 'Phone', 'Alternate Phone',
        'Email', 'Physical Address', 'City', 'District', 'Province', 'Postal Code',
        'Employment Status', 'Employer', 'Job Title', 'Monthly Income', 'Status',
        'Risk Rating', 'KYC Verified', 'Registration Date'
    ])
    
    for client in clients:
        writer.writerow([
            client.client_id,
            client.full_name,
            client.first_name,
            client.last_name,
            client.nrc,
            client.phone_number,
            client.alternate_phone or '',
            client.email or '',
            client.physical_address,
            client.city,
            client.district or '',
            client.province or '',
            client.postal_code or '',
            client.get_employment_status_display(),
            client.employer or '',
            client.job_title or '',
            client.monthly_income or 0,
            client.get_status_display(),
            client.get_risk_rating_display(),
            'Yes' if client.kyc_verified else 'No',
            client.registration_date.strftime('%Y-%m-%d %H:%M') if client.registration_date else ''
        ])
    
    return response


# ==================== API ENDPOINTS ====================

@login_required
def api_client_list(request):
    """API endpoint for client list with filtering"""
    if not can_view_clients(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    clients = Client.objects.all().order_by('-registration_date')
    
    # Apply filters from request GET parameters
    search = request.GET.get('search', '')
    if search:
        clients = clients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(client_id__icontains=search) |
            Q(nrc__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(email__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        clients = clients.filter(status=status)
    
    risk = request.GET.get('risk', '')
    if risk:
        clients = clients.filter(risk_rating=risk)
    
    city = request.GET.get('city', '')
    if city:
        clients = clients.filter(city=city)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        clients = clients.filter(registration_date__gte=date_from)
    date_to = request.GET.get('date_to', '')
    if date_to:
        clients = clients.filter(registration_date__lte=date_to)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    paginator = Paginator(clients, per_page)
    page_obj = paginator.get_page(page)
    
    client_list = []
    for client in page_obj:
        client_list.append({
            'id': client.id,
            'client_id': client.client_id,
            'full_name': client.full_name,
            'first_name': client.first_name,
            'last_name': client.last_name,
            'nrc': client.nrc,
            'phone_number': client.phone_number,
            'email': client.email,
            'city': client.city,
            'status': client.status,
            'risk_rating': client.risk_rating,
            'kyc_verified': client.kyc_verified,
            'monthly_income': float(client.monthly_income) if client.monthly_income else 0,
            'registration_date': client.registration_date.isoformat() if client.registration_date else None,
            'created_at': client.registration_date.isoformat() if client.registration_date else None,
            'initials': f"{client.first_name[0] if client.first_name else ''}{client.last_name[0] if client.last_name else ''}".upper()
        })
    
    return JsonResponse({
        'clients': client_list,
        'total': paginator.count,
        'page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@login_required
def api_client_stats(request):
    """API endpoint for client statistics"""
    if not can_view_clients(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Calculate growth percentage
    now = timezone.now()
    last_month = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)
    
    this_month_count = Client.objects.filter(registration_date__gte=last_month).count()
    last_month_count = Client.objects.filter(registration_date__range=[two_months_ago, last_month]).count()
    
    growth = 0
    if last_month_count > 0:
        growth = round(((this_month_count - last_month_count) / last_month_count) * 100, 1)
    
    stats = {
        'total': Client.objects.count(),
        'active': Client.objects.filter(status='active').count(),
        'pending': Client.objects.filter(status='pending').count(),
        'inactive': Client.objects.filter(status='inactive').count(),
        'blacklisted': Client.objects.filter(status='blacklisted').count(),
        'kyc_verified': Client.objects.filter(kyc_verified=True).count(),
        'kyc_pending': Client.objects.filter(kyc_verified=False).count(),
        'growth': growth,
        'low_risk': Client.objects.filter(risk_rating='low').count(),
        'medium_risk': Client.objects.filter(risk_rating='medium').count(),
        'high_risk': Client.objects.filter(risk_rating='high').count(),
    }
    
    return JsonResponse(stats)