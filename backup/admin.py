# backup/admin.py - Fixed version
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import BackupLog

@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'operation_type_badge', 'status_badge', 'filename_truncated', 
        'file_size_display', 'started_at', 'created_by', 'actions_display'
    ]
    list_filter = [
        'operation_type', 'status', 'started_at', 'created_by'  # Changed from 'created_at' to 'started_at'
    ]
    search_fields = [
        'filename', 'error_message', 'notes', 'created_by__username'
    ]
    readonly_fields = [
        'operation_type', 'status', 'filename', 'file_size', 
        'started_at', 'completed_at', 'error_message', 'created_by'
    ]
    list_per_page = 25
    date_hierarchy = 'started_at'  # Changed from 'created_at' to 'started_at'
    
    fieldsets = (
        ('Operation Information', {
            'fields': ('operation_type', 'status', 'created_by')
        }),
        ('File Information', {
            'fields': ('filename', 'file_size_display_readonly', 'notes')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def operation_type_badge(self, obj):
        colors = {
            'full': 'purple',
            'database': 'blue',
            'media': 'green',
            'restore': 'orange',
            'export': 'teal',
            'import': 'cyan',
        }
        color = colors.get(obj.operation_type, 'gray')
        color_map = {
            'purple': '#7c3aed', 'blue': '#3b82f6', 'green': '#10b981',
            'orange': '#f59e0b', 'teal': '#14b8a6', 'cyan': '#06b6d4', 'gray': '#6b7280'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color_map[color],
            obj.get_operation_type_display()
        )
    operation_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'running': 'yellow',
            'failed': 'red',
            'pending': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        color_map = {
            'green': '#10b981', 'yellow': '#f59e0b', 'red': '#ef4444', 'gray': '#6b7280'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color_map[color],
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def filename_truncated(self, obj):
        if obj.filename:
            return obj.filename[:50] + '...' if len(obj.filename) > 50 else obj.filename
        return '-'
    filename_truncated.short_description = 'Filename'
    
    def file_size_display(self, obj):
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return '-'
    file_size_display.short_description = 'Size'
    
    def file_size_display_readonly(self, obj):
        return self.file_size_display(obj)
    file_size_display_readonly.short_description = 'File Size'
    
    def actions_display(self, obj):
        actions = []
        
        # Download button
        if obj.filename and obj.status == 'completed':
            actions.append(format_html(
                '<a href="{}" style="margin-right: 8px; color: #3b82f6; text-decoration: none;" title="Download">📥</a>',
                f'/backup/download/{obj.id}/'
            ))
        
        # Restore button
        if obj.status == 'completed' and obj.operation_type != 'export':
            actions.append(format_html(
                '<a href="{}" style="margin-right: 8px; color: #10b981; text-decoration: none;" title="Restore">🔄</a>',
                f'/backup/restore/{obj.id}/'
            ))
        
        # Delete button
        actions.append(format_html(
            '<a href="{}" style="color: #ef4444; text-decoration: none;" title="Delete" onclick="return confirm(\'Are you sure you want to delete this backup?\')">🗑️</a>',
            f'/backup/delete/{obj.id}/'
        ))
        
        return format_html(''.join(actions)) if actions else '-'
    actions_display.short_description = 'Actions'
    
    def has_add_permission(self, request):
        """Disable add permission since backups are created programmatically"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete only for superusers"""
        return request.user.is_superuser
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly when editing"""
        if obj:  # Editing existing object
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields
    
    actions = ['delete_selected_backups', 'download_selected_backups']
    
    @admin.action(description='Delete selected backups')
    def delete_selected_backups(self, request, queryset):
        """Custom action to delete selected backups"""
        deleted_count = 0
        for backup in queryset:
            backup.delete()
            deleted_count += 1
        self.message_user(request, f'Successfully deleted {deleted_count} backup(s).')
    
    @admin.action(description='Download selected backups (will create ZIP)')
    def download_selected_backups(self, request, queryset):
        """Custom action to download multiple backups as ZIP"""
        import zipfile
        from django.http import HttpResponse
        import io
        import os
        from django.conf import settings
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for backup in queryset:
                backup_path = os.path.join(settings.BASE_DIR, 'backups', backup.filename)
                if os.path.exists(backup_path):
                    zip_file.write(backup_path, backup.filename)
        
        # Prepare response
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="selected_backups_{queryset.count()}.zip"'
        return response


# Register BackupLog model if not already registered
if not admin.site.is_registered(BackupLog):
    admin.site.register(BackupLog, BackupLogAdmin)


# Optional: Add custom admin views (if you want to add statistics view)
from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import render

class BackupAdminSite(AdminSite):
    site_header = 'Korata Backup Administration'
    site_title = 'Backup Admin'
    index_title = 'Backup Management'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('backup-stats/', self.admin_view(self.backup_stats_view), name='backup-stats'),
            path('system-health/', self.admin_view(self.system_health_view), name='system-health'),
        ]
        return custom_urls + urls
    
    def backup_stats_view(self, request):
        """Custom view for backup statistics"""
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # Get statistics
        total_backups = BackupLog.objects.count()
        successful_backups = BackupLog.objects.filter(status='completed').count()
        failed_backups = BackupLog.objects.filter(status='failed').count()
        total_size = BackupLog.objects.aggregate(total=Sum('file_size'))['total'] or 0
        
        # Last 7 days backups
        last_week = timezone.now() - timedelta(days=7)
        weekly_backups = BackupLog.objects.filter(started_at__gte=last_week).count()
        
        # Backup by type
        backups_by_type = BackupLog.objects.values('operation_type').annotate(count=Count('id'))
        
        context = {
            'title': 'Backup Statistics',
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            'total_size': self.format_size(total_size),
            'weekly_backups': weekly_backups,
            'backups_by_type': backups_by_type,
        }
        
        return render(request, 'admin/backup_stats.html', context)
    
    def system_health_view(self, request):
        """System health check view"""
        import os
        import psutil
        from django.conf import settings
        
        # Check disk space
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        disk_usage = psutil.disk_usage(backup_dir if os.path.exists(backup_dir) else settings.BASE_DIR)
        
        # Check database size
        db_path = settings.BASE_DIR / 'db.sqlite3'
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        # Count recent failed backups
        from datetime import timedelta
        recent_failures = BackupLog.objects.filter(
            status='failed',
            started_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        context = {
            'title': 'System Health',
            'disk_total': self.format_size(disk_usage.total),
            'disk_used': self.format_size(disk_usage.used),
            'disk_free': self.format_size(disk_usage.free),
            'disk_percent': disk_usage.percent,
            'db_size': self.format_size(db_size),
            'recent_failures': recent_failures,
            'backup_dir_exists': os.path.exists(backup_dir),
            'backup_dir_writable': os.access(backup_dir, os.W_OK) if os.path.exists(backup_dir) else False,
        }
        
        return render(request, 'admin/system_health.html', context)
    
    def format_size(self, size):
        """Format file size"""
        if not size:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


# Create custom admin site instance (optional)
# backup_admin_site = BackupAdminSite(name='backup_admin')