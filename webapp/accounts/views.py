from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from .models import User
from .forms import (
    CustomUserCreationForm, 
    LoginForm, 
    PasswordChangeForm, 
    AdminPasswordResetForm
)


def is_admin(user):
    """관리자 권한 체크"""
    return user.is_authenticated and user.is_admin()


def login_view(request):
    """로그인 뷰"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'{user.username}님, 환영합니다!')
                return redirect('dashboard:home')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    messages.info(request, '로그아웃되었습니다.')
    return redirect('accounts:login')


def signup_view(request):
    """회원가입 뷰"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request, 
                '회원가입이 완료되었습니다. 관리자의 승인을 기다려주세요.'
            )
            return redirect('accounts:login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile_view(request):
    """프로필 조회/수정 뷰"""
    if request.method == 'POST':
        user = request.user
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        if email and phone:
            user.email = email
            user.phone = phone
            user.save()
            messages.success(request, '프로필이 성공적으로 업데이트되었습니다.')
            return redirect('accounts:profile')
        else:
            messages.error(request, '모든 필드를 입력해주세요.')
    
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def password_change_view(request):
    """비밀번호 변경 뷰"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '비밀번호가 변경되었습니다.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    """사용자 목록 뷰 (관리자 전용)"""
    users = User.objects.all().order_by('-created_at')
    
    # 필터링
    status = request.GET.get('status', '')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    role = request.GET.get('role', '')
    if role:
        users = users.filter(role=role)
    
    # 페이지네이션
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status': status,
        'role': role,
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def approve_user_view(request, user_id):
    """사용자 승인 뷰 (관리자 전용)"""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_active:
        messages.warning(request, '이미 승인된 사용자입니다.')
    else:
        user.approve_user(request.user)
        messages.success(request, f'{user.username} 사용자가 승인되었습니다.')
    
    return redirect('accounts:user_list')


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def deactivate_user_view(request, user_id):
    """사용자 비활성화 뷰 (관리자 전용)"""
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, '자기 자신을 비활성화할 수 없습니다.')
    elif user.role == 'admin':
        messages.error(request, '관리자는 비활성화할 수 없습니다.')
    else:
        user.is_active = False
        user.save()
        messages.success(request, f'{user.username} 사용자가 비활성화되었습니다.')
    
    return redirect('accounts:user_list')


@login_required
@user_passes_test(is_admin)
def reset_password_view(request, user_id):
    """사용자 비밀번호 재설정 뷰 (관리자 전용)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.save()
            messages.success(request, f'{user.username} 사용자의 비밀번호가 재설정되었습니다.')
            return redirect('accounts:user_list')
    else:
        form = AdminPasswordResetForm()
    
    context = {
        'form': form,
        'target_user': user,
    }
    return render(request, 'accounts/reset_password.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_user_view(request, user_id):
    """사용자 삭제 뷰 (관리자 전용)"""
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, '자기 자신을 삭제할 수 없습니다.')
    elif user.role == 'admin':
        messages.error(request, '관리자는 삭제할 수 없습니다.')
    else:
        username = user.username
        user.delete()
        messages.success(request, f'{username} 사용자가 삭제되었습니다.')
    
    return redirect('accounts:user_list')
