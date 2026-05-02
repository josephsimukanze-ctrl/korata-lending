# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),  # Make sure this exists
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('keep-alive/', views.keep_alive, name='keep_alive'),
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-chat-api/', views.ai_chat_api, name='ai_chat_api'),
    path('ai-assessment/<int:loan_id>/', views.ai_loan_assessment, name='ai_loan_assessment'),
    path('ai-eligibility/<int:client_id>/', views.ai_eligibility_check, name='ai_eligibility_check'),
    path('ai-status/', views.ai_status, name='ai_status'),
]