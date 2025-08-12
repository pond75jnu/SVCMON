#!/usr/bin/env python
"""
상태 계산 로직 디버그 스크립트
"""
import os
import sys
import django
from datetime import timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from monitoring.models import NetworkGroup, Endpoint, Check

def debug_endpoint_status():
    """엔드포인트 상태 디버그"""
    current_time = timezone.now()
    print(f"=== 상태 계산 디버그 ({current_time}) ===\n")
    
    # 교내망 네트워크 그룹 찾기
    try:
        network_group = NetworkGroup.objects.get(name='교내망')
        print(f"네트워크 그룹: {network_group.name}")
    except NetworkGroup.DoesNotExist:
        print("교내망 네트워크 그룹을 찾을 수 없습니다.")
        return
    
    # 교내망의 모든 엔드포인트 확인
    endpoints = Endpoint.objects.filter(
        domain__network_group=network_group,
        is_enabled=True
    )
    
    print(f"활성화된 엔드포인트 수: {endpoints.count()}\n")
    
    for endpoint in endpoints:
        print(f"--- 엔드포인트: {endpoint.url} ---")
        print(f"폴링 간격: {endpoint.poll_interval_sec}초")
        
        latest_check = endpoint.checks.first()
        
        if latest_check:
            print(f"마지막 체크 시간: {latest_check.checked_at}")
            print(f"마지막 상태 코드: {latest_check.status_code}")
            print(f"마지막 오류: {latest_check.error}")
            
            # 예상 다음 체크 시간
            expected_next_check = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
            print(f"예상 다음 체크 시간: {expected_next_check}")
            
            # 현재 시간과 비교
            time_diff = (current_time - expected_next_check).total_seconds()
            print(f"예상 시간과의 차이: {time_diff:.1f}초")
            
            # 상태 계산
            if current_time > expected_next_check:
                status = 'AMBER'
                print(f"상태: AMBER (폴링 간격 초과)")
            elif (latest_check.status_code and 
                  200 <= latest_check.status_code < 300 and 
                  not latest_check.error):
                status = 'GREEN'
                print(f"상태: GREEN (정상)")
            else:
                status = 'RED'
                print(f"상태: RED (오류)")
        else:
            status = 'AMBER'
            print("체크 이력 없음")
            print("상태: AMBER")
        
        print(f"최종 상태: {status}\n")

if __name__ == "__main__":
    debug_endpoint_status()
