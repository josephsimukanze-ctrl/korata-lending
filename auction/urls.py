from django.urls import path
from . import views

app_name = 'auction'

urlpatterns = [
    # Main views
    path('', views.auction_list, name='list'),
    path('<int:auction_id>/', views.auction_detail, name='detail'),
    path('create/', views.create_auction, name='create'),  # No loan_id - shows selection
    path('create/<int:loan_id>/', views.create_auction, name='create'),  # With loan_id - creates auction
    path('<int:auction_id>/start/', views.start_auction, name='start'),
    path('<int:auction_id>/end/', views.end_auction, name='end'),
    path('<int:auction_id>/cancel/', views.cancel_auction, name='cancel'),
    
    # Bids
    path('<int:auction_id>/place-bid/', views.place_bid, name='place_bid'),
    
    # Notices
    path('notices/', views.default_notices, name='notices'),
    path('notices/create/<int:loan_id>/', views.create_default_notice, name='create_notice'),
    
    # API
    path('api/list/', views.api_auction_list, name='api_list'),
    path('api/stats/', views.api_auction_stats, name='api_stats'),
]