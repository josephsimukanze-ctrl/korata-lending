from django.urls import path
from . import views

app_name = 'collateral'

urlpatterns = [
    # Main collateral views
    path('', views.collateral_list, name='list'),
    path('create/', views.collateral_create, name='create'),
    path('<int:pk>/', views.collateral_detail, name='detail'),
    path('<int:pk>/edit/', views.collateral_edit, name='edit'),
    path('<int:pk>/delete/', views.collateral_delete, name='delete'),
    
    # Asset type management
    path('asset-types/', views.asset_types, name='asset_types'),
    path('asset-types/create/', views.asset_type_create, name='asset_type_create'),
    path('asset-types/<int:pk>/edit/', views.asset_type_edit, name='asset_type_edit'),
    path('asset-types/<int:pk>/delete/', views.asset_type_delete, name='asset_type_delete'),
    
    # Inspection management
    path('inspections/', views.inspections, name='inspections'),
    path('inspections/create/', views.inspection_create, name='inspection_create'),
    path('inspections/<int:pk>/', views.inspection_detail, name='inspection_detail'),
    path('inspections/<int:pk>/edit/', views.inspection_edit, name='inspection_edit'),
    
    # Movement tracking
    path('movements/', views.movements, name='movements'),
    path('movements/create/', views.movement_create, name='movement_create'),
    path('movements/<int:pk>/', views.movement_detail, name='movement_detail'),
    
    # Reports
    path('reports/', views.collateral_reports, name='reports'),
    path('reports/valuation/', views.valuation_report, name='valuation_report'),
    path('reports/insurance/', views.insurance_report, name='insurance_report'),
    
    # Actions
    path('<int:pk>/verify/', views.verify_collateral, name='verify'),
    path('<int:pk>/seize/', views.seize_collateral, name='seize'),
    path('<int:pk>/release/', views.release_collateral, name='release'),
    path('<int:pk>/generate-qr/', views.generate_qr_code, name='generate_qr'),
    
    # API endpoints
    path('api/stats/', views.api_collateral_stats, name='api_stats'),
    path('api/list/', views.api_collateral_list, name='api_list'),
    path('api/<int:pk>/', views.api_collateral_detail, name='api_detail'),
    
    # Export
    path('export/csv/', views.export_collateral_csv, name='export_csv'),
    path('export/excel/', views.export_collateral_excel, name='export_excel'),

    path('insurance/', views.insurance_list, name='insurance_list'),
    path('insurance/create/', views.insurance_create, name='insurance_create'),
    path('insurance/<int:pk>/', views.insurance_detail, name='insurance_detail'),
    path('insurance/<int:pk>/edit/', views.insurance_edit, name='insurance_edit'),
    path('insurance/<int:pk>/delete/', views.insurance_delete, name='insurance_delete'),
    path('insurance/claims/', views.insurance_claims, name='insurance_claims'),
    path('insurance/reports/', views.insurance_reports, name='insurance_reports'),
    path('api/insurance/stats/', views.api_insurance_stats, name='api_insurance_stats'),




    path('reports/', views.collateral_reports_dashboard, name='reports_dashboard'),
    path('reports/valuation/', views.valuation_report, name='valuation_report'),
    path('reports/insurance/', views.insurance_report, name='insurance_report'),
    path('reports/movements/', views.movement_report, name='movement_report'),
    path('reports/inspections/', views.inspection_report, name='inspection_report'),
    
    # Print versions (will auto-trigger print dialog)
    path('reports/print/', views.collateral_reports_dashboard, {'format': 'print'}, name='reports_print'),
    
]