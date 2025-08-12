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

def verify_polling_logic():
    """실제 대시보드에서 사용되는 로직과 동일한 방식으로 검증"""
    print("=== 실제 대시보드 로직 검증 ===")
    current_time = timezone.now()
    print(f"검증 시간: {current_time}")
    print()
    
    endpoints = Endpoint.objects.filter(is_enabled=True)[:10]
    
    for endpoint in endpoints:
        print(f"엔드포인트: {endpoint.url}")
        print(f"호출주기: {endpoint.poll_interval_sec}초")
        
        # 실제 대시보드 코드와 동일한 로직
        latest_check = endpoint.checks.first()
        
        if latest_check:
            # 예상 다음 체크 시간 계산
            expected_next_check = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
            
            print(f"최근 체크: {latest_check.checked_at}")
            print(f"예상 다음 체크: {expected_next_check}")
            
            # 상태 판단 로직 (views.py와 동일)
            if current_time > expected_next_check:
                status = 'AMBER'
                reason = '신호없음'
            elif (latest_check.status_code and 
                  200 <= latest_check.status_code < 300 and 
                  not latest_check.error):
                status = 'GREEN'
                reason = '정상'
            elif latest_check.status_code and 300 <= latest_check.status_code < 400:
                status = 'AMBER'
                reason = f'리다이렉션 ({latest_check.status_code})'
            else:
                status = 'RED'
                reason = f'장애 ({latest_check.status_code or "오류"})'
            
            print(f"판정 상태: {status} - {reason}")
            
            # 시간 차이 분석
            time_diff = current_time - latest_check.checked_at
            print(f"경과시간: {time_diff.total_seconds():.1f}초")
            print(f"허용시간: {endpoint.poll_interval_sec}초")
            
            if time_diff.total_seconds() > endpoint.poll_interval_sec:
                print(">>> 호출주기 초과 - AMBER 상태 적용됨")
            else:
                print(">>> 호출주기 내 - HTTP 상태코드 기준 판정")
        else:
            print("체크 이력 없음 - AMBER")
        
        print("-" * 60)

if __name__ == "__main__":
    verify_polling_logic()
