from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Notification, NotificationTemplate, UserNotificationSettings
from users.models import CustomUser
import logging

logger = logging.getLogger(__name__)


def is_admin_or_ceo(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin'])


# ==================== MAIN VIEWS ====================

@login_required
def notification_list(request):
    """View all notifications"""
    notifications = Notification.objects.filter(user=request.user)
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    
    type_filter = request.GET.get('type', '')
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)
    
    search_query = request.GET.get('search', '')
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        notifications = notifications.filter(created_at__date__gte=date_from)
    date_to = request.GET.get('date_to', '')
    if date_to:
        notifications = notifications.filter(created_at__date__lte=date_to)
    
    items_per_page = int(request.GET.get('per_page', 20))
    paginator = Paginator(notifications, items_per_page)
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)
    
    total_unread = Notification.objects.filter(user=request.user, is_read=False).count()
    urgent_count = Notification.objects.filter(user=request.user, priority='urgent', is_read=False).count()
    
    context = {
        'notifications': notifications_page,
        'filter_type': filter_type,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_unread': total_unread,
        'urgent_count': urgent_count,
        'is_admin': is_admin_or_ceo(request.user),
    }
    return render(request, 'notifications/list.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def create_notification(request):
    """Create and send notifications"""
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        recipient_type = request.POST.get('recipient_type', 'single')
        recipient_id = request.POST.get('recipient_id')
        priority = request.POST.get('priority', 'medium')
        notification_type = request.POST.get('notification_type', 'info')
        
        if not title or not message:
            messages.error(request, 'Title and message are required.')
            return redirect('notifications:create')
        
        users = []
        if recipient_type == 'all':
            users = CustomUser.objects.filter(is_active=True)
        elif recipient_type == 'single' and recipient_id:
            try:
                user = CustomUser.objects.get(id=recipient_id, is_active=True)
                users = [user]
            except CustomUser.DoesNotExist:
                messages.error(request, 'Selected user does not exist.')
                return redirect('notifications:create')
        else:
            messages.error(request, 'Invalid recipient selection.')
            return redirect('notifications:create')
        
        created_count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                created_by=request.user,
                is_sent=True,
                sent_at=timezone.now()
            )
            created_count += 1
        
        messages.success(request, f'Notification sent to {created_count} user(s)!')
        return redirect('notifications:list')
    
    users = CustomUser.objects.filter(is_active=True).order_by('username')
    context = {'users': users}
    return render(request, 'notifications/create.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def manage_templates(request):
    """Manage notification templates"""
    templates = NotificationTemplate.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        priority = request.POST.get('priority', 'medium')
        
        if not name or not title or not message:
            messages.error(request, 'All fields are required.')
            return redirect('notifications:templates')
        
        NotificationTemplate.objects.create(
            name=name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority
        )
        messages.success(request, 'Template created successfully!')
        return redirect('notifications:templates')
    
    context = {'templates': templates}
    return render(request, 'notifications/templates.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def delete_template(request, template_id):
    """Delete a notification template"""
    if request.method == 'POST':
        template = get_object_or_404(NotificationTemplate, id=template_id)
        template.delete()
        messages.success(request, 'Template deleted successfully!')
    return redirect('notifications:templates')


@login_required
@user_passes_test(is_admin_or_ceo)
def scheduled_notifications(request):
    """View scheduled notifications"""
    scheduled = Notification.objects.filter(created_by=request.user, is_sent=False).order_by('scheduled_for')
    context = {'scheduled': scheduled}
    return render(request, 'notifications/scheduled.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def cancel_scheduled(request, notification_id):
    """Cancel a scheduled notification"""
    notification = get_object_or_404(Notification, id=notification_id, is_sent=False)
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Scheduled notification cancelled.')
        return redirect('notifications:scheduled')
    return render(request, 'notifications/cancel_scheduled.html', {'notification': notification})


@login_required
def notification_settings(request):
    """User notification preferences"""
    settings, created = UserNotificationSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        settings.email_notifications = request.POST.get('email_notifications') == 'on'
        settings.sms_notifications = request.POST.get('sms_notifications') == 'on'
        settings.push_notifications = request.POST.get('push_notifications') == 'on'
        settings.save()
        messages.success(request, 'Notification preferences updated!')
        return redirect('notifications:settings')
    
    context = {'settings': settings}
    return render(request, 'notifications/settings.html', context)


# ==================== API ENDPOINTS ====================

@login_required
def api_notifications(request):
    """API endpoint for notifications"""
    limit = int(request.GET.get('limit', 50))
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:limit]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'priority': n.priority,
            'priority_display': n.get_priority_display(),
            'is_read': n.is_read,
            'time_ago': n.time_ago,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'link': n.link,
        })
    
    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count
    })


