from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from monitoring.models import NetworkGroup, Domain, Endpoint, Check, Rollup
from accounts.models import User


def calculate_endpoint_status(endpoint, current_time):
    """엔드포인트 상태 계산"""
    import pytz
    
    latest_check = endpoint.checks.first()
    
    if latest_check:
        # 저장된 시간이 UTC로 표시되어 있지만 실제로는 KST 시간이므로 보정
        # 저장된 시간을 naive datetime으로 변환 후 KST로 해석
        kst = pytz.timezone('Asia/Seoul')
        
        # timezone 정보 제거 후 KST로 해석
        naive_check_time = latest_check.checked_at.replace(tzinfo=None)
        kst_check_time = kst.localize(naive_check_time)
        
        # 호출주기 기반으로 신호 없음 판단
        expected_next_check = kst_check_time + timedelta(seconds=endpoint.poll_interval_sec)
        
        # 현재 시간을 KST로 변환하여 비교
        current_kst = current_time.astimezone(kst)
        
        if current_kst > expected_next_check:
            # 호출주기를 넘어서면 신호없음 (AMBER)
            return 'AMBER'
        elif (latest_check.status_code and 
              200 <= latest_check.status_code < 300 and 
              not latest_check.error):
            # 성공 조건: 상태코드가 200-299이고 에러가 없는 경우
            return 'GREEN'
        else:
            # 체크는 있지만 실패한 경우
            return 'RED'
    else:
        # 체크 이력이 없는 경우
        return 'AMBER'


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
        
        current_time = timezone.now()
        
        for endpoint in endpoints:
            status = calculate_endpoint_status(endpoint, current_time)
            
            if status == 'RED':
                red_count += 1
            elif status == 'AMBER':
                amber_count += 1
            else:  # GREEN
                green_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        # 등록된 엔드포인트가 없는 경우 AMBER로 표시
        if total_endpoints == 0:
            status = 'AMBER'
        elif red_count > 0:
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
    current_time = timezone.now()
    
    for domain in domains:
        # 해당 도메인의 모든 엔드포인트
        endpoints = domain.endpoints.filter(is_enabled=True)
        
        # 상태 계산
        total_endpoints = endpoints.count()
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for endpoint in endpoints:
            status = calculate_endpoint_status(endpoint, current_time)
            
            if status == 'RED':
                red_count += 1
            elif status == 'AMBER':
                amber_count += 1
            else:  # GREEN
                green_count += 1
        
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
    current_time = timezone.now()
    
    for endpoint in endpoints:
        status = calculate_endpoint_status(endpoint, current_time)
        latest_check = endpoint.checks.first()
        
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
    
    # 차트용 데이터 (최신 10개)
    chart_checks = endpoint.checks.all()[:10]
    
    # 페이징 처리를 위한 전체 체크 데이터
    all_checks = endpoint.checks.all()
    
    # 페이징 처리 (페이지당 5개)
    paginator = Paginator(all_checks, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'endpoint': endpoint,
        'chart_checks': chart_checks,  # 차트용 데이터
        'page_obj': page_obj,  # 페이징된 체크 데이터
    }
    return render(request, 'dashboard/endpoint_chart.html', context)


