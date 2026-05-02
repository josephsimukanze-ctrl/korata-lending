# korata_lending/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# Import views for API endpoints
from clients import views as client_views
from loans import views as loan_views
from payments import views as payment_views
from users import views as user_views

urlpatterns = [
    # Redirects
    re_path(r'^admin/logs/$', RedirectView.as_view(url='/admin/', permanent=False)),
    re_path(r'^admin/backup/$', RedirectView.as_view(url='/admin/', permanent=False)),
    re_path(r'^admin/settings/$', RedirectView.as_view(url='/admin/', permanent=False)),
    
    # Admin URL
    path('admin/', admin.site.urls),
    
    # Main app URLs with namespaces
    path('', include('core.urls')),  # This is the core app WITHOUT namespace
    path('users/', include('users.urls', namespace='users')),
    path('clients/', include('clients.urls', namespace='clients')),
    path('loans/', include('loans.urls', namespace='loans')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('auction/', include('auction.urls', namespace='auction')),
    path('collateral/', include('collateral.urls', namespace='collateral')),
    path('payments/', include('payments.urls', namespace='payments')),
    
    # API Endpoints for Dashboard Statistics
    path('api/users/stats/', user_views.api_user_stats, name='api_user_stats'),
    path('api/clients/stats/', client_views.api_client_stats, name='api_client_stats'),
    path('api/loans/stats/', loan_views.api_loan_stats, name='api_loan_stats'),
    path('api/payments/stats/', payment_views.api_payment_stats, name='api_payment_stats'),
    path('backup/', include('backup.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)