from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('network/<int:network_group_id>/', views.network_detail_view, name='network_detail'),
    path('domain/<int:domain_id>/', views.domain_detail_view, name='domain_detail'),
    path('endpoint/<int:endpoint_id>/chart/', views.endpoint_chart_view, name='endpoint_chart'),
    
    # API endpoints
    path('api/dashboard/', views.dashboard_api_view, name='dashboard_api'),
    path('api/network/<int:network_group_id>/status/', views.network_status_api_view, name='network_status_api'),
]
