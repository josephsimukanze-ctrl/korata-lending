# backup/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class BackupLog(models.Model):
    """Track backup operations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('full', 'Full Backup'),
        ('database', 'Database Only'),
        ('media', 'Media Files Only'),
        ('restore', 'Restore Operation'),
        ('export', 'Data Export'),
        ('import', 'Data Import'),
    ]
    
    operation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.started_at}"