import os
import sys
import django
import pytz
from datetime import datetime, timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
sys.path.append('D:/MyRepos/SVCMON/webapp')
django.setup()

from django.utils import timezone
from monitoring.models import Endpoint

def analyze_database_times():
    """데이터베이스 시간 저장 방식 분석"""
    print("=== 데이터베이스 시간 저장 방식 분석 ===")
    
    current_time = timezone.now()
    print(f"현재 시간 (Django timezone.now()): {current_time}")
    
    endpoint = Endpoint.objects.filter(is_enabled=True).first()
    if endpoint:
        latest_check = endpoint.checks.first()
        if latest_check:
            print(f"\n--- 데이터베이스 저장 시간 분석 ---")
            print(f"저장된 시간: {latest_check.checked_at}")
            print(f"저장된 시간 타입: {type(latest_check.checked_at)}")
            print(f"저장된 시간 timezone: {latest_check.checked_at.tzinfo}")
            
            # 직접 시간 차이 계산 (Django 방식)
            time_diff = current_time - latest_check.checked_at
            print(f"Django 직접 계산 시간 차이: {time_diff.total_seconds()}초")
            
            # 예상 다음 체크 시간 (Django 방식)
            expected_next = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
            print(f"예상 다음 체크 시간 (Django): {expected_next}")
            
            # 상태 판정 (Django 방식)
            if current_time > expected_next:
                django_status = 'AMBER'
            elif latest_check.status_code and 200 <= latest_check.status_code < 300:
                django_status = 'GREEN'
            else:
                django_status = 'RED'
            print(f"Django 방식 상태: {django_status}")
            
            print(f"\n--- 기존 함수와 비교 ---")
            # 기존 함수 방식
            kst = pytz.timezone('Asia/Seoul')
            stored_time_utc = latest_check.checked_at.replace(tzinfo=None)
            kst_time = kst.localize(stored_time_utc)
            actual_utc_time = kst_time.astimezone(pytz.UTC)
            
            old_time_diff = current_time - actual_utc_time
            old_expected_next = actual_utc_time + timedelta(seconds=endpoint.poll_interval_sec)
            
            print(f"기존 방식 변환 시간: {actual_utc_time}")
            print(f"기존 방식 시간 차이: {old_time_diff.total_seconds()}초")
            print(f"기존 방식 예상 다음 체크: {old_expected_next}")
            
            if current_time > old_expected_next:
                old_status = 'AMBER'
            elif latest_check.status_code and 200 <= latest_check.status_code < 300:
                old_status = 'GREEN'
            else:
                old_status = 'RED'
            print(f"기존 방식 상태: {old_status}")

if __name__ == "__main__":
    analyze_database_times()