@csrf_exempt
def dashboard_api_view(request):
    """대시보드 API (실시간 상태 업데이트용)"""
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
        
        current_time = timezone.now()
        
        for endpoint in endpoints:
            status = calculate_endpoint_status(endpoint, current_time)
            
            if status == 'RED':
                red_count += 1
            elif status == 'AMBER':
                amber_count += 1
            else:  # GREEN
                green_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        if total_endpoints == 0:
            status = 'AMBER'
        elif red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        network_status.append({
            'id': ng.id,
            'name': ng.name,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    # 전체 통계
    total_endpoints = Endpoint.objects.filter(is_enabled=True).count()
    total_red = sum(ns['red_count'] for ns in network_status)
    total_amber = sum(ns['amber_count'] for ns in network_status)
    total_green = sum(ns['green_count'] for ns in network_status)

    data = {
        'network_groups': network_status,
        'total_endpoints': total_endpoints,
        'red_count': total_red,
        'amber_count': total_amber,
        'green_count': total_green,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@csrf_exempt
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
    
    current_time = timezone.now()
    
    for endpoint in endpoints:
        status = calculate_endpoint_status(endpoint, current_time)
        
        if status == 'RED':
            red_count += 1
        elif status == 'AMBER':
            amber_count += 1
        else:  # GREEN
            green_count += 1
    
    # 우선순위: RED > AMBER > GREEN
    # 등록된 엔드포인트가 없는 경우 AMBER로 표시
    total_endpoints = endpoints.count()
    if total_endpoints == 0:
        status = 'AMBER'
    elif red_count > 0:
        status = 'RED'
    elif amber_count > 0:
        status = 'AMBER'
    else:
        status = 'GREEN'
    
    data = {
        'network_group_id': network_group_id,
        'name': network_group.name,
        'status': status,
        'total_endpoints': total_endpoints,
        'red_count': red_count,
        'amber_count': amber_count,
        'green_count': green_count,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@csrf_exempt
def all_networks_status_api_view(request):
    """모든 망구분 상태 API (실시간 업데이트용)"""
    network_groups = NetworkGroup.objects.all()
    network_status = []
    
    current_time = timezone.now()
    
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
            status = calculate_endpoint_status(endpoint, current_time)
            
            if status == 'RED':
                red_count += 1
            elif status == 'AMBER':
                amber_count += 1
            else:  # GREEN
                green_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        # 등록된 엔드포인트가 없는 경우 AMBER로 표시
        if total_endpoints == 0:
            status = 'AMBER'
        elif red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        network_status.append({
            'network_group_id': ng.id,
            'name': ng.name,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    data = {
        'network_status': network_status,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@csrf_exempt
def network_detail_api_view(request, network_group_id):
    """망구분 상세 API (실시간 업데이트용)"""
    network_group = get_object_or_404(NetworkGroup, id=network_group_id)
    domains = network_group.domains.all()
    
    domain_status = []
    current_time = timezone.now()
    
    for domain in domains:
        # 해당 도메인의 모든 엔드포인트
        endpoints = domain.endpoints.filter(is_enabled=True)
        
        # 상태 계산
        total_endpoints = endpoints.count()
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for endpoint in endpoints:
            status = calculate_endpoint_status(endpoint, current_time)
            
            if status == 'RED':
                red_count += 1
            elif status == 'AMBER':
                amber_count += 1
            else:  # GREEN
                green_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        if total_endpoints == 0:
            status = 'AMBER'
        elif red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        domain_status.append({
            'domain_id': domain.id,
            'name': domain.site_name,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    data = {
        'network_group_id': network_group_id,
        'network_group_name': network_group.name,
        'domain_status': domain_status,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@csrf_exempt
def domain_detail_api_view(request, domain_id):
    """도메인 상세 API (실시간 업데이트용)"""
    domain = get_object_or_404(Domain, id=domain_id)
    endpoints = domain.endpoints.filter(is_enabled=True)
    
    endpoint_status = []
    current_time = timezone.now()
    
    for endpoint in endpoints:
        status = calculate_endpoint_status(endpoint, current_time)
        latest_check = endpoint.checks.first()
        
        endpoint_status.append({
            'endpoint_id': endpoint.id,
            'url': endpoint.url,
            'status': status,
            'latest_check': {
                'checked_at': latest_check.checked_at.isoformat() if latest_check else None,
                'status_code': latest_check.status_code if latest_check else None,
                'latency_ms': latest_check.latency_ms if latest_check else None,
                'error': latest_check.error if latest_check else None,
            } if latest_check else None,
        })
    
    data = {
        'domain_id': domain_id,
        'domain_name': domain.site_name,
        'endpoint_status': endpoint_status,
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


@csrf_exempt
def endpoint_chart_api_view(request, endpoint_id):
    """엔드포인트 차트 API (실시간 업데이트용)"""
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    # 차트용 데이터 (최근 10개만)
    chart_checks = endpoint.checks.all()[:10]
    
    # 현재 상태 계산
    current_time = timezone.now()
    latest_check = endpoint.checks.first()
    status = calculate_endpoint_status(endpoint, current_time)
    
    # 차트 데이터 포맷 (JavaScript에서 사용할 형식)
    chart_data = []
    for check in reversed(chart_checks):  # 시간순 정렬
        chart_data.append({
            'time': check.checked_at.strftime('%m-%d %H:%M'),
            'latency': check.latency_ms or 0,
            'status': check.status_code or 0,
            'success': check.status_code == 200 if check.status_code else False
        })
    
    # 체크 기록 데이터 (페이지네이션용)
    page = request.GET.get('page', 1)
    paginator = Paginator(chart_checks, 5)
    page_obj = paginator.get_page(page)
    
    check_records = []
    for check in page_obj.object_list:
        if check.status_code == 200:
            record_status = 'GREEN'
        else:
            record_status = 'RED'
            
        check_records.append({
            'check_time': check.checked_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': record_status,
            'latency_ms': check.latency_ms,
            'error_message': check.error or ''
        })
    
    data = {
        'current_status': status,
        'latest_latency': latest_check.latency_ms if latest_check else None,
        'latest_status_code': latest_check.status_code if latest_check else None,
        'chart_data': chart_data,
        'check_records': check_records if str(page) == '1' else None,  # 첫 페이지만
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)