@login_required
def api_notification_stats(request):
    """Get notification statistics"""
    total = Notification.objects.filter(user=request.user).count()
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    read = total - unread
    urgent = Notification.objects.filter(user=request.user, priority='urgent', is_read=False).count()
    
    by_type = {}
    type_counts = Notification.objects.filter(user=request.user).values('notification_type').annotate(count=Count('id'))
    for item in type_counts:
        by_type[item['notification_type']] = item['count']
    
    stats = {
        'total': total,
        'unread': unread,
        'read': read,
        'urgent': urgent,
        'by_type': by_type,
    }
    return JsonResponse(stats)


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def mark_all_read(request):
    """Mark all notifications as read"""
    try:
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, 
            read_at=timezone.now()
        )
        return JsonResponse({'success': True, 'count': updated})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def delete_notification(request, notification_id):
    """Delete a notification"""
    if not is_admin_or_ceo(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        notification.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin_or_ceo)
def create_bulk_notification(request):
    """Create bulk notifications using templates"""
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        recipient_type = request.POST.get('recipient_type', 'all')
        role = request.POST.get('role', '')
        priority = request.POST.get('priority', 'medium')
        
        if not template_id:
            messages.error(request, 'Please select a template.')
            return redirect('notifications:create')
        
        template = get_object_or_404(NotificationTemplate, id=template_id)
        
        if recipient_type == 'all':
            users = CustomUser.objects.filter(is_active=True)
        elif recipient_type == 'role' and role:
            users = CustomUser.objects.filter(role=role, is_active=True)
        else:
            messages.error(request, 'Invalid recipient selection.')
            return redirect('notifications:create')
        
        created_count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                title=template.title,
                message=template.message,
                notification_type=template.notification_type,
                priority=priority,
                created_by=request.user,
                is_sent=True,
                sent_at=timezone.now()
            )
            created_count += 1
        
        messages.success(request, f'Bulk notification sent to {created_count} user(s)!')
        return redirect('notifications:list')
    
    return redirect('notifications:create')

# ==================== ADDITIONAL VIEWS ====================

@login_required
def get_template_api(request, template_id):
    """Get template details (API)"""
    template = get_object_or_404(NotificationTemplate, id=template_id)
    return JsonResponse({
        'title': template.title,
        'message': template.message,
        'notification_type': template.notification_type,
        'priority': template.priority
    })


@login_required
@user_passes_test(is_admin_or_ceo)
def send_test_notification(request):
    """Send test notification to yourself"""
    if request.method == 'POST':
        channel = request.POST.get('channel', 'push')
        phone_number = request.POST.get('phone_number', '')
        email = request.POST.get('email', '')
        
        test_title = "Test Notification from Korata"
        test_message = "This is a test notification. If you're receiving this, your notification system is working correctly!"
        
        results = {}
        
        if channel == 'push' or channel == 'all':
            notification = Notification.objects.create(
                user=request.user,
                title=test_title,
                message=test_message,
                notification_type='system',
                priority='medium',
                created_by=request.user,
                is_sent=True,
                sent_at=timezone.now()
            )
            results['push'] = {'success': True, 'id': notification.id}
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    
    return render(request, 'notifications/test_notification.html')


@login_required
@user_passes_test(is_admin_or_ceo)
def notification_report(request):
    """Generate notification delivery report"""
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    notifications = Notification.objects.all()
    
    if date_from:
        notifications = notifications.filter(created_at__date__gte=date_from)
    if date_to:
        notifications = notifications.filter(created_at__date__lte=date_to)
    
    total_sent = notifications.filter(is_sent=True).count()
    total_failed = notifications.filter(is_sent=False).count()
    
    recent_failures = notifications.filter(is_sent=False).order_by('-created_at')[:20]
    
    context = {
        'total_sent': total_sent,
        'total_failed': total_failed,
        'recent_failures': recent_failures,
        'date_from': date_from,
        'date_to': date_to,
        'report_date': timezone.now()
    }
    
    if request.GET.get('format') == 'print':
        return render(request, 'notifications/report_print.html', context)
    
    return render(request, 'notifications/report.html', context)


@login_required
@user_passes_test(is_admin_or_ceo)
def create_bulk_notification(request):
    """Create bulk notifications using templates"""
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        recipient_type = request.POST.get('recipient_type', 'all')
        role = request.POST.get('role', '')
        priority = request.POST.get('priority', 'medium')
        
        if not template_id:
            messages.error(request, 'Please select a template.')
            return redirect('notifications:create')
        
        template = get_object_or_404(NotificationTemplate, id=template_id)
        
        if recipient_type == 'all':
            users = CustomUser.objects.filter(is_active=True)
        elif recipient_type == 'role' and role:
            users = CustomUser.objects.filter(role=role, is_active=True)
        else:
            messages.error(request, 'Invalid recipient selection.')
            return redirect('notifications:create')
        
        created_count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                title=template.title,
                message=template.message,
                notification_type=template.notification_type,
                priority=priority,
                created_by=request.user,
                is_sent=True,
                sent_at=timezone.now()
            )
            created_count += 1
        
        messages.success(request, f'Bulk notification sent to {created_count} user(s)!')
        return redirect('notifications:list')
    
    return redirect('notifications:create')
