# notifications/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('payment_received', '💰 Payment Received'),
        ('payment_approved', '✅ Payment Approved'),
        ('payment_rejected', '❌ Payment Rejected'),
        ('payment_reminder', '⏰ Payment Reminder'),
        ('loan_approved', '✅ Loan Approved'),
        ('loan_rejected', '❌ Loan Rejected'),
        ('loan_disbursed', '💸 Loan Disbursed'),
        ('loan_due', '📅 Loan Due'),
        ('loan_overdue', '⚠️ Loan Overdue'),
        ('collateral_due', '🏦 Collateral Due'),
        ('late_payment', '⚠️ Late Payment Warning'),
        ('account_activity', '👤 Account Activity'),
        ('system', '🖥️ System Notification'),
        ('reminder', '🔔 Reminder'),
        ('alert', '🚨 Alert'),
        ('info', 'ℹ️ Information'),
        ('promotion', '🎉 Promotion'),
    )
    
    PRIORITY_CHOICES = (
        ('low', '🟢 Low'),
        ('medium', '🟡 Medium'),
        ('high', '🟠 High'),
        ('urgent', '🔴 Urgent'),
    )
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notifications')
    
    # Notification Details
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='info')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)  # Whether notification was sent via email/SMS
    is_archived = models.BooleanField(default=False)
    
    # Links and Actions
    link = models.CharField(max_length=500, blank=True, null=True)
    action_button_text = models.CharField(max_length=50, blank=True, null=True)
    action_button_link = models.CharField(max_length=500, blank=True, null=True)
    
    # Related Objects
    related_payment_id = models.IntegerField(blank=True, null=True)
    related_loan_id = models.IntegerField(blank=True, null=True)
    related_client_id = models.IntegerField(blank=True, null=True)
    related_collateral_id = models.IntegerField(blank=True, null=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)  # When email/SMS was sent
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Auto-set expiry for certain notification types (e.g., payment reminders expire after 7 days)
        if not self.expires_at:
            if self.notification_type in ['payment_reminder', 'loan_due']:
                self.expires_at = timezone.now() + timedelta(days=7)
            elif self.notification_type in ['alert', 'urgent']:
                self.expires_at = timezone.now() + timedelta(days=3)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def time_ago(self):
        """Get human-readable time ago"""
        diff = timezone.now() - self.created_at
        
        if diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"
    
    @property
    def priority_color(self):
        """Get color for priority"""
        colors = {
            'low': 'gray',
            'medium': 'blue',
            'high': 'orange',
            'urgent': 'red',
        }
        return colors.get(self.priority, 'gray')
    
    @property
    def priority_icon(self):
        """Get icon for priority"""
        icons = {
            'low': 'fa-circle',
            'medium': 'fa-circle-info',
            'high': 'fa-exclamation-circle',
            'urgent': 'fa-exclamation-triangle',
        }
        return icons.get(self.priority, 'fa-bell')
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_sent(self):
        """Mark notification as sent (email/SMS)"""
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=['is_sent', 'sent_at'])


class NotificationTemplate(models.Model):
    """Pre-defined notification templates"""
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=Notification.NOTIFICATION_TYPES, default='info')
    priority = models.CharField(max_length=10, choices=Notification.PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def render_title(self, context=None):
        """Render title with context variables"""
        if context:
            return self.title.format(**context)
        return self.title
    
    def render_message(self, context=None):
        """Render message with context variables"""
        if context:
            return self.message.format(**context)
        return self.message


class UserNotificationSettings(models.Model):
    """User preferences for notifications"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    
    # Channel preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    whatsapp_notifications = models.BooleanField(default=False)
    
    # Type preferences
    notify_payment = models.BooleanField(default=True)
    notify_loan = models.BooleanField(default=True)
    notify_reminder = models.BooleanField(default=True)
    notify_alert = models.BooleanField(default=True)
    notify_promotion = models.BooleanField(default=False)
    notify_system = models.BooleanField(default=True)
    
    # Digest settings
    digest_enabled = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=10, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='daily')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification settings for {self.user.username}"