# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Main views
    path('', views.notification_list, name='list'),
    path('create/', views.create_notification, name='create'),
    path('templates/', views.manage_templates, name='templates'),
    path('templates/<int:template_id>/delete/', views.delete_template, name='delete_template'),
    path('settings/', views.notification_settings, name='settings'),
    path('scheduled/', views.scheduled_notifications, name='scheduled'),
    path('scheduled/<int:notification_id>/cancel/', views.cancel_scheduled, name='cancel_scheduled'),
    
    # Bulk operations
    path('bulk/', views.create_bulk_notification, name='bulk'),
    
    # API endpoints
    path('api/', views.api_notifications, name='api_notifications'),
    path('api/list/', views.api_notifications, name='api_list'),
    path('api/stats/', views.api_notification_stats, name='api_stats'),
    path('api/template/<int:template_id>/', views.get_template_api, name='api_template'),
    
    # Actions
    path('api/mark-read/<int:notification_id>/', views.mark_as_read, name='mark_read'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('api/', views.api_notifications, name='api_notifications'),
]

# Alias for backward compatibility (if needed)
get_notifications = views.api_notifications
notification_stats = views.api_notification_stats