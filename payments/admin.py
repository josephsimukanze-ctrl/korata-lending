from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PaymentMethod, PaymentCategory, Payment, 
    PaymentRefund, ScheduledPayment, PaymentNotification
)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'method_type', 'is_active', 'is_default']
    list_filter = ['method_type', 'is_active', 'is_default']
    search_fields = ['name', 'account_name', 'account_number']
    list_editable = ['is_active', 'is_default']


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'requires_approval']
    list_filter = ['is_active', 'requires_approval']
    search_fields = ['name', 'code']


class PaymentRefundInline(admin.TabularInline):
    model = PaymentRefund
    extra = 0
    fields = ['amount', 'status', 'reason', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'client', 'amount', 'status', 'payment_date', 'payment_method_display']
    list_filter = ['status', 'payment_date', 'payment_method']
    search_fields = ['payment_id', 'client__first_name', 'client__last_name', 'transaction_reference']
    readonly_fields = ['payment_id', 'total_amount', 'created_at', 'updated_at']
    inlines = [PaymentRefundInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_id', 'client', 'loan', 'category', 'payment_method')
        }),
        ('Payment Details', {
            'fields': ('amount', 'processing_fee', 'total_amount', 'status')
        }),
        ('Reference Information', {
            'fields': ('transaction_reference', 'cheque_number', 'mobile_transaction_id', 'receipt_number')
        }),
        ('Dates', {
            'fields': ('payment_date', 'approved_date')
        }),
        ('Additional Info', {
            'fields': ('notes', 'receipt_upload', 'created_by', 'approved_by')
        }),
    )
    
    def payment_method_display(self, obj):
        if obj.payment_method:
            return obj.payment_method.name
        return '-'
    payment_method_display.short_description = 'Payment Method'
    
    actions = ['approve_payments']
    
    def approve_payments(self, request, queryset):
        for payment in queryset:
            if payment.status == 'pending':
                payment.approve(request.user)
        self.message_user(request, f"{queryset.count()} payments approved successfully.")
    approve_payments.short_description = "Approve selected payments"


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ['original_payment', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['original_payment__payment_id', 'reason']
    readonly_fields = ['created_at']


@admin.register(ScheduledPayment)
class ScheduledPaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'amount', 'frequency', 'next_payment_date', 'is_active']
    list_filter = ['frequency', 'is_active']
    search_fields = ['client__first_name', 'client__last_name']


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ['client', 'notification_type', 'sent_via', 'sent_at', 'is_read']
    list_filter = ['notification_type', 'sent_via', 'is_read']
    search_fields = ['client__first_name', 'client__last_name', 'subject']
    readonly_fields = ['sent_at']