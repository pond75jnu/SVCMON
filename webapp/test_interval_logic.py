#!/usr/bin/env python
import os
import sys
import django
from datetime import timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.utils import timezone
from monitoring.models import Endpoint, Check

def test_interval_logic():
    """호출주기 로직 테스트"""
    print("=== 호출주기 로직 테스트 ===")
    current_time = timezone.now()
    print(f"현재 시간 (UTC): {current_time}")
    print(f"현재 시간 (Local): {timezone.localtime(current_time)}")
    print()
    
    endpoints = Endpoint.objects.filter(is_enabled=True)[:5]  # 상위 5개만 테스트
    
    for endpoint in endpoints:
        print(f"엔드포인트: {endpoint.url}")
        print(f"호출주기: {endpoint.poll_interval_sec}초")
        
        latest_check = endpoint.checks.first()
        if latest_check:
            print(f"최근 체크 (UTC): {latest_check.checked_at}")
            print(f"최근 체크 (Local): {timezone.localtime(latest_check.checked_at)}")
            
            # 예상 다음 체크 시간
            expected_next_check = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
            print(f"예상 다음 체크 (UTC): {expected_next_check}")
            print(f"예상 다음 체크 (Local): {timezone.localtime(expected_next_check)}")
            
            # 시간 차이
            time_diff = current_time - latest_check.checked_at
            print(f"경과 시간: {time_diff}")
            print(f"경과 시간 (초): {time_diff.total_seconds()}")
            
            # 상태 판단
            if current_time > expected_next_check:
                status = 'AMBER (신호없음)'
                print(f"신호없음 조건: 현재시간({current_time}) > 예상체크시간({expected_next_check})")
            elif (latest_check.status_code and 
                  200 <= latest_check.status_code < 300 and 
                  not latest_check.error):
                status = 'GREEN (정상)'
            else:
                status = 'RED (장애)'
            
            print(f"현재 상태: {status}")
            print(f"HTTP 상태코드: {latest_check.status_code}")
            print(f"에러: {latest_check.error if latest_check.error else 'None'}")
        else:
            print("체크 이력 없음 - AMBER")
        
        print("-" * 50)

if __name__ == "__main__":
    test_interval_logic()
