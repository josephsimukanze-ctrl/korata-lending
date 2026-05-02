# backup/urls.py
from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup_dashboard, name='dashboard'),
    path('backup/database/', views.backup_database, name='backup_database'),
    path('backup/media/', views.backup_media, name='backup_media'),
    path('backup/full/', views.full_backup, name='full_backup'),
    path('restore/<int:backup_id>/', views.restore_backup, name='restore_backup'),
    path('download/<int:backup_id>/', views.download_backup, name='download_backup'),
    path('delete/<int:backup_id>/', views.delete_backup, name='delete_backup'),
    path('export/', views.export_data, name='export_data'),
    path('import/', views.import_data, name='import_data'),
]