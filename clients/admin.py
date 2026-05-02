from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Client, Guarantor, ClientAsset, ClientNote

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'full_name_display', 'phone_number', 'status_badge', 'risk_badge', 'kyc_badge', 'registration_date')
    list_filter = ('status', 'risk_rating', 'kyc_verified', 'employment_status', 'city')
    search_fields = ('client_id', 'first_name', 'last_name', 'nrc', 'phone_number', 'email')
    readonly_fields = ('client_id', 'registration_date', 'last_updated', 'kyc_verified_date')
    
    fieldsets = (
        ('Client Information', {
            'fields': ('client_id', 'first_name', 'middle_name', 'last_name', 'nrc')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'alternate_phone', 'email')
        }),
        ('Address', {
            'fields': ('physical_address', 'postal_address', 'city', 'district', 'province', 'country')
        }),
        ('Employment', {
            'fields': ('employment_status', 'employer', 'job_title', 'monthly_income', 'employment_start_date')
        }),
        ('Business (if applicable)', {
            'fields': ('business_name', 'business_type', 'business_registration_number'),
            'classes': ('collapse',)
        }),
        ('KYC Documents', {
            'fields': ('nrc_photo', 'client_photo', 'proof_of_residence', 'proof_of_income')
        }),
        ('KYC Status', {
            'fields': ('kyc_verified', 'kyc_verified_date', 'kyc_verified_by')
        }),
        ('Risk Assessment', {
            'fields': ('risk_rating', 'credit_score', 'risk_notes')
        }),
        ('Status', {
            'fields': ('status', 'blacklist_reason', 'blacklisted_date')
        }),
        ('Additional Info', {
            'fields': ('general_notes', 'tags', 'last_contact_date')  # Changed from 'notes' to 'general_notes'
        }),
    )
    
    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Full Name'
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'gray',
            'blacklisted': 'red',
            'pending': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.status.title()}</span>')
    status_badge.short_description = 'Status'
    
    def risk_badge(self, obj):
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
        }
        color = colors.get(obj.risk_rating, 'gray')
        return format_html(f'<span style="color: {color};">{obj.risk_rating.title()}</span>')
    risk_badge.short_description = 'Risk'
    
    def kyc_badge(self, obj):
        if obj.kyc_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    kyc_badge.short_description = 'KYC'
    
    actions = ['verify_kyc_selected', 'blacklist_selected']
    
    def verify_kyc_selected(self, request, queryset):
        updated = queryset.update(kyc_verified=True, status='active')
        self.message_user(request, f'{updated} client(s) verified successfully.')
    verify_kyc_selected.short_description = "Verify KYC for selected clients"
    
    def blacklist_selected(self, request, queryset):
        updated = queryset.update(status='blacklisted')
        self.message_user(request, f'{updated} client(s) blacklisted.')
    blacklist_selected.short_description = "Blacklist selected clients"


@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'client_link', 'phone_number', 'relationship', 'is_active')
    list_filter = ('relationship', 'is_active')
    search_fields = ('first_name', 'last_name', 'nrc', 'phone_number', 'client__first_name', 'client__last_name')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'nrc')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'alternate_phone', 'email')
        }),
        ('Address', {
            'fields': ('physical_address', 'city')
        }),
        ('Employment', {
            'fields': ('employer', 'job_title', 'monthly_income')
        }),
        ('Relationship', {
            'fields': ('relationship', 'relationship_years')
        }),
        ('Documents', {
            'fields': ('nrc_photo', 'photo', 'proof_of_residence')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'
    
    def client_link(self, obj):
        url = reverse('admin:clients_client_change', args=[obj.client.id])
        return format_html('<a href="{}">{}</a>', url, obj.client.full_name)
    client_link.short_description = 'Client'


@admin.register(ClientAsset)
class ClientAssetAdmin(admin.ModelAdmin):
    list_display = ('client', 'asset_type', 'description', 'estimated_value', 'is_verified')
    list_filter = ('asset_type', 'is_verified')
    search_fields = ('client__first_name', 'client__last_name', 'description', 'serial_number')
    
    fieldsets = (
        ('Asset Information', {
            'fields': ('client', 'asset_type', 'description', 'estimated_value')
        }),
        ('Asset Details', {
            'fields': ('make', 'model', 'year', 'serial_number', 'location')
        }),
        ('Verification', {
            'fields': ('proof_of_ownership', 'photos', 'is_verified', 'verified_by', 'verification_notes')
        }),
    )


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ('client', 'note_type', 'created_by', 'created_at')
    list_filter = ('note_type', 'created_at')
    search_fields = ('client__first_name', 'client__last_name', 'note')
    
    fieldsets = (
        ('Note Information', {
            'fields': ('client', 'note_type', 'note', 'created_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)