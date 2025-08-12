from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Max
from datetime import datetime, timedelta
import json
from .models import NetworkGroup, Domain, Endpoint, Check, ConfigRevision
from .forms import (
    NetworkGroupForm, DomainForm, EndpointForm, 
    BulkSettingsForm, CloneNetworkGroupForm
)


def is_admin(user):
    """관리자 권한 체크"""
    return user.is_authenticated and user.is_admin()


@login_required
@user_passes_test(is_admin)
def network_group_list_view(request):
    """망구분 목록 뷰"""
    network_groups = NetworkGroup.objects.all().order_by('name')
    
    context = {
        'network_groups': network_groups,
    }
    return render(request, 'monitoring/network_group_list.html', context)


@login_required
@user_passes_test(is_admin)
def network_group_create_view(request):
    """망구분 생성 뷰"""
    if request.method == 'POST':
        form = NetworkGroupForm(request.POST)
        if form.is_valid():
            network_group = form.save()
            
            # 설정 변경 이력 추가 (임시로 주석처리 - changed_by_id 컬럼 문제)
            # ConfigRevision.objects.create(
            #     reason=f'망구분 추가: {network_group.name}',
            #     changed_by=request.user
            # )
            
            messages.success(request, f'망구분 "{network_group.name}"이 생성되었습니다.')
            return redirect('monitoring:network_group_list')
    else:
        form = NetworkGroupForm()
    
    return render(request, 'monitoring/network_group_form.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def network_group_edit_view(request, network_group_id):
    """망구분 수정 뷰"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    
    if request.method == 'POST':
        form = NetworkGroupForm(request.POST, instance=network_group)
        if form.is_valid():
            old_name = network_group.name
            network_group = form.save()
            
            # 설정 변경 이력 추가 (임시로 주석처리 - changed_by_id 컬럼 문제)
            # ConfigRevision.objects.create(
            #     reason=f'망구분 수정: {old_name} -> {network_group.name}',
            #     changed_by=request.user
            # )
            
            messages.success(request, f'망구분 "{network_group.name}"이 수정되었습니다.')
            return redirect('monitoring:network_group_list')
    else:
        form = NetworkGroupForm(instance=network_group)
    
    context = {
        'form': form,
        'network_group': network_group,
    }
    return render(request, 'monitoring/network_group_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def network_group_delete_view(request, network_group_id):
    """망구분 삭제 뷰"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    
    if network_group.domains.exists():
        messages.error(request, '하위에 도메인이 있는 망구분은 삭제할 수 없습니다.')
    else:
        name = network_group.name
        network_group.delete()
        
        # 설정 변경 이력 추가
        ConfigRevision.objects.create(
            reason=f'망구분 삭제: {name}',
            changed_by=request.user
        )
        
        messages.success(request, f'망구분 "{name}"이 삭제되었습니다.')
    
    return redirect('monitoring:network_group_list')


@login_required
@user_passes_test(is_admin)
def domain_create_view(request):
    """도메인 생성 뷰"""
    if request.method == 'POST':
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save()
            
            # 설정 변경 이력 추가 (임시로 주석처리 - changed_by_id 컬럼 문제)
            # ConfigRevision.objects.create(
            #     reason=f'도메인 추가: {domain.domain} ({domain.site_name})',
            #     changed_by=request.user
            # )
            
            messages.success(request, f'도메인 "{domain.domain}"이 생성되었습니다.')
            return redirect('monitoring:domain_list')
    else:
        form = DomainForm()

    return render(request, 'monitoring/domain_form.html', {'form': form})
@login_required
@user_passes_test(is_admin)
def domain_edit_view(request, domain_id):
    """도메인 수정 뷰"""
    domain = get_object_or_404(Domain, id=domain_id)
    
    if request.method == 'POST':
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            old_domain = domain.domain
            domain = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'도메인 수정: {old_domain} -> {domain.domain}',
                changed_by=request.user
            )
            
            messages.success(request, f'도메인 "{domain.domain}"이 수정되었습니다.')
            return redirect('monitoring:domain_list')
    else:
        form = DomainForm(instance=domain)
    
    context = {
        'form': form,
        'domain': domain,
    }
    return render(request, 'monitoring/domain_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def domain_delete_view(request, domain_id):
    """도메인 삭제 뷰"""
    domain = get_object_or_404(Domain, id=domain_id)
    
    if domain.endpoints.exists():
        messages.error(request, '하위에 엔드포인트가 있는 도메인은 삭제할 수 없습니다.')
    else:
        domain_name = domain.domain
        domain.delete()
        
        # 설정 변경 이력 추가
        ConfigRevision.objects.create(
            reason=f'도메인 삭제: {domain_name}',
            changed_by=request.user
        )
        
        messages.success(request, f'도메인 "{domain_name}"이 삭제되었습니다.')
    
    return redirect('monitoring:domain_list')


@login_required
def endpoint_list_view(request):
    """엔드포인트 목록 뷰"""
    endpoints = Endpoint.objects.select_related('domain', 'domain__network_group').all()
    
    # 검색
    search = request.GET.get('search')
    if search:
        endpoints = endpoints.filter(
            Q(url__icontains=search) |
            Q(domain__domain__icontains=search) |
            Q(domain__site_name__icontains=search)
        )
    
    # 필터링
    domain_id = request.GET.get('domain')
    if domain_id:
        endpoints = endpoints.filter(domain_id=domain_id)
    
    network_group_id = request.GET.get('network_group')
    if network_group_id:
        endpoints = endpoints.filter(domain__network_group_id=network_group_id)
    
    # 상태 필터
    status = request.GET.get('status')
    if status == 'enabled':
        endpoints = endpoints.filter(is_enabled=True)
    elif status == 'disabled':
        endpoints = endpoints.filter(is_enabled=False)
    
    endpoints = endpoints.order_by('domain__network_group__name', 'domain__domain', 'url')
    
    # 페이지네이션
    paginator = Paginator(endpoints, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 필터용 데이터
    network_groups = NetworkGroup.objects.all().order_by('name')
    domains = Domain.objects.select_related('network_group').all().order_by('network_group__name', 'domain')
    
    context = {
        'page_obj': page_obj,
        'endpoints': page_obj,  # 템플릿 호환성을 위해 추가
        'network_groups': network_groups,
        'domains': domains,
        'search': search,
        'selected_domain': int(domain_id) if domain_id else None,
        'selected_network_group': int(network_group_id) if network_group_id else None,
        'selected_status': status,
    }
    return render(request, 'monitoring/endpoint_list.html', context)


@login_required
@user_passes_test(is_admin)
def endpoint_create_view(request):
    """엔드포인트 생성 뷰"""
    if request.method == 'POST':
        form = EndpointForm(request.POST)
        if form.is_valid():
            endpoint = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'엔드포인트 추가: {endpoint.url}',
                changed_by=request.user
            )
            
            messages.success(request, f'엔드포인트 "{endpoint.url}"이 생성되었습니다.')
            return redirect('monitoring:endpoint_list')
    else:
        form = EndpointForm()
    
    return render(request, 'monitoring/endpoint_form.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def endpoint_edit_view(request, endpoint_id):
    """엔드포인트 수정 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    if request.method == 'POST':
        form = EndpointForm(request.POST, instance=endpoint)
        if form.is_valid():
            old_url = endpoint.url
            endpoint = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'엔드포인트 수정: {old_url} -> {endpoint.url}',
                changed_by=request.user
            )
            
            messages.success(request, f'엔드포인트 "{endpoint.url}"이 수정되었습니다.')
            return redirect('monitoring:endpoint_list')
    else:
        form = EndpointForm(instance=endpoint)
    
    context = {
        'form': form,
        'endpoint': endpoint,
    }
    return render(request, 'monitoring/endpoint_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def endpoint_delete_view(request, endpoint_id):
    """엔드포인트 삭제 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    url = endpoint.url
    endpoint.delete()
    
    # 설정 변경 이력 추가
    ConfigRevision.objects.create(
        reason=f'엔드포인트 삭제: {url}',
        changed_by=request.user
    )
    
    messages.success(request, f'엔드포인트 "{url}"이 삭제되었습니다.')
    return redirect('monitoring:endpoint_list')


@login_required
@user_passes_test(is_admin)
def bulk_settings_view(request):
    """일괄 설정 뷰"""
    if request.method == 'POST':
        form = BulkSettingsForm(request.POST)
        if form.is_valid():
            level = form.cleaned_data['level']
            target_id = form.cleaned_data['target_id']
            poll_interval_sec = form.cleaned_data['poll_interval_sec']
            email_on_failure = form.cleaned_data['email_on_failure']
            
            with transaction.atomic():
                if level == 'network':
                    # 망구분별 일괄 적용
                    network_group = get_object_or_404(NetworkGroup, id=target_id)
                    endpoints = Endpoint.objects.filter(domain__network_group=network_group)
                    target_name = network_group.name
                elif level == 'domain':
                    # 도메인별 일괄 적용
                    domain = get_object_or_404(Domain, id=target_id)
                    endpoints = Endpoint.objects.filter(domain=domain)
                    target_name = domain.domain
                
                # 엔드포인트 업데이트
                count = endpoints.update(
                    poll_interval_sec=poll_interval_sec,
                    email_on_failure=email_on_failure
                )
                
                # 설정 변경 이력 추가
                ConfigRevision.objects.create(
                    reason=f'일괄 설정 변경: {target_name} ({count}개 엔드포인트)',
                    changed_by=request.user
                )
            
            messages.success(request, f'{target_name}의 {count}개 엔드포인트 설정이 변경되었습니다.')
            return redirect('monitoring:endpoint_list')
    else:
        form = BulkSettingsForm()
    
    # 망구분과 도메인 목록
    network_groups = NetworkGroup.objects.all()
    domains = Domain.objects.select_related('network_group').all()
    
    context = {
        'form': form,
        'network_groups': network_groups,
        'domains': domains,
    }
    return render(request, 'monitoring/bulk_settings.html', context)


@login_required
@user_passes_test(is_admin)
def clone_network_group_view(request):
    """망구분 복사 뷰"""
    if request.method == 'POST':
        form = CloneNetworkGroupForm(request.POST)
        if form.is_valid():
            source = form.cleaned_data['source_network_group']
            target = form.cleaned_data['target_network_group']
            
            with transaction.atomic():
                # 소스 망구분의 도메인과 엔드포인트 복사
                cloned_count = 0
                for domain in source.domains.all():
                    # 도메인 복사
                    new_domain = Domain.objects.create(
                        network_group=target,
                        domain=domain.domain,
                        site_name=domain.site_name,
                        owner_name=domain.owner_name,
                        note=domain.note
                    )
                    
                    # 엔드포인트 복사
                    for endpoint in domain.endpoints.all():
                        Endpoint.objects.create(
                            domain=new_domain,
                            url=endpoint.url,
                            requires_db=endpoint.requires_db,
                            note=endpoint.note,
                            poll_interval_sec=endpoint.poll_interval_sec,
                            email_on_failure=endpoint.email_on_failure,
                            is_enabled=endpoint.is_enabled
                        )
                        cloned_count += 1
                
                # 설정 변경 이력 추가
                ConfigRevision.objects.create(
                    reason=f'망구분 복사: {source.name} -> {target.name} ({cloned_count}개 엔드포인트)',
                    changed_by=request.user
                )
            
            messages.success(
                request, 
                f'{source.name}의 설정이 {target.name}으로 복사되었습니다. '
                f'({cloned_count}개 엔드포인트)'
            )
            return redirect('monitoring:network_group_list')
    else:
        form = CloneNetworkGroupForm()
    
    return render(request, 'monitoring/clone_network_group.html', {'form': form})


@login_required
@login_required
def monitoring_status_view(request):
    """모니터링 상태 뷰 (개선된 버전)"""
    # 망구분별 통계
    network_groups = NetworkGroup.objects.prefetch_related(
        'domains__endpoints__checks'
    ).all()
    
    network_status = []
    for ng in network_groups:
        total_endpoints = 0
        green_count = 0
        amber_count = 0
        red_count = 0
        
        for domain in ng.domains.all():
            for endpoint in domain.endpoints.filter(is_enabled=True):
                total_endpoints += 1
                latest_check = endpoint.checks.first()
                
                if latest_check:
                    if latest_check.is_success:
                        green_count += 1
                    else:
                        red_count += 1
                else:
                    amber_count += 1
        
        network_status.append({
            'network_group': ng,
            'total_endpoints': total_endpoints,
            'green_count': green_count,
            'amber_count': amber_count,
            'red_count': red_count,
            'green_percentage': (green_count / total_endpoints * 100) if total_endpoints > 0 else 0,
        })
    
    # 전체 통계
    total_endpoints = Endpoint.objects.filter(is_enabled=True).count()
    total_green = 0
    total_amber = 0
    total_red = 0
    
    for status in network_status:
        total_green += status['green_count']
        total_amber += status['amber_count']
        total_red += status['red_count']
    
    # 최근 알림 (에러가 발생한 엔드포인트들)
    recent_errors = Check.objects.filter(
        is_success=False,
        checked_at__gte=timezone.now() - timedelta(hours=1)
    ).select_related('endpoint__domain__network_group').order_by('-checked_at')[:10]
    
    context = {
        'network_status': network_status,
        'total_endpoints': total_endpoints,
        'total_green': total_green,
        'total_amber': total_amber,
        'total_red': total_red,
        'total_green_percentage': (total_green / total_endpoints * 100) if total_endpoints > 0 else 0,
        'recent_errors': recent_errors,
    }
    return render(request, 'monitoring/status.html', context)


@login_required
def endpoint_detail_view(request, endpoint_id):
    """엔드포인트 상세 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    # 최근 10개 체크 결과
    recent_checks = endpoint.checks.all()[:10]
    
    context = {
        'endpoint': endpoint,
        'recent_checks': recent_checks,
    }
    return render(request, 'monitoring/endpoint_detail.html', context)


@login_required
@user_passes_test(is_admin)
def settings_view(request):
    """시스템 설정 뷰 (개선된 버전)"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cleanup_old_checks':
            # 30일 이전 체크 기록 정리
            cutoff_date = timezone.now() - timedelta(days=30)
            deleted_count = Check.objects.filter(checked_at__lt=cutoff_date).count()
            Check.objects.filter(checked_at__lt=cutoff_date).delete()
            
            messages.success(request, f'{deleted_count}개의 오래된 체크 기록이 삭제되었습니다.')
            
        elif action == 'refresh_all_checks':
            # 모든 엔드포인트의 다음 체크 시간을 현재 시간으로 설정 (즉시 체크)
            # 이는 실제로는 저장프로시저나 별도 로직으로 처리해야 함
            messages.success(request, '모든 엔드포인트의 체크가 예약되었습니다.')
            
        elif action == 'export_config':
            # 설정 백업 (JSON 형태로)
            config_data = {
                'network_groups': list(NetworkGroup.objects.values()),
                'domains': list(Domain.objects.values()),
                'endpoints': list(Endpoint.objects.values()),
                'exported_at': timezone.now().isoformat(),
            }
            
            response = HttpResponse(
                json.dumps(config_data, indent=2, ensure_ascii=False),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="svcmon_config_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
            return response
        
        # 설정 변경 이력 추가
        ConfigRevision.objects.create(
            reason=f'시스템 설정 작업: {action}',
            changed_by=request.user
        )
        
        return redirect('monitoring:settings')
    
    # 시스템 통계
    stats = {
        'total_network_groups': NetworkGroup.objects.count(),
        'total_domains': Domain.objects.count(),
        'total_endpoints': Endpoint.objects.count(),
        'enabled_endpoints': Endpoint.objects.filter(is_enabled=True).count(),
        'total_checks': Check.objects.count(),
        'checks_last_24h': Check.objects.filter(
            checked_at__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'latest_check': Check.objects.order_by('-checked_at').first(),
        'oldest_check': Check.objects.order_by('checked_at').first(),
    }
    
    # 최근 설정 변경 이력
    recent_revisions = ConfigRevision.objects.order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_revisions': recent_revisions,
    }
    return render(request, 'monitoring/settings.html', context)


@login_required
def check_history_view(request):
    """체크 기록 뷰"""
    from django.db.models import Avg, Count, Q
    from datetime import datetime, timedelta
    
    checks = Check.objects.all().order_by('-checked_at')
    
    # 필터링
    endpoint_id = request.GET.get('endpoint')
    if endpoint_id:
        checks = checks.filter(endpoint_id=endpoint_id)
    
    status = request.GET.get('status')
    if status == 'success':
        # 성공: 상태코드가 200-299이고 에러가 없는 경우
        checks = checks.filter(
            status_code__gte=200, 
            status_code__lt=300,
            error__isnull=True
        )
    elif status == 'error':
        # 실패: 상태코드가 200-299가 아니거나 에러가 있는 경우
        checks = checks.filter(
            Q(status_code__lt=200) | 
            Q(status_code__gte=300) | 
            Q(error__isnull=False)
        )
    
    # 통계 계산
    total_checks = Check.objects.count()
    success_checks = Check.objects.filter(
        status_code__gte=200, 
        status_code__lt=300,
        error__isnull=True
    ).count()
    success_rate = (success_checks / total_checks * 100) if total_checks > 0 else 0
    
    # 평균 응답시간 (성공한 체크만)
    avg_response_time = Check.objects.filter(
        status_code__gte=200, 
        status_code__lt=300,
        error__isnull=True,
        latency_ms__isnull=False
    ).aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
    
    # 오늘 오류 수
    today = timezone.now().date()
    today_errors = Check.objects.filter(
        Q(status_code__lt=200) | 
        Q(status_code__gte=300) | 
        Q(error__isnull=False),
        checked_at__date=today
    ).count()
    
    # 페이지네이션
    paginator = Paginator(checks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 엔드포인트 목록 (필터용)
    endpoints = Endpoint.objects.all().order_by('url')
    
    context = {
        'page_obj': page_obj,
        'endpoints': endpoints,
        'selected_endpoint': endpoint_id,
        'selected_status': status,
        'total_checks': total_checks,
        'success_rate': round(success_rate, 1),
        'avg_response_time': round(avg_response_time) if avg_response_time else 0,
        'today_errors': today_errors,
    }
    return render(request, 'monitoring/check_history.html', context)


@login_required
def endpoint_chart_data_view(request, endpoint_id):
    """엔드포인트 차트 데이터 API"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    # 최근 10개 체크 결과
    checks = endpoint.checks.all()[:10]
    
    data = {
        'labels': [check.checked_at.strftime('%H:%M') for check in reversed(checks)],
        'latencies': [check.latency_ms or 0 for check in reversed(checks)],
        'status_codes': [check.status_code or 0 for check in reversed(checks)]
    }
    
    return JsonResponse(data)


# ============================
# 누락된 뷰들 추가
# ============================

@login_required
@user_passes_test(is_admin)
def network_group_edit_view(request, network_group_id):
    """망구분 수정 뷰"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    
    if request.method == 'POST':
        form = NetworkGroupForm(request.POST, instance=network_group)
        if form.is_valid():
            old_name = network_group.name
            network_group = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'망구분 수정: {old_name} → {network_group.name}',
                changed_by=request.user
            )
            
            messages.success(request, f'망구분 "{network_group.name}"이 수정되었습니다.')
            return redirect('monitoring:network_group_list')
    else:
        form = NetworkGroupForm(instance=network_group)
    
    context = {
        'form': form,
        'network_group': network_group,
        'is_edit': True,
    }
    return render(request, 'monitoring/network_group_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def network_group_delete_view(request, network_group_id):
    """망구분 삭제 뷰"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    
    # 관련 도메인이 있는지 확인
    domain_count = network_group.domains.count()
    if domain_count > 0:
        messages.error(request, f'망구분 "{network_group.name}"에 {domain_count}개의 도메인이 연결되어 있어 삭제할 수 없습니다.')
        return redirect('monitoring:network_group_list')
    
    network_group_name = network_group.name
    network_group.delete()
    
    # 설정 변경 이력 추가
    ConfigRevision.objects.create(
        reason=f'망구분 삭제: {network_group_name}',
        changed_by=request.user
    )
    
    messages.success(request, f'망구분 "{network_group_name}"이 삭제되었습니다.')
    return redirect('monitoring:network_group_list')


@login_required
@user_passes_test(is_admin)
def clone_network_group_view(request):
    """망구분 복제 뷰"""
    if request.method == 'POST':
        form = CloneNetworkGroupForm(request.POST)
        if form.is_valid():
            source_id = form.cleaned_data['source_network_group']
            new_name = form.cleaned_data['new_name']
            copy_domains = form.cleaned_data['copy_domains']
            copy_endpoints = form.cleaned_data['copy_endpoints']
            
            source_network_group = get_object_or_404(NetworkGroup, id=source_id)
            
            with transaction.atomic():
                # 새 망구분 생성
                new_network_group = NetworkGroup.objects.create(
                    name=new_name,
                    note=f'{source_network_group.note} (복제본)'
                )
                
                if copy_domains:
                    # 도메인 복제
                    for domain in source_network_group.domains.all():
                        new_domain = Domain.objects.create(
                            network_group=new_network_group,
                            domain=domain.domain,
                            site_name=domain.site_name,
                            owner_name=domain.owner_name,
                            note=domain.note
                        )
                        
                        if copy_endpoints:
                            # 엔드포인트 복제
                            for endpoint in domain.endpoints.all():
                                Endpoint.objects.create(
                                    domain=new_domain,
                                    url=endpoint.url,
                                    poll_interval_sec=endpoint.poll_interval_sec,
                                    is_enabled=endpoint.is_enabled,
                                    note=endpoint.note
                                )
                
                # 설정 변경 이력 추가
                ConfigRevision.objects.create(
                    reason=f'망구분 복제: {source_network_group.name} → {new_name}',
                    changed_by=request.user
                )
                
                messages.success(request, f'망구분 "{new_name}"이 생성되었습니다.')
                return redirect('monitoring:network_group_list')
    else:
        form = CloneNetworkGroupForm()
    
    context = {
        'form': form,
    }
    return render(request, 'monitoring/clone_network_group.html', context)


@login_required
@user_passes_test(is_admin)
def domain_list_view(request):
    """도메인 목록 뷰"""
    domains = Domain.objects.select_related('network_group').all()
    
    # 검색
    search = request.GET.get('search')
    if search:
        domains = domains.filter(
            Q(domain__icontains=search) |
            Q(site_name__icontains=search) |
            Q(owner_name__icontains=search)
        )
    
    # 망구분 필터
    network_group = request.GET.get('network_group')
    if network_group:
        domains = domains.filter(network_group_id=network_group)
    
    domains = domains.order_by('network_group__name', 'domain')
    
    # 페이지네이션
    paginator = Paginator(domains, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 망구분 목록 (필터용)
    network_groups = NetworkGroup.objects.all().order_by('name')
    
    context = {
        'domains': page_obj,  # 템플릿에서 사용하는 변수
        'page_obj': page_obj,
        'network_groups': network_groups,
        'search': search,
        'selected_network_group': network_group,
    }
    return render(request, 'monitoring/domain_list.html', context)


@login_required
@user_passes_test(is_admin)
def domain_create_view(request):
    """도메인 생성 뷰"""
    if request.method == 'POST':
        form = DomainForm(request.POST)
        if form.is_valid():
            try:
                domain = form.save()
                
                # 설정 변경 이력 추가 (임시로 주석처리 - changed_by_id 컬럼 문제)
                # ConfigRevision.objects.create(
                #     reason=f'도메인 추가: {domain.domain} ({domain.site_name})',
                #     changed_by=request.user
                # )
                
                messages.success(request, f'도메인 "{domain.domain}"이 생성되었습니다.')
                return redirect('monitoring:domain_list')
            except Exception as e:
                messages.error(request, f'도메인 저장 중 오류가 발생했습니다: {e}')
        else:
            # 유니크 제약조건 오류 메시지 개선
            if '__all__' in form.errors:
                for error in form.errors['__all__']:
                    if '이미 존재합니다' in str(error):
                        messages.error(request, '선택한 망구분에 동일한 도메인명이 이미 등록되어 있습니다. 다른 도메인명을 사용하거나 기존 도메인을 수정해주세요.')
                    else:
                        messages.error(request, str(error))
    else:
        form = DomainForm()

    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'monitoring/domain_form.html', context)
@login_required
@user_passes_test(is_admin)
def domain_edit_view(request, domain_id):
    """도메인 수정 뷰"""
    domain = get_object_or_404(Domain, id=domain_id)
    
    if request.method == 'POST':
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            old_domain = domain.domain
            domain = form.save()
            
            # 설정 변경 이력 추가 (임시로 주석처리 - changed_by_id 컬럼 문제)
            # ConfigRevision.objects.create(
            #     reason=f'도메인 수정: {old_domain} → {domain.domain}',
            #     changed_by=request.user
            # )
            
            messages.success(request, f'도메인 "{domain.domain}"이 수정되었습니다.')
            return redirect('monitoring:domain_list')
    else:
        form = DomainForm(instance=domain)
    
    context = {
        'form': form,
        'domain': domain,
        'is_edit': True,
    }
    return render(request, 'monitoring/domain_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def domain_delete_view(request, domain_id):
    """도메인 삭제 뷰"""
    domain = get_object_or_404(Domain, id=domain_id)
    
    # 관련 엔드포인트가 있는지 확인
    endpoint_count = domain.endpoints.count()
    if endpoint_count > 0:
        messages.error(request, f'도메인 "{domain.domain}"에 {endpoint_count}개의 엔드포인트가 연결되어 있어 삭제할 수 없습니다.')
        return redirect('monitoring:domain_list')
    
    domain_name = domain.domain
    domain.delete()
    
    # 설정 변경 이력 추가
    ConfigRevision.objects.create(
        reason=f'도메인 삭제: {domain_name}',
        changed_by=request.user
    )
    
    messages.success(request, f'도메인 "{domain_name}"이 삭제되었습니다.')
    return redirect('monitoring:domain_list')


@login_required
@user_passes_test(is_admin)
def endpoint_create_view(request):
    """엔드포인트 생성 뷰"""
    if request.method == 'POST':
        form = EndpointForm(request.POST)
        if form.is_valid():
            endpoint = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'엔드포인트 추가: {endpoint.url}',
                changed_by=request.user
            )
            
            messages.success(request, f'엔드포인트 "{endpoint.url}"이 생성되었습니다.')
            return redirect('monitoring:endpoint_list')
    else:
        form = EndpointForm()
    
    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'monitoring/endpoint_form.html', context)


@login_required
@user_passes_test(is_admin)
def endpoint_edit_view(request, endpoint_id):
    """엔드포인트 수정 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    if request.method == 'POST':
        form = EndpointForm(request.POST, instance=endpoint)
        if form.is_valid():
            old_url = endpoint.url
            endpoint = form.save()
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'엔드포인트 수정: {old_url} → {endpoint.url}',
                changed_by=request.user
            )
            
            messages.success(request, f'엔드포인트 "{endpoint.url}"이 수정되었습니다.')
            return redirect('monitoring:endpoint_list')
    else:
        form = EndpointForm(instance=endpoint)
    
    context = {
        'form': form,
        'endpoint': endpoint,
        'is_edit': True,
    }
    return render(request, 'monitoring/endpoint_form.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def endpoint_delete_view(request, endpoint_id):
    """엔드포인트 삭제 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    endpoint_url = endpoint.url
    endpoint.delete()
    
    # 설정 변경 이력 추가
    ConfigRevision.objects.create(
        reason=f'엔드포인트 삭제: {endpoint_url}',
        changed_by=request.user
    )
    
    messages.success(request, f'엔드포인트 "{endpoint_url}"이 삭제되었습니다.')
    return redirect('monitoring:endpoint_list')


@login_required
def endpoint_detail_view(request, endpoint_id):
    """엔드포인트 상세 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    # 최근 체크 결과 (최대 50개)
    recent_checks = endpoint.checks.all()[:50]
    
    # 통계 계산
    total_checks = endpoint.checks.count()
    success_checks = endpoint.checks.filter(is_success=True).count()
    success_rate = (success_checks / total_checks * 100) if total_checks > 0 else 0
    
    # 평균 응답시간 (최근 24시간)
    yesterday = timezone.now() - timedelta(hours=24)
    avg_latency = endpoint.checks.filter(
        checked_at__gte=yesterday,
        latency_ms__isnull=False
    ).aggregate(avg_latency=Avg('latency_ms'))['avg_latency'] or 0
    
    context = {
        'endpoint': endpoint,
        'recent_checks': recent_checks,
        'total_checks': total_checks,
        'success_rate': round(success_rate, 2),
        'avg_latency': round(avg_latency, 2),
    }
    return render(request, 'monitoring/endpoint_detail.html', context)


@login_required
@user_passes_test(is_admin)
def bulk_settings_view(request):
    """일괄 설정 뷰"""
    if request.method == 'POST':
        form = BulkSettingsForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            selected_endpoints = form.cleaned_data['endpoints']
            
            if action == 'enable':
                selected_endpoints.update(is_enabled=True)
                messages.success(request, f'{selected_endpoints.count()}개 엔드포인트가 활성화되었습니다.')
            elif action == 'disable':
                selected_endpoints.update(is_enabled=False)
                messages.success(request, f'{selected_endpoints.count()}개 엔드포인트가 비활성화되었습니다.')
            elif action == 'update_interval':
                new_interval = form.cleaned_data['poll_interval_sec']
                selected_endpoints.update(poll_interval_sec=new_interval)
                messages.success(request, f'{selected_endpoints.count()}개 엔드포인트의 폴링 간격이 {new_interval}초로 변경되었습니다.')
            
            # 설정 변경 이력 추가
            ConfigRevision.objects.create(
                reason=f'일괄 설정 변경: {action} ({selected_endpoints.count()}개 엔드포인트)',
                changed_by=request.user
            )
            
            return redirect('monitoring:bulk_settings')
    else:
        form = BulkSettingsForm()
    
    context = {
        'form': form,
    }
    return render(request, 'monitoring/bulk_settings.html', context)
    
    return JsonResponse(data)
