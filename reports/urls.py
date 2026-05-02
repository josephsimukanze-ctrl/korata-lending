# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main reports dashboard
    path('', views.report_index, name='index'),
    
    # Individual report pages
    path('collections/', views.collections_report, name='collections'),
    path('loans/', views.loans_report, name='loans'),
    path('clients/', views.clients_report, name='clients'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss'),
    path('collateral/', views.collateral_report, name='collateral'),
    
    # Print functionality - opens print-friendly version
    path('print/<str:report_type>/', views.print_report_direct, name='print'),
    
    # Export functionality
    path('export/<str:report_type>/csv/', views.export_report_csv, name='export_csv'),
    path('export/<str:report_type>/excel/', views.export_report_excel, name='export_excel'),
    
    # Optional: Direct print views for each report type (more specific)
    path('print/collections/', views.print_report_direct, {'report_type': 'collections'}, name='print_collections'),
    path('print/loans/', views.print_report_direct, {'report_type': 'loans'}, name='print_loans'),
    path('print/clients/', views.print_report_direct, {'report_type': 'clients'}, name='print_clients'),
    path('print/profit-loss/', views.print_report_direct, {'report_type': 'profit-loss'}, name='print_profit_loss'),
    path('print/collateral/', views.print_report_direct, {'report_type': 'collateral'}, name='print_collateral'),



       path('', views.report_index, name='index'),
    path('collections/', views.collections_report, name='collections'),
    path('loans/', views.loans_report, name='loans'),
    path('clients/', views.clients_report, name='clients'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss'),
    path('collateral/', views.collateral_report, name='collateral'),
    
    # Export URLs
    path('export/<str:report_type>/csv/', views.export_report_csv, name='export_csv'),
    path('export/<str:report_type>/excel/', views.export_report_excel, name='export_excel'),
]

