from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Auction, AuctionBid, DefaultNotice
from loans.models import Loan
from collateral.models import Collateral
from clients.models import Client
from users.models import CustomUser

def is_admin_or_ceo(user):
    return user.is_superuser or user.role in ['ceo', 'admin']

def is_officer_or_higher(user):
    return user.is_superuser or user.role in ['ceo', 'admin', 'collateral_officer']

@login_required
def auction_list(request):
    """List all auctions"""
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    auctions = Auction.objects.all().select_related('client', 'collateral')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        auctions = auctions.filter(
            Q(auction_id__icontains=search_query) |
            Q(client__first_name__icontains=search_query) |
            Q(client__last_name__icontains=search_query) |
            Q(collateral__serial_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        auctions = auctions.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(auctions, 20)
    page = request.GET.get('page', 1)
    auctions = paginator.get_page(page)
    
    # Statistics
    stats = {
        'total': Auction.objects.count(),
        'pending': Auction.objects.filter(status='pending').count(),
        'scheduled': Auction.objects.filter(status='scheduled').count(),
        'active': Auction.objects.filter(status='active').count(),
        'completed': Auction.objects.filter(status='completed').count(),
        'cancelled': Auction.objects.filter(status='cancelled').count(),
        'total_value': Auction.objects.filter(status='completed').aggregate(total=Sum('final_sale_price'))['total'] or 0,
    }
    
    context = {
        'auctions': auctions,
        'stats': stats,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'auction/auction_list.html', context)

@login_required
def auction_detail(request, auction_id):
    """View auction details"""
    auction = get_object_or_404(Auction, id=auction_id)
    
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    # Get bids
    bids = AuctionBid.objects.filter(auction=auction).order_by('-amount', '-bid_time')
    
    # Check if auction can be started
    can_start = auction.status == 'scheduled' and timezone.now() >= auction.scheduled_date
    
    # Check if auction can be ended
    can_end = auction.status == 'active'
    
    context = {
        'auction': auction,
        'bids': bids,
        'can_start': can_start,
        'can_end': can_end,
    }
    
    return render(request, 'auction/auction_detail.html', context)

@login_required
@user_passes_test(is_admin_or_ceo)
def create_auction(request, loan_id):
    """Create an auction for a defaulted loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if loan.status != 'defaulted':
        messages.error(request, 'Only defaulted loans can be auctioned.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    # Check if auction already exists
    if hasattr(loan, 'auction'):
        messages.warning(request, 'An auction already exists for this loan.')
        return redirect('auction:detail', auction_id=loan.auction.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        starting_bid = request.POST.get('starting_bid')
        reserve_price = request.POST.get('reserve_price')
        bid_increment = request.POST.get('bid_increment', 100)
        scheduled_date = request.POST.get('scheduled_date')
        
        # Calculate loan balance
        loan_balance = loan.remaining_balance or loan.total_payback
        
        auction = Auction.objects.create(
            loan=loan,
            collateral=loan.collateral,
            client=loan.client,
            title=title,
            description=description,
            starting_bid=starting_bid,
            reserve_price=reserve_price or None,
            bid_increment=bid_increment,
            scheduled_date=scheduled_date,
            loan_balance_at_auction=loan_balance,
            created_by=request.user,
            status='pending'
        )
        
        messages.success(request, f'Auction {auction.auction_id} created successfully!')
        return redirect('auction:detail', auction_id=auction.id)
    
    # Calculate suggested starting bid (70% of collateral value)
    collateral_value = loan.collateral.estimated_value if loan.collateral else 0
    suggested_bid = collateral_value * Decimal('0.7')
    
    context = {
        'loan': loan,
        'suggested_bid': suggested_bid,
    }
    
    return render(request, 'auction/auction_form.html', context)

@login_required
@user_passes_test(is_admin_or_ceo)
def start_auction(request, auction_id):
    """Start an auction"""
    auction = get_object_or_404(Auction, id=auction_id)
    
    if auction.status != 'scheduled':
        messages.error(request, 'Only scheduled auctions can be started.')
        return redirect('auction:detail', auction_id=auction.id)
    
    if request.method == 'POST':
        auction.start_auction()
        messages.success(request, f'Auction {auction.auction_id} has started!')
        return redirect('auction:detail', auction_id=auction.id)
    
    return render(request, 'auction/auction_start.html', {'auction': auction})

@login_required
@user_passes_test(is_admin_or_ceo)
def end_auction(request, auction_id):
    """End an auction"""
    auction = get_object_or_404(Auction, id=auction_id)
    
    if auction.status != 'active':
        messages.error(request, 'Only active auctions can be ended.')
        return redirect('auction:detail', auction_id=auction.id)
    
    if request.method == 'POST':
        final_price = request.POST.get('final_price')
        winner_name = request.POST.get('winner_name')
        winner_contact = request.POST.get('winner_contact')
        winner_email = request.POST.get('winner_email', '')
        
        auction.end_auction(final_price, winner_name, winner_contact)
        
        if winner_email:
            # Send email to winner (implement email sending)
            pass
        
        messages.success(request, f'Auction {auction.auction_id} completed!')
        return redirect('auction:detail', auction_id=auction.id)
    
    # Get highest bid
    highest_bid = auction.bids.order_by('-amount').first()
    
    context = {
        'auction': auction,
        'highest_bid': highest_bid,
    }
    
    return render(request, 'auction/auction_end.html', context)

@login_required
def place_bid(request, auction_id):
    """Place a bid on an auction"""
    auction = get_object_or_404(Auction, id=auction_id)
    
    if auction.status != 'active':
        return JsonResponse({'error': 'Auction is not active'}, status=400)
    
    if request.method == 'POST':
        bidder_name = request.POST.get('bidder_name')
        bidder_contact = request.POST.get('bidder_contact')
        bidder_email = request.POST.get('bidder_email', '')
        amount = Decimal(request.POST.get('amount', 0))
        
        # Validate bid amount
        min_bid = auction.current_bid + auction.bid_increment if auction.current_bid > 0 else auction.starting_bid
        
        if amount < min_bid:
            return JsonResponse({'error': f'Minimum bid is ZMW {min_bid:,.2f}'}, status=400)
        
        # Create bid
        bid = AuctionBid.objects.create(
            auction=auction,
            bidder_name=bidder_name,
            bidder_contact=bidder_contact,
            bidder_email=bidder_email,
            amount=amount
        )
        
        # Update auction current bid
        auction.current_bid = amount
        auction.save()
        
        return JsonResponse({
            'success': True,
            'bid': {
                'bidder_name': bid.bidder_name,
                'amount': float(bid.amount),
                'bid_time': bid.bid_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@user_passes_test(is_admin_or_ceo)
def cancel_auction(request, auction_id):
    """Cancel an auction"""
    auction = get_object_or_404(Auction, id=auction_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        auction.cancel_auction(reason)
        messages.success(request, f'Auction {auction.auction_id} has been cancelled.')
        return redirect('auction:list')
    
    return render(request, 'auction/auction_cancel.html', {'auction': auction})

@login_required
def default_notices(request):
    """View default notices"""
    if not is_officer_or_higher(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    notices = DefaultNotice.objects.all().select_related('loan__client')
    
    context = {
        'notices': notices,
    }
    
    return render(request, 'auction/default_notices.html', context)

@login_required
@user_passes_test(is_admin_or_ceo)
def create_default_notice(request, loan_id):
    """Create a default notice for a loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    if request.method == 'POST':
        days_overdue = request.POST.get('days_overdue')
        response_deadline = request.POST.get('response_deadline')
        
        notice = DefaultNotice.objects.create(
            loan=loan,
            days_overdue=days_overdue,
            response_deadline=response_deadline
        )
        
        messages.success(request, f'Default notice {notice.notice_number} created!')
        return redirect('auction:notices')
    
    # Calculate days overdue
    if loan.start_date:
        days_overdue = (timezone.now().date() - loan.start_date).days - (loan.duration_weeks * 7)
    else:
        days_overdue = 0
    
    context = {
        'loan': loan,
        'days_overdue': max(days_overdue, 0),
    }
    
    return render(request, 'auction/default_notice_form.html', context)

@login_required
def api_auction_list(request):
    """API endpoint for auction list"""
    auctions = Auction.objects.all().values(
        'id', 'auction_id', 'title', 'status', 'starting_bid', 'current_bid',
        'scheduled_date', 'client__first_name', 'client__last_name'
    )
    
    auction_list = []
    for auction in auctions:
        auction_list.append({
            'id': auction['id'],
            'auction_id': auction['auction_id'],
            'title': auction['title'],
            'client_name': f"{auction['client__first_name']} {auction['client__last_name']}",
            'status': auction['status'],
            'starting_bid': float(auction['starting_bid']),
            'current_bid': float(auction['current_bid']),
            'scheduled_date': auction['scheduled_date'],
        })
    
    return JsonResponse({'auctions': auction_list})

@login_required
def api_auction_stats(request):
    """API endpoint for auction statistics"""
    stats = {
        'total': Auction.objects.count(),
        'pending': Auction.objects.filter(status='pending').count(),
        'scheduled': Auction.objects.filter(status='scheduled').count(),
        'active': Auction.objects.filter(status='active').count(),
        'completed': Auction.objects.filter(status='completed').count(),
        'cancelled': Auction.objects.filter(status='cancelled').count(),
        'total_recovered': float(Auction.objects.filter(status='completed').aggregate(total=Sum('final_sale_price'))['total'] or 0),
    }
    
    return JsonResponse(stats)


@login_required
@user_passes_test(is_admin_or_ceo)
def create_auction(request, loan_id=None):
    """Create an auction for a defaulted loan"""
    
    # If no loan_id provided, show loan selection page
    if not loan_id:
        defaulted_loans = Loan.objects.filter(
            status='defaulted'
        ).exclude(
            id__in=Auction.objects.values_list('loan_id', flat=True)
        ).select_related('client', 'collateral')
        
        context = {'loans': defaulted_loans}
        return render(request, 'auction/select_loan.html', context)
    
    loan = get_object_or_404(Loan, id=loan_id)
    
    if loan.status != 'defaulted':
        messages.error(request, 'Only defaulted loans can be auctioned.')
        return redirect('loans:loan_detail', loan_id=loan.id)
    
    # Check if auction already exists
    if hasattr(loan, 'auction'):
        messages.warning(request, 'An auction already exists for this loan.')
        return redirect('auction:detail', auction_id=loan.auction.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        starting_bid = request.POST.get('starting_bid')
        reserve_price = request.POST.get('reserve_price')
        bid_increment = request.POST.get('bid_increment', 100)
        scheduled_date = request.POST.get('scheduled_date')
        
        # Calculate loan balance
        loan_balance = loan.remaining_balance or loan.total_payback
        
        auction = Auction.objects.create(
            loan=loan,
            collateral=loan.collateral,
            client=loan.client,
            title=title,
            description=description,
            starting_bid=starting_bid,
            reserve_price=reserve_price or None,
            bid_increment=bid_increment,
            scheduled_date=scheduled_date,
            loan_balance_at_auction=loan_balance,
            created_by=request.user,
            status='pending'
        )
        
        messages.success(request, f'Auction {auction.auction_id} created successfully!')
        return redirect('auction:detail', auction_id=auction.id)
    
    # Calculate suggested starting bid (70% of collateral value)
    collateral_value = loan.collateral.estimated_value if loan.collateral else 0
    suggested_bid = float(collateral_value) * 0.7 if collateral_value else 5000
    
    context = {
        'loan': loan,
        'suggested_bid': suggested_bid,
    }
    
    return render(request, 'auction/auction_form.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def select_loan_for_auction(request):
    """Select a defaulted loan to create an auction"""
    # Get all defaulted loans that don't have an auction yet
    defaulted_loans = Loan.objects.filter(
        status='defaulted'
    ).exclude(
        id__in=Auction.objects.values_list('loan_id', flat=True)
    ).select_related('client', 'collateral')
    
    # Calculate additional stats
    total_balance = sum(loan.remaining_balance or 0 for loan in defaulted_loans)
    total_collateral = sum(loan.collateral.estimated_value or 0 for loan in defaulted_loans if loan.collateral)
    loans_with_collateral = sum(1 for loan in defaulted_loans if loan.collateral)
    
    context = {
        'loans': defaulted_loans,
        'total_balance': total_balance,
        'total_collateral': total_collateral,
        'loans_with_collateral': loans_with_collateral,
    }
    return render(request, 'auction/select_loan.html', context)