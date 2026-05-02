from django.contrib import admin
from django.utils.html import format_html
from .models import Loan, RepaymentSchedule, Payment

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_id', 'client', 'principal', 'status_badge', 'total_payback', 'remaining_balance', 'created_at')
    list_filter = ('status', 'interest_period', 'created_at')
    search_fields = ('loan_id', 'client__first_name', 'client__last_name', 'client__nrc')
    readonly_fields = ('loan_id', 'total_interest', 'total_payback', 'weekly_payment', 'remaining_balance', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Loan Information', {
            'fields': ('loan_id', 'client', 'collateral', 'principal', 'interest_rate', 'interest_period', 'duration_weeks')
        }),
        ('Financial Calculations', {
            'fields': ('total_interest', 'total_payback', 'weekly_payment', 'remaining_balance')
        }),
        ('Status', {
            'fields': ('status', 'purpose', 'notes')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approval_date', 'approval_notes', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('application_date', 'start_date', 'expected_end_date', 'actual_end_date'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'active': 'green',
            'completed': 'purple',
            'defaulted': 'red',
            'rejected': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_badge.short_description = 'Status'
    
    actions = ['approve_loans', 'activate_loans', 'reject_loans']
    
    def approve_loans(self, request, queryset):
        for loan in queryset:
            if loan.status == 'pending':
                loan.approve(request.user)
        self.message_user(request, f'{queryset.count()} loan(s) approved.')
    approve_loans.short_description = "Approve selected loans"
    
    def activate_loans(self, request, queryset):
        for loan in queryset:
            if loan.status == 'approved':
                loan.activate()
        self.message_user(request, f'{queryset.count()} loan(s) activated.')
    activate_loans.short_description = "Activate selected loans"
    
    def reject_loans(self, request, queryset):
        for loan in queryset:
            if loan.status == 'pending':
                loan.reject('Rejected by admin')
        self.message_user(request, f'{queryset.count()} loan(s) rejected.')
    reject_loans.short_description = "Reject selected loans"

@admin.register(RepaymentSchedule)
class RepaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ('loan', 'week_number', 'due_date', 'expected_amount', 'paid_amount', 'status', 'penalty_amount')
    list_filter = ('status', 'due_date')
    search_fields = ('loan__loan_id', 'loan__client__first_name', 'loan__client__last_name')
    readonly_fields = ('week_number', 'due_date', 'expected_amount')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'loan', 'amount', 'payment_method', 'payment_date', 'collected_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('receipt_number', 'loan__loan_id', 'loan__client__first_name', 'loan__client__last_name')
    readonly_fields = ('receipt_number', 'payment_date')