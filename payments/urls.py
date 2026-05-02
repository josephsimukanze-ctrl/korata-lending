from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Main payment views
    path('', views.payment_list, name='payment_list'),
    path('<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('create/', views.payment_create, name='payment_create'),
    path('<int:payment_id>/approve/', views.payment_approve, name='payment_approve'),
    path('<int:payment_id>/refund/', views.payment_refund, name='payment_refund'),
    path('<int:payment_id>/cancel/', views.payment_cancel, name='payment_cancel'),
    
    # Loan payment
    path('loan/<int:loan_id>/pay/', views.make_loan_payment, name='make_loan_payment'),
    
    # Payment methods
    path('methods/', views.payment_method_list, name='payment_method_list'),
    path('methods/create/', views.payment_method_create, name='payment_method_create'),
    path('methods/<int:method_id>/edit/', views.payment_method_edit, name='payment_method_edit'),
    path('methods/<int:method_id>/delete/', views.payment_method_delete, name='payment_method_delete'),
    path('methods/<int:method_id>/toggle/', views.payment_method_toggle, name='payment_method_toggle'),
    
    # Scheduled payments
    path('scheduled/', views.scheduled_payment_list, name='scheduled_payment_list'),
    path('scheduled/create/', views.scheduled_payment_create, name='scheduled_payment_create'),
    path('scheduled/process/', views.process_scheduled_payments, name='process_scheduled_payments'),
    path('scheduled/<int:schedule_id>/toggle/', views.toggle_scheduled_payment, name='toggle_scheduled_payment'),
    path('scheduled/<int:schedule_id>/delete/', views.delete_scheduled_payment, name='delete_scheduled_payment'),
    
    # Reports and exports
    path('report/', views.payment_report, name='payment_report'),
    path('export/', views.export_payments, name='export_payments'),
    path('export/report/', views.export_payment_report, name='export_payment_report'),
    
    # API endpoints
    path('api/stats/', views.api_payment_stats, name='api_payment_stats'),
    path('api/client/<int:client_id>/payments/', views.api_client_payments, name='api_client_payments'),
    path('api/loan/<int:loan_id>/upcoming/', views.api_loan_upcoming_payments, name='api_loan_upcoming_payments'),
    path('api/list/', views.api_payment_list, name='api_payment_list'),
    path('api/reports/', views.api_payment_reports, name='api_payment_reports'),
    path('api/scheduled/stats/', views.api_scheduled_stats, name='api_scheduled_stats'),
    path('api/method/<int:method_id>/fees/', views.api_method_fees, name='api_method_fees'),
    # payments/urls.py - Add this line if not already present
path('api/reports/', views.api_payment_reports, name='api_payment_reports'),
]