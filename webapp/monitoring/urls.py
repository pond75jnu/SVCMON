from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # 망구분 관리
    path('network-groups/', views.network_group_list_view, name='network_group_list'),
    path('network-groups/create/', views.network_group_create_view, name='network_group_create'),
    path('network-groups/<int:network_group_id>/edit/', views.network_group_edit_view, name='network_group_edit'),
    path('network-groups/<int:network_group_id>/delete/', views.network_group_delete_view, name='network_group_delete'),
    path('network-groups/clone/', views.clone_network_group_view, name='clone_network_group'),
    
    # 도메인 관리
    path('domains/', views.domain_list_view, name='domain_list'),
    path('domains/create/', views.domain_create_view, name='domain_create'),
    path('domains/<int:domain_id>/edit/', views.domain_edit_view, name='domain_edit'),
    path('domains/<int:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),
    
    # 엔드포인트 관리
    path('endpoints/', views.endpoint_list_view, name='endpoint_list'),
    path('endpoints/create/', views.endpoint_create_view, name='endpoint_create'),
    path('endpoints/<int:endpoint_id>/edit/', views.endpoint_edit_view, name='endpoint_edit'),
    path('endpoints/<int:endpoint_id>/delete/', views.endpoint_delete_view, name='endpoint_delete'),
    path('endpoints/<int:endpoint_id>/detail/', views.endpoint_detail_view, name='endpoint_detail'),
    
    # 일괄 설정
    path('bulk-settings/', views.bulk_settings_view, name='bulk_settings'),
    
    # 모니터링 상태
    path('status/', views.monitoring_status_view, name='status'),
    
    # 설정 및 기록
    path('settings/', views.settings_view, name='settings'),
    path('check-history/', views.check_history_view, name='check_history'),
    
    # API
    path('api/endpoints/<int:endpoint_id>/chart-data/', views.endpoint_chart_data_view, name='endpoint_chart_data'),
]
