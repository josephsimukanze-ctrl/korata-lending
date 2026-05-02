from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    # Main views
    path('', views.client_list, name='client_list'),
    path('<int:client_id>/', views.client_detail, name='client_detail'),
    path('create/', views.client_create, name='client_create'),
    path('<int:client_id>/edit/', views.client_edit, name='client_edit'),
    path('<int:client_id>/delete/', views.client_delete, name='client_delete'),
    
    # KYC and Notes
    path('<int:client_id>/verify-kyc/', views.verify_kyc, name='verify_kyc'),
    path('<int:client_id>/add-note/', views.add_note, name='add_note'),
    path('notes/<int:note_id>/delete/', views.delete_note, name='delete_note'),
    
    # Export
    path('export/', views.export_clients, name='export_clients'),
    
    # API endpoints for AJAX
    path('api/list/', views.api_client_list, name='api_client_list'),
    path('api/stats/', views.api_client_stats, name='api_client_stats'),
    path('api/stats/', views.api_client_stats, name='api_client_stats'),
]

# Optional: If you need to handle client ID with custom format (like CUS-20241225-1234)
# You can add a path for URL lookup by client_id string instead of integer primary key
# path('by-id/<str:client_id>/', views.client_detail_by_client_id, name='client_detail_by_id'),