from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Main views
    path('', views.loan_list, name='loan_list'),
    path('<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('create/', views.loan_create, name='loan_create'),
    path('<int:loan_id>/edit/', views.loan_edit, name='loan_edit'),
    path('<int:loan_id>/delete/', views.loan_delete, name='loan_delete'),
    
    # Loan actions
    path('<int:loan_id>/approve/', views.loan_approve, name='loan_approve'),
    path('<int:loan_id>/activate/', views.loan_activate, name='loan_activate'),
    path('<int:loan_id>/complete/', views.loan_complete, name='loan_complete'),
    path('<int:loan_id>/default/', views.loan_default, name='loan_default'),
    path('<int:loan_id>/reject/', views.loan_reject, name='loan_reject'),
     path('api/stats/', views.api_loan_stats, name='api_loan_stats'),
# Add these to your urlpatterns
path('<int:loan_id>/agreement/', views.view_loan_agreement, name='loan_agreement'),
path('<int:loan_id>/agreement/download/', views.generate_loan_agreement, name='download_loan_agreement'),
    path('<int:loan_id>/agreement/', views.view_loan_agreement, name='loan_agreement'),
    path('<int:loan_id>/agreement/download/', views.generate_loan_agreement, name='download_loan_agreement'),
    path('<int:loan_id>/agreement/sign/', views.sign_loan_agreement, name='sign_loan_agreement'),
    # Calculator
    path('calculator/', views.loan_calculator, name='loan_calculator'),
      path('<int:loan_id>/agreement/sign/', views.sign_loan_agreement, name='sign_loan_agreement'),
    # API endpoints
    path('api/list/', views.api_loan_list, name='api_loan_list'),
    path('api/stats/', views.api_loan_stats, name='api_loan_stats'),
    path('api/calculate/', views.api_loan_calculate, name='api_loan_calculate'),
     path('api/<int:loan_id>/upcoming-payments/', views.api_upcoming_payments, name='api_upcoming_payments'),
     # loans/urls.py
path('api/clients/', views.api_client_list, name='api_client_list'),
]