from django.db import models
from django.utils import timezone
from users.models import CustomUser

class Report(models.Model):
    REPORT_TYPES = (
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Range'),
    )
    
    REPORT_CATEGORIES = (
        ('collections', 'Collections Report'),
        ('loans', 'Loans Report'),
        ('clients', 'Clients Report'),
        ('profit_loss', 'Profit & Loss'),
        ('collateral', 'Collateral Report'),
    )
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    category = models.CharField(max_length=20, choices=REPORT_CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    generated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='reports/', blank=True, null=True)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.created_at.date()}"
    
    class Meta:
        ordering = ['-created_at']