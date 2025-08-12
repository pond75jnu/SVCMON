from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    
    # 관리자 전용
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/approve/', views.approve_user_view, name='approve_user'),
    path('users/<int:user_id>/deactivate/', views.deactivate_user_view, name='deactivate_user'),
    path('users/<int:user_id>/reset-password/', views.reset_password_view, name='reset_password'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
]
