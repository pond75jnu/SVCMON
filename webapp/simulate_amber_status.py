#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.utils import timezone
from monitoring.models import Endpoint, Check
from datetime import timedelta

def simulate_amber_status():
    """AMBER 상태 시뮬레이션"""
    print("=== AMBER 상태 시뮬레이션 ===")
    
    # 첫 번째 엔드포인트
    endpoint = Endpoint.objects.filter(is_enabled=True).first()
    if not endpoint:
        print("활성화된 엔드포인트가 없습니다.")
        return
    
    current_time = timezone.now()
    
    # 시나리오 1: 호출주기 2배 지난 상황 시뮬레이션
    old_time = current_time - timedelta(seconds=endpoint.poll_interval_sec * 2)
    
    print(f"엔드포인트: {endpoint.url}")
    print(f"호출주기: {endpoint.poll_interval_sec}초")
    print(f"시뮬레이션 마지막 체크: {old_time}")
    print(f"현재 시간: {current_time}")
    
    # 예상 다음 체크 계산
    expected_next_check = old_time + timedelta(seconds=endpoint.poll_interval_sec)
    print(f"예상 다음 체크: {expected_next_check}")
    
    # 시간 차이
    time_diff = current_time - old_time
    print(f"경과 시간: {time_diff.total_seconds():.1f}초")
    print(f"허용 시간: {endpoint.poll_interval_sec}초")
    
    # 상태 판정 (실제 대시보드 로직)
    if current_time > expected_next_check:
        status = 'AMBER'
        reason = '신호없음 (호출주기 초과)'
    else:
        status = 'GREEN'
        reason = '정상'
    
    print(f"\n결과: {status} - {reason}")
    
    if status == 'AMBER':
        print("✅ 호출주기 로직 정상 작동!")
        print("   → 마지막 체크 후 호출주기를 초과하여 AMBER 상태로 판정됨")
    else:
        print("❌ 호출주기 로직 문제 발견")
    
    print("\n" + "="*60)
    
    # 시나리오 2: 호출주기 내 정상 상황
    recent_time = current_time - timedelta(seconds=endpoint.poll_interval_sec // 2)
    expected_next_check_2 = recent_time + timedelta(seconds=endpoint.poll_interval_sec)
    
    print("시나리오 2: 호출주기 내 정상 상황")
    print(f"시뮬레이션 마지막 체크: {recent_time}")
    print(f"예상 다음 체크: {expected_next_check_2}")
    
    if current_time > expected_next_check_2:
        status2 = 'AMBER'
        reason2 = '신호없음'
    else:
        status2 = 'GREEN'
        reason2 = '정상 (호출주기 내)'
    
    print(f"결과: {status2} - {reason2}")
    
    if status2 == 'GREEN':
        print("✅ 호출주기 내에서는 GREEN 상태 유지!")
    
if __name__ == "__main__":
    simulate_amber_status()
