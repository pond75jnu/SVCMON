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

def test_timezone_calculation():
    """시간대 계산 테스트"""
    print("=== 시간대 계산 디버깅 ===")
    
    current_time = timezone.now()
    print(f"현재 시간 (Django timezone.now()): {current_time}")
    print(f"현재 시간 timezone: {current_time.tzinfo}")
    
    kst = pytz.timezone('Asia/Seoul')
    current_kst = current_time.astimezone(kst)
    print(f"현재 시간 (KST): {current_kst}")
    
    endpoints = Endpoint.objects.filter(is_enabled=True).first()
    if endpoints:
        latest_check = endpoints.checks.first()
        if latest_check:
            print(f"\n--- 체크 시간 분석 ---")
            print(f"저장된 체크 시간: {latest_check.checked_at}")
            print(f"저장된 체크 시간 timezone: {latest_check.checked_at.tzinfo}")
            
            # 방법 1: 현재 로직
            stored_time_utc = latest_check.checked_at.replace(tzinfo=None)
            kst_time = kst.localize(stored_time_utc)
            actual_utc_time = kst_time.astimezone(pytz.UTC)
            print(f"KST로 해석 후 UTC 변환: {actual_utc_time}")
            
            # 방법 2: 단순 9시간 빼기
            simple_utc = latest_check.checked_at - timedelta(hours=9)
            print(f"단순히 9시간 뺀 결과: {simple_utc}")
            
            # 방법 3: 직접 시간차 계산
            time_diff = current_time - actual_utc_time
            print(f"시간 차이 (방법1): {time_diff.total_seconds()}초")
            
            time_diff2 = current_time - simple_utc
            print(f"시간 차이 (방법2): {time_diff2.total_seconds()}초")
            
            # 폴링 간격과 비교
            print(f"폴링 간격: {endpoints.poll_interval_sec}초")
            print(f"예상 다음 체크 (방법1): {actual_utc_time + timedelta(seconds=endpoints.poll_interval_sec)}")
            print(f"예상 다음 체크 (방법2): {simple_utc + timedelta(seconds=endpoints.poll_interval_sec)}")
            
            # 상태 판정
            if current_time > actual_utc_time + timedelta(seconds=endpoints.poll_interval_sec):
                print("상태 (방법1): AMBER")
            else:
                print("상태 (방법1): GREEN")
                
            if current_time > simple_utc + timedelta(seconds=endpoints.poll_interval_sec):
                print("상태 (방법2): AMBER") 
            else:
                print("상태 (방법2): GREEN")

if __name__ == "__main__":
    test_timezone_calculation()
