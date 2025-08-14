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
        # status_code가 'N/A'인 경우 AMBER로 처리
        if latest_check.status_code == 'N/A':
            return 'AMBER'
            
        # 저장된 시간이 실제로는 KST 시간인데 UTC timezone으로 잘못 저장되어 있음
        # 이를 올바르게 처리하기 위해 9시간을 빼서 실제 UTC 시간으로 변환
        
        # 방법: 저장된 시간에서 9시간을 빼서 실제 UTC 시간으로 변환
        actual_utc_time = latest_check.checked_at - timedelta(hours=9)
        
        # 호출주기 기반으로 신호 없음 판단
        expected_next_check = actual_utc_time + timedelta(seconds=endpoint.poll_interval_sec)
        
        # 현재 시간과 비교 (둘 다 UTC)
        if current_time > expected_next_check:
            # 호출주기를 넘어서면 신호없음 (AMBER)
            return 'AMBER'
        elif (latest_check.status_code and 
              latest_check.status_code != 'N/A' and
              latest_check.status_code.isdigit() and
              200 <= int(latest_check.status_code) < 300 and 
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
    
    # 차트용 데이터 (최신 10개) - 명시적으로 정렬
    chart_checks = endpoint.checks.order_by('-checked_at')[:10]
    
    # 페이징 처리를 위한 체크 데이터 - 시간대 필터 제거
    all_checks = endpoint.checks.order_by('-checked_at')
    
    # 페이징 처리 (페이지당 5개)
    paginator = Paginator(all_checks, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 현재 상태 계산
    current_time = timezone.now()
    current_status = calculate_endpoint_status(endpoint, current_time)
    
    # 최신 체크 정보 (AMBER 상태 처리용)
    latest_check = endpoint.checks.first()
    
    context = {
        'endpoint': endpoint,
        'chart_checks': chart_checks,  # 차트용 데이터
        'page_obj': page_obj,  # 페이징된 체크 데이터
        'current_status': current_status,  # 현재 상태 (GREEN/AMBER/RED)
        'latest_check': latest_check,  # 최신 체크 정보
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
    from datetime import timedelta
    
    endpoint = get_object_or_404(Endpoint, id=endpoint_id)
    
    # 디버그: 데이터베이스 연결 강제 새로고침
    from django.db import connection
    connection.close()
    
    # 디버그: raw SQL로 실제 최신 데이터 확인
    with connection.cursor() as cursor:
        cursor.execute("SELECT TOP 3 checked_at, status_code FROM [dbo].[checks] WHERE endpoint_id = %s ORDER BY checked_at DESC", [endpoint_id])
        raw_results = cursor.fetchall()
        print(f"[DEBUG] Raw SQL 결과 (endpoint {endpoint_id}): {raw_results}")
    
    # 차트용 데이터 - Raw SQL로 직접 가져오기 (캐시 문제 해결)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TOP 10 
                id, checked_at, status_code, latency_ms, error
            FROM [dbo].[checks] 
            WHERE endpoint_id = %s 
            ORDER BY checked_at DESC
        """, [endpoint_id])
        raw_chart_data = cursor.fetchall()
        print(f"[DEBUG] Raw SQL 차트 데이터 (최신 3개): {raw_chart_data[:3]}")
    
    # Raw 데이터를 Django 객체처럼 변환
    class MockCheck:
        def __init__(self, id, checked_at, status_code, latency_ms, error):
            self.id = id
            self.checked_at = checked_at
            self.status_code = status_code
            self.latency_ms = latency_ms
            self.error = error
    
    chart_checks = [MockCheck(*row) for row in raw_chart_data]
    
    # 현재 상태 계산
    current_time = timezone.now()
    latest_check = endpoint.checks.first()
    status = calculate_endpoint_status(endpoint, current_time)
    
    # 차트 데이터 생성 - 단순히 실제 체크 기록만 반환 (AMBER 레코드 포함)
    chart_data = []
    max_points = 10
    
    if chart_checks:
        # 실제 체크 기록을 시간순으로 정렬 (오래된 것부터)
        sorted_checks = list(reversed(chart_checks[:max_points]))
        
        for check in sorted_checks:
            # AMBER나 N/A 레코드도 latency 0으로 차트에 표시 (시각적 구분을 위해)
            latency_value = check.latency_ms if check.latency_ms is not None else 0
            
            # 모든 체크 데이터 추가 (AMBER 레코드 포함)
            chart_data.append({
                'time': check.checked_at.strftime('%m-%d %H:%M:%S'),
                'latency': latency_value,
                'status': check.status_code,
                'success': (check.status_code == '200' or 
                           (check.status_code and check.status_code != 'N/A' and check.status_code != 'AMBER' and check.status_code.isdigit() and 
                            200 <= int(check.status_code) < 300)) if check.status_code else False
            })
    
    # 체크 기록 데이터 (페이지네이션용) - 최근 100개로 제한
    page = request.GET.get('page', 1)
    recent_checks = endpoint.checks.order_by('-checked_at')[:100]
    paginator = Paginator(recent_checks, 5)
    page_obj = paginator.get_page(page)
    
    check_records = []
    
    # 기존 체크 기록들 추가
    for check in page_obj.object_list:
        if (check.status_code and check.status_code != 'N/A' and check.status_code != 'AMBER' and check.status_code.isdigit() and 
            200 <= int(check.status_code) < 300):
            record_status = 'GREEN'
        elif check.status_code == 'N/A' or check.status_code == 'AMBER' or check.status_code is None:
            record_status = 'AMBER'
        else:
            record_status = 'RED'
            
        check_records.append({
            'check_time': check.checked_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': record_status,
            'status_code': check.status_code,
            'latency_ms': check.latency_ms,
            'error_message': check.error or ''
        })
    
    data = {
        'current_status': status,
        'latest_latency': latest_check.latency_ms if latest_check and status != 'AMBER' else None,
        'latest_status_code': latest_check.status_code if latest_check and status != 'AMBER' else None,
        'chart_data': chart_data,
        'check_records': check_records,  # 항상 반환
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)
