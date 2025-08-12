from django.contrib import admin
from .models import (
    NetworkGroup, Domain, Endpoint, Check, 
    Rollup, Setting, ConfigRevision, Notification
)


@admin.register(NetworkGroup)
class NetworkGroupAdmin(admin.ModelAdmin):
    """망구분 관리자"""
    
    list_display = ['name', 'note', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """도메인 관리자"""
    
    list_display = ['domain', 'site_name', 'owner_name', 'network_group', 'created_at']
    list_filter = ['network_group', 'created_at']
    search_fields = ['domain', 'site_name', 'owner_name']
    ordering = ['network_group', 'domain']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    """엔드포인트 관리자"""
    
    list_display = [
        'url', 'domain', 'requires_db', 'poll_interval_sec', 
        'email_on_failure', 'is_enabled', 'created_at'
    ]
    list_filter = [
        'requires_db', 'email_on_failure', 'is_enabled', 
        'domain__network_group', 'created_at'
    ]
    search_fields = ['url', 'domain__domain', 'domain__site_name']
    ordering = ['domain', 'url']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    """헬스체크 관리자"""
    
    list_display = [
        'endpoint', 'status_code', 'latency_ms', 'checked_at', 'trace_id'
    ]
    list_filter = ['status_code', 'checked_at', 'endpoint__domain__network_group']
    search_fields = ['endpoint__url', 'trace_id']
    ordering = ['-checked_at']
    readonly_fields = ['trace_id', 'checked_at']
    
    def has_add_permission(self, request):
        """추가 권한 없음 (콘솔에서만 생성)"""
        return False


@admin.register(Rollup)
class RollupAdmin(admin.ModelAdmin):
    """상태롤업 관리자"""
    
    list_display = ['level', 'ref_id', 'last_status', 'last_change_at', 'updated_at']
    list_filter = ['level', 'last_status', 'last_change_at']
    ordering = ['level', 'ref_id']
    readonly_fields = ['updated_at']


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    """설정 관리자"""
    
    list_display = ['key', 'value', 'updated_at']
    search_fields = ['key']
    ordering = ['key']
    readonly_fields = ['updated_at']


@admin.register(ConfigRevision)
class ConfigRevisionAdmin(admin.ModelAdmin):
    """설정변경이력 관리자"""
    
    list_display = ['id', 'reason', 'changed_by', 'changed_at']
    list_filter = ['changed_at', 'changed_by']
    search_fields = ['reason']
    ordering = ['-changed_at']
    readonly_fields = ['changed_at']
    
    def has_add_permission(self, request):
        """추가 권한 없음 (자동 생성)"""
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """알림 관리자"""
    
    list_display = ['title', 'sent_to', 'endpoint', 'status', 'sent_at']
    list_filter = ['status', 'level', 'sent_at']
    search_fields = ['title', 'sent_to', 'endpoint__url']
    ordering = ['-sent_at']
    readonly_fields = ['sent_at']
    
    def has_add_permission(self, request):
        """추가 권한 없음 (자동 생성)"""
        return False
