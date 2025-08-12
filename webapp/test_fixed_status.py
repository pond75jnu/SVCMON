#!/usr/bin/env python
"""
수정된 상태 계산 로직 테스트
"""
import os
import sys
import django
from datetime import timedelta
import pytz

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from monitoring.models import NetworkGroup, Endpoint

def test_fixed_status_calculation():
    """수정된 상태 계산 로직 테스트"""
    from dashboard.views import calculate_endpoint_status
    
    current_time = timezone.now()
    kst = pytz.timezone('Asia/Seoul')
    current_kst = current_time.astimezone(kst)
    
    print(f"=== 수정된 상태 계산 테스트 ===")
    print(f"현재 UTC: {current_time}")
    print(f"현재 KST: {current_kst}")
    print()
    
    # 교내망 엔드포인트 확인
    network_group = NetworkGroup.objects.get(name='교내망')
    endpoints = Endpoint.objects.filter(
        domain__network_group=network_group,
        is_enabled=True
    )
    
    for endpoint in endpoints[:2]:  # 처음 2개만 테스트
        print(f"--- 엔드포인트: {endpoint.url} ---")
        print(f"폴링 간격: {endpoint.poll_interval_sec}초")
        
        latest_check = endpoint.checks.first()
        if latest_check:
            print(f"저장된 체크 시간: {latest_check.checked_at}")
            
            # 수정된 로직 적용
            naive_check_time = latest_check.checked_at.replace(tzinfo=None)
            kst_check_time = kst.localize(naive_check_time)
            print(f"KST로 해석된 체크 시간: {kst_check_time}")
            
            expected_next_check = kst_check_time + timedelta(seconds=endpoint.poll_interval_sec)
            print(f"예상 다음 체크 시간: {expected_next_check}")
            
            time_diff = (current_kst - expected_next_check).total_seconds()
            print(f"예상 시간과의 차이: {time_diff:.1f}초")
            
            # 상태 계산
            status = calculate_endpoint_status(endpoint, current_time)
            print(f"계산된 상태: {status}")
        
        print()

if __name__ == "__main__":
    test_fixed_status_calculation()
