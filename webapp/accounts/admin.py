from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """사용자 관리자"""
    
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    list_display = ['username', 'email', 'phone', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('개인정보', {'fields': ('email', 'phone')}),
        ('권한', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('승인정보', {'fields': ('approved_by', 'approved_at')}),
        ('중요한 날짜', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        """읽기 전용 필드 설정"""
        readonly_fields = list(self.readonly_fields)
        if obj:  # 수정 시
            readonly_fields.append('username')
        return readonly_fields
