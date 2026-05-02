from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser, UserProfile, UserSession, UserActivityLog

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('employee_number', 'hire_date', 'email_notifications', 'sms_notifications', 
              'whatsapp_notifications', 'push_notifications', 'language', 'timezone', 'theme')
    readonly_fields = ('employee_number',)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'get_role', 'phone_number', 'get_status', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active', 'department')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'employee_id')
    readonly_fields = ('last_login', 'date_joined', 'last_activity', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture', 'bio')}),
        ('Employment Details', {'fields': ('role', 'employee_id', 'department', 'position')}),
        ('Address', {'fields': ('address', 'city', 'postal_code', 'country')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Tracking', {'fields': ('last_login_ip', 'is_online', 'last_activity', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'first_name', 'last_name', 'phone_number'),
        }),
    )
    
    inlines = [UserProfileInline]
    actions = ['activate_users', 'deactivate_users', 'set_as_ceo', 'set_as_admin']
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return obj.full_name
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'first_name'
    
    def get_role(self, obj):
        """Return role display name"""
        return obj.get_role_display()
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'role'
    
    def get_status(self, obj):
        """Return status with HTML"""
        if obj.is_active:
            return mark_safe('<span style="color: #10b981;">● Active</span>')
        return mark_safe('<span style="color: #ef4444;">● Inactive</span>')
    get_status.short_description = 'Status'
    get_status.admin_order_field = 'is_active'
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) were successfully activated.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) were successfully deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def set_as_ceo(self, request, queryset):
        """Set selected users as CEO"""
        updated = queryset.update(role='ceo')
        self.message_user(request, f'{updated} user(s) were set as CEO.')
    set_as_ceo.short_description = "Set as CEO"
    
    def set_as_admin(self, request, queryset):
        """Set selected users as System Admin"""
        updated = queryset.update(role='admin')
        self.message_user(request, f'{updated} user(s) were set as System Admin.')
    set_as_admin.short_description = "Set as System Admin"
    
    def save_model(self, request, obj, form, change):
        """Save model"""
        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'employee_number', 'hire_date', 'email_notifications', 'two_factor_enabled')
    list_filter = ('email_notifications', 'sms_notifications', 'two_factor_enabled', 'language', 'theme')
    search_fields = ('user__username', 'employee_number')
    readonly_fields = ('api_key', 'api_key_created', 'api_key_last_used')
    
    fieldsets = (
        ('Professional Info', {'fields': ('employee_number', 'hire_date')}),
        ('Notifications', {'fields': ('email_notifications', 'sms_notifications', 'whatsapp_notifications', 'push_notifications')}),
        ('Preferences', {'fields': ('language', 'timezone', 'date_format', 'theme', 'sidebar_collapsed')}),
        ('Security', {'fields': ('two_factor_enabled', 'two_factor_secret', 'api_key', 'api_key_created', 'api_key_last_used')}),
        ('Activity', {'fields': ('login_count', 'failed_login_attempts', 'locked_until')}),
    )
    
    def get_username(self, obj):
        """Return username with link to user admin"""
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'ip_address', 'device_type', 'login_time', 'last_activity', 'is_active')
    list_filter = ('is_active', 'device_type')
    search_fields = ('user__username', 'ip_address', 'session_key')
    readonly_fields = ('session_key', 'login_time', 'last_activity')
    
    def get_username(self, obj):
        """Return username with link"""
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    get_username.short_description = 'User'
    get_username.admin_order_field = 'user__username'
    
    def has_add_permission(self, request):
        """Disable add permission for sessions"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable change permission for sessions"""
        return False


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'action', 'model_name', 'object_repr', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action', 'model_name', 'object_repr')
    readonly_fields = ('timestamp',)
    
    def get_username(self, obj):
        """Return username with link"""
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    get_username.short_description = 'User'
    get_username.admin_order_field = 'user__username'
    
    def has_add_permission(self, request):
        """Disable add permission for logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable change permission for logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete for superusers only"""
        return request.user.is_superuser