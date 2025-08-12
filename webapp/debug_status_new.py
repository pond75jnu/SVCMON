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

print("=== 상태 계산 디버깅 ===")

current_time = timezone.now()
print(f"현재 시간 (Django timezone.now()): {current_time}")
print(f"현재 시간 (로컬): {timezone.localtime(current_time)}")
print()

endpoints = Endpoint.objects.filter(is_enabled=True)
print(f"활성화된 엔드포인트 수: {endpoints.count()}")
print()

for endpoint in endpoints:
    print(f"엔드포인트: {endpoint.url}")
    print(f"호출주기: {endpoint.poll_interval_sec}초")
    
    latest_check = endpoint.checks.first()
    if latest_check:
        print(f"최근 체크 시간 (DB): {latest_check.checked_at}")
        print(f"최근 체크 시간 (로컬): {timezone.localtime(latest_check.checked_at)}")
        
        # 예상 다음 체크 시간
        expected_next_check = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
        print(f"예상 다음 체크: {expected_next_check}")
        print(f"예상 다음 체크 (로컬): {timezone.localtime(expected_next_check)}")
        
        # 시간 차이 계산
        time_diff = current_time - latest_check.checked_at
        print(f"경과 시간: {time_diff}")
        print(f"경과 시간 (초): {time_diff.total_seconds()}")
        
        # 조건 확인
        is_overdue = current_time > expected_next_check
        print(f"호출주기 초과 여부: {is_overdue}")
        print(f"조건: {current_time} > {expected_next_check}")
        
        # 상태 판정
        if is_overdue:
            status = 'AMBER (신호없음)'
        elif (latest_check.status_code and 
              200 <= latest_check.status_code < 300 and 
              not latest_check.error):
            status = 'GREEN (정상)'
        else:
            status = 'RED (장애)'
        
        print(f"판정 상태: {status}")
        print(f"HTTP 상태코드: {latest_check.status_code}")
        print(f"에러: {latest_check.error if latest_check.error else 'None'}")
    else:
        print("체크 이력 없음 → AMBER")
    
    print("=" * 60)
