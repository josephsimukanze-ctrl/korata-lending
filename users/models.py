from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
import secrets
from .managers import CustomUserManager

class CustomUser(AbstractUser):
    """
    Custom User Model with roles and additional fields
    """
    ROLE_CHOICES = (
        ('ceo', 'CEO'),
        ('admin', 'System Admin'),
        ('collateral_officer', 'Collateral Officer'),
        ('accountant', 'Accountant'),
        ('auditor', 'Auditor'),
    )
    
    DEPARTMENT_CHOICES = (
        ('executive', 'Executive'),
        ('it', 'Information Technology'),
        ('finance', 'Finance'),
        ('operations', 'Operations'),
        ('risk', 'Risk Management'),
        ('legal', 'Legal'),
        ('hr', 'Human Resources'),
    )
    
    # Role and basic info
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='collateral_officer')
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Profile details
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True, help_text="Short biography")
    
    # Address information
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='Zambia')
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Tracking fields
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Account security
    account_locked = models.BooleanField(default=False)
    lock_reason = models.CharField(max_length=200, blank=True, null=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['employee_id']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-generate employee_id if not provided
        if not self.employee_id:
            import uuid
            self.employee_id = f"EMP-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def full_address(self):
        """Return complete address"""
        parts = [self.address, self.city, self.postal_code, self.country]
        return ', '.join([p for p in parts if p])
    
    @property
    def is_ceo(self):
        return self.role == 'ceo' or self.is_superuser
    
    @property
    def is_admin_user(self):
        return self.role == 'admin' or self.is_superuser
    
    @property
    def is_collateral_officer(self):
        return self.role == 'collateral_officer'
    
    @property
    def is_accountant(self):
        return self.role == 'accountant'
    
    @property
    def is_auditor(self):
        return self.role == 'auditor'
    
    @property
    def get_initial(self):
        """Get user's initial for avatar"""
        if self.first_name:
            return self.first_name[0].upper()
        return self.username[0].upper()
    
    @property
    def get_role_icon(self):
        """Return icon based on role"""
        icons = {
            'ceo': 'fas fa-crown',
            'admin': 'fas fa-user-shield',
            'collateral_officer': 'fas fa-gem',
            'accountant': 'fas fa-calculator',
            'auditor': 'fas fa-clipboard-list'
        }
        return icons.get(self.role, 'fas fa-user')
    
    @property
    def get_role_color(self):
        """Return color based on role"""
        colors = {
            'ceo': 'bg-red-500',
            'admin': 'bg-purple-500',
            'collateral_officer': 'bg-blue-500',
            'accountant': 'bg-green-500',
            'auditor': 'bg-yellow-500'
        }
        return colors.get(self.role, 'bg-gray-500')
    
    @property
    def initials(self):
        """Get user's initials"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.last_name:
            return self.last_name[0].upper()
        else:
            return self.username[0].upper()
    
    def get_permissions(self):
        """Return permissions based on role"""
        permissions = {
            'ceo': ['view_all', 'edit_all', 'delete_all', 'manage_users', 'view_reports', 'export_data'],
            'admin': ['view_all', 'edit_all', 'manage_users', 'view_reports'],
            'collateral_officer': ['view_clients', 'add_collateral', 'edit_collateral', 'view_collateral'],
            'accountant': ['view_payments', 'process_payments', 'view_reports', 'reconcile_accounts'],
            'auditor': ['view_all', 'export_reports', 'view_audit_logs']
        }
        return permissions.get(self.role, [])
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        return permission in self.get_permissions()
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def lock_account(self, reason=None):
        """Lock user account"""
        self.account_locked = True
        self.lock_reason = reason or "Account locked by administrator"
        self.is_active = False
        self.save(update_fields=['account_locked', 'lock_reason', 'is_active'])
    
    def unlock_account(self):
        """Unlock user account"""
        self.account_locked = False
        self.lock_reason = None
        self.is_active = True
        self.save(update_fields=['account_locked', 'lock_reason', 'is_active'])


class UserProfile(models.Model):
    """Extended user profile information"""
    
    # Language choices
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('fr', 'French'),
        ('sw', 'Swahili'),
        ('pt', 'Portuguese'),
        ('zh', 'Chinese'),
    )
    
    # Timezone choices (common African timezones)
    TIMEZONE_CHOICES = (
        ('Africa/Lusaka', 'Lusaka (GMT+2)'),
        ('Africa/Johannesburg', 'Johannesburg (GMT+2)'),
        ('Africa/Nairobi', 'Nairobi (GMT+3)'),
        ('Africa/Lagos', 'Lagos (GMT+1)'),
        ('Africa/Cairo', 'Cairo (GMT+2)'),
        ('Africa/Casablanca', 'Casablanca (GMT+1)'),
        ('UTC', 'UTC'),
    )
    
    # Date format choices
    DATE_FORMAT_CHOICES = (
        ('Y-m-d', 'YYYY-MM-DD'),
        ('d/m/Y', 'DD/MM/YYYY'),
        ('m/d/Y', 'MM/DD/YYYY'),
        ('d M Y', 'DD Mon YYYY'),
        ('F j, Y', 'Month DD, YYYY'),
    )
    
    # Theme choices
    THEME_CHOICES = (
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
        ('auto', 'Auto (Follow System)'),
    )
    
    # User relation
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Professional details
    employee_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")
    sms_notifications = models.BooleanField(default=False, help_text="Receive SMS notifications")
    whatsapp_notifications = models.BooleanField(default=False, help_text="Receive WhatsApp notifications")
    push_notifications = models.BooleanField(default=True, help_text="Receive browser push notifications")
    
    # Display preferences
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Africa/Lusaka')
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default='Y-m-d')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    sidebar_collapsed = models.BooleanField(default=False, help_text="Keep sidebar collapsed by default")
    
    # Security preferences
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=100, blank=True, null=True)
    two_factor_backup_codes = models.TextField(blank=True, null=True, help_text="Comma-separated backup codes")
    
    # API access
    api_key = models.CharField(max_length=100, blank=True, null=True, unique=True)
    api_key_created = models.DateTimeField(null=True, blank=True)
    api_key_last_used = models.DateTimeField(null=True, blank=True)
    
    # Activity tracking
    login_count = models.IntegerField(default=0)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    last_active = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['user__username']
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Generate API key if not exists
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
            self.api_key_created = timezone.now()
        super().save(*args, **kwargs)
    
    def regenerate_api_key(self):
        """Regenerate API key"""
        self.api_key = secrets.token_urlsafe(32)
        self.api_key_created = timezone.now()
        self.save(update_fields=['api_key', 'api_key_created'])
    
    def increment_login_count(self):
        """Increment login counter"""
        self.login_count += 1
        self.save(update_fields=['login_count', 'last_active'])
    
    def record_failed_attempt(self):
        """Record failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'locked_until'])
    
    def reset_failed_attempts(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])
    
    @property
    def is_locked(self):
        """Check if profile is locked"""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False
    
    @property
    def get_notification_summary(self):
        """Get summary of enabled notifications"""
        enabled = []
        if self.email_notifications:
            enabled.append('Email')
        if self.sms_notifications:
            enabled.append('SMS')
        if self.whatsapp_notifications:
            enabled.append('WhatsApp')
        if self.push_notifications:
            enabled.append('Push')
        return ', '.join(enabled) if enabled else 'None'
    
    @property
    def get_theme_display_name(self):
        """Get display name for theme"""
        return dict(self.THEME_CHOICES).get(self.theme, self.theme)
    
    @property
    def get_language_display_name(self):
        """Get display name for language"""
        return dict(self.LANGUAGE_CHOICES).get(self.language, self.language)


class UserSession(models.Model):
    """Track user sessions"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Session for {self.user.username} - {self.login_time}"
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]


class UserActivityLog(models.Model):
    """Log user activities for audit trail"""
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    object_repr = models.CharField(max_length=200, blank=True, null=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
    
    class Meta:
        db_table = 'user_activity_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]


# Alias ActivityLog for backward compatibility
ActivityLog = UserActivityLog