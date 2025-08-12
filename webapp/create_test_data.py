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

def create_test_data():
    """테스트용 오래된 체크 데이터 생성"""
    print("=== 테스트 데이터 생성 ===")
    
    # 첫 번째 엔드포인트에 오래된 체크 추가
    endpoint = Endpoint.objects.filter(is_enabled=True).first()
    if endpoint:
        # 2분 전 체크 생성 (30초 주기이므로 AMBER가 되어야 함)
        old_time = timezone.now() - timedelta(minutes=2)
        
        check = Check.objects.create(
            endpoint=endpoint,
            checked_at=old_time,
            status_code=200,
            latency_ms=100,
            error=None
        )
        
        print(f"테스트 체크 생성됨:")
        print(f"엔드포인트: {endpoint.url}")
        print(f"체크 시간: {old_time}")
        print(f"호출주기: {endpoint.poll_interval_sec}초")
        print()
        
        # 상태 확인
        current_time = timezone.now()
        expected_next_check = old_time + timedelta(seconds=endpoint.poll_interval_sec)
        
        print(f"현재 시간: {current_time}")
        print(f"예상 다음 체크: {expected_next_check}")
        print(f"신호없음 조건: {current_time > expected_next_check}")
        
        if current_time > expected_next_check:
            print("결과: AMBER (신호없음) - 호출주기 로직 정상 작동!")
        else:
            print("결과: GREEN - 아직 신호 대기 시간 내")

if __name__ == "__main__":
    create_test_data()
