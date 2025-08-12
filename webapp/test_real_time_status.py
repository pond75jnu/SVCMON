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

def test_real_time_status():
    """실시간 상태 변화 테스트"""
    print("=== 실시간 상태 변화 테스트 ===")
    
    current_time = timezone.now()
    print(f"현재 시간: {current_time}")
    print(f"현재 시간 (로컬): {timezone.localtime(current_time)}")
    print()
    
    for endpoint in Endpoint.objects.filter(is_enabled=True):
        print(f"엔드포인트: {endpoint.url}")
        print(f"호출주기: {endpoint.poll_interval_sec}초")
        
        latest_check = endpoint.checks.first()
        if latest_check:
            # 시간 보정 적용
            corrected_check_time = latest_check.checked_at - timedelta(hours=9)
            
            print(f"최근 체크 (원본): {latest_check.checked_at}")
            print(f"최근 체크 (보정): {corrected_check_time}")
            print(f"현재 시간과 차이: {(current_time - corrected_check_time).total_seconds():.1f}초")
            
            # 예상 다음 체크 계산
            expected_next_check = corrected_check_time + timedelta(seconds=endpoint.poll_interval_sec)
            print(f"예상 다음 체크: {expected_next_check}")
            
            # 상태 판정
            if current_time > expected_next_check:
                status = 'AMBER'
                time_overdue = (current_time - expected_next_check).total_seconds()
                print(f"상태: {status} (호출주기 {time_overdue:.1f}초 초과)")
            elif (latest_check.status_code and 
                  200 <= latest_check.status_code < 300 and 
                  not latest_check.error):
                status = 'GREEN'
                print(f"상태: {status} (정상)")
            else:
                status = 'RED'
                print(f"상태: {status} (오류)")
            
            print(f"HTTP 상태코드: {latest_check.status_code}")
            print(f"에러: {latest_check.error if latest_check.error else 'None'}")
        else:
            status = 'AMBER'
            print("상태: AMBER (체크 이력 없음)")
        
        print("-" * 50)
    
    print("\n=== 시나리오 테스트 ===")
    print("1. 콘솔 서비스 중단 상황 → 모든 URL이 AMBER가 되어야 함")
    print("2. 콘솔 서비스 재시작 → 새로운 체크 결과에 따라 GREEN/RED로 변경")
    print("3. 실시간 업데이트 → 30초마다 자동 갱신")

if __name__ == "__main__":
    test_real_time_status()
