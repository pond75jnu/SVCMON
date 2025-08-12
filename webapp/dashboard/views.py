from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from monitoring.models import NetworkGroup, Domain, Endpoint, Check, Rollup
from accounts.models import User


@login_required
def home_view(request):
    """대시보드 홈 뷰"""
    # 망구분별 상태 집계
    network_groups = NetworkGroup.objects.all()
    network_status = []
    
    for ng in network_groups:
        # 해당 망구분의 모든 엔드포인트
        endpoints = Endpoint.objects.filter(
            domain__network_group=ng,
            is_enabled=True
        )
        
        # 상태 계산
        total_endpoints = endpoints.count()
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for endpoint in endpoints:
            latest_check = endpoint.checks.first()
            if latest_check:
                # 성공 조건: 상태코드가 200-299이고 에러가 없는 경우
                if (latest_check.status_code and 
                    200 <= latest_check.status_code < 300 and 
                    not latest_check.error):
                    green_count += 1
                else:
                    red_count += 1
            else:
                amber_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        if red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        network_status.append({
            'network_group': ng,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    # 전체 통계
    total_endpoints = Endpoint.objects.filter(is_enabled=True).count()
    total_users = User.objects.filter(is_active=True).count()
    pending_users = User.objects.filter(is_active=False).count()
    
    context = {
        'network_status': network_status,
        'total_endpoints': total_endpoints,
        'total_users': total_users,
        'pending_users': pending_users,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def network_detail_view(request, network_group_id):
    """망구분 상세 뷰 (도메인 목록)"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    domains = network_group.domains.all()
    
    domain_status = []
    for domain in domains:
        # 해당 도메인의 모든 엔드포인트
        endpoints = domain.endpoints.filter(is_enabled=True)
        
        # 상태 계산
        total_endpoints = endpoints.count()
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for endpoint in endpoints:
            latest_check = endpoint.checks.first()
            if latest_check:
                # 성공 조건: 상태코드가 200-299이고 에러가 없는 경우
                if (latest_check.status_code and 
                    200 <= latest_check.status_code < 300 and 
                    not latest_check.error):
                    green_count += 1
                else:
                    red_count += 1
            else:
                amber_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        if red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        domain_status.append({
            'domain': domain,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    context = {
        'network_group': network_group,
        'domain_status': domain_status,
    }
    return render(request, 'dashboard/network_detail.html', context)


@login_required
def domain_detail_view(request, domain_id):
    """도메인 상세 뷰 (엔드포인트 목록)"""
    domain = get_object_or_404(Domain, id=domain_id)
    endpoints = domain.endpoints.filter(is_enabled=True)
    
    endpoint_status = []
    for endpoint in endpoints:
        latest_check = endpoint.checks.first()
        
        if latest_check:
            # 성공 조건: 상태코드가 200-299이고 에러가 없는 경우
            if (latest_check.status_code and 
                200 <= latest_check.status_code < 300 and 
                not latest_check.error):
                status = 'GREEN'
            else:
                status = 'RED'
        else:
            status = 'AMBER'
        
        endpoint_status.append({
            'endpoint': endpoint,
            'latest_check': latest_check,
            'status': status,
        })
    
    context = {
        'domain': domain,
        'endpoint_status': endpoint_status,
    }
    return render(request, 'dashboard/domain_detail.html', context)


@login_required
def endpoint_chart_view(request, endpoint_id):
    """엔드포인트 차트 뷰"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    recent_checks = endpoint.checks.all()[:10]
    
    context = {
        'endpoint': endpoint,
        'recent_checks': recent_checks,
    }
    return render(request, 'dashboard/endpoint_chart.html', context)


@login_required
def dashboard_api_view(request):
    """대시보드 API (실시간 상태 업데이트용)"""
    # 전체 통계
    total_endpoints = Endpoint.objects.filter(is_enabled=True).count()
    
    # 상태별 카운트
    red_count = 0
    amber_count = 0
    green_count = 0
    
    for endpoint in Endpoint.objects.filter(is_enabled=True):
        latest_check = endpoint.checks.first()
        if latest_check:
            if latest_check.is_success:
                green_count += 1
            else:
                red_count += 1
        else:
            amber_count += 1
    
    data = {
        'total_endpoints': total_endpoints,
        'red_count': red_count,
        'amber_count': amber_count,
        'green_count': green_count,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@login_required
def network_status_api_view(request, network_group_id):
    """망구분 상태 API"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    endpoints = Endpoint.objects.filter(
        domain__network_group=network_group,
        is_enabled=True
    )
    
    # 상태 계산
    red_count = 0
    amber_count = 0
    green_count = 0
    
    for endpoint in endpoints:
        latest_check = endpoint.checks.first()
        if latest_check:
            if latest_check.is_success:
                green_count += 1
            else:
                red_count += 1
        else:
            amber_count += 1
    
    # 우선순위: RED > AMBER > GREEN
    if red_count > 0:
        status = 'RED'
    elif amber_count > 0:
        status = 'AMBER'
    else:
        status = 'GREEN'
    
    data = {
        'network_group_id': network_group_id,
        'name': network_group.name,
        'status': status,
        'total_endpoints': endpoints.count(),
        'red_count': red_count,
        'amber_count': amber_count,
        'green_count': green_count,
    }
    
    return JsonResponse(data)
