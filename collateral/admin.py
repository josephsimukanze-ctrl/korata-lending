from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import AssetType, Collateral, CollateralInspection, CollateralMovement

@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = ('collateral_id', 'client', 'title', 'serial_number', 'estimated_value', 'condition_badge', 'status_badge', 'verification_badge')
    list_filter = ('condition', 'status', 'verification_status', 'asset_type')
    search_fields = ('collateral_id', 'serial_number', 'client__first_name', 'client__last_name', 'title')
    readonly_fields = ('collateral_id', 'created_at', 'updated_at', 'qr_code_preview')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('collateral_id', 'client', 'asset_type', 'title', 'description')
        }),
        ('Asset Details', {
            'fields': ('make', 'model', 'year', 'color', 'serial_number')
        }),
        ('Valuation', {
            'fields': ('condition', 'estimated_value', 'appraised_value', 'loan_to_value_ratio')
        }),
        ('Location', {
            'fields': ('storage_location', 'storage_section', 'storage_shelf')
        }),
        ('Documents', {
            'fields': ('primary_photo', 'additional_photos', 'certificate_of_ownership', 'valuation_certificate', 'insurance_certificate')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verified_by', 'verification_date', 'verification_notes')
        }),
        ('Insurance', {
            'fields': ('is_insured', 'insurance_provider', 'insurance_policy_number', 'insurance_expiry_date', 'insurance_value')
        }),
        ('Status', {
            'fields': ('status', 'is_seized', 'seized_date', 'seized_by', 'release_date')
        }),
        ('Additional', {
            'fields': ('notes', 'tags', 'qr_code_preview', 'last_physical_check', 'next_physical_check')
        }),
    )
    
    def condition_badge(self, obj):
        colors = {
            'new': 'green',
            'excellent': 'blue',
            'very_good': 'teal',
            'good': 'green',
            'fair': 'yellow',
            'poor': 'orange',
            'damaged': 'red',
        }
        color = colors.get(obj.condition, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.get_condition_display_name}</span>')
    condition_badge.short_description = 'Condition'
    
    def status_badge(self, obj):
        colors = {
            'available': 'green',
            'pledged': 'blue',
            'seized': 'red',
            'sold': 'purple',
            'released': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display_name}</span>')
    status_badge.short_description = 'Status'
    
    def verification_badge(self, obj):
        if obj.verification_status == 'verified':
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.verification_status == 'pending':
            return format_html('<span style="color: orange;">⏳ Pending</span>')
        elif obj.verification_status == 'rejected':
            return format_html('<span style="color: red;">✗ Rejected</span>')
        return format_html('<span style="color: purple;">⚠ Review</span>')
    verification_badge.short_description = 'Verification'
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="80" height="80" style="border-radius: 8px;" />', obj.qr_code.url)
        return 'No QR Code'
    qr_code_preview.short_description = 'QR Code'
    
    actions = ['verify_selected', 'seize_selected']
    
    def verify_selected(self, request, queryset):
        for collateral in queryset:
            collateral.verify(request.user)
        self.message_user(request, f'{queryset.count()} collateral item(s) verified.')
    verify_selected.short_description = "Verify selected collaterals"
    
    def seize_selected(self, request, queryset):
        for collateral in queryset:
            collateral.seize(request.user)
        self.message_user(request, f'{queryset.count()} collateral item(s) seized.')
    seize_selected.short_description = "Seize selected collaterals"

@admin.register(CollateralInspection)
class CollateralInspectionAdmin(admin.ModelAdmin):
    list_display = ('collateral', 'inspection_date', 'inspection_type', 'condition', 'inspected_by')
    list_filter = ('inspection_type', 'condition', 'inspection_date')
    search_fields = ('collateral__collateral_id', 'collateral__serial_number')
    
    fieldsets = (
        ('Inspection Information', {
            'fields': ('collateral', 'inspection_type', 'inspection_date', 'inspected_by')
        }),
        ('Findings', {
            'fields': ('condition', 'notes', 'photos')
        }),
        ('Recommendations', {
            'fields': ('recommendation', 'requires_action', 'action_taken', 'action_notes')
        }),
        ('Follow-up', {
            'fields': ('next_inspection_date',)
        }),
    )

@admin.register(CollateralMovement)
class CollateralMovementAdmin(admin.ModelAdmin):
    list_display = ('collateral', 'movement_type', 'to_location', 'movement_date', 'moved_by')
    list_filter = ('movement_type', 'movement_date')
    search_fields = ('collateral__collateral_id', 'collateral__serial_number')
    
    fieldsets = (
        ('Movement Information', {
            'fields': ('collateral', 'movement_type', 'from_location', 'to_location', 'reason')
        }),
        ('Authorization', {
            'fields': ('moved_by', 'authorized_by', 'authorization_date')
        }),
        ('Additional', {
            'fields': ('notes',)
        }),
    )