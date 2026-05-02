from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication URLs
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # User Management URLs (Admin only)
    path('', views.user_list, name='user_list'),
    path('create/', views.user_create, name='user_create'),
    path('<int:user_id>/', views.user_detail, name='user_detail'),
    path('<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('<int:user_id>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('<int:user_id>/reset-password/', views.reset_user_password, name='reset_password'),
    
    # Profile Management (User self-service)
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),  # Edit own profile
    path('change-password/', views.change_password, name='change_password'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('preferences/', views.update_preferences, name='preferences'),
    
    # Bulk Actions (Admin only)
    path('bulk-action/', views.bulk_user_action, name='bulk_user_action'),
    path('export/', views.export_users, name='export_users'),
    
    # API Endpoints
    path('api/list/', views.api_user_list, name='api_user_list'),
    path('api/count/', views.api_user_count, name='api_user_count'),
    path('api/stats/', views.api_user_stats, name='api_user_stats'),
    path('api/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
]