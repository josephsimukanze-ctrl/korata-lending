from django.contrib import admin
from django.utils.html import format_html
from .models import Auction, AuctionBid, DefaultNotice

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('auction_id', 'collateral', 'status_badge', 'starting_bid', 'current_bid', 'scheduled_date')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('auction_id', 'collateral__serial_number', 'client__first_name', 'client__last_name')
    readonly_fields = ('auction_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Auction Information', {
            'fields': ('auction_id', 'loan', 'collateral', 'client', 'title', 'description')
        }),
        ('Bidding Details', {
            'fields': ('starting_bid', 'reserve_price', 'current_bid', 'bid_increment')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'start_date', 'end_date', 'actual_end_date', 'status')
        }),
        ('Financial Results', {
            'fields': ('final_sale_price', 'loan_balance_at_auction', 'surplus_amount', 'deficit_amount')
        }),
        ('Fees', {
            'fields': ('auction_fee', 'storage_fee', 'legal_fee')
        }),
        ('Winner Information', {
            'fields': ('winner_name', 'winner_contact', 'winner_email')
        }),
        ('Documents', {
            'fields': ('legal_notice', 'auction_certificate')
        }),
        ('Tracking', {
            'fields': ('created_by', 'approved_by', 'notes')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'scheduled': 'blue',
            'active': 'green',
            'completed': 'purple',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_badge.short_description = 'Status'
    
    actions = ['approve_auction', 'start_auction']
    
    def approve_auction(self, request, queryset):
        queryset.update(status='scheduled')
        self.message_user(request, f'{queryset.count()} auction(s) approved.')
    approve_auction.short_description = "Approve selected auctions"
    
    def start_auction(self, request, queryset):
        for auction in queryset:
            if auction.status == 'scheduled':
                auction.start_auction()
        self.message_user(request, f'{queryset.count()} auction(s) started.')
    start_auction.short_description = "Start selected auctions"

@admin.register(AuctionBid)
class AuctionBidAdmin(admin.ModelAdmin):
    list_display = ('auction', 'bidder_name', 'amount', 'bid_time', 'is_winning_bid')
    list_filter = ('is_winning_bid', 'bid_time')
    search_fields = ('bidder_name', 'bidder_contact')

@admin.register(DefaultNotice)
class DefaultNoticeAdmin(admin.ModelAdmin):
    list_display = ('notice_number', 'loan', 'days_overdue', 'notice_date', 'response_deadline', 'is_responded')
    list_filter = ('is_responded', 'legal_action_taken')
    search_fields = ('notice_number', 'loan__loan_id')